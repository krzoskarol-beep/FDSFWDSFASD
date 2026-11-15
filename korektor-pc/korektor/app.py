"""Okno Korektora (tkinter, bez dodatkowych bibliotek).

Wygląd jak w wersji na Androida: konsola audio, ciemne tło, bursztynowe diody.
Każda zmiana jest od razu zapisywana do Equalizer APO, który stroi cały dźwięk
komputera — także po zamknięciu tego okna.
"""
from __future__ import annotations

import ctypes
import sys
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from pathlib import Path
from tkinter import filedialog

from . import __version__, apo, eq, settings
from .eq import EqState

BG = "#0F1113"
PANEL = "#181B1F"
RAISED = "#21252A"
LINE = "#2E333A"
TEXT = "#ECEEF0"
DIM = "#9198A1"
FAINT = "#5A616A"
ACCENT = "#F2B134"
ON_ACCENT = "#1A1205"
TRACK = "#2A2F35"
OK = "#5FCB8A"
WARN = "#F2B134"
ERR = "#F06A5A"

APPLY_DELAY_MS = 120


def _dpi_aware() -> None:
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


class Ui:
    """Skala i czcionki zależne od DPI ekranu."""

    def __init__(self, root: tk.Tk):
        self.k = max(1.0, root.winfo_fpixels("1i") / 96.0)
        fams = set(tkfont.families(root))
        base = next((f for f in ("Segoe UI Variable Text", "Segoe UI", "Inter", "DejaVu Sans") if f in fams),
                    "TkDefaultFont")
        disp = next((f for f in ("Segoe UI Variable Display", "Segoe UI Semibold", "Segoe UI", "DejaVu Sans")
                     if f in fams), base)
        self.hero = tkfont.Font(root, family=disp, size=20, weight="bold")
        self.title = tkfont.Font(root, family=base, size=9, weight="bold")
        self.body = tkfont.Font(root, family=base, size=10)
        self.bold = tkfont.Font(root, family=base, size=10, weight="bold")
        self.small = tkfont.Font(root, family=base, size=8)
        self.small_bold = tkfont.Font(root, family=base, size=8, weight="bold")

    def px(self, v: float) -> int:
        return int(round(v * self.k))


# ---------------------------------------------------------------- kontrolki

class Toggle(tk.Canvas):
    def __init__(self, master, ui: Ui, command, bg=BG):
        self.ui = ui
        self.w, self.h = ui.px(58), ui.px(32)
        super().__init__(master, width=self.w, height=self.h, bg=bg, highlightthickness=0, cursor="hand2")
        self.on = False
        self.command = command
        self.bind("<Button-1>", lambda e: self.command(not self.on))
        self.draw()

    def set(self, on: bool):
        self.on = on
        self.draw()

    def draw(self):
        self.delete("all")
        w, h, r = self.w, self.h, self.h / 2
        fill = ACCENT if self.on else TRACK
        self.create_oval(0, 0, h, h, fill=fill, outline=fill)
        self.create_oval(w - h, 0, w, h, fill=fill, outline=fill)
        self.create_rectangle(r, 0, w - r, h, fill=fill, outline=fill)
        p = self.ui.px(4)
        x = w - h + p if self.on else p
        self.create_oval(x, p, x + h - 2 * p, h - p, fill=ON_ACCENT if self.on else DIM, outline="")


