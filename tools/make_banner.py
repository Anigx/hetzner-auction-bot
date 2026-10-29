"""Baut das Banner für das README (docs/assets/banner.png).

Aufruf: .venv/Scripts/python.exe tools/make_banner.py
Braucht Pillow (nur zum Bauen des Bildes, nicht zur Laufzeit).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 640
BG_TOP = (10, 15, 16)
BG_BOTTOM = (14, 24, 24)
GREEN = (0, 168, 143)
GREEN_LIGHT = (77, 214, 190)
WHITE = (240, 244, 244)
GRAY = (150, 162, 162)
CARD = (21, 29, 32)
CARD_BORDER = (36, 48, 51)
CHIP_BG = (17, 27, 26)
CHIP_BORDER = (31, 58, 52)

FONT_DIR = Path("C:/Windows/Fonts")
OUT = Path("docs/assets/banner.png")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


def gradient(draw: ImageDraw.ImageDraw) -> None:
    for y in range(H):
        t = y / (H - 1)
        color = tuple(int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM))
        draw.line([(0, y), (W, y)], fill=color)


def grid(draw: ImageDraw.ImageDraw) -> None:
    for x in range(0, W, 48):
        draw.line([(x, 0), (x, H)], fill=(18, 26, 27))
    for y in range(0, H, 48):
        draw.line([(0, y), (W, y)], fill=(18, 26, 27))


def chip(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, f: ImageFont.FreeTypeFont) -> int:
    pad_x, pad_y = 18, 10
    left, top, right, bottom = draw.textbbox((0, 0), text, font=f)
    width = (right - left) + pad_x * 2
    height = (bottom - top) + pad_y * 2
    draw.rounded_rectangle(
        [x, y, x + width, y + height], radius=height // 2, fill=CHIP_BG, outline=CHIP_BORDER
    )
    draw.text((x + pad_x, y + pad_y - top), text, font=f, fill=GREEN_LIGHT)
    return width


def build() -> None:
    image = Image.new("RGB", (W, H), BG_TOP)
    draw = ImageDraw.Draw(image)
    gradient(draw)
    grid(draw)

    # Akzentkante links
    draw.rectangle([0, 0, 6, H], fill=GREEN)

    label = font("consolab.ttf", 18)
    title = font("segoeuib.ttf", 54)
    subtitle = font("segoeui.ttf", 24)
    chip_font = font("segoeuib.ttf", 17)

    draw.text((80, 118), "S E R V E R B Ö R S E", font=label, fill=GREEN)
    draw.text((78, 152), "Hetzner Auction Bot", font=title, fill=WHITE)
    draw.line([(80, 230), (188, 230)], fill=GREEN, width=5)
    draw.text(
        (80, 258),
        "Deals aus der Serverbörse direkt in Discord.",
        font=subtitle,
        fill=GRAY,
    )

    x = 80
    for text in ("10 Min Polling", "Slash-Commands", "Preisverfall", "Docker"):
        x += chip(draw, x, 344, text, chip_font) + 12

    draw.text((80, 500), "github.com/Anigx/hetzner-auction-bot", font=font("consola.ttf", 19), fill=(96, 110, 110))

    # Karte rechts: ein Treffer, wie er im Kanal landet
    cx, cy, cw, ch = 716, 150, 484, 348
    draw.rounded_rectangle([cx, cy, cx + cw, cy + ch], radius=20, fill=CARD, outline=CARD_BORDER, width=2)
    draw.rounded_rectangle([cx, cy, cx + 6, cy + ch], radius=0, fill=GREEN)

    draw.text((cx + 34, cy + 30), "Hetzner Serverbörse", font=font("segoeui.ttf", 19), fill=GRAY)
    draw.text((cx + 34, cy + 66), "AMD Ryzen 9 5950X", font=font("segoeuib.ttf", 33), fill=WHITE)
    draw.text(
        (cx + 34, cy + 116),
        "16 Kerne · 64 GB ECC · 2 TB NVMe",
        font=font("segoeui.ttf", 21),
        fill=(184, 194, 194),
    )
    draw.text(
        (cx + 34, cy + 150), "FSN1-DC14 · 1 Gbit/s · unlimited", font=font("segoeui.ttf", 21), fill=(184, 194, 194)
    )

    draw.text((cx + 34, cy + 206), "39", font=font("segoeuib.ttf", 62), fill=GREEN_LIGHT)
    draw.text((cx + 112, cy + 236), "€ / Monat", font=font("segoeui.ttf", 24), fill=GRAY)

    badge = font("segoeuib.ttf", 17)
    draw.rounded_rectangle([cx + 34, cy + 290, cx + 132, cy + 322], radius=16, fill=(19, 61, 52))
    draw.text((cx + 48, cy + 298), "PREISFALL", font=badge, fill=GREEN_LIGHT)
    draw.text(
        (cx + 146, cy + 298), "vorher 45 €", font=font("segoeui.ttf", 19), fill=(120, 132, 132)
    )

    # Fusszeile
    draw.line([(80, 596), (1200, 596)], fill=(24, 34, 35), width=1)
    foot = font("segoeui.ttf", 17)
    draw.text((80, 612), "Open Source · MIT-Lizenz", font=foot, fill=(92, 104, 104))
    right = "Python 3.12 · discord.py · SQLite"
    box = draw.textbbox((0, 0), right, font=foot)
    draw.text((1200 - (box[2] - box[0]), 612), right, font=foot, fill=(92, 104, 104))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT, "PNG", optimize=True)
    print(f"{OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    build()
