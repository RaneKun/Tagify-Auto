"""
run_tagger.py — one-click orchestrator for the Tagify pipeline.

Runs, in this exact order, each inside its OWN conda environment
(see setup_venvs.bat):

  1. bpm_mood_tagger.py       source_music_directory  →  temporary_output/
  2. online_genre_tagger.py   temporary_output/, tagged in place
  3. local_genre_tagger.py    rechecks failed/no_genre/
  4. online_lyrics_tagger.py  temporary_output/, tagged in place
  5. local_lyrics_tagger.py   rechecks failed/instrumental/ + failed/no_lyrics/
  6. spotify_tagger.py        temporary_output/  →  output/  (final pass)

The true source folder (from config.json) is only ever read, never written.
Soft misses (no genre / instrumental / no lyrics / no Spotify match) are
logged to failed/<type>/ and the song keeps moving through the rest of the
pipeline. A REAL error (network down, corrupt file, unexpected exception)
halts the whole run immediately for manual review — re-running run_tagger
afterwards automatically skips everything already tagged.
"""

import os
import re
import sys
import json
import shutil
import textwrap
import subprocess
import unicodedata
import logging
from datetime import datetime
from pathlib import Path

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  LOOK & FEEL  ─  same palette/box style as the six tagger scripts        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
BLUE    = "\033[94m"
CYAN    = "\033[96m"
MAGENTA = "\033[95m"
WHITE   = "\033[97m"
DIM     = "\033[2m"
BOLD    = "\033[1m"
RESET   = "\033[0m"

THEME        = WHITE   # run_tagger's own signature color — the "conductor"
SCRIPT_EMOJI = "🎛️"

def c_green(text):   return f"{GREEN}{text}{RESET}"
def c_yellow(text):  return f"{YELLOW}{text}{RESET}"
def c_red(text):     return f"{RED}{text}{RESET}"
def c_blue(text):    return f"{BLUE}{text}{RESET}"
def c_cyan(text):    return f"{CYAN}{text}{RESET}"
def c_magenta(text): return f"{MAGENTA}{text}{RESET}"
def c_theme(text):   return f"{THEME}{text}{RESET}"
def c_dim(text):     return f"{DIM}{text}{RESET}"
def c_bold(text):    return f"{BOLD}{text}{RESET}"

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")

# Codepoints that are TEXT-presentation by default and only render as emoji
# because of a trailing VS16 (U+FE0F) — e.g. 🎛️, ⚠️, ✈️, ☁️. Most Windows
# terminal fonts still only allocate 1 column for these (unlike natively
# double-width emoji like 🎧/🌐/📝), so they need a width override or the
# banner's right border drifts left by one char on that line.
_NARROW_DESPITE_VS16 = {0x1F39B}  # 🎛 control knobs (run_tagger's own icon)

def _visible_width(text: str) -> int:
    """Approximate on-screen column width of a string, ignoring ANSI codes
    (same emoji-aware logic as the six tagger scripts, so boxes line up)."""
    text = _ANSI_RE.sub("", text)
    chars = list(text)
    n = len(chars)
    width = 0
    i = 0
    while i < n:
        ch = chars[i]
        cp = ord(ch)
        if cp == 0x200D:
            i += 1
            continue
        if cp == 0xFE0F:
            i += 1
            continue
        if unicodedata.combining(ch):
            i += 1
            continue
        next_is_vs16 = (i + 1 < n) and ord(chars[i + 1]) == 0xFE0F
        if next_is_vs16 and cp in _NARROW_DESPITE_VS16:
            width += 1
            i += 2
            continue
        if (0x1F300 <= cp <= 0x1FAFF) or (0x1F1E6 <= cp <= 0x1F1FF):
            width += 2
            i += 2 if next_is_vs16 else 1
            continue
        if next_is_vs16:
            width += 2
            i += 2
            continue
        width += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        i += 1
    return width

