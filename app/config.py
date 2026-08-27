"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_local_env(path: Path) -> None:
    """Load simple KEY=VALUE pairs without overriding the real environment."""
    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_local_env(PROJECT_ROOT / ".env")


@dataclass(frozen=True, slots=True)
class Settings:
    """Small, explicit configuration surface for the foundation."""

    environment: str
    host: str
    port: int
    log_level: str
    project_root: Path
    data_directory: Path
    knowledge_base_directory: Path
    openai_api_key: str | None
    openai_model: str


def get_settings() -> Settings:
    """Read settings after local .env values and process environment values merge."""
    return Settings(
        environment=os.getenv("APP_ENV", "development"),
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", "8000")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        project_root=PROJECT_ROOT,
        data_directory=PROJECT_ROOT / "data",
        knowledge_base_directory=PROJECT_ROOT / "knowledge-base",
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    )
