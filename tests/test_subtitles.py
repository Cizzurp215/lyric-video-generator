from pathlib import Path

from app.lyrics import LyricLine
from app.subtitles import build_ass_subtitles, build_srt_subtitles, seconds_to_ass


def test_seconds_to_ass_formats_centiseconds() -> None:
    assert seconds_to_ass(65.34) == "0:01:05.34"


def test_build_ass_subtitles_writes_events(tmp_path: Path) -> None:
    target = tmp_path / "demo.ass"
    build_ass_subtitles(
        [LyricLine(text="Hello world", start=0.0, end=3.5)],
        target,
        width=1920,
        height=1080,
        font_name="Montserrat Bold",
        font_size=56,
        text_position="bottom",
        primary_color="#FFFFFF",
        highlight_color="#FFD54A",
    )
    content = target.read_text(encoding="utf-8")
    assert "Hello world" in content
    assert "Style: Default" in content


def test_build_srt_subtitles_writes_caption_rows(tmp_path: Path) -> None:
    target = tmp_path / "demo.srt"
    build_srt_subtitles(
        [LyricLine(text="Hello world", start=0.0, end=3.5)],
        target,
    )
    content = target.read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:03,500" in content
    assert "Hello world" in content
