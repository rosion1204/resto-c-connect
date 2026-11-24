#!/usr/bin/env python3
"""Apply Resto C Connect branding to the RustDesk source tree.

Run from the repository root (CI does this right after checkout):
    pip install pillow fonttools
    python branding/apply_branding.py

Based on RustDesk (https://github.com/rustdesk/rustdesk), AGPL-3.0.
"""
import io
import os
import pathlib
import sys
import urllib.request
import zipfile

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from PIL import Image, ImageDraw, ImageFont

APP_NAME = "RestoC-Connect"          # technical name: no spaces (service / exe / uri)
DISPLAY_NAME = "Resto C Connect"     # name shown in file properties and logo
SERVER = "cabinet.restocalculator.kz"
KEY = "wHv1DOAA6+8RhfZubN38qHPBi6tLPZB9SW3r+jvZIGg="
RED = "#A10A0A"
DARK = "#1F1715"
MONO = "RC"

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = ROOT / "branding" / "_build"
WORK.mkdir(parents=True, exist_ok=True)


def patch(path, old, new):
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    if old not in text:
        sys.exit(f"[branding] pattern not found in {path}: {old!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"[branding] patched {path}")


# ---------------------------------------------------------------- fonts
def get_fonts():
    """Inter (brand font) from GitHub; fall back to Segoe UI Bold."""
    bold = WORK / "Inter-Bold.otf"
    xbold = WORK / "Inter-ExtraBold.otf"
    if not xbold.exists():
        try:
            url = "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip"
            data = urllib.request.urlopen(url, timeout=60).read()
            z = zipfile.ZipFile(io.BytesIO(data))
            for n in z.namelist():
                base = os.path.basename(n)
                if base == "Inter-ExtraBold.otf":
                    xbold.write_bytes(z.read(n))
                elif base == "Inter-Bold.otf":
                    bold.write_bytes(z.read(n))
        except Exception as e:  # noqa: BLE001
            print(f"[branding] Inter download failed: {e}")
    if xbold.exists() and bold.exists():
        return str(xbold), str(bold)
    seg = r"C:\Windows\Fonts\segoeuib.ttf"
    print("[branding] using Segoe UI Bold")
    return seg, seg


FONT_X, FONT_B = get_fonts()


# ---------------------------------------------------------------- icons
def render(size):
    big = size * 4
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle([0, 0, big - 1, big - 1], radius=int(big * 0.22), fill=RED)
    f = ImageFont.truetype(FONT_X, int(big * 0.5))
    b = dr.textbbox((0, 0), MONO, font=f)
    fs = int(big * 0.5 * (big * 0.62) / (b[2] - b[0]))
    f = ImageFont.truetype(FONT_X, fs)
    b = dr.textbbox((0, 0), MONO, font=f)
    w, h = b[2] - b[0], b[3] - b[1]
    dr.text(((big - w) / 2 - b[0], (big - h) / 2 - b[1]), MONO, font=f, fill="white")
    return img.resize((size, size), Image.LANCZOS)


def icon_svg():
    font = TTFont(FONT_X)
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    pen = SVGPathPen(gs)
    x = 0
    xmin = ymin = 1e9
    xmax = ymax = -1e9
    for ch in MONO:
        g = cmap[ord(ch)]
        gs[g].draw(TransformPen(pen, (1, 0, 0, 1, x, 0)))
        bp = BoundsPen(gs)
        gs[g].draw(bp)
        if bp.bounds:
            x0, y0, x1, y1 = bp.bounds
            xmin, xmax = min(xmin, x0 + x), max(xmax, x1 + x)
            ymin, ymax = min(ymin, y0), max(ymax, y1)
        x += gs[g].width
    S = 1024
    tw, th = xmax - xmin, ymax - ymin
    sc = S * 0.62 / tw
    tx = (S - tw * sc) / 2 - xmin * sc
    ty = (S + th * sc) / 2 + ymin * sc
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}" width="{S}" height="{S}">'
        f'<rect width="{S}" height="{S}" rx="{int(S * 0.22)}" fill="{RED}"/>'
        f'<path fill="#FFFFFF" transform="translate({tx:.2f},{ty:.2f}) scale({sc:.5f},{-sc:.5f})" '
        f'd="{pen.getCommands()}"/></svg>\n'
    )


def logo(color):
    W, H = 600, 120
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ic = render(104)
    img.paste(ic, (0, 8), ic)
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT_B, 52)
    b = d.textbbox((0, 0), DISPLAY_NAME, font=f)
    d.text((124, (H - (b[3] - b[1])) / 2 - b[1]), DISPLAY_NAME, font=f, fill=color)
    return img


def out(rel):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    print(f"[branding] wrote {rel}")
    return p


ICO = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
render(256).save(out("res/icon.ico"), sizes=ICO)
render(256).save(out("flutter/windows/runner/resources/app_icon.ico"), sizes=ICO)
render(64).save(out("res/tray-icon.ico"), sizes=ICO[:5])
render(1024).save(out("res/icon.png"))
render(1024).save(out("flutter/assets/icon.png"))
for s, name in [(32, "32x32.png"), (64, "64x64.png"), (128, "128x128.png"),
                (256, "128x128@2x.png"), (512, "mac-icon.png")]:
    render(s).save(out(f"res/{name}"))
svg = icon_svg()
for rel in ["flutter/assets/icon.svg", "res/logo.svg", "res/scalable.svg"]:
    out(rel).write_text(svg, encoding="utf-8")
logo(DARK).save(out("flutter/assets/logo.png"))
logo(DARK).save(out("flutter/assets/logo_light.png"))
logo("#FFFFFF").save(out("flutter/assets/logo_dark.png"))

# ---------------------------------------------------------------- code
cfg = "libs/hbb_common/src/config.rs"
patch(cfg, 'RwLock::new("RustDesk".to_owned())', f'RwLock::new("{APP_NAME}".to_owned())')
patch(cfg, 'pub const RENDEZVOUS_SERVERS: &[&str] = &["rs-ny.rustdesk.com"];',
      f'pub const RENDEZVOUS_SERVERS: &[&str] = &["{SERVER}"];')
patch(cfg, 'pub const RS_PUB_KEY: &str = "OeVuKk5nlHiXp+APNn0Y3pC1Iwpwn44JGqrQCsWqmBw=";',
      f'pub const RS_PUB_KEY: &str = "{KEY}";')
patch("flutter/windows/runner/main.cpp", 'std::wstring app_name = L"RustDesk";',
      f'std::wstring app_name = L"{APP_NAME}";')
rc = "flutter/windows/runner/Runner.rc"
patch(rc, '"FileDescription", "RustDesk Remote Desktop"', f'"FileDescription", "{DISPLAY_NAME}"')
patch(rc, '"ProductName", "RustDesk"', f'"ProductName", "{DISPLAY_NAME}"')
patch(rc, '"CompanyName", "Purslane Tech Pte. Ltd."', '"CompanyName", "Resto Calculator"')

print("[branding] done")
