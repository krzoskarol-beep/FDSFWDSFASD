import math

from korektor import eq
from korektor.eq import EqState


def test_disabled_config_has_no_filters():
    text = eq.build_config(EqState(enabled=False, gains=[6.0] * 10, bass=80))
    assert "Filter" not in text and "Preamp" not in text and "Copy" not in text


def test_flat_enabled_is_neutral():
    text = eq.build_config(EqState(enabled=True))
    assert "Preamp: 0 dB" in text
    assert "Filter" not in text


def test_bands_become_peaking_filters_with_preamp():
    gains = [0.0] * 10
    gains[5] = 6.0   # 1 kHz
    gains[0] = -3.0  # 31 Hz
    text = eq.build_config(EqState(enabled=True, gains=gains))
    assert "Filter: ON PK Fc 1000 Hz Gain 6 dB Q 1.41" in text
    assert "Filter: ON PK Fc 31 Hz Gain -3 dB Q 1.41" in text
    pre = [ln for ln in text.splitlines() if ln.startswith("Preamp:")][0]
    db = float(pre.split()[1])
    assert -6.5 < db <= -5.9  # szczyt +6 dB kompensowany
    # kolejność: selektory przed filtrami
    lines = text.splitlines()
    assert lines.index("Channel: all") < lines.index(pre)


def test_bass_and_surround():
    text = eq.build_config(EqState(enabled=True, bass=50, surround=100))
    assert "Filter: ON LSC Fc 100 Hz Gain 5 dB Q 0.707" in text
    assert "Copy: L=1.6*L+-0.6*R R=1.6*R+-0.6*L" in text
    pre = float([ln for ln in text.splitlines() if ln.startswith("Preamp:")][0].split()[1])
    assert pre <= -(5 + 20 * math.log10(1.6)) + 0.2


def test_response_matches_gain_at_center():
    gains = [0.0] * 10
    gains[3] = 9.0
    r = eq.response_db(EqState(enabled=True, gains=gains), [250.0, 20.0, 20000.0])
    assert abs(r[0] - 9.0) < 0.05
    assert abs(r[1]) < 0.5 and abs(r[2]) < 0.5


def test_normalized_repairs_bad_values():
    s = EqState.from_dict({"enabled": 1, "preset": "???", "gains": [99, "x", float("nan")], "bass": 500,
                           "surround": -3})
    assert s.gains[:3] == [12.0, 0.0, 0.0] and len(s.gains) == 10
    assert s.bass == 100 and s.surround == 0 and s.preset == eq.CUSTOM and s.enabled is True
    assert EqState.from_dict(None) == EqState()


def test_presets_valid_and_matched():
    for name, values in eq.PRESETS.items():
        assert len(values) == len(eq.BANDS)
        assert all(eq.MIN_DB <= v <= eq.MAX_DB for v in values)
        assert eq.matching_preset(list(values)) == name
    assert eq.matching_preset([1.3] * 10) == eq.CUSTOM


def test_labels():
    assert eq.format_db(0.01) == "0 dB"
    assert eq.format_db(3) == "+3.0 dB"
    assert eq.format_db(-6) == "−6.0 dB"
    assert eq.format_freq(31) == "31 Hz"
    assert eq.format_freq(1000) == "1 kHz"
    assert eq.format_freq(2500) == "2.5 kHz"
    assert eq.format_freq(16000) == "16 kHz"
