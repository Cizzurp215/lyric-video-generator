# Lyric Video Generator

Local FastAPI app that turns an audio track plus lyrics into MP4 lyric videos for YouTube and TikTok/Reels.

## Features

- Upload MP3 or WAV audio.
- Paste lyrics and optionally add a background image or looping video.
- Render `1920x1080`, `1080x1920`, or both.
- Burn animated ASS subtitles into the final MP4.
- Track render progress and download completed files from the browser.
- Use local Whisper when installed, with a duration-based fallback when it is not.

## Project Structure

```text
app/
  config.py
  jobs.py
  lyrics.py
  main.py
  models.py
  render.py
  subtitles.py
  transcription.py
renders/
static/
templates/
tests/
requirements.txt
README.md
```

## Requirements

- Python 3.11+
- FFmpeg installed and available on `PATH`
- Optional: local Whisper package for rough vocal timing

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Optional Whisper support:

```bash
pip install openai-whisper
```

## FFmpeg Install

1. Download FFmpeg and add the `bin` folder containing `ffmpeg.exe` and `ffprobe.exe` to `PATH`.
2. Confirm:

```bash
ffmpeg -version
ffprobe -version
```

## Run

```bash
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

If you prefer double-clicking instead of using a terminal, run [launch_lyric_video_generator.bat](C:\Users\C_Car\OneDrive\Documents\Codex%20Agents\launch_lyric_video_generator.bat).

## API

- `POST /upload`
- `POST /render`
- `GET /status/{job_id}`
- `GET /download/{job_id}/{format}`

## Sample Demo Flow

1. Start the server.
2. Upload `song.mp3` and paste lyrics.
3. Optionally add `cover.jpg` or `background.mp4`.
4. Render `Both`.
5. Download `youtube.mp4` and `tiktok.mp4`.

## Sample Test Assets Layout

```text
tests/assets/
  demo-song.mp3
  demo-background.jpg
  demo-lyrics.txt
```

## Troubleshooting

- `ffmpeg was not found`
  Install FFmpeg and make sure both `ffmpeg` and `ffprobe` are on `PATH`.
- `Local Whisper was not found`
  The app still renders using even lyric timing. Install `openai-whisper` for better timestamps.
- Render fails when using ASS subtitles on Windows
  Keep the project in a simple local path and avoid special characters in filenames.
- Audio uploads are rejected
  Use MP3 or WAV files only in this MVP.

## Notes

- The MVP favors reliability over exact karaoke timing.
- When Whisper is unavailable or sparse, lyric timing is estimated across the song duration and warnings are shown in the UI.