# ── Helper to split ANSI codes from text ──────────────────────────────
def _split_ansi_codes(text: str):
    """Return (clean_text, list_of_ansi_sequences_in_order)."""
    ansi_re = re.compile(r'\033\[[0-9;]*[a-zA-Z]')
    parts = []
    last_end = 0
    for m in ansi_re.finditer(text):
        start, end = m.span()
        if start > last_end:
            parts.append(('text', text[last_end:start]))
        parts.append(('ansi', m.group()))
        last_end = end
    if last_end < len(text):
        parts.append(('text', text[last_end:]))
    return parts

def _wrap_line_with_ansi(line: str, max_width: int) -> list[str]:
    """
    Wrap a single line into multiple lines that each fit within max_width,
    preserving ANSI color codes and re‑applying them to each wrapped line.
    """
    parts = _split_ansi_codes(line)
    clean_text = ''.join(p[1] for p in parts if p[0] == 'text')
    if not clean_text:
        return [line]

    # Collect all ANSI codes that appear before any text (leading prefix)
    leading_ansi = []
    for part in parts:
        if part[0] == 'ansi':
            leading_ansi.append(part[1])
        else:
            break
    prefix = ''.join(leading_ansi)

    wrapped_texts = textwrap.wrap(clean_text, width=max_width, break_long_words=True)
    if not wrapped_texts:
        return [line]
    # Prepend the prefix to each wrapped line
    return [prefix + w for w in wrapped_texts]

# ── Dynamic banner function ──
def banner(lines: list[str], color_fn=None) -> None:
    """Print a boxed banner that wraps long lines, fitting terminal width."""
    color_fn = color_fn or c_theme

    try:
        term_width = shutil.get_terminal_size().columns
    except Exception:
        term_width = 80
    box_width = min(term_width - 2, 100)
    box_width = max(box_width, 40)
    inner_width = box_width - 2

    print(f"\n{color_fn('╔' + '═'*box_width + '╗')}")
    for line in lines:
        wrapped = _wrap_line_with_ansi(line, inner_width)
        for wline in wrapped:
            visible_len = _visible_width(wline)
            pad = max(inner_width - visible_len, 0)
            print(f"{color_fn('║')} {wline}{' '*pad} {color_fn('║')}")
    print(f"{color_fn('╚' + '═'*box_width + '╝')}")

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  DIRECTORY & LOGGING SETUP                                               ║
# ╚══════════════════════════════════════════════════════════════════════════╝

BASE_DIR        = Path(__file__).parent.resolve()
SCRIPTS_DIR     = BASE_DIR / "scripts"
VENVS_DIR       = BASE_DIR / "venvs"
LOGS_DIR        = BASE_DIR / "logs"
FAILED_DIR      = BASE_DIR / "failed"
TEMP_OUTPUT_DIR = BASE_DIR / "temporary_output"
OUTPUT_DIR      = BASE_DIR / "output"
CONFIG_FILE     = BASE_DIR / "config.json"

for _d in (LOGS_DIR, FAILED_DIR, TEMP_OUTPUT_DIR, OUTPUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS_DIR / "run_tagger.log"


class ImmediateFileHandler(logging.FileHandler):
    """A FileHandler that flushes after every single record — crash-safe logs."""
    def emit(self, record):
        super().emit(record)
        self.flush()


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s │ %(levelname)-8s │ %(funcName)-22s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[ImmediateFileHandler(LOG_FILE, mode='w', encoding="utf-8")],
)
logger = logging.getLogger(__name__)

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  PIPELINE ORDER  ─  matches setup_venvs.bat's env names exactly          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

