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
from .render import FORMATS, render_job


app = FastAPI(title="Lyric Video Generator")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)
executor = ThreadPoolExecutor(max_workers=2)


def sanitize_filename(filename: str) -> str:
    cleaned = "".join(char for char in filename if char.isalnum() or char in {".", "-", "_"})
    return cleaned.strip("._") or "upload.bin"


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload", response_model=UploadResponse)
async def upload_assets(
    audio: UploadFile = File(...),
    lyrics: str = Form(...),
    background: UploadFile | None = File(default=None),
) -> UploadResponse:
    if audio.content_type not in {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp3"}:
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
    if format_name not in FORMATS:
        raise HTTPException(status_code=404, detail="Format not found.")
    output_name = FORMATS[format_name]["suffix"] + ".mp4"
    absolute_path = RENDERS_DIR / job_id / output_name
    if not absolute_path.exists():
        raise HTTPException(status_code=404, detail="File not ready.")
    return FileResponse(absolute_path, media_type="video/mp4", filename=output_name)
