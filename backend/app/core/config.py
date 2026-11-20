"""Runtime settings, read from environment variables.

Kept dependency-free (no pydantic-settings) because there are only two knobs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# backend/app/core/config.py -> repo root is three levels above `app/`
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_DATA_PATH = _REPO_ROOT / "data" / "flights.json"


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    data_path: Path = field(
        default_factory=lambda: Path(os.environ.get("DATA_PATH", str(_DEFAULT_DATA_PATH)))
    )
    # Only needed when the frontend is served from a different origin (e.g. `vite dev`
    # without its proxy). In docker-compose nginx proxies /api, so it's same-origin.
    cors_origins: list[str] = field(
        default_factory=lambda: _split_csv(
            os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
        )
    )


def get_settings() -> Settings:
    return Settings()
