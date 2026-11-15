"""Zapamiętane ustawienia: %APPDATA%\\Korektor\\ustawienia.json."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .eq import EqState


def settings_path(env: dict | None = None) -> Path:
    env = os.environ if env is None else env
    base = env.get("KOREKTOR_SETTINGS_DIR") or env.get("APPDATA")
    root = Path(base) / "Korektor" if base and not env.get("KOREKTOR_SETTINGS_DIR") else (
        Path(base) if base else Path.home() / ".korektor")
    return root / "ustawienia.json"


def load(path: Path) -> tuple[EqState, str | None]:
    """Stan korektora i ewentualnie ręcznie wskazany folder Equalizer APO."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return EqState(), None
    if not isinstance(data, dict):
        return EqState(), None
    apo_dir = data.get("apo_dir")
    return EqState.from_dict(data.get("eq")), apo_dir if isinstance(apo_dir, str) else None


def save(path: Path, state: EqState, apo_dir: str | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps({"eq": state.to_dict(), "apo_dir": apo_dir}, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    os.replace(tmp, path)
