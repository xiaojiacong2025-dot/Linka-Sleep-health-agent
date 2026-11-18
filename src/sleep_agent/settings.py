from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


@dataclass(frozen=True)
class Settings:
    project_root: Path
    database_path: Path
    knowledge_index_path: Path
    app_timezone: str
    demo_mode: bool
    llm_api_key: str | None
    llm_base_url: str
    llm_model: str | None
    config: dict[str, Any]

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key and self.llm_model)


def load_settings(config_path: Path | None = None) -> Settings:
    _load_dotenv(PROJECT_ROOT / ".env")
    path = config_path or PROJECT_ROOT / "configs" / "default.yaml"
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    return Settings(
        project_root=PROJECT_ROOT,
        database_path=_resolve_path(os.getenv("DATABASE_PATH", "./data/sleep.db")),
        knowledge_index_path=_resolve_path(os.getenv("KNOWLEDGE_INDEX_PATH", "./data/index")),
        app_timezone=os.getenv("APP_TIMEZONE", "Asia/Shanghai"),
        demo_mode=os.getenv("DEMO_MODE", "false").lower() in {"1", "true", "yes"},
        llm_api_key=os.getenv("LLM_API_KEY") or None,
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        llm_model=os.getenv("LLM_MODEL") or None,
        config=config,
    )

