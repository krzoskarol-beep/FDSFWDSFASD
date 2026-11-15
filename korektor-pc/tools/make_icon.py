"""Rysuje ikonę Korektora (bursztynowe słupki na ciemnym tle) do pliku .ico. Wymaga Pillow."""
import sys

from PIL import Image, ImageDraw

BG, ACCENT = (15, 17, 19, 255), (242, 177, 52, 255)


def draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = size * 0.22
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=r, fill=BG)
    bars = (0.42, 0.72, 0.55, 0.85, 0.35)
    pad, gap = size * 0.17, size * 0.05
    w = (size - 2 * pad - gap * (len(bars) - 1)) / len(bars)
    for i, h in enumerate(bars):
        x = pad + i * (w + gap)
        top = size - pad - h * (size - 2 * pad)
        d.rounded_rectangle((x, top, x + w, size - pad), radius=w * 0.35, fill=ACCENT)
    return img


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "korektor.ico"
    big = draw(256)
    big.save(out, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(out)
