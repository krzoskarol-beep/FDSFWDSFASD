"""Test okna: wymaga tkintera i ekranu (Windows w CI, Xvfb na Linuksie). Bez nich — pominięty."""
import pytest

tk = pytest.importorskip("tkinter")

from korektor import app as app_mod  # noqa: E402
from korektor import eq  # noqa: E402


@pytest.fixture
def window(tmp_path, monkeypatch):
    apo_dir = tmp_path / "config"
    apo_dir.mkdir()
    (apo_dir / "config.txt").write_text("Preamp: -2 dB\n", encoding="utf-8")
    monkeypatch.setenv("KOREKTOR_APO_DIR", str(apo_dir))
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("brak ekranu")
    a = app_mod.App(root, tmp_path / "ustawienia.json")
    root.update()
    yield a, root, apo_dir
    root.destroy()


def test_toggle_preset_and_fader_drag_write_config(window):
    a, root, apo_dir = window
    a.set_enabled(True)
    a.choose_preset("Bas")
    f = a.faders[5]  # 1 kHz
    f.event_generate("<Button-1>", x=f.W // 2, y=int(f.y_of(6.0)))
    root.update()
    assert f.value == 6.0
    assert a.state.preset == eq.CUSTOM
    a.flush()
    text = (apo_dir / "korektor.txt").read_text(encoding="utf-8")
    assert "Filter: ON PK Fc 1000 Hz Gain 6 dB" in text
    assert "Filter: ON PK Fc 31 Hz Gain 7 dB" in text
    assert "Include: korektor.txt" in (apo_dir / "config.txt").read_text(encoding="utf-8")


def test_disabled_ignores_edits_and_writes_neutral_file(window):
    a, root, apo_dir = window
    a.set_enabled(False)
    f = a.faders[0]
    f.event_generate("<Button-1>", x=f.W // 2, y=int(f.y_of(9.0)))
    a.choose_preset("Rock")
    a.flush()
    assert a.state.gains == [0.0] * 10
    assert "Filter" not in (apo_dir / "korektor.txt").read_text(encoding="utf-8")