STAGES = [
    {"script": "bpm_mood_tagger.py",      "venv": "bpm_mood_tagger",      "name": "BPM + Mood Tagger",    "emoji": "🎧",   "color": c_yellow},
    {"script": "online_genre_tagger.py",  "venv": "online_genre_tagger",  "name": "Online Genre Tagger",  "emoji": "🌐",   "color": c_blue},
    {"script": "local_genre_tagger.py",   "venv": "local_genre_tagger",   "name": "Local Genre Tagger",   "emoji": "🎼",   "color": c_cyan},
    {"script": "online_lyrics_tagger.py", "venv": "online_lyrics_tagger", "name": "Online Lyrics Tagger", "emoji": "🌐📝", "color": c_magenta},
    {"script": "local_lyrics_tagger.py",  "venv": "local_lyrics_tagger",  "name": "Local Lyrics Tagger",  "emoji": "📝",   "color": c_magenta},
    {"script": "spotify_tagger.py",       "venv": "spotify_tagger",       "name": "Spotify Tagger",       "emoji": "🟢",   "color": c_green},
]

_CONDA_EXE = shutil.which("conda")


# ──────────────────────────────────────────────────────────────────────────────
#  CONFIG + ENVIRONMENT
# ──────────────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        sys.exit(f"[!] config.json not found at {CONFIG_FILE}\n    Create it before running run_tagger.")
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        sys.exit(f"[!] config.json is not valid JSON: {exc}")

    src = str(cfg.get("source_music_directory", "")).strip()
    if not src:
        sys.exit("[!] config.json is missing \"source_music_directory\" — edit config.json and set it.")
    if not os.path.isdir(src):
        sys.exit(f"[!] source_music_directory does not exist:\n    {src}")
    return cfg


def _mask(value: str) -> str:
    if not value:
        return c_red("(not set)")
    if len(value) <= 8:
        return c_dim("*" * len(value))
    return c_dim(value[:4] + "…" + value[-4:])


def check_environments() -> None:
    """Make sure setup_venvs.bat has actually been run for every stage —
    fail clearly here rather than partway through stage 1."""
    if _CONDA_EXE is None:
        print(f"\n{c_red('✗ conda not found on PATH.')}")
        print(f"  {c_dim('Open an Anaconda/Miniconda prompt (or add conda to PATH), then try again.')}")
        logger.critical("conda not found on PATH")
        sys.exit(1)

    missing = [s["venv"] for s in STAGES if not (VENVS_DIR / s["venv"] / ".setup_ok").exists()]
    if missing:
        print(f"\n{c_red('✗ Missing conda environment(s):')} {', '.join(missing)}")
        print(f"  {c_dim('Run setup_venvs.bat first, then try run_tagger again.')}")
        logger.critical(f"Missing conda environments: {missing}")
        sys.exit(1)


# ──────────────────────────────────────────────────────────────────────────────
#  INPUT VALIDATION  (requirement: thorough check before anything else runs)
# ──────────────────────────────────────────────────────────────────────────────

