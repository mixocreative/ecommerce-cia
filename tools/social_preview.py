#!/usr/bin/env python3
"""Render the 1280x640 GitHub social-preview PNGs for cia and ecommerce-cia.

Usage:  python tools/social_preview.py [out-dir]        (default: .github/)
Needs Pillow and a Traditional-Chinese Noto Sans CJK on the machine (Windows path below; edit FONT_DIR).
Upload the PNG by hand: repo -> Settings -> Social preview (GitHub has no API for it).
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path(r"C:\Windows\Fonts")
BLACK = FONT_DIR / "NotoSansCJKtc-Black.otf"
BOLD = FONT_DIR / "NotoSansCJKtc-Bold.otf"
REG = FONT_DIR / "NotoSansCJKtc-Regular.otf"
W, H = 1280, 640

CARDS = {
    "ecommerce-cia": {
        "kicker": "AI SKILL · CLAUDE CODE · CODEX · CURSOR",
        "title": "台灣電商金流\n串接與完整性審查",
        "sub": "藍新 NewebPay · 綠界 ECPay（另含 PAYUNi、TapPay）",
        "chips": ["超商取貨付款", "電子發票", "個資法", "實機探針驗證", "新手引導"],
        "foot": "github.com/mixocreative/ecommerce-cia",
        "accent": (30, 180, 140),
        "ground": (16, 24, 32),
    },
    "cia": {
        "kicker": "AI SKILL · CLAUDE CODE · CODEX · CURSOR",
        "title": "程式碼完整性審查\nCode Integrity Auditor",
        "sub": "審查元件之間的接線，而不是單一函式",
        "chips": ["dead control", "TOCTOU", "fail-open", "blind watchdog", "Viable System Model"],
        "foot": "github.com/mixocreative/cia",
        "accent": (235, 170, 60),
        "ground": (22, 20, 30),
    },
}


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def render(name: str, spec: dict, out: Path) -> Path:
    img = Image.new("RGB", (W, H), spec["ground"])
    d = ImageDraw.Draw(img)
    ax, ay, az = spec["accent"]
    # left accent bar + faint grid, so the card is not a flat rectangle
    d.rectangle([0, 0, 14, H], fill=spec["accent"])
    for x in range(80, W, 80):
        d.line([(x, 0), (x, H)], fill=(spec["ground"][0] + 8, spec["ground"][1] + 8, spec["ground"][2] + 8), width=1)
    x0 = 72
    d.text((x0, 56), spec["kicker"], font=font(BOLD, 22), fill=(ax, ay, az))
    y = 100
    for line in spec["title"].split("\n"):
        d.text((x0, y), line, font=font(BLACK, 84), fill=(245, 245, 240))
        y += 100
    d.text((x0, y + 12), spec["sub"], font=font(REG, 34), fill=(200, 205, 210))
    # chips
    cy = y + 84
    cx = x0
    f = font(BOLD, 24)
    for chip in spec["chips"]:
        tw = d.textlength(chip, font=f)
        d.rounded_rectangle([cx, cy, cx + tw + 34, cy + 46], radius=23, outline=(ax, ay, az), width=2)
        d.text((cx + 17, cy + 8), chip, font=f, fill=(ax, ay, az))
        cx += tw + 50
    d.text((x0, H - 72), spec["foot"], font=font(REG, 26), fill=(150, 155, 160))
    d.text((W - 72 - d.textlength("MIT · 繁體中文 · English", font=font(REG, 22)), H - 68), "MIT · 繁體中文 · English", font=font(REG, 22), fill=(150, 155, 160))
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"social-preview-{name}.png"
    img.save(p, optimize=True)
    return p


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".github")
    for name, spec in CARDS.items():
        print(render(name, spec, out))
