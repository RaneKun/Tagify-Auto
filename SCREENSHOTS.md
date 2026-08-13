# 🖼️ Tagify (Auto Edition) — Screenshots

## 📂 Project Stucture
```
Tagify/
├── failed/
│   ├── instrumental/
│   │   ├── Geoxor - Aurora.ogg
│   │   └── N!GHT - Yume.ogg
│   ├── no_genre/
│   └── no_lyrics/
├── logs/
│   ├── bpm_mood.log
│   ├── bpm_mood_checkpoint.json
│   ├── feature_stats.json
│   ├── genre__offline.log
│   ├── genre_offline_checkpoint.json
│   ├── genre_online.log
│   ├── genre_online_artist_cache.json
│   ├── genre_online_checkpoint.json
│   ├── lyrics_offline.log
│   ├── lyrics_offline_checkpoint.json
│   └── ...
├── output/
│   ├── 2 Man Embassy - The End.ogg
│   ├── BellyJay - MONTAGEM HASHIRU.ogg
│   ├── Geoxor - Aurora.ogg
│   ├── Leat'eq - Tokyo - Bubblegum.ogg
│   ├── N!GHT - Yume.ogg
│   ├── NEFFEX - Rumors.ogg
│   └── The Chainsmokers - Closer.ogg
├── scripts/
│   ├── bpm_mood_tagger.py
│   ├── local_genre_tagger.py
│   ├── local_lyrics_tagger.py
│   ├── online_genre_tagger.py
│   ├── online_lyrics_tagger.py
│   └── spotify_tagger.py
├── temporary_output/
│   ├── 2 Man Embassy - The End.ogg
│   ├── BellyJay - MONTAGEM HASHIRU.ogg
│   ├── Geoxor - Aurora.ogg
│   ├── Leat'eq - Tokyo - Bubblegum.ogg
│   ├── N!GHT - Yume.ogg
│   ├── NEFFEX - Rumors.ogg
│   └── The Chainsmokers - Closer.ogg
├── venvs/
│   ├── bpm_mood_tagger/
│   ├── local_genre_tagger/
│   ├── local_lyrics_tagger/
│   ├── online_genre_tagger/
│   ├── online_lyrics_tagger/
│   └── spotify_tagger/
├── config.json
├── run_tagger.py
└── setup_venvs.bat
```

## ⚙️ Setup
One-pass conda environment builder — sets up all six per-stage environments in one go.

<img width="965" height="1233" alt="Screenshot 2026-08-05 105800" src="https://github.com/user-attachments/assets/a12b9125-8990-446e-b141-e737feb46116" />

## 🎛️ Run Tagger
The orchestrator in action — and a final summary banner.

<img width="1147" height="443" alt="Screenshot 2026-08-09 221102" src="https://github.com/user-attachments/assets/a72f78f5-b4f1-42d6-bdce-6895d6461438" />

<img width="1034" height="464" alt="Screenshot 2026-08-09 222019" src="https://github.com/user-attachments/assets/5bb0eb54-f2c8-4f37-a3d9-5edc4fb2e3b5" />

## 🎧 BPM Mood Tagger
Cross-validates BPM with aubio + librosa and assigns a mood tag from 23 prototypes normalized against your library.

<img width="1209" height="1009" alt="Screenshot 2026-08-09 221314" src="https://github.com/user-attachments/assets/b3546b87-a77d-4191-9c30-5408f65bcfe9" />

## 🌐 Online Genre Tagger
Queries Last.fm, iTunes, and MusicBrainz, merges and scores their tags into up to 3 genres.

<img width="864" height="1349" alt="Screenshot 2026-08-05 174216" src="https://github.com/user-attachments/assets/8ba62c13-b5f7-4ff6-bf86-d9118bf6bfaf" />

## 🎼 Local Genre Tagger
Offline fallback pass using MusicNN — rechecks anything the online tagger couldn't find a genre for.

<img width="853" height="802" alt="Screenshot 2026-08-05 174228" src="https://github.com/user-attachments/assets/89e26506-5780-4d43-9dca-647cc489cf11" />

## 🌐📝 Online Lyrics Tagger
Pulls plain lyrics from LRCLib, NetEase, and Musixmatch, stripped of timestamps and metadata lines.

<img width="1177" height="834" alt="Screenshot 2026-08-05 174512" src="https://github.com/user-attachments/assets/c8fcc2ac-9803-4ce9-a3a4-5d1788799538" />

## 📝 Local Lyrics Tagger
Offline fallback pass — transcribes lyrics locally via Demucs → DeepFilterNet3 → Faster-Whisper for anything still missing lyrics.

<img width="1476" height="957" alt="Screenshot 2026-08-05 174520" src="https://github.com/user-attachments/assets/b583a31a-4f45-4f56-a1ab-a3093553222f" />

## 🟢 Spotify Tagger
Final pass — fetches title, artist, album, release year, and embedded album art, then moves the finished file into `output/`.

<img width="1269" height="958" alt="Screenshot 2026-08-09 222005" src="https://github.com/user-attachments/assets/05bb8243-be03-442b-b2ac-4f7ab3d42c6b" />
