#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ファビコン・OGP 画像の生成と head タグ出力。"""

from __future__ import annotations

import html
import re
from pathlib import Path

from tools.site_config import (
    brand_logo_lines,
    brand_name,
    clean_origin,
    exam_name,
    public_url,
    resolve_site_root,
    theme,
)

FONT_BOLD = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
FONT_REG = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
BRAND_DIR = "assets/brand"
MARKER = "<!--BRAND_ASSET_HEAD-->"


def theme_ink() -> str:
    t = theme()
    return str(t.get("accent") or "#333333")


def theme_page_bg() -> str:
    t = theme()
    return str(t.get("background") or "#f0f0f1")


def theme_text() -> str:
    t = theme()
    return str(t.get("text") or "#111111")


def theme_text_muted() -> str:
    t = theme()
    return str(t.get("textMuted") or "#555555")


def brand_assets_root(site_root: Path | None = None) -> Path:
    root = (site_root or resolve_site_root()).resolve()
    return root / BRAND_DIR


def assets_ready(site_root: Path | None = None) -> bool:
    d = brand_assets_root(site_root)
    return (d / "og-image.png").is_file() and (d / "favicon-32.png").is_file()


def _fit_font(draw, text: str, max_w: int, start_size: int, *, bold: bool = True):
    from PIL import ImageFont

    path = FONT_BOLD if bold else FONT_REG
    size = start_size
    while size >= 6:
        font = ImageFont.truetype(path, size, index=0)
        if draw.textlength(text, font=font) <= max_w:
            return font, size
        size -= 1
    return ImageFont.truetype(path, 6, index=0), 6


def _draw_logo_mark(
    draw,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    top: str,
    bottom: str,
    bg: str,
    fg: str,
    radius: int,
) -> None:
    draw.rounded_rectangle([x, y, x + width, y + height], radius=radius, fill=bg)
    pad_x = max(8, width // 10)
    inner_w = width - pad_x * 2
    top_font, top_size = _fit_font(draw, top, inner_w, max(8, height // 4), bold=True)
    bottom_font, bottom_size = _fit_font(draw, bottom, inner_w, max(7, height // 5), bold=True)
    gap = max(2, height // 24)
    block_h = top_size + gap + bottom_size
    ty = y + (height - block_h) // 2
    tw = draw.textlength(top, font=top_font)
    bw = draw.textlength(bottom, font=bottom_font)
    draw.text((x + (width - tw) / 2, ty), top, fill=fg, font=top_font)
    draw.text((x + (width - bw) / 2, ty + top_size + gap), bottom, fill=fg, font=bottom_font)


def favicon_top_line() -> str:
    top, _ = brand_logo_lines()
    if len(top) > 4:
        from tools.site_config import brand_mark

        return brand_mark()
    return top


def render_favicon(size: int):
    from PIL import Image, ImageDraw

    top, bottom = brand_logo_lines()
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = max(1, size // 16)
    inner = size - margin * 2

    if size <= 32:
        label = favicon_top_line()
        draw.rounded_rectangle(
            [margin, margin, size - margin, size - margin],
            radius=max(2, size // 8),
            fill=theme_ink(),
        )
        font, _ = _fit_font(draw, label, inner - 4, max(6, size // 2), bold=True)
        tw = draw.textlength(label, font=font)
        th = font.size
        draw.text(
            ((size - tw) / 2, (size - th) / 2),
            label,
            fill="#ffffff",
            font=font,
        )
        return img

    _draw_logo_mark(
        draw,
        x=margin,
        y=margin,
        width=inner,
        height=inner,
        top=top,
        bottom=bottom,
        bg=theme_ink(),
        fg="#ffffff",
        radius=max(2, size // 8),
    )
    return img


def render_og_image():
    from PIL import Image, ImageDraw

    w, h = 1200, 630
    top, bottom = brand_logo_lines()
    name = brand_name()
    exam = exam_name()
    bg = theme_page_bg()
    ink = theme_ink()
    text = theme_text()
    muted = theme_text_muted()

    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    box_w, box_h = 300, 280
    box_x, box_y = 80, (h - box_h) // 2
    _draw_logo_mark(
        draw,
        x=box_x,
        y=box_y,
        width=box_w,
        height=box_h,
        top=top,
        bottom=bottom,
        bg=ink,
        fg="#ffffff",
        radius=12,
    )

    tx = box_x + box_w + 56
    name_font, name_size = _fit_font(draw, name, w - tx - 80, 64, bold=True)
    exam_font, exam_size = _fit_font(draw, exam, w - tx - 80, 40, bold=False)
    tagline = "過去問・演習・用語解説"
    tag_font, _ = _fit_font(draw, tagline, w - tx - 80, 34, bold=False)

    draw.text((tx, box_y + 24), name, fill=text, font=name_font)
    draw.text((tx, box_y + 24 + name_size + 20), exam, fill=muted, font=exam_font)
    draw.text((tx, box_y + 24 + name_size + 20 + exam_size + 28), tagline, fill=muted, font=tag_font)
    return img


def write_brand_assets(site_root: Path | None = None) -> Path:
    out = brand_assets_root(site_root)
    out.mkdir(parents=True, exist_ok=True)
    render_favicon(16).save(out / "favicon-16.png", optimize=True)
    render_favicon(32).save(out / "favicon-32.png", optimize=True)
    render_favicon(180).save(out / "apple-touch-icon.png", optimize=True)
    render_og_image().save(out / "og-image.png", optimize=True)
    return out


def _rel_href(rel_path: Path, to_site_rel: str) -> str:
    from tools.html_footer import footer_href

    return footer_href(rel_path, to_site_rel)


def brand_head_markup(rel_path: Path, *, site_root: Path | None = None) -> str:
    if not assets_ready(site_root):
        return ""
    icon16 = html.escape(_rel_href(rel_path, f"{BRAND_DIR}/favicon-16.png"))
    icon32 = html.escape(_rel_href(rel_path, f"{BRAND_DIR}/favicon-32.png"))
    apple = html.escape(_rel_href(rel_path, f"{BRAND_DIR}/apple-touch-icon.png"))
    og_img = html.escape(public_url(f"{BRAND_DIR}/og-image.png"))
    theme_color = html.escape(theme_ink())
    return f"""{MARKER}
<link rel="icon" type="image/png" sizes="32x32" href="{icon32}">
<link rel="icon" type="image/png" sizes="16x16" href="{icon16}">
<link rel="apple-touch-icon" sizes="180x180" href="{apple}">
<meta name="theme-color" content="{theme_color}">
<meta property="og:image" content="{og_img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:image" content="{og_img}">"""


def inject_brand_head(html_text: str, rel_path: Path, *, site_root: Path | None = None) -> str:
    block = brand_head_markup(rel_path, site_root=site_root)
    if not block:
        return html_text
    if MARKER in html_text:
        html_text = re.sub(
            rf"{re.escape(MARKER)}[\s\S]*?<meta name=\"twitter:image\" content=\"[^\"]+\">",
            block.rstrip(),
            html_text,
            count=1,
        )
    else:
        html_text = re.sub(
            r'(<meta charset="UTF-8">)',
            r"\1\n" + block,
            html_text,
            count=1,
        )
    html_text = html_text.replace(
        '<meta name="twitter:card" content="summary">',
        '<meta name="twitter:card" content="summary_large_image">',
    )
    if html_text.count('meta name="theme-color"') > 1:
        html_text = re.sub(
            r'\n<meta name="theme-color" content="[^"]*">',
            "",
            html_text,
            count=1,
        )
    return html_text
