"""Load the versioned C1 labeling config (TOML, standard library only)."""
from __future__ import annotations
import tomllib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "c1_labeling_v1.toml"

def _to_namespace(value: Any) -> Any:
    if isinstance(value, dict):
        return SimpleNamespace(**{k: _to_namespace(v) for k, v in value.items()})
    return value

def load_config(path: Path | str | None = None) -> SimpleNamespace:
    """Return the config as nested attribute namespaces."""
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with config_path.open("rb") as handle:
        return _to_namespace(tomllib.load(handle))

def is_approved(cfg: SimpleNamespace) -> bool:
    """A dataset may only be frozen when every parameter is justified."""
    return cfg.meta.parameter_status == "APPROVED"