class Fader(tk.Canvas):
    """Pionowy suwak pasma jak w konsoli: zero na środku, bursztynowe wypełnienie."""

    def __init__(self, master, ui: Ui, label: str, on_change):
        self.ui = ui
        self.W, self.H = ui.px(66), ui.px(184)
        super().__init__(master, width=self.W, height=self.H, bg=PANEL, highlightthickness=0, cursor="sb_v_double_arrow")
        self.label = label
        self.value = 0.0
        self.active = True
        self.on_change = on_change
        self.top = ui.px(34)
        self.bottom = self.H - ui.px(30)
        self.bind("<Button-1>", self._drag)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<Double-Button-1>", lambda e: self._set(0.0))
        self.bind("<MouseWheel>", lambda e: self._set(self.value + (0.5 if e.delta > 0 else -0.5)))
        self.bind("<Button-4>", lambda e: self._set(self.value + 0.5))
        self.bind("<Button-5>", lambda e: self._set(self.value - 0.5))
        self.draw()

    def y_of(self, db: float) -> float:
        f = (db - eq.MIN_DB) / (eq.MAX_DB - eq.MIN_DB)
        return self.bottom - f * (self.bottom - self.top)

    def _drag(self, e):
        f = (self.bottom - e.y) / (self.bottom - self.top)
        db = eq.MIN_DB + f * (eq.MAX_DB - eq.MIN_DB)
        if abs(db) < 0.35:  # lekkie „przyciąganie” do zera
            db = 0.0
        self._set(round(db * 2) / 2)

    def _set(self, db: float):
        if not self.active:
            return
        db = eq.clamp(db, eq.MIN_DB, eq.MAX_DB)
        if db != self.value:
            self.value = db
            self.draw()
            self.on_change()

    def set(self, db: float, active: bool):
        self.value, self.active = db, active
        self.configure(cursor="sb_v_double_arrow" if active else "arrow")
        self.draw()

    def draw(self):
        self.delete("all")
        ui, cx = self.ui, self.W / 2
        lit = self.active
        # wartość
        self.create_text(cx, ui.px(14), text=eq.format_db(self.value), font=ui.small_bold,
                         fill=(ACCENT if abs(self.value) >= 0.05 else TEXT) if lit else FAINT)
        # podziałka
        for db in (-12, -6, 0, 6, 12):
            y = self.y_of(db)
            ln = ui.px(9 if db == 0 else 5)
            self.create_line(cx - ui.px(16) - ln, y, cx - ui.px(16), y, fill=DIM if db == 0 else LINE)
            self.create_line(cx + ui.px(16), y, cx + ui.px(16) + ln, y, fill=DIM if db == 0 else LINE)
        # szyna
        tw = ui.px(3)
        self.create_rectangle(cx - tw, self.top, cx + tw, self.bottom, fill=TRACK, outline="")
        y0, yv = self.y_of(0), self.y_of(self.value)
        if abs(self.value) >= 0.05:
            self.create_rectangle(cx - tw, min(y0, yv), cx + tw, max(y0, yv),
                                  fill=ACCENT if lit else FAINT, outline="")
        # gałka
        kw, kh = ui.px(17), ui.px(9)
        self.create_rectangle(cx - kw, yv - kh, cx + kw, yv + kh, fill=RAISED if lit else PANEL,
                              outline=ACCENT if lit and abs(self.value) >= 0.05 else LINE, width=max(1, ui.px(1)))
        for dy in (-ui.px(3), 0, ui.px(3)):
            self.create_line(cx - ui.px(9), yv + dy, cx + ui.px(9), yv + dy, fill=DIM if lit else LINE)
        # częstotliwość
        self.create_text(cx, self.H - ui.px(12), text=self.label, font=ui.small, fill=DIM if lit else FAINT)


class HSlider(tk.Canvas):
    """Poziomy suwak 0–100% (bas, przestrzeń)."""

    def __init__(self, master, ui: Ui, on_change, width: int):
        self.ui = ui
        self.W, self.H = width, ui.px(30)
        super().__init__(master, width=self.W, height=self.H, bg=PANEL, highlightthickness=0, cursor="sb_h_double_arrow")
        self.value = 0
        self.active = True
        self.on_change = on_change
        self.pad = ui.px(12)
        self.bind("<Button-1>", self._drag)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<Configure>", lambda e: (setattr(self, "W", e.width), self.draw()))
        self.bind("<MouseWheel>", lambda e: self._set(self.value + (5 if e.delta > 0 else -5)))
        self.bind("<Button-4>", lambda e: self._set(self.value + 5))
        self.bind("<Button-5>", lambda e: self._set(self.value - 5))

    def _drag(self, e):
        f = (e.x - self.pad) / max(1, self.W - 2 * self.pad)
        self._set(int(round(eq.clamp(f, 0, 1) * 100)))

    def _set(self, v: int):
        if not self.active:
            return
        v = int(eq.clamp(v, 0, 100))
        if v != self.value:
            self.value = v
            self.draw()
            self.on_change()

    def set(self, v: int, active: bool):
        self.value, self.active = v, active
        self.draw()

    def draw(self):
        self.delete("all")
        ui, cy, p = self.ui, self.H / 2, self.pad
        x = p + (self.W - 2 * p) * self.value / 100
        th = ui.px(3)
        self.create_rectangle(p, cy - th, self.W - p, cy + th, fill=TRACK, outline="")
        if self.value:
            self.create_rectangle(p, cy - th, x, cy + th, fill=ACCENT if self.active else FAINT, outline="")
        r = ui.px(9)
        self.create_oval(x - r, cy - r, x + r, cy + r, fill=ACCENT if self.active and self.value else RAISED,
                         outline=LINE if not self.value else "")


