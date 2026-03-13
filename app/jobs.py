from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from .config import RENDERS_DIR, TEMP_DIR, UPLOADS_DIR


@dataclass
class UploadRecord:
    upload_id: str
    job_dir: Path
    audio_path: Path
    lyrics_path: Path
    background_path: Path | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class JobRecord:
    job_id: str
    upload_id: str
    state: str = "queued"
    progress: int = 0
    message: str = "Queued"
    warnings: list[str] = field(default_factory=list)
    outputs: dict[str, str] = field(default_factory=dict)


class JobStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._uploads: dict[str, UploadRecord] = {}
        self._jobs: dict[str, JobRecord] = {}

    def new_upload_dir(self) -> tuple[str, Path]:
        upload_id = uuid.uuid4().hex
        job_dir = UPLOADS_DIR / upload_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return upload_id, job_dir

    def save_upload(self, record: UploadRecord) -> None:
        with self._lock:
            self._uploads[record.upload_id] = record

    def get_upload(self, upload_id: str) -> UploadRecord | None:
        with self._lock:
            return self._uploads.get(upload_id)

    def create_job(self, upload_id: str) -> JobRecord:
        job_id = uuid.uuid4().hex
        record = JobRecord(job_id=job_id, upload_id=upload_id)
        with self._lock:
            self._jobs[job_id] = record
        (TEMP_DIR / job_id).mkdir(parents=True, exist_ok=True)
        (RENDERS_DIR / job_id).mkdir(parents=True, exist_ok=True)
        return record

    def get_job(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update_job(self, job_id: str, **fields: object) -> JobRecord | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            for key, value in fields.items():
                setattr(job, key, value)
            return job


store = JobStore()
