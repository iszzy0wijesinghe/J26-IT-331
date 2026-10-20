"""Settings for the C1 API. Everything can be overridden with environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# apps/c1_api/app/config.py -> the repo root is three levels above this folder
REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_MODEL = "models/c1/c1_xgboost_v1.json"
DEFAULT_ORIGINS = ("http://127.0.0.1:5173", "http://localhost:5173")
# fallback only: the order the classes were encoded in during training (0, 1, 2).
# the meta file's "classes" list wins over this, see inference.py
DEFAULT_CLASS_ORDER = ("CLEAN", "ANOMALY", "VALID_EVENT")


def _resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def _csv(value: str | None) -> tuple[str, ...]:
    return tuple(x.strip() for x in value.split(",") if x.strip()) if value else ()


@dataclass(frozen=True)
class Settings:
    model_path: Path
    meta_path: Path
    cors_origins: tuple[str, ...]
    env_class_order: tuple[str, ...]
    max_batch: int
    history_size: int


def load_settings() -> Settings:
    model_path = _resolve(os.getenv("C1_MODEL_PATH", DEFAULT_MODEL))
    default_meta = model_path.with_name(model_path.stem + "_meta.json")
    return Settings(
        model_path=model_path,
        meta_path=_resolve(os.getenv("C1_META_PATH", str(default_meta))),
        cors_origins=_csv(os.getenv("C1_CORS_ORIGINS")) or DEFAULT_ORIGINS,
        env_class_order=_csv(os.getenv("C1_CLASS_ORDER")),
        max_batch=int(os.getenv("C1_MAX_BATCH", "1000")),
        history_size=int(os.getenv("C1_HISTORY_SIZE", "200")),
    )
