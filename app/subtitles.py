from __future__ import annotations

from pathlib import Path

from .lyrics import LyricLine


ASS_TEMPLATE = """[Script Info]
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_color},{highlight_color},&H64000000,&H78000000,-1,0,0,0,100,100,0,0,1,2,1,{alignment},{margin_lr},{margin_lr},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{events}
"""


def hex_to_ass_bgr(color: str, alpha: str = "00") -> str:
    value = color.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Expected a #RRGGBB color, received {color!r}")
    rr, gg, bb = value[0:2], value[2:4], value[4:6]
    return f"&H{alpha}{bb}{gg}{rr}"


def seconds_to_ass(seconds: float) -> str:
    total_centiseconds = int(round(seconds * 100))
    hours, remainder = divmod(total_centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    secs, centis = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def _escape_ass(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def build_ass_subtitles(
    aligned_lines: list[LyricLine],
    subtitle_path: Path,
    *,
    width: int,
    height: int,
    font_name: str,
    font_size: int,
    text_position: str,
    primary_color: str,
    highlight_color: str,
) -> None:
    alignment_map = {"top": 8, "middle": 5, "bottom": 2}
    margin_map = {"top": 90, "middle": 80, "bottom": 120}
    alignment = alignment_map[text_position]
    margin_v = margin_map[text_position]

    events: list[str] = []
    for line in aligned_lines:
        start = seconds_to_ass(line.start)
        end = seconds_to_ass(line.end)
        events.append(
            (
                "Dialogue: 1,{start},{end},Default,,0,0,0,,"
                "{{\\fad(80,140)\\blur0.8\\fsp6\\fax-0.12\\fscx86\\fscy86"
                "\\t(0,120,\\fscx116\\fscy116\\blur0.25)"
                "\\t(120,260,\\fscx100\\fscy100\\fsp0\\fax-0.04)}}{text}"
            ).format(
                start=start,
                end=end,
                text=_escape_ass(line.text),
            )
        )

    payload = ASS_TEMPLATE.format(
        play_res_x=width,
        play_res_y=height,
        font_name=font_name,
        font_size=font_size,
        primary_color=hex_to_ass_bgr(primary_color),
        highlight_color=hex_to_ass_bgr(highlight_color),
        alignment=alignment,
        margin_lr=72,
        margin_v=margin_v,
        events="\n".join(events),
    )
    subtitle_path.write_text(payload, encoding="utf-8")


def seconds_to_srt(seconds: float) -> str:
    total_milliseconds = int(round(seconds * 1000))
    hours, remainder = divmod(total_milliseconds, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def build_srt_subtitles(aligned_lines: list[LyricLine], subtitle_path: Path) -> None:
    rows: list[str] = []
    for index, line in enumerate(aligned_lines, start=1):
        rows.append(str(index))
        rows.append(f"{seconds_to_srt(line.start)} --> {seconds_to_srt(line.end)}")
        rows.append(line.text)
        rows.append("")
    subtitle_path.write_text("\n".join(rows).strip() + "\n", encoding="utf-8")
