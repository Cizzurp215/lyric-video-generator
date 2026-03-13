from app.lyrics import align_lyrics, normalize_lyrics, split_for_display


def test_normalize_lyrics_strips_blank_lines() -> None:
    payload = "Verse 1\n\n  Hello   world  \n"
    assert normalize_lyrics(payload) == ["Verse 1", "Hello world"]


def test_split_for_display_wraps_long_lines() -> None:
    wrapped = split_for_display(["This is a deliberately long lyric line that should wrap cleanly"], max_chars=22)
    assert len(wrapped) > 1


def test_align_lyrics_generates_progressive_timestamps() -> None:
    aligned, warnings = align_lyrics(["One", "Two", "Three"], 9.0)
    assert len(aligned) == 3
    assert aligned[0].start == 0.0
    assert aligned[-1].end == 9.0
    assert warnings
