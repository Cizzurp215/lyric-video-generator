from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .config import DEFAULT_FONT, RENDERS_DIR, TEMP_DIR
from .jobs import JobRecord, UploadRecord, store
from .lyrics import align_lyrics, load_lyrics
from .models import RenderRequest
from .subtitles import build_ass_subtitles
from .transcription import get_media_duration, transcribe_audio


FORMATS = {
    "horizontal": {"width": 1920, "height": 1080, "suffix": "youtube"},
    "vertical": {"width": 1080, "height": 1920, "suffix": "tiktok"},
}


def find_binary(binary_name: str) -> str | None:
    discovered = shutil.which(binary_name)
    if discovered:
        return discovered

    fallback_roots = [
        Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages",
        Path("C:/Program Files"),
        Path("C:/Program Files (x86)"),
    ]
    for root in fallback_roots:
        if not root.exists():
            continue
        matches = list(root.rglob(binary_name))
        if matches:
            return str(matches[0])
    return None


def _build_background_input(
    background_path: Path | None,
    width: int,
    height: int,
    dim_amount: float,
) -> tuple[list[str], str]:
    if background_path is None:
        return (
            ["-f", "lavfi", "-i", f"color=c=0x121212:s={width}x{height}:r=30"],
            "[0:v]format=yuv420p[bg]",
        )

    suffix = background_path.suffix.lower()
    if suffix in {".mp4", ".mov", ".mkv", ".webm"}:
        args = ["-stream_loop", "-1", "-i", str(background_path)]
    else:
        args = ["-loop", "1", "-i", str(background_path)]
    filter_complex = (
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},format=yuv420p,eq=brightness=-{dim_amount/2:.2f}[bg]"
    )
    return args, filter_complex


def render_job(job: JobRecord, upload: UploadRecord, request: RenderRequest) -> None:
    ffmpeg_path = find_binary("ffmpeg.exe") or find_binary("ffmpeg")
    if not ffmpeg_path:
        store.update_job(
            job.job_id,
            state="failed",
            progress=100,
            message="ffmpeg was not found. Install FFmpeg and try again.",
        )
        return

    try:
        store.update_job(job.job_id, state="running", progress=10, message="Inspecting audio")
        duration = get_media_duration(upload.audio_path)
    except Exception as exc:
        store.update_job(
            job.job_id,
            state="failed",
            progress=100,
            message=str(exc),
            warnings=upload.warnings,
        )
        return

    store.update_job(job.job_id, progress=25, message="Transcribing vocals")
    segments, warnings = transcribe_audio(upload.audio_path)
    warnings = list(upload.warnings) + warnings

    store.update_job(job.job_id, progress=40, message="Aligning lyrics")
    lyrics_lines = load_lyrics(upload.lyrics_path)
    aligned_lines, alignment_warnings = align_lyrics(lyrics_lines, duration, segments)
    warnings.extend(alignment_warnings)
    if not aligned_lines:
        store.update_job(
            job.job_id,
            state="failed",
            progress=100,
            message="No lyric lines were available after normalization.",
            warnings=warnings,
        )
        return

    outputs: dict[str, str] = {}
    modes = ["horizontal", "vertical"] if request.output_mode == "both" else [request.output_mode]
    progress_points = {"horizontal": 65, "vertical": 90}

    for mode in modes:
        format_config = FORMATS[mode]
        width = format_config["width"]
        height = format_config["height"]
        subtitle_path = TEMP_DIR / job.job_id / f"{mode}.ass"
        build_ass_subtitles(
            aligned_lines,
            subtitle_path,
            width=width,
            height=height,
            font_name=DEFAULT_FONT,
            font_size=request.font_size if mode == "horizontal" else max(request.font_size - 6, 24),
            text_position=request.text_position,
            primary_color=request.primary_color,
            highlight_color=request.highlight_color,
        )

        store.update_job(job.job_id, progress=progress_points[mode], message=f"Rendering {mode} video")
        output_path = RENDERS_DIR / job.job_id / f"{format_config['suffix']}.mp4"
        input_args, filter_complex = _build_background_input(
            upload.background_path, width, height, request.background_dim
        )
        subtitle_filter_path = subtitle_path.as_posix().replace(":", r"\:")
        filter_complex = f"{filter_complex};[bg]ass={subtitle_filter_path}[vout]"

        command = [
            ffmpeg_path,
            "-y",
            *input_args,
            "-i",
            str(upload.audio_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(output_path),
        ]

        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            warnings.append(exc.stderr.strip() or "ffmpeg render failed")
            store.update_job(
                job.job_id,
                state="failed",
                progress=100,
                message=f"Render failed for {mode} output.",
                warnings=warnings,
            )
            return

        outputs[mode] = output_path.name

    store.update_job(
        job.job_id,
        state="completed",
        progress=100,
        message="Render complete",
        warnings=warnings,
        outputs=outputs,
    )
