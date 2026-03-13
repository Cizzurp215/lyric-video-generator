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
Style: ContextTop,{font_name},{context_size},{context_color},{highlight_color},&H64000000,&H78000000,-1,0,0,0,100,100,0,0,1,2,1,{alignment},{margin_lr},{margin_lr},{context_top_margin_v},1
Style: ContextBottom,{font_name},{context_size},{context_color},{highlight_color},&H64000000,&H78000000,-1,0,0,0,100,100,0,0,1,2,1,{alignment},{margin_lr},{margin_lr},{context_bottom_margin_v},1

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
    if text_position == "bottom":
        context_top_margin_v = margin_v + 74
        context_bottom_margin_v = max(margin_v - 74, 40)
    elif text_position == "top":
        context_top_margin_v = max(margin_v - 74, 40)
        context_bottom_margin_v = margin_v + 74
    else:
        context_top_margin_v = margin_v + 74
        context_bottom_margin_v = max(margin_v - 74, 40)
    context_size = max(font_size - 12, 24)
    context_color = "&H80FFFFFF"

    events: list[str] = []
    for index, line in enumerate(aligned_lines):
        start = seconds_to_ass(line.start)
        end = seconds_to_ass(line.end)
        previous_line = aligned_lines[index - 1].text if index > 0 else ""
        next_line = aligned_lines[index + 1].text if index + 1 < len(aligned_lines) else ""
        if previous_line:
            events.append(f"Dialogue: 0,{start},{end},ContextTop,,0,0,0,,{_escape_ass(previous_line)}")
        events.append(
            "Dialogue: 1,{start},{end},Default,,0,0,0,,{{\\fad(120,180)\\move(0,18,0,0)}}{text}".format(
                start=start,
                end=end,
                text=_escape_ass(line.text),
            )
        )
        if next_line:
            events.append(f"Dialogue: 0,{start},{end},ContextBottom,,0,0,0,,{_escape_ass(next_line)}")

    payload = ASS_TEMPLATE.format(
        play_res_x=width,
        play_res_y=height,
        font_name=font_name,
        font_size=font_size,
        context_size=context_size,
        primary_color=hex_to_ass_bgr(primary_color),
        highlight_color=hex_to_ass_bgr(highlight_color),
        context_color=context_color,
        alignment=alignment,
        margin_lr=72,
        margin_v=margin_v,
        context_top_margin_v=context_top_margin_v,
        context_bottom_margin_v=context_bottom_margin_v,
        events="\n".join(events),
    )
    subtitle_path.write_text(payload, encoding="utf-8")
