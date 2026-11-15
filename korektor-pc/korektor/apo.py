"""Połączenie z Equalizer APO: znalezienie folderu config i zapis plików.

Korektor nie dotyka ustawień użytkownika w config.txt poza jedną linią
„Include: korektor.txt” dopisaną na końcu (z kopią zapasową przy pierwszej zmianie).
Equalizer APO sam wczytuje zmienione pliki, więc dźwięk zmienia się od razu.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

OUR_FILE = "korektor.txt"
INCLUDE_LINE = f"Include: {OUR_FILE}"
BACKUP_SUFFIX = ".korektor-kopia"
DOWNLOAD_URL = "https://sourceforge.net/projects/equalizerapo/files/latest/download"
_INCLUDE_RE = re.compile(r"^\s*include\s*:\s*korektor\.txt\s*(#.*)?$", re.IGNORECASE)


class ApoError(Exception):
    """Błąd zapisu, z komunikatem do pokazania użytkownikowi."""

    def __init__(self, message: str, needs_admin: bool = False):
        super().__init__(message)
        self.needs_admin = needs_admin


def _registry_paths() -> list[Path]:
    if sys.platform != "win32":
        return []
    import winreg

    found: list[Path] = []
    for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\EqualizerAPO", 0,
                                winreg.KEY_READ | view) as key:
                for name, suffix in (("ConfigPath", ""), ("InstallPath", "config")):
                    try:
                        value, _ = winreg.QueryValueEx(key, name)
                    except OSError:
                        continue
                    if value:
                        found.append(Path(value) / suffix if suffix else Path(value))
        except OSError:
            continue
    return found


def candidate_dirs(env: dict | None = None) -> list[Path]:
    env = os.environ if env is None else env
    out: list[Path] = []
    if env.get("KOREKTOR_APO_DIR"):
        out.append(Path(env["KOREKTOR_APO_DIR"]))
    out += _registry_paths()
    for var in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
        if env.get(var):
            out.append(Path(env[var]) / "EqualizerAPO" / "config")
    out.append(Path(r"C:\Program Files\EqualizerAPO\config"))
    uniq, seen = [], set()
    for p in out:
        key = str(p).lower()
        if key not in seen:
            seen.add(key)
            uniq.append(p)
    return uniq


def is_config_dir(path: Path) -> bool:
    return path.is_dir() and (path / "config.txt").is_file()


def find_config_dir(preferred: str | None = None, env: dict | None = None) -> Path | None:
    if preferred and is_config_dir(Path(preferred)):
        return Path(preferred)
    for p in candidate_dirs(env):
        if is_config_dir(p):
            return p
    return None


def has_include(text: str) -> bool:
    return any(_INCLUDE_RE.match(line) for line in text.splitlines())


def _write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except PermissionError as e:
        _cleanup(tmp)
        raise ApoError(
            f"Brak uprawnień do zapisu w {path.parent}. Uruchom Korektor jako administrator.",
            needs_admin=True) from e
    except OSError as e:
        _cleanup(tmp)
        raise ApoError(f"Nie udało się zapisać {path.name}: {e}") from e


def _cleanup(p: Path) -> None:
    try:
        p.unlink()
    except OSError:
        pass


def _read(path: Path) -> str:
    # Equalizer APO zapisuje config.txt w UTF-8 (czasem z BOM).
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp1250"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def ensure_include(config_dir: Path) -> bool:
    """Dopisuje „Include: korektor.txt” do config.txt. Zwraca True, gdy coś zmieniono."""
    cfg = config_dir / "config.txt"
    try:
        text = _read(cfg)
    except OSError as e:
        raise ApoError(f"Nie można odczytać {cfg}: {e}") from e
    if has_include(text):
        return False
    backup = cfg.with_name(cfg.name + BACKUP_SUFFIX)
    if not backup.exists():
        _write_atomic(backup, text)
    sep = "" if text.endswith(("\n", "\r")) or not text else "\n"
    new = text.replace("\r\n", "\n") + sep + "# Dodane przez aplikację Korektor:\n" + INCLUDE_LINE + "\n"
    _write_atomic(cfg, new)
    return True


def apply(config_dir: Path, config_text: str) -> None:
    """Zapisuje korektor.txt (najpierw) i podpina go w config.txt."""
    _write_atomic(config_dir / OUR_FILE, config_text)
    ensure_include(config_dir)


def remove_include(config_dir: Path) -> bool:
    """Odłącza Korektor od config.txt (deinstalacja). Zwraca True, gdy coś zmieniono."""
    cfg = config_dir / "config.txt"
    text = _read(cfg)
    if not has_include(text):
        return False
    kept = [ln for ln in text.splitlines()
            if not _INCLUDE_RE.match(ln) and ln.strip() != "# Dodane przez aplikację Korektor:"]
    _write_atomic(cfg, "\n".join(kept) + "\n")
    return True