class Response(tk.Canvas):
    """Wykres charakterystyki: jak korektor zmienia dźwięk w całym paśmie."""

    def __init__(self, master, ui: Ui):
        self.ui = ui
        super().__init__(master, height=ui.px(86), bg=PANEL, highlightthickness=0)
        self.state = EqState()
        self.bind("<Configure>", lambda e: self.draw())

    def show(self, state: EqState):
        self.state = state
        self.draw()

    def draw(self):
        import math

        self.delete("all")
        ui = self.ui
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10:
            return
        lx, rx, ty, by = ui.px(34), w - ui.px(8), ui.px(8), h - ui.px(20)
        rng = 15.0

        def X(f):
            return lx + (rx - lx) * math.log10(f / 20) / 3

        def Y(db):
            return ty + (by - ty) * (rng - eq.clamp(db, -rng, rng)) / (2 * rng)

        for db in (-12, -6, 0, 6, 12):
            self.create_line(lx, Y(db), rx, Y(db), fill=DIM if db == 0 else LINE, dash=() if db == 0 else (2, 3))
            if db % 12 == 0:
                self.create_text(lx - ui.px(6), Y(db), text=f"{db:+d}" if db else "0", anchor="e", font=ui.small,
                                 fill=FAINT)
        for f, t in ((50, "50"), (100, "100"), (500, "500"), (1000, "1k"), (5000, "5k"), (10000, "10k")):
            self.create_line(X(f), ty, X(f), by, fill=LINE, dash=(1, 4))
            self.create_text(X(f), h - ui.px(9), text=t, font=ui.small, fill=FAINT)
        freqs = eq.log_freqs(140)
        resp = eq.response_db(self.state, freqs)
        pts = []
        for f, db in zip(freqs, resp):
            pts += [X(f), Y(db)]
        color = ACCENT if self.state.enabled else FAINT
        poly = [X(20), Y(0)] + pts + [X(20000), Y(0)]
        self.create_polygon(poly, fill="#3A2E12" if self.state.enabled else "#22262B", outline="")
        self.create_line(pts, fill=color, width=max(2, ui.px(2)), smooth=True)


class Chip(tk.Label):
    def __init__(self, master, ui: Ui, text: str, command):
        super().__init__(master, text=text, font=ui.bold, padx=ui.px(12), pady=ui.px(5), cursor="hand2",
                         bg=RAISED, fg=TEXT, bd=0)
        self.bind("<Button-1>", lambda e: command())
        self.selected = False
        self.enabled = True

    def style(self, selected: bool, enabled: bool):
        self.selected, self.enabled = selected, enabled
        if selected:
            self.configure(bg=ACCENT if enabled else FAINT, fg=ON_ACCENT)
        else:
            self.configure(bg=RAISED, fg=TEXT if enabled else FAINT)


def button(master, ui: Ui, text: str, command, primary=False, bg=PANEL):
    b = tk.Label(master, text=text, font=ui.bold, padx=ui.px(14), pady=ui.px(6), cursor="hand2",
                 bg=ACCENT if primary else bg, fg=ON_ACCENT if primary else TEXT,
                 highlightthickness=1, highlightbackground=ACCENT if primary else LINE, bd=0)
    b.bind("<Button-1>", lambda e: command())
    return b


# ---------------------------------------------------------------- okno

