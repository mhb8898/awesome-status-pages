#!/usr/bin/env python3
"""Render assets/social-preview.png (1280x640), used as the GitHub social preview and og:image."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "social-preview.png"
SCALE = 2  # draw at 2x, downsample for smooth edges
W, H = 1280 * SCALE, 640 * SCALE

BG = (13, 17, 23)
PANEL = (22, 27, 34)
BORDER = (48, 54, 61)
TEXT = (230, 237, 243)
MUTED = (139, 148, 158)
GREEN = (63, 185, 80)
AMBER = (210, 153, 34)


def font(size, bold=False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(c, size * SCALE)
    return ImageFont.load_default()


def s(*v):
    return tuple(x * SCALE for x in v)


img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

# Left: title block
d.text(s(72, 150), "Awesome", font=font(76, True), fill=TEXT)
d.text(s(72, 238), "Status Pages", font=font(76, True), fill=TEXT)
d.text(s(76, 350), "Open source & self-hosted status page", font=font(28), fill=MUTED)
d.text(s(76, 388), "tools ranked by GitHub stars,", font=font(28), fill=MUTED)
d.text(s(76, 426), "updated every week.", font=font(28), fill=MUTED)
d.text(s(76, 540), "github.com/mhb8898/awesome-status-pages", font=font(22), fill=MUTED)

# Right: a mock status page panel
x0, y0, x1, y1 = 760, 92, 1208, 548
d.rounded_rectangle(s(x0, y0, x1, y1), radius=18 * SCALE, fill=PANEL, outline=BORDER, width=2 * SCALE)
d.rounded_rectangle(s(x0 + 24, y0 + 24, x1 - 24, y0 + 84), radius=10 * SCALE, fill=(35, 134, 54))
d.text(s(x0 + 48, y0 + 40), "All systems operational", font=font(24, True), fill=(255, 255, 255))

rows = [
    ("Self-hosted tools", ()),
    ("Hosted services", (6,)),
    ("Public pages", ()),
    ("Cloud providers", (3, 4)),
]
y = y0 + 116
for label, incidents in rows:
    d.ellipse(s(x0 + 40, y + 6, x0 + 58, y + 24), fill=GREEN)
    d.text(s(x0 + 76, y), label, font=font(24), fill=TEXT)
    # 90-day-style uptime bars, right-aligned
    bx = x1 - 40 - 10 * 9
    for i in range(10):
        c = AMBER if i in incidents else GREEN
        d.rounded_rectangle(s(bx + i * 9, y + 2, bx + i * 9 + 5, y + 28), radius=2 * SCALE, fill=c)
    y += 88

OUT.parent.mkdir(exist_ok=True)
img.resize((1280, 640), Image.LANCZOS).save(OUT, optimize=True)
print(OUT)
