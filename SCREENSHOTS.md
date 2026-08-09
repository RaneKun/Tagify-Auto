# 🖼️ Tagify (Auto Edition) — Screenshots

## 🎛️ Run Tagger
The orchestrator in action — and a final summary banner.

<img width="1147" height="443" alt="Screenshot 2026-08-09 221102" src="https://github.com/user-attachments/assets/a72f78f5-b4f1-42d6-bdce-6895d6461438" />

<img width="1039" height="421" alt="Screenshot 2026-08-09 221125" src="https://github.com/user-attachments/assets/73c9ee49-d2d2-447d-9760-f93fd191a1ca" />

## ⚙️ Setup
One-pass conda environment builder — sets up all six per-stage environments in one go.

<img width="965" height="1233" alt="Screenshot 2026-08-05 105800" src="https://github.com/user-attachments/assets/a12b9125-8990-446e-b141-e737feb46116" />

## 🎧 BPM Mood Tagger
Cross-validates BPM with aubio + librosa and assigns a mood tag from 23 prototypes normalized against your library.

<img width="1209" height="1058" alt="Screenshot 2026-08-09 221314" src="https://github.com/user-attachments/assets/3e3d0337-2838-4126-89aa-6c0578468179" />

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

<img width="1092" height="956" alt="Screenshot 2026-08-05 174541" src="https://github.com/user-attachments/assets/a156c8f3-c0f4-40b6-a9b5-928f09d3bfe8" />