def validate_input_directory(source_dir: str) -> int:
    """
    Thorough pre-flight check of the source music folder:
      - flags any non-.ogg files / subfolders sitting in it (warning only)
      - opens every .ogg file with mutagen to confirm it's valid, non-corrupt
        Ogg Vorbis (HALTS if any are broken — better to know now than to find
        out 400 files deep into bpm_mood_tagger)
      - warns (doesn't block) about filenames that don't look like "Artist - Title"
    Returns the number of valid .ogg files found.
    """
    print(f"\n{c_theme('◆ Checking input folder...')}")

    entries    = sorted(os.listdir(source_dir))
    ogg_files  = [f for f in entries if f.lower().endswith(".ogg") and os.path.isfile(os.path.join(source_dir, f))]
    other_files = [f for f in entries if os.path.isfile(os.path.join(source_dir, f)) and not f.lower().endswith(".ogg")]
    sub_dirs   = [f for f in entries if os.path.isdir(os.path.join(source_dir, f))]

    if not ogg_files:
        sys.exit(f"[!] No .ogg files found in:\n    {source_dir}")

    if other_files:
        print(f"  {c_yellow('⚠')} {len(other_files)} non-.ogg file(s) found — these will just be ignored:")
        for f in other_files[:10]:
            print(f"      {c_dim(f)}")
        if len(other_files) > 10:
            print(f"      {c_dim(f'... and {len(other_files) - 10} more')}")

    if sub_dirs:
        print(f"  {c_yellow('⚠')} {len(sub_dirs)} subfolder(s) found — Tagify only scans the top level, these are ignored:")
        for d in sub_dirs[:10]:
            print(f"      {c_dim(d)}")

    try:
        from mutagen.oggvorbis import OggVorbis
        have_mutagen = True
    except ImportError:
        have_mutagen = False
        print(f"  {c_yellow('⚠')} mutagen isn't installed in THIS environment — skipping deep file validation (extension check only).")
        logger.warning("mutagen not available to run_tagger — deep validation skipped")

    bad_files, bad_names = [], []
    for f in ogg_files:
        full = os.path.join(source_dir, f)
        if have_mutagen:
            try:
                OggVorbis(full)
            except Exception as exc:
                bad_files.append((f, str(exc)))
        if " - " not in f:
            bad_names.append(f)

    if bad_files:
        print(f"\n{c_red(f'✗ {len(bad_files)} corrupt/unreadable .ogg file(s) found:')}")
        for f, err in bad_files[:15]:
            print(f"    {c_red('•')} {f}  {c_dim('(' + err + ')')}")
        if len(bad_files) > 15:
            print(f"    {c_dim(f'... and {len(bad_files) - 15} more — see logs/run_tagger.log for the full list')}")
        logger.critical(f"Corrupt input files: {bad_files}")
        print(f"\n{c_dim('Fix or remove these files, then run run_tagger again.')}")
        sys.exit(1)

    if bad_names:
        msg = 'don’t look like "Artist - Title.ogg" — they may not get full metadata/Spotify matches:'
        print(f"\n  {c_yellow(f'⚠ {len(bad_names)} file(s)')} {c_dim(msg)}")
        for f in bad_names[:10]:
            print(f"      {c_dim(f)}")
        if len(bad_names) > 10:
            print(f"      {c_dim(f'... and {len(bad_names) - 10} more')}")

    print(f"  {c_green('✓')} {len(ogg_files)} valid .ogg file(s) ready to process.")
    logger.debug(
        f"Input validation OK: {len(ogg_files)} valid, {len(bad_files)} corrupt, "
        f"{len(bad_names)} oddly-named, {len(other_files)} non-ogg ignored, {len(sub_dirs)} subfolders ignored"
    )
    return len(ogg_files)


# ──────────────────────────────────────────────────────────────────────────────
#  STAGE EXECUTION
# ──────────────────────────────────────────────────────────────────────────────

