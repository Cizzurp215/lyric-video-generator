from __future__ import annotations

import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import RENDERS_DIR, STATIC_DIR, TEMPLATES_DIR
from .jobs import UploadRecord, store
from .models import JobStatusResponse, RenderRequest, UploadResponse
from .presets import PRESETS
from .render import FORMATS, render_job


app = FastAPI(title="Lyric Video Generator")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)
executor = ThreadPoolExecutor(max_workers=2)


def sanitize_filename(filename: str) -> str:
    cleaned = "".join(char for char in filename if char.isalnum() or char in {".", "-", "_"})
    return cleaned.strip("._") or "upload.bin"


def is_allowed_audio_upload(upload: UploadFile) -> bool:
    allowed_types = {
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "audio/vnd.wave",
        "application/octet-stream",
    }
    extension = Path(upload.filename or "").suffix.lower()
    return upload.content_type in allowed_types or extension in {".mp3", ".wav"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request, "presets": PRESETS})


@app.post("/upload", response_model=UploadResponse)
async def upload_assets(
    audio: UploadFile = File(...),
    lyrics: str = Form(...),
    background: UploadFile | None = File(default=None),
) -> UploadResponse:
    if not is_allowed_audio_upload(audio):
        raise HTTPException(status_code=400, detail="Audio must be an MP3 or WAV file.")
    if not lyrics.strip():
        raise HTTPException(status_code=400, detail="Lyrics are required.")

    upload_id, upload_dir = store.new_upload_dir()
    warnings: list[str] = []

    audio_filename = sanitize_filename(audio.filename or "audio.mp3")
    audio_path = upload_dir / audio_filename
    with audio_path.open("wb") as destination:
        shutil.copyfileobj(audio.file, destination)

    lyrics_path = upload_dir / "lyrics.txt"
    lyrics_path.write_text(lyrics, encoding="utf-8")

    background_path: Path | None = None
    background_filename: str | None = None
    if background and background.filename:
        background_filename = sanitize_filename(background.filename)
        background_path = upload_dir / background_filename
        with background_path.open("wb") as destination:
            shutil.copyfileobj(background.file, destination)
    else:
        warnings.append("No background supplied. A generated dark background will be used.")

    store.save_upload(
        UploadRecord(
            upload_id=upload_id,
            job_dir=upload_dir,
            audio_path=audio_path,
            lyrics_path=lyrics_path,
            background_path=background_path,
            warnings=warnings,
        )
    )

    return UploadResponse(
        upload_id=upload_id,
        audio_filename=audio_filename,
        background_filename=background_filename,
        warnings=warnings,
    )


@app.post("/render")
async def render_video(request: RenderRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    upload = store.get_upload(request.upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found.")

    job = store.create_job(request.upload_id)

    background_tasks.add_task(executor.submit, render_job, job, upload, request)
    return {"job_id": job.job_id}


@app.get("/status/{job_id}", response_model=JobStatusResponse)
async def job_status(job_id: str) -> JobStatusResponse:
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobStatusResponse(
        job_id=job.job_id,
        state=job.state,
        progress=job.progress,
        message=job.message,
        warnings=job.warnings,
        outputs=job.outputs,
    )


@app.get("/download/{job_id}/{format_name}")
async def download(job_id: str, format_name: str) -> FileResponse:
    filename_map = {
        "horizontal": "youtube.mp4",
        "vertical": "tiktok.mp4",
        "captions": "captions.srt",
    }
    if format_name not in filename_map:
        raise HTTPException(status_code=404, detail="Format not found.")
    output_name = filename_map[format_name]
    absolute_path = RENDERS_DIR / job_id / output_name
    if not absolute_path.exists():
        raise HTTPException(status_code=404, detail="File not ready.")
    media_type = "text/plain" if output_name.endswith(".srt") else "video/mp4"
    return FileResponse(absolute_path, media_type=media_type, filename=output_name)


@app.get("/artifact/{job_id}/{format_name}")
async def artifact(job_id: str, format_name: str) -> FileResponse:
    filename_map = {
        "horizontal": "youtube.mp4",
        "vertical": "tiktok.mp4",
        "captions": "captions.srt",
    }
    if format_name not in filename_map:
        raise HTTPException(status_code=404, detail="Format not found.")
    absolute_path = RENDERS_DIR / job_id / filename_map[format_name]
    if not absolute_path.exists():
        raise HTTPException(status_code=404, detail="File not ready.")
    media_type = "text/plain" if absolute_path.suffix == ".srt" else "video/mp4"
    return FileResponse(absolute_path, media_type=media_type)
