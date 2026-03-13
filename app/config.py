from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
RENDERS_DIR = BASE_DIR / "renders"
TEMP_DIR = BASE_DIR / "temp"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

DEFAULT_FONT = "Montserrat Bold"

for directory in (UPLOADS_DIR, RENDERS_DIR, TEMP_DIR):
    directory.mkdir(parents=True, exist_ok=True)
