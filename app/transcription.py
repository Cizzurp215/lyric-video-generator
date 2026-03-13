from __future__ import annotations

import importlib
import json
import shutil
import subprocess
from pathlib import Path


def get_media_duration(media_path: Path) -> float:
    ffprobe_path = shutil.which("ffprobe")
    if not ffprobe_path:
        raise RuntimeError("ffprobe is required to inspect media duration. Install FFmpeg first.")
    command = [
        ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(media_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    payload = json.loads(result.stdout)
    return float(payload["format"]["duration"])


def transcribe_audio(audio_path: Path) -> tuple[list[dict[str, float | str]], list[str]]:
    warnings: list[str] = []
    whisper_module = importlib.util.find_spec("whisper")
    if whisper_module is None:
        warnings.append("Local Whisper was not found. Falling back to duration-based lyric timing.")
        return [], warnings

    whisper = importlib.import_module("whisper")
    model = whisper.load_model("base")
    result = model.transcribe(str(audio_path), verbose=False)
    segments = [
        {
            "start": float(segment["start"]),
            "end": float(segment["end"]),
            "text": str(segment["text"]).strip(),
        }
        for segment in result.get("segments", [])
        if str(segment.get("text", "")).strip()
    ]
    if not segments:
        warnings.append("Whisper returned no segments. Falling back to duration-based lyric timing.")
    return segments, warnings