def run_stage(stage: dict, index: int, total: int) -> None:
    color       = stage["color"]
    script_path = SCRIPTS_DIR / stage["script"]
    env_path    = VENVS_DIR / stage["venv"]
    python_exe  = env_path / "python.exe"

    banner([f"{c_bold(stage['emoji'] + '  Stage ' + str(index) + '/' + str(total) + ': ' + stage['name'])}"], color_fn=color)

    if not script_path.exists():
        print(f"{c_red('✗ missing script:')} {script_path}")
        logger.critical(f"Missing script: {script_path}")
        sys.exit(1)

    if not python_exe.exists():
        print(f"{c_red('✗ missing interpreter:')} {python_exe}")
        print(f"  {c_dim('Run setup_venvs.bat first, then try run_tagger again.')}")
        logger.critical(f"Missing interpreter: {python_exe}")
        sys.exit(1)

    # We call the env's python.exe DIRECTLY rather than through `conda run`.
    # `conda run` on Windows routes the child through an extra cmd.exe/conda.bat
    # layer that is documented to reset/clear the terminal before the wrapped
    # command's output starts (conda/conda#9700). Calling python.exe directly
    # skips that layer, so live output stays intact.
    #
    # To keep DLL-backed packages (librosa, numpy, aubio, etc.) resolving
    # their shared libraries correctly, we manually prepend the same
    # directories `conda activate` would add to PATH.
    # `-u` + PYTHONUNBUFFERED force the CHILD python process to flush every
    # print() immediately. Without this, Python fully buffers stdout the
    # moment it isn't a real terminal (true here, since stdout is piped back
    # into run_tagger) — so none of the per-file progress each script
    # normally prints would show up until a buffer filled or the script exited.
    conda_path_dirs = [
        str(env_path),
        str(env_path / "Library" / "mingw-w64" / "bin"),
        str(env_path / "Library" / "usr" / "bin"),
        str(env_path / "Library" / "bin"),
        str(env_path / "Scripts"),
        str(env_path / "bin"),
    ]

    child_env = os.environ.copy()
    child_env["PYTHONUNBUFFERED"] = "1"
    # `conda run` was implicitly forcing UTF-8 stdio on the child; calling
    # python.exe directly does not, so it falls back to the system codepage
    # (e.g. cp932), which chokes on em dashes/emoji the scripts print.
    # PYTHONUTF8 forces UTF-8 mode everywhere; PYTHONIOENCODING backs it up
    # for older Python behavior/edge cases.
    child_env["PYTHONUTF8"] = "1"
    child_env["PYTHONIOENCODING"] = "utf-8"
    child_env["CONDA_PREFIX"] = str(env_path)
    child_env["PATH"] = os.pathsep.join(conda_path_dirs + [child_env.get("PATH", "")])

    logger.debug(f"Launching stage {index}/{total}: {python_exe} -u {script_path}")

    start = datetime.now()
    proc = subprocess.Popen(
        [str(python_exe), "-u", str(script_path)],
        cwd=str(SCRIPTS_DIR), env=child_env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, encoding="utf-8", errors="replace",
    )

    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        logger.debug(f"[{stage['script']}] {line.rstrip()}")

    proc.wait()
    elapsed = (datetime.now() - start).total_seconds()

    if proc.returncode != 0:
        print(f"\n{c_red('✗ ' + stage['name'] + ' stopped with an error')} {c_dim(f'(exit code {proc.returncode}, after {elapsed:.0f}s)')}")
        print(f"  {c_dim('run_tagger is halting here — fix the issue above, then run run_tagger again.')}")
        print(f"  {c_dim('Already-tagged files are skipped automatically on the next run.')}")
        logger.critical(f"Stage {stage['script']} exited with code {proc.returncode} after {elapsed:.0f}s — HALTING run_tagger")
        sys.exit(1)

    print(f"\n{c_green('✓ ' + stage['name'] + ' complete')} {c_dim(f'({elapsed:.0f}s)')}")
    logger.debug(f"Stage {stage['script']} completed OK in {elapsed:.0f}s")


def _count_ogg(dir_path: Path) -> int:
    if not dir_path.exists():
        return 0
    return len([f for f in os.listdir(dir_path) if f.lower().endswith(".ogg")])


# ──────────────────────────────────────────────────────────────────────────────
#  POST-RUN CLEANUP  (asked after all 6 stages finish)
# ──────────────────────────────────────────────────────────────────────────────

def cleanup_after_run() -> None:
    """
    Ask the user to review failed/ and temporary_output/ (logs/ is never
    touched — everything in there is kept as-is). If they confirm with Y,
    delete temporary_output/ and failed/ entirely.
    """
    banner([
        f"{c_bold('◆ Cleanup')}",
        f"Please review {c_theme('failed/')} and {c_theme('temporary_output/')} now.",
        f"Once you're done, confirm below to delete {c_theme('temporary_output/')} and {c_theme('failed/')}.",
        f"({c_theme('logs/')} .log files will be refreshed in the next run, but the checkpoints and stats will be preserved.)",
    ], color_fn=c_yellow)

    while True:
        try:
            answer = input(f"\n  {c_bold('Delete these now?')} {c_dim('[Y/N]:')} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{c_yellow('Cleanup skipped.')}")
            logger.info("Post-run cleanup skipped (no input / interrupted)")
            return

        if answer in ("y", "n"):
            break
        print(f"  {c_red('Please enter Y or N.')}")

    if answer == "n":
        print(f"  {c_dim('Skipped — nothing was deleted.')}")
        logger.info("Post-run cleanup declined by user")
        return

    logger.debug("Post-run cleanup confirmed by user — starting")

    for dir_path in (TEMP_OUTPUT_DIR, FAILED_DIR):
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path)
                print(f"  {c_green('✓')} deleted {c_theme(str(dir_path.relative_to(BASE_DIR)))}/")
                logger.debug(f"Deleted directory: {dir_path}")
            except Exception as exc:
                print(f"  {c_red('✗')} could not delete {dir_path}: {exc}")
                logger.warning(f"Failed to delete directory {dir_path}: {exc}")


