from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LyricLine:
    text: str
    start: float
    end: float


def normalize_lyrics(raw_lyrics: str) -> list[str]:
    cleaned_lines: list[str] = []
    for raw_line in raw_lyrics.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if line:
            cleaned_lines.append(line)
    return cleaned_lines


def load_lyrics(path: Path) -> list[str]:
    return normalize_lyrics(path.read_text(encoding="utf-8"))


def split_for_display(lines: list[str], max_chars: int = 42) -> list[str]:
    display_lines: list[str] = []
    for line in lines:
        if len(line) <= max_chars:
            display_lines.append(line)
            continue
        words = line.split(" ")
        current: list[str] = []
        current_len = 0
        for word in words:
            projected = current_len + len(word) + (1 if current else 0)
            if projected > max_chars and current:
                display_lines.append(" ".join(current))
                current = [word]
                current_len = len(word)
            else:
                current.append(word)
                current_len = projected
        if current:
            display_lines.append(" ".join(current))
    return display_lines


def align_lyrics(
    lyrics_lines: list[str],
    duration_seconds: float,
    detected_segments: list[dict[str, float | str]] | None = None,
) -> tuple[list[LyricLine], list[str]]:
    warnings: list[str] = []
    display_lines = split_for_display(lyrics_lines)
    if not display_lines:
        return [], ["No usable lyric lines were found."]

    if detected_segments and len(detected_segments) >= len(display_lines):
        start_times = [float(segment["start"]) for segment in detected_segments[: len(display_lines)]]
        warnings.append("Used detected speech segments for rough line alignment.")
    else:
        if detected_segments:
            warnings.append("Detected speech segments were too sparse, using even timing fallback.")
        per_line = max(duration_seconds / max(len(display_lines), 1), 1.5)
        start_times = [index * per_line for index in range(len(display_lines))]
        warnings.append("Alignment fallback used estimated line timing.")

    aligned: list[LyricLine] = []
    for index, line in enumerate(display_lines):
        start = min(start_times[index], duration_seconds)
        if index + 1 < len(display_lines):
            end = min(max(start_times[index + 1] - 0.15, start + 1.0), duration_seconds)
        else:
            end = duration_seconds
        if end <= start:
            end = min(start + 1.5, duration_seconds)
        aligned.append(LyricLine(text=line, start=round(start, 2), end=round(end, 2)))
    return aligned, warnings
