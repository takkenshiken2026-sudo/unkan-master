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

BRAND_DIR = "assets/brand"
MARKER = "<!--BRAND_ASSET_HEAD-->"
OG_WIDTH = 1200
OG_HEIGHT = 630
# SNS の 1:1 中央クロップ（630×630）でも切れないよう、コンテンツ幅をこの範囲に収める
OG_SAFE_WIDTH = 630


def _font_candidates(*, bold: bool) -> list[Path]:
    if bold:
        return [
            Path("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
            Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        ]
    return [
        Path("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    ]


def _resolve_font_path(*, bold: bool) -> str:
    for path in _font_candidates(bold=bold):
        if path.is_file():
            return str(path)
    kind = "bold" if bold else "regular"
    raise FileNotFoundError(f"No {kind} font found for brand asset generation")


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

    path = _resolve_font_path(bold=bold)
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

    w, h = OG_WIDTH, OG_HEIGHT
    top, bottom = brand_logo_lines()
    name = brand_name()
    exam = exam_name()
    tagline = "過去問・演習・用語解説"
    bg = theme_page_bg()
    ink = theme_ink()
    text_col = theme_text()
    muted = theme_text_muted()

    measure = Image.new("RGB", (w, h), bg)
    mdraw = ImageDraw.Draw(measure)

    gap = 32
    name_gap, exam_gap = 18, 24
    layout = None
    for box_w in (260, 250, 240, 230, 220, 210, 200, 190, 180, 170, 160, 150, 140, 130, 120):
        box_h = max(120, int(box_w * 0.95))
        text_max_w = OG_SAFE_WIDTH - box_w - gap
        name_font, name_size = _fit_font(mdraw, name, text_max_w, 56, bold=True)
        exam_font, exam_size = _fit_font(mdraw, exam, text_max_w, 36, bold=False)
        tag_font, tag_size = _fit_font(mdraw, tagline, text_max_w, 32, bold=False)
        text_w = max(
            mdraw.textlength(name, font=name_font),
            mdraw.textlength(exam, font=exam_font),
            mdraw.textlength(tagline, font=tag_font),
        )
        text_h = name_size + name_gap + exam_size + exam_gap + tag_size
        content_w = box_w + gap + int(text_w)
        content_h = max(box_h, text_h)
        if content_w <= OG_SAFE_WIDTH:
            layout = {
                "box_w": box_w,
                "box_h": box_h,
                "gap": gap,
                "name_font": name_font,
                "name_size": name_size,
                "exam_font": exam_font,
                "exam_size": exam_size,
                "tag_font": tag_font,
                "tag_size": tag_size,
                "text_h": text_h,
                "content_w": content_w,
                "content_h": content_h,
            }
            break

    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    if layout is None:
        # 横並びが収まらない場合: ロゴ＋テキストを縦積みで中央配置
        mark_w, mark_h = 260, 240
        text_max_w = OG_SAFE_WIDTH - 20
        name_font, name_size = _fit_font(mdraw, name, text_max_w, 52, bold=True)
        exam_font, exam_size = _fit_font(mdraw, exam, text_max_w, 34, bold=False)
        tag_font, tag_size = _fit_font(mdraw, tagline, text_max_w, 30, bold=False)
        stack_gap, line_gap = 32, 16
        content_w = int(
            max(
                mark_w,
                mdraw.textlength(name, font=name_font),
                mdraw.textlength(exam, font=exam_font),
                mdraw.textlength(tagline, font=tag_font),
            )
        )
        content_h = mark_h + stack_gap + name_size + line_gap + exam_size + line_gap + tag_size
        block_x = (w - content_w) // 2
        block_y = (h - content_h) // 2
        _draw_logo_mark(
            draw,
            x=block_x + (content_w - mark_w) // 2,
            y=block_y,
            width=mark_w,
            height=mark_h,
            top=top,
            bottom=bottom,
            bg=ink,
            fg="#ffffff",
            radius=12,
        )
        ty = block_y + mark_h + stack_gap
        draw.text((block_x + (content_w - mdraw.textlength(name, font=name_font)) / 2, ty), name, fill=text_col, font=name_font)
        ty += name_size + line_gap
        draw.text((block_x + (content_w - mdraw.textlength(exam, font=exam_font)) / 2, ty), exam, fill=muted, font=exam_font)
        ty += exam_size + line_gap
        draw.text((block_x + (content_w - mdraw.textlength(tagline, font=tag_font)) / 2, ty), tagline, fill=muted, font=tag_font)
        return img

    block_x = (w - layout["content_w"]) // 2
    block_y = (h - layout["content_h"]) // 2
    box_x = block_x
    box_y = block_y + (layout["content_h"] - layout["box_h"]) // 2
    tx = block_x + layout["box_w"] + layout["gap"]
    ty = block_y + (layout["content_h"] - layout["text_h"]) // 2

    _draw_logo_mark(
        draw,
        x=box_x,
        y=box_y,
        width=layout["box_w"],
        height=layout["box_h"],
        top=top,
        bottom=bottom,
        bg=ink,
        fg="#ffffff",
        radius=12,
    )
    draw.text((tx, ty), name, fill=text_col, font=layout["name_font"])
    draw.text(
        (tx, ty + layout["name_size"] + name_gap),
        exam,
        fill=muted,
        font=layout["exam_font"],
    )
    draw.text(
        (
            tx,
            ty + layout["name_size"] + name_gap + layout["exam_size"] + exam_gap,
        ),
        tagline,
        fill=muted,
        font=layout["tag_font"],
    )
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
    accent = html.escape(theme_ink())
    html_text = re.sub(
        r'(<meta name="theme-color" content=")[^"]*(">)',
        rf"\g<1>{accent}\2",
        html_text,
    )
    return html_text