# ──────────────────────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    logger.debug("═" * 72)
    logger.debug("run_tagger session starting")

    banner([
        f"{c_bold(SCRIPT_EMOJI + '  Tagify — run_tagger')}",
        f"bpm/mood → genre (online + local)",
        f"→ lyrics (online + local) → spotify",
    ])

    cfg = load_config()
    source_dir = str(cfg.get("source_music_directory", "")).strip()

    print(f"\n{c_theme('◆ Config summary')}")
    print(f"  Source folder : {source_dir}")
    print(f"  Spotify       : {_mask(cfg.get('spotify', {}).get('client_id', ''))}")
    print(f"  Last.fm       : {_mask(cfg.get('lastfm', {}).get('api_key', ''))}")
    print(f"  MusicBrainz   : {cfg.get('musicbrainz', {}).get('contact', '(not set)')}")

    check_environments()
    n_files = validate_input_directory(source_dir)

    banner([f"{c_bold('Ready')}  {c_dim(f'· {n_files} source file(s) · 6 stages')}"])

    start_all = datetime.now()
    for i, stage in enumerate(STAGES, 1):
        run_stage(stage, i, len(STAGES))
    elapsed_all = (datetime.now() - start_all).total_seconds()
    mins, secs = divmod(int(elapsed_all), 60)

    out_count = _count_ogg(OUTPUT_DIR)
    cataloged = {
        "no_genre":     _count_ogg(FAILED_DIR / "no_genre"),
        "instrumental": _count_ogg(FAILED_DIR / "instrumental"),
        "no_lyrics":    _count_ogg(FAILED_DIR / "no_lyrics"),
        "no_match":     _count_ogg(FAILED_DIR / "no_match"),
        "bad_filename": _count_ogg(FAILED_DIR / "bad_filename"),
        "error":        _count_ogg(FAILED_DIR / "error"),
        "network_error": _count_ogg(FAILED_DIR / "network_error"),
    }

    banner([
        f"{c_bold('✓ All 6 stages complete')}",
        f"Total time       : {mins}m {secs}s",
        f"Files in output/ : {out_count}",
        f"— still missing a genre    : {cataloged['no_genre']}",
        f"— confirmed instrumental   : {cataloged['instrumental']}",
        f"— still missing lyrics     : {cataloged['no_lyrics']}",
        f"— no Spotify match         : {cataloged['no_match']}",
        f"— unparseable filename     : {cataloged['bad_filename']}",
    ], color_fn=c_green)

    cleanup_after_run()

    print(f"\n  {c_dim('all tagged and ready, happy listening (｡•̀ᴗ-)✧')}\n")
    logger.debug(f"run_tagger session complete in {elapsed_all:.0f}s. output={out_count} cataloged={cataloged}")
    logger.debug("═" * 72)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{c_yellow('Interrupted —')} the currently running stage may be left partway through.")
        logger.info("run_tagger interrupted by user")
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as exc:
        logger.critical(f"Fatal error in run_tagger: {exc}", exc_info=True)
        print(f"\n{c_red('FATAL:')} {exc}")
        sys.exit(1)