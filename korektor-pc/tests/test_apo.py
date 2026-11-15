from pathlib import Path

from korektor import apo, settings
from korektor.eq import EqState


def make_apo(tmp_path: Path, content: str = "Preamp: -3 dB\nInclude: example.txt") -> Path:
    d = tmp_path / "config"
    d.mkdir()
    (d / "config.txt").write_text(content, encoding="utf-8")
    return d


def test_find_config_dir_via_env_and_preferred(tmp_path):
    d = make_apo(tmp_path)
    assert apo.find_config_dir(env={"KOREKTOR_APO_DIR": str(d)}) == d
    assert apo.find_config_dir(preferred=str(d), env={}) == d
    assert apo.find_config_dir(preferred=str(tmp_path / "nie"), env={"ProgramFiles": str(tmp_path / "x")}) is None


def test_apply_writes_file_and_include_once_with_backup(tmp_path):
    d = make_apo(tmp_path)
    apo.apply(d, "Preamp: -1 dB\n")
    apo.apply(d, "Preamp: -2 dB\n")
    cfg = (d / "config.txt").read_text(encoding="utf-8")
    assert cfg.count("Include: korektor.txt") == 1
    assert cfg.startswith("Preamp: -3 dB\nInclude: example.txt\n")  # ustawienia użytkownika nietknięte
    assert (d / "korektor.txt").read_text(encoding="utf-8").strip() == "Preamp: -2 dB"
    assert (d / ("config.txt" + apo.BACKUP_SUFFIX)).read_text(encoding="utf-8").startswith("Preamp: -3 dB")
    assert not list(d.glob("*.tmp"))


def test_include_detection_is_lenient(tmp_path):
    assert apo.has_include("x\n  include :  KOREKTOR.txt  # moje\n")
    assert not apo.has_include("# Include: korektor.txt\n")
    d = make_apo(tmp_path, "\ufeffInclude: korektor.txt\r\n")
    assert apo.ensure_include(d) is False


def test_remove_include(tmp_path):
    d = make_apo(tmp_path, "Preamp: -3 dB\n")
    apo.ensure_include(d)
    assert apo.remove_include(d) is True
    assert (d / "config.txt").read_text(encoding="utf-8") == "Preamp: -3 dB\n"


def test_settings_roundtrip(tmp_path):
    p = settings.settings_path({"KOREKTOR_SETTINGS_DIR": str(tmp_path)})
    st = EqState(enabled=True, preset="Rock", gains=[1.0] * 10, bass=20, surround=10)
    settings.save(p, st, "C:/x")
    assert settings.load(p) == (st, "C:/x")
    p.write_text("{zepsute", encoding="utf-8")
    assert settings.load(p) == (EqState(), None)
