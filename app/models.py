from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RenderRequest(BaseModel):
    upload_id: str = Field(min_length=8)
    output_mode: Literal["horizontal", "vertical", "both"] = "both"
    font_size: int = Field(default=56, ge=24, le=120)
    text_position: Literal["top", "middle", "bottom"] = "bottom"
    primary_color: str = "#FFFFFF"
    highlight_color: str = "#FFD54A"
    background_dim: float = Field(default=0.35, ge=0.0, le=0.9)


class UploadResponse(BaseModel):
    upload_id: str
    audio_filename: str
    background_filename: str | None
    warnings: list[str] = []


class JobStatusResponse(BaseModel):
    job_id: str
    state: str
    progress: int
    message: str
    warnings: list[str]
    outputs: dict[str, str]
