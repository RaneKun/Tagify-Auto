# 🎛️ Tagify (Auto Edition)

![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

A one-click pipeline that runs all six Tagify taggers back-to-back against your `.ogg` music library — BPM/mood, genre (online + offline), lyrics (online + offline), and Spotify metadata — so you don't have to launch each module by hand.

> This is the **Auto Edition** — a single orchestrator script (`run_tagger.py`) chains all six taggers together and moves each file through the full pipeline automatically. Prefer running modules one at a time yourself? Check out [Tagify (Manual Edition)](https://github.com/RaneKun/Tagify), the standalone version each of these scripts is built from.

## ✨ How It's Different From the Manual Edition

- **One config file** — a single `config.json` at the repo root holds your source folder and all API credentials, instead of setting each script up interactively.
- **One command to run everything** — `run_tagger.py` runs all six stages in the correct order, in each stage's own conda environment, without you switching environments by hand.
- **Automatic folder routing** — files flow through `temporary_output/` as they pick up tags, land in `failed/<type>/` if a stage can't fully tag them, and land in `output/` once the full pipeline is done.
- **Resumable by design** — every stage checkpoints its own progress, so stopping mid-run (or hitting a real error) and re-running `run_tagger.py` picks up exactly where it left off, skipping anything already tagged.

## 🧩 Pipeline Stages

Runs in this exact order:

1. **🎧 BPM + Mood Tagger** — cross-validates BPM with aubio + librosa, then assigns one of 23 mood prototypes normalized against your whole library. Fully offline.
2. **🌐 Online Genre Tagger** — queries Last.fm, iTunes, and MusicBrainz, merges and scores results, writes up to 3 genres.
3. **🎼 Local Genre Tagger** — rechecks anything still missing a genre using MusicNN, fully offline.
4. **🌐📝 Online Lyrics Tagger** — pulls plain lyrics from LRCLib, NetEase, and Musixmatch.
5. **📝 Local Lyrics Tagger** — rechecks anything flagged instrumental or still missing lyrics using a local Demucs → DeepFilterNet3 → Faster-Whisper pipeline.
6. **🟢 Spotify Tagger** — final pass; fetches title, artist, album, release year, and embedded album art, then moves the finished file into `output/`.

Soft misses (no genre found, confirmed instrumental, no lyrics, no Spotify match) don't stop the run — the file is logged under `failed/<type>/` and keeps moving through the remaining stages. A real error (network down, corrupt file, unexpected exception) halts the whole run immediately so you can look into it; re-running `run_tagger.py` afterward automatically skips everything already tagged.

## 📋 Requirements

- Python 3.10 **and** 3.11 (different stages use different versions — `setup_venvs.bat` handles this per stage)
- [Miniconda or Anaconda](https://docs.conda.io/en/latest/miniconda.html) on PATH — every stage runs in its own isolated conda environment, launched directly by `run_tagger.py`
- System-wide [ffmpeg](https://www.gyan.dev/ffmpeg/builds/) on PATH (required by the offline Genre and Lyrics stages)
- An NVIDIA GPU + driver (optional but strongly recommended for the offline Genre and Lyrics stages — both fall back to CPU automatically)
- A free [Spotify Developer](https://developer.spotify.com/) client ID/secret
- A free [Last.fm](https://www.last.fm/api/account/create) API key
- No MusicBrainz key needed — it just asks every app to identify itself (app name is enough; contact email is optional)

## 🎯 How It Works

### 1. Fill in `config.json`
Open `config.json` at the repo root and set:
- `source_music_directory` — the folder of `.ogg` files to tag (read-only; never written to)
- `spotify.client_id` / `spotify.client_secret`
- `lastfm.api_key`
- `musicbrainz.app_name` (and optionally `contact`)

### 2. Run the setup script
Double-click `setup_venvs.bat`. It builds one conda environment per stage inside `venvs/`, skipping any that are already set up. This can take a while — the offline stages pull in TensorFlow or PyTorch with CUDA support.

### 3. Run the pipeline
Double-click `run_tagger.py` (or run `python run_tagger.py`). It will:
- Print a config summary and mask your API credentials in the console
- Confirm every stage's conda environment is actually set up
- Validate every file in your source folder is a real, non-corrupt `.ogg` file before touching anything
- Run all six stages in order, printing each stage's live output as it goes
- Print a final summary — how many files landed in `output/`, and how many were cataloged as missing a genre, instrumental, missing lyrics, no Spotify match, or badly named

### 4. Review and clean up
Once all six stages finish, you'll be asked whether to review `failed/` and `temporary_output/` before Tagify deletes them. `logs/` is never touched — checkpoints and stats are always preserved so you can re-run safely.

## ⚙️ Configuration

Everything shared across stages (source folder, API credentials) lives in `config.json`:

```json
{
  "source_music_directory": "C:\\Users\\<user_name>\\OneDrive\\Desktop\\Spytify",
  "spotify": { "client_id": "<your_client_id>", "client_secret": "<your_client_secret>" },
  "lastfm": { "api_key": "<your_api_key>" },
  "musicbrainz": { "app_name": "<anyappname>", "app_version": "1.0", "contact": "not-provided@example.com" }
}
```

Everything else (genre count, mood prototypes, Whisper/Demucs thresholds, Spotify's daily call budget) still lives inside each script under `scripts/`, for example:

```python
# online_genre_tagger.py / local_genre_tagger.py
TOP_N_GENRES = 3        # max genre tags written per track
```

```python
# spotify_tagger.py
DAILY_CALL_LIMIT = 700  # soft warning limit, not a hard stop
```

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| **`run_tagger.py` says a conda environment is missing** | Run `setup_venvs.bat` first, then try again |
| **`run_tagger.py` says conda not found** | Open an Anaconda/Miniconda prompt (or add conda to PATH), then try again |
| **Corrupt/unreadable `.ogg` file(s) found during validation** | Fix or remove the listed files, then run `run_tagger.py` again — the whole run halts before any tagging starts if this happens |
| **A stage exits with an error partway through** | `run_tagger.py` halts immediately — check the error above and `logs/run_tagger.log`, then re-run once it's fixed; already-tagged files are skipped automatically |
| **Offline Genre/Lyrics stage fails at runtime** | Make sure system-wide `ffmpeg` is on PATH — these two stages use the system copy, not a conda-installed one |
| **Files piling up in `failed/`** | These are soft misses (no genre/lyrics/match found), not errors — the file still made it through the rest of the pipeline |
| **Want to re-tag everything from scratch** | Delete the relevant checkpoint JSON in `logs/` for that stage |

## 🆚 Auto Edition vs. Manual Edition

| Feature | Auto Edition | Manual Edition |
|---------|--------------|-----------------|
| **Running modules** | One command runs all six stages in order | Each module launched by hand, one at a time |
| **Configuration** | Single shared `config.json` at repo root | Interactive prompts saved per-script to `configs/` |
| **Folder handling** | Automatic — `temporary_output/` → `failed/<type>/` or `output/` | Each script asks for its own input/output folder |
| **Best for** | Tagging a large library end-to-end, unattended | Running just one or two taggers, or full manual control |

## 📝 Notes

- Your source folder is only ever **read**, never written — nothing in `source_music_directory` is modified by any stage.
- `run_tagger.py` calls each stage's conda `python.exe` directly rather than through `conda run`, since `conda run` is known to reset the terminal mid-output on Windows.
- Every stage logs everything (DEBUG level) to its own file under `logs/`, even when the console only shows a summary.
- For a deeper technical breakdown of each individual tagger, see the [Manual Edition's Technical Guide](https://github.com/RaneKun/Tagify/blob/main/TECHNICAL_GUIDE.md) — every stage here is the same script, just orchestrated automatically.

## 🙏 Credits

Made with ♥ by Rane Kun
