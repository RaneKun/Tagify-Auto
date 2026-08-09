# 🖼️ Tagify (Auto Edition) — Screenshots

Drop each script's screenshot/GIF in place of the placeholder image link below its heading. Keep the captions or swap in your own.

## 🎛️ run_tagger.py
![run_tagger placeholder](./screenshots/run_tagger.png)
The orchestrator in action — running all six stages back-to-back with live per-file progress and a final summary banner.

## ⚙️ setup_venvs.bat
![setup_venvs placeholder](./screenshots/setup_venvs.png)
One-pass conda environment builder — sets up all six per-stage environments and skips anything already installed.

## 🎧 bpm_mood_tagger.py
![bpm_mood_tagger placeholder](./screenshots/bpm_mood_tagger.png)
Cross-validates BPM with aubio + librosa and assigns a mood tag from 23 prototypes normalized against your library.

## 🌐 online_genre_tagger.py
![online_genre_tagger placeholder](./screenshots/online_genre_tagger.png)
Queries Last.fm, iTunes, and MusicBrainz, merges and scores their tags into up to 3 genres.

## 🎼 local_genre_tagger.py
![local_genre_tagger placeholder](./screenshots/local_genre_tagger.png)
Offline fallback pass using MusicNN — rechecks anything the online tagger couldn't find a genre for.

## 🌐📝 online_lyrics_tagger.py
![online_lyrics_tagger placeholder](./screenshots/online_lyrics_tagger.png)
Pulls plain lyrics from LRCLib, NetEase, and Musixmatch, stripped of timestamps and metadata lines.

## 📝 local_lyrics_tagger.py
![local_lyrics_tagger placeholder](./screenshots/local_lyrics_tagger.png)
Offline fallback pass — transcribes lyrics locally via Demucs → DeepFilterNet3 → Faster-Whisper for anything still missing lyrics.

## 🟢 spotify_tagger.py
![spotify_tagger placeholder](./screenshots/spotify_tagger.png)
Final pass — fetches title, artist, album, release year, and embedded album art, then moves the finished file into `output/`.