class App:
    def __init__(self, root: tk.Tk, settings_file: Path | None = None):
        self.root = root
        self.ui = ui = Ui(root)
        self.settings_file = settings_file or settings.settings_path()
        self.state, self.apo_pref = settings.load(self.settings_file)
        self.config_dir = apo.find_config_dir(self.apo_pref)
        self.error: apo.ApoError | None = None
        self._pending = None

        root.title("Korektor")
        root.configure(bg=BG)
        root.minsize(ui.px(1000), ui.px(560))
        self._icon()

        outer = tk.Frame(root, bg=BG, padx=ui.px(22), pady=ui.px(14))
        outer.pack(fill="both", expand=True)

        # nagłówek
        head = tk.Frame(outer, bg=BG)
        head.pack(fill="x")
        left = tk.Frame(head, bg=BG)
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text="Korektor", font=ui.hero, fg=TEXT, bg=BG).pack(anchor="w")
        tk.Label(left, text="Działa na cały dźwięk komputera: Spotify, YouTube, gry, filmy",
                 font=ui.body, fg=DIM, bg=BG).pack(anchor="w")
        right = tk.Frame(head, bg=BG)
        right.pack(side="right")
        self.power_label = tk.Label(right, text="", font=ui.bold, fg=DIM, bg=BG)
        self.power_label.pack(side="left", padx=(0, ui.px(10)))
        self.toggle = Toggle(right, ui, self.set_enabled)
        self.toggle.pack(side="left")

        # pasek stanu Equalizer APO
        self.status = tk.Frame(outer, bg=PANEL, padx=ui.px(14), pady=ui.px(8),
                               highlightthickness=1, highlightbackground=LINE)
        self.status.pack(fill="x", pady=(ui.px(12), 0))

        # zestawy
        self._section(outer, "ZESTAWY")
        chips = tk.Frame(outer, bg=BG)
        chips.pack(fill="x")
        self.chips: dict[str, Chip] = {}
        for name in list(eq.PRESETS) + [eq.CUSTOM]:
            c = Chip(chips, ui, name, lambda n=name: self.choose_preset(n))
            c.pack(side="left", padx=(0, ui.px(6)), pady=(0, ui.px(4)))
            self.chips[name] = c

        # wykres + fadery
        bands_head = tk.Frame(outer, bg=BG)
        bands_head.pack(fill="x", pady=(ui.px(12), ui.px(6)))
        tk.Label(bands_head, text="PASMA", font=ui.title, fg=DIM, bg=BG).pack(side="left")
        self.hint = tk.Label(bands_head, text="", font=ui.small, fg=DIM, bg=BG)
        self.hint.pack(side="left", padx=ui.px(12))
        button(bands_head, ui, "Wyzeruj", self.reset, bg=BG).pack(side="right")

        main = tk.Frame(outer, bg=BG)
        main.pack(fill="x")
        board = tk.Frame(main, bg=PANEL, padx=ui.px(14), pady=ui.px(10),
                         highlightthickness=1, highlightbackground=LINE)
        board.pack(side="left", fill="y")
        side = tk.Frame(main, bg=BG)
        side.pack(side="left", fill="both", expand=True, padx=(ui.px(12), 0))
        self.response = Response(board, ui)
        self.response.pack(fill="x")
        tk.Frame(board, bg=LINE, height=1).pack(fill="x", pady=ui.px(6))
        row = tk.Frame(board, bg=PANEL)
        row.pack()
        self.faders = []
        for hz in eq.BANDS:
            f = Fader(row, ui, eq.format_freq(hz), self.on_bands)
            f.pack(side="left", padx=ui.px(2))
            self.faders.append(f)

        # bas i przestrzeń
        self.bass, self.bass_val = self._knob_panel(side, "Wzmocnienie basu", "Półka poniżej 100 Hz", self.on_extra)
        self.surround, self.surround_val = self._knob_panel(side, "Przestrzeń", "Szersza scena stereo", self.on_extra)

        foot = tk.Label(outer, text=f"Korektor {__version__} · zmiany działają od razu, także po zamknięciu okna",
                        font=ui.small, fg=FAINT, bg=BG)
        foot.pack(anchor="w", pady=(ui.px(10), 0))

        self.refresh()
        self.render_status()
        if self.config_dir:
            self.schedule_apply(0)

    # -------------------------------------------------------------- budowa
    def _section(self, parent, text):
        tk.Label(parent, text=text, font=self.ui.title, fg=DIM, bg=BG).pack(anchor="w", pady=(self.ui.px(12), self.ui.px(6)))

    def _knob_panel(self, parent, title, sub, cb):
        ui = self.ui
        p = tk.Frame(parent, bg=PANEL, padx=ui.px(14), pady=ui.px(12), highlightthickness=1,
                     highlightbackground=LINE)
        p.pack(fill="x", pady=(0, ui.px(10)))
        top = tk.Frame(p, bg=PANEL)
        top.pack(fill="x")
        tk.Label(top, text=title, font=ui.bold, fg=TEXT, bg=PANEL).pack(side="left")
        val = tk.Label(top, text="0%", font=ui.bold, fg=DIM, bg=PANEL)
        val.pack(side="right")
        tk.Label(p, text=sub, font=ui.small, fg=DIM, bg=PANEL).pack(anchor="w")
        s = HSlider(p, ui, cb, ui.px(220))
        s.pack(fill="x", pady=(ui.px(8), 0))
        return s, val

    def _icon(self):
        try:
            img = tk.PhotoImage(width=32, height=32)
            img.put(BG, to=(0, 0, 32, 32))
            for i, h in enumerate((12, 22, 16, 26, 10)):
                x = 3 + i * 6
                img.put(ACCENT, to=(x, 30 - h, x + 4, 30))
            self.root.iconphoto(True, img)
            self._icon_img = img
        except tk.TclError:
            pass

    # -------------------------------------------------------------- akcje
    def set_enabled(self, on: bool):
        self.state.enabled = on
        self.refresh()
        self.schedule_apply()

    def choose_preset(self, name: str):
        if not self.state.enabled:
            return
        if name in eq.PRESETS:
            self.state.gains = [float(v) for v in eq.PRESETS[name]]
        self.state.preset = name
        self.refresh()
        self.schedule_apply()

    def reset(self):
        if not self.state.enabled:
            return
        self.state.gains = [0.0] * len(eq.BANDS)
        self.state.bass = 0
        self.state.surround = 0
        self.state.preset = "Płaski"
        self.refresh()
        self.schedule_apply()

    def on_bands(self):
        self.state.gains = [f.value for f in self.faders]
        self.state.preset = eq.matching_preset(self.state.gains)
        self.refresh(faders=False)
        self.schedule_apply()

    def on_extra(self):
        self.state.bass = self.bass.value
        self.state.surround = self.surround.value
        self.refresh(faders=False)
        self.schedule_apply()

    def refresh(self, faders: bool = True):
        s, on = self.state, self.state.enabled
        self.toggle.set(on)
        self.power_label.configure(text="WŁĄCZONY" if on else "WYŁĄCZONY", fg=ACCENT if on else DIM)
        for name, chip in self.chips.items():
            chip.style(name == s.preset, on)
        if faders:
            for f, g in zip(self.faders, s.gains):
                f.set(g, on)
            self.bass.set(s.bass, on)
            self.surround.set(s.surround, on)
        self.bass_val.configure(text=f"{eq.format_db(eq.bass_db(s.bass))} · {s.bass}%" if s.bass else "0%",
                                fg=ACCENT if on and s.bass else DIM)
        self.surround_val.configure(text=f"{s.surround}%", fg=ACCENT if on and s.surround else DIM)
        self.hint.configure(text="Przeciągnij suwak · kółko myszy ±0,5 dB · dwuklik = 0 dB" if on else
                            "Włącz korektor przełącznikiem u góry, aby zmieniać dźwięk.")
        self.response.show(s)

    # -------------------------------------------------------------- zapis
    def schedule_apply(self, delay: int = APPLY_DELAY_MS):
        if self._pending is not None:
            self.root.after_cancel(self._pending)
        self._pending = self.root.after(delay, self.apply_now)

    def apply_now(self):
        self._pending = None
        try:
            settings.save(self.settings_file, self.state, self.apo_pref)
        except OSError:
            pass
        if not self.config_dir:
            return
        try:
            apo.apply(self.config_dir, eq.build_config(self.state))
            err_before, self.error = self.error, None
            if err_before:
                self.render_status()
        except apo.ApoError as e:
            self.error = e
            self.render_status()

    def flush(self):
        if self._pending is not None:
            self.root.after_cancel(self._pending)
            self.apply_now()

    # -------------------------------------------------------------- stan APO
    def render_status(self):
        ui = self.ui
        for w in self.status.winfo_children():
            w.destroy()
        if self.error:
            dot, color = "●", ERR
            msg = str(self.error)
            actions = [("Uruchom jako administrator", self.relaunch_admin, True)] if self.error.needs_admin else []
        elif self.config_dir:
            dot, color = "●", OK
            msg = f"Połączono z Equalizer APO  ·  {_short(self.config_dir)}"
            actions = [("Zmień folder…", self.pick_folder, False)]
        else:
            dot, color = "●", WARN
            msg = ("Potrzebny darmowy sterownik Equalizer APO: zainstaluj go, w Configuratorze zaznacz "
                   "głośniki/słuchawki i uruchom ponownie komputer.")
            actions = [("Pobierz Equalizer APO", lambda: webbrowser.open(apo.DOWNLOAD_URL), True),
                       ("Wskaż folder…", self.pick_folder, False), ("Sprawdź ponownie", self.recheck, False)]
        line = tk.Frame(self.status, bg=PANEL)
        line.pack(fill="x")
        tk.Label(line, text=dot, font=ui.bold, fg=color, bg=PANEL).pack(side="left", padx=(0, ui.px(8)))
        tk.Label(line, text=msg, font=ui.body, fg=TEXT, bg=PANEL, justify="left", anchor="w",
                 wraplength=ui.px(640 if len(actions) <= 1 else 900)).pack(side="left", fill="x", expand=True)
        if len(actions) == 1:
            text, cmd, primary = actions[0]
            button(line, ui, text, cmd, primary=primary).pack(side="right", padx=(ui.px(6), 0))
        elif actions:
            row = tk.Frame(self.status, bg=PANEL)
            row.pack(fill="x", pady=(ui.px(8), 0), padx=(ui.px(18), 0))
            for text, cmd, primary in actions:
                button(row, ui, text, cmd, primary=primary).pack(side="left", padx=(0, ui.px(6)))

    def recheck(self):
        self.config_dir = apo.find_config_dir(self.apo_pref)
        self.error = None
        self.render_status()
        if self.config_dir:
            self.schedule_apply(0)

    def pick_folder(self):
        d = filedialog.askdirectory(title="Folder config Equalizer APO (z plikiem config.txt)")
        if not d:
            return
        if not apo.is_config_dir(Path(d)):
            self.error = apo.ApoError(f"W {d} nie ma pliku config.txt — to nie jest folder config Equalizer APO.")
            self.render_status()
            return
        self.apo_pref = d
        self.recheck()

    def relaunch_admin(self):
        if sys.platform != "win32":
            return
        self.flush()
        if getattr(sys, "frozen", False):
            exe, params = sys.executable, ""
        else:
            exe = sys.executable.replace("python.exe", "pythonw.exe")
            params = "-m korektor"
        cwd = str(Path(__file__).resolve().parents[1])
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, cwd, 1)
        if rc > 32:
            self.root.destroy()


def _short(p: Path, limit: int = 60) -> str:
    s = str(p)
    return s if len(s) <= limit else s[:20] + "…" + s[-(limit - 21):]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--self-test" in argv:
        # Szybki test zbudowanego .exe: logika i zapis do folderu z KOREKTOR_APO_DIR.
        text = eq.build_config(EqState(enabled=True, gains=list(eq.PRESETS["Rock"]), bass=30, surround=20))
        d = apo.find_config_dir()
        if d:
            apo.apply(d, text)
        return 0 if "Filter: ON PK" in text else 1
    if "--odlacz" in argv:
        d = apo.find_config_dir(settings.load(settings.settings_path())[1])
        if d:
            apo.remove_include(d)
            (d / apo.OUR_FILE).unlink(missing_ok=True)
        return 0
    _dpi_aware()
    root = tk.Tk()
    app = App(root)

    def close():
        app.flush()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
