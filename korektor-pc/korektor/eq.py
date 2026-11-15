"""Czysta logika korektora (bez Windows i bez GUI, łatwa do testów).

Stan korektora -> tekst konfiguracji dla Equalizer APO. Equalizer APO to darmowy
sterownik (APO) Windows, który przepuszcza przez filtry CAŁY dźwięk wybranego
urządzenia wyjściowego. Ta aplikacja tylko zapisuje jego plik konfiguracyjny.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

# 10 pasm co oktawę, jak w klasycznym korektorze graficznym.
BANDS: tuple[int, ...] = (31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000)
MIN_DB = -12.0
MAX_DB = 12.0
BAND_Q = 1.41          # ~1 oktawa szerokości: sąsiednie pasma ładnie się łączą
BASS_FC = 100           # półka basowa
BASS_Q = 0.707
BASS_MAX_DB = 10.0      # siła basu 100% = +10 dB poniżej ~100 Hz
SURROUND_MAX = 0.6      # siła 100% = poszerzenie stereo o 60% (mid/side)
SAMPLE_RATE = 48000

CUSTOM = "Własny"

# Zestawy w dB dla kolejnych pasm (31 Hz ... 16 kHz).
PRESETS: dict[str, tuple[float, ...]] = {
    "Płaski":      (0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    "Bas":         (7, 6, 4.5, 2, 0, 0, 0, 0, 0, 0),
    "Rock":        (5, 4, 2.5, 0, -1.5, -1, 1, 3, 4, 4.5),
    "Pop":         (-1, 0, 2, 3.5, 4, 3, 1, 0, -0.5, -1),
    "Jazz":        (3, 2, 1, 1.5, -1, -1, 0, 1.5, 3, 3.5),
    "Klasyczna":   (4, 3, 2, 1, 0, 0, 0, 1.5, 2.5, 3.5),
    "Elektronika": (6, 5, 2, 0, -2, 1, 0, 1, 4, 5),
    "Głos":        (-3, -2, -1, 1, 3.5, 4, 3.5, 2, 0, -2),
    "Słuchawki":   (3, 2.5, 1, 0, -0.5, 0, 1, 2.5, 3, 2),
}


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


@dataclass
class EqState:
    enabled: bool = False
    preset: str = "Płaski"
    gains: list[float] = field(default_factory=lambda: [0.0] * len(BANDS))
    bass: int = 0        # 0..100 %
    surround: int = 0    # 0..100 %

    def normalized(self) -> "EqState":
        """Kopia z poprawionymi wartościami (np. po wczytaniu uszkodzonego pliku)."""
        gains = list(self.gains)[: len(BANDS)]
        gains += [0.0] * (len(BANDS) - len(gains))
        clean = []
        for g in gains:
            try:
                g = float(g)
            except (TypeError, ValueError):
                g = 0.0
            if math.isnan(g) or math.isinf(g):
                g = 0.0
            clean.append(round(clamp(g, MIN_DB, MAX_DB), 1))
        preset = self.preset if (self.preset in PRESETS or self.preset == CUSTOM) else CUSTOM
        return EqState(
            enabled=bool(self.enabled),
            preset=preset,
            gains=clean,
            bass=int(clamp(_int(self.bass), 0, 100)),
            surround=int(clamp(_int(self.surround), 0, 100)),
        )

    def to_dict(self) -> dict:
        return {"enabled": self.enabled, "preset": self.preset, "gains": list(self.gains),
                "bass": self.bass, "surround": self.surround}

    @classmethod
    def from_dict(cls, d: dict | None) -> "EqState":
        if not isinstance(d, dict):
            return cls()
        gains = d.get("gains")
        return cls(
            enabled=d.get("enabled", False),
            preset=str(d.get("preset", "Płaski")),
            gains=list(gains) if isinstance(gains, list) else [0.0] * len(BANDS),
            bass=d.get("bass", 0),
            surround=d.get("surround", 0),
        ).normalized()


def _int(v) -> int:
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return 0


def bass_db(bass: int) -> float:
    return round(BASS_MAX_DB * clamp(bass, 0, 100) / 100.0, 1)


def surround_width(surround: int) -> float:
    return round(SURROUND_MAX * clamp(surround, 0, 100) / 100.0, 3)


# ---------------------------------------------------------------- charakterystyka
# Wzory RBJ „Audio EQ Cookbook” — te same biquady liczy Equalizer APO.

def _peaking(fc: float, gain_db: float, q: float, fs: int = SAMPLE_RATE):
    a = 10 ** (gain_db / 40)
    w0 = 2 * math.pi * fc / fs
    alpha = math.sin(w0) / (2 * q)
    cw = math.cos(w0)
    return ((1 + alpha * a, -2 * cw, 1 - alpha * a), (1 + alpha / a, -2 * cw, 1 - alpha / a))


def _low_shelf(fc: float, gain_db: float, q: float, fs: int = SAMPLE_RATE):
    a = 10 ** (gain_db / 40)
    w0 = 2 * math.pi * fc / fs
    alpha = math.sin(w0) / (2 * q)
    cw = math.cos(w0)
    sa = 2 * math.sqrt(a) * alpha
    b = (a * ((a + 1) - (a - 1) * cw + sa), 2 * a * ((a - 1) - (a + 1) * cw), a * ((a + 1) - (a - 1) * cw - sa))
    den = ((a + 1) + (a - 1) * cw + sa, -2 * ((a - 1) + (a + 1) * cw), (a + 1) + (a - 1) * cw - sa)
    return b, den


def _mag_db(coeffs, f: float, fs: int = SAMPLE_RATE) -> float:
    (b0, b1, b2), (a0, a1, a2) = coeffs
    w = 2 * math.pi * f / fs
    z1 = complex(math.cos(w), -math.sin(w))
    z2 = z1 * z1
    h = (b0 + b1 * z1 + b2 * z2) / (a0 + a1 * z1 + a2 * z2)
    return 20 * math.log10(max(abs(h), 1e-12))


def _filters(state: EqState):
    out = [_peaking(fc, g, BAND_Q) for fc, g in zip(BANDS, state.gains) if abs(g) >= 0.05]
    b = bass_db(state.bass)
    if b > 0:
        out.append(_low_shelf(BASS_FC, b, BASS_Q))
    return out


def log_freqs(n: int = 160, lo: float = 20.0, hi: float = 20000.0) -> list[float]:
    return [lo * (hi / lo) ** (i / (n - 1)) for i in range(n)]


def response_db(state: EqState, freqs: list[float] | None = None) -> list[float]:
    """Wzmocnienie [dB] całego łańcucha filtrów (bez przedwzmacniacza)."""
    freqs = freqs or log_freqs()
    filters = _filters(state)
    return [sum(_mag_db(c, f) for c in filters) for f in freqs]


def preamp_db(state: EqState) -> float:
    """Ujemny przedwzmacniacz, który zapobiega przesterowaniu przy podbiciach."""
    peak = max([0.0] + response_db(state, log_freqs(400)))
    w = surround_width(state.surround)
    peak += 20 * math.log10(1 + w)
    return -math.ceil(peak * 10) / 10 if peak > 0.05 else 0.0


# ---------------------------------------------------------------- konfiguracja APO

def _num(v: float) -> str:
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def build_config(state: EqState) -> str:
    """Tekst pliku korektor.txt dla Equalizer APO."""
    s = state.normalized()
    lines = [
        "# Plik tworzy aplikacja Korektor — nie edytuj ręcznie, zostanie nadpisany.",
    ]
    if not s.enabled:
        lines.append("# Korektor wyłączony: brak filtrów, dźwięk bez zmian.")
        return "\n".join(lines) + "\n"

    lines += [
        "Device: all",
        "Stage: post-mix",
        "Channel: all",
        f"Preamp: {_num(preamp_db(s))} dB",
    ]
    for fc, g in zip(BANDS, s.gains):
        if abs(g) >= 0.05:
            lines.append(f"Filter: ON PK Fc {fc} Hz Gain {_num(g)} dB Q {_num(BAND_Q)}")
    b = bass_db(s.bass)
    if b > 0:
        lines.append(f"Filter: ON LSC Fc {BASS_FC} Hz Gain {_num(b)} dB Q {_num(BASS_Q)}")
    w = surround_width(s.surround)
    if w > 0:
        # Poszerzenie stereo: wzmacnia różnicę L-R (side), środek (mid) zostaje.
        k = _num(1 + w)
        m = _num(w)
        lines.append(f"Copy: L={k}*L+-{m}*R R={k}*R+-{m}*L")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- etykiety

def format_db(db: float) -> str:
    if abs(db) < 0.05:
        return "0 dB"
    sign = "+" if db > 0 else "−"
    return f"{sign}{abs(db):.1f} dB"


def format_freq(hz: float) -> str:
    if hz < 1000:
        return f"{int(round(hz))} Hz"
    k = hz / 1000
    return f"{k:.1f} kHz".replace(".0 kHz", " kHz") if k < 10 else f"{int(round(k))} kHz"


def matching_preset(gains: list[float]) -> str:
    for name, values in PRESETS.items():
        if all(abs(a - b) < 0.05 for a, b in zip(gains, values)):
            return name
    return CUSTOM
