"""Draw web/demo/{dinner,sarcasm,wave}.jpg: simple stick figures + a big 'DEMO INPUT' label.

No real photos, no faces with features: just shapes, so nothing identifiable is committed.
Deterministic: same pixels every run. Run: python scripts/make_demo_images.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web/demo"
W, H = 640, 480
BG = (38, 50, 56)
FG = (236, 239, 241)
ACCENT = (255, 213, 79)


def font(size: int) -> ImageFont.ImageFont:
    for name in ("DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def figure(d: ImageDraw.ImageDraw, x: int, y: int, s: float = 1.0) -> None:
    """Stick figure standing at (x, y) = head centre. Blank head, no facial features."""
    r = int(28 * s)
    d.ellipse([x - r, y - r, x + r, y + r], outline=FG, width=4)
    d.line([x, y + r, x, y + int(150 * s)], fill=FG, width=5)
    hip = y + int(150 * s)
    d.line([x, hip, x - int(40 * s), hip + int(90 * s)], fill=FG, width=5)
    d.line([x, hip, x + int(40 * s), hip + int(90 * s)], fill=FG, width=5)


def arm(d: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int) -> None:
    d.line([x0, y0, x1, y1], fill=FG, width=5)


def label(d: ImageDraw.ImageDraw, caption: str) -> None:
    d.rectangle([0, 0, W, 70], fill=(183, 28, 28))
    d.text((W // 2, 35), "DEMO INPUT", font=font(44), fill=(255, 255, 255), anchor="mm")
    d.rectangle([0, H - 44, W, H], fill=(0, 0, 0))
    d.text((W // 2, H - 22), caption, font=font(20), fill=ACCENT, anchor="mm")


def dinner(d: ImageDraw.ImageDraw) -> None:
    x, y = 320, 150
    figure(d, x, y, 1.1)
    sh = y + 60
    arm(d, x, sh, x - 70, sh + 80)
    arm(d, x, sh, x + 110, sh + 20)  # open hand toward the camera
    d.ellipse([x + 105, sh + 5, x + 135, sh + 35], outline=ACCENT, width=4)
    label(d, "Scripted scene: person offering an open hand")


def sarcasm(d: ImageDraw.ImageDraw) -> None:
    x, y = 220, 150
    figure(d, x, y, 1.1)
    sh = y + 60
    arm(d, x, sh, x - 70, sh - 30)  # exaggerated shrug: both hands up
    arm(d, x - 70, sh - 30, x - 90, sh - 70)
    arm(d, x, sh, x + 70, sh - 30)
    arm(d, x + 70, sh - 30, x + 90, sh - 70)
    # laptop showing a calendar
    d.rectangle([380, 220, 580, 340], outline=FG, width=4)
    d.line([360, 350, 600, 350], fill=FG, width=6)
    for row in range(3):
        for col in range(5):
            cx, cy = 395 + col * 37, 240 + row * 32
            fill = ACCENT if (row, col) == (1, 2) else None
            d.rectangle([cx, cy, cx + 28, cy + 22], outline=FG, fill=fill, width=2)
    label(d, "Scripted scene: shrug while looking at a calendar")


def wave(d: ImageDraw.ImageDraw) -> None:
    x, y = 420, 190
    figure(d, x, y, 0.8)  # across the room: smaller
    sh = y + 45
    arm(d, x, sh, x - 50, sh + 60)
    arm(d, x, sh, x + 50, sh - 70)  # raised hand
    hx, hy = x + 50, sh - 70
    d.ellipse([hx - 14, hy - 14, hx + 14, hy + 14], outline=ACCENT, width=4)
    for i in range(3):  # motion marks
        d.arc([hx - 40 - i * 12, hy - 40 - i * 12, hx + 40 + i * 12, hy + 40 + i * 12],
              start=300, end=340, fill=ACCENT, width=3)
    d.line([0, 400, W, 400], fill=(84, 110, 122), width=3)  # floor
    label(d, "Scripted scene: someone across the room waving")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, draw in (("dinner", dinner), ("sarcasm", sarcasm), ("wave", wave)):
        img = Image.new("RGB", (W, H), BG)
        draw(ImageDraw.Draw(img))
        img.save(OUT / f"{name}.jpg", "JPEG", quality=85)
        print(f"wrote web/demo/{name}.jpg")


if __name__ == "__main__":
    main()
