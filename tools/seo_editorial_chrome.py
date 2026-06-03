#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験ガイド・用語解説・知識ハブ詳細ページ向けの共通 head / CSS 部品。

フォント・色味の調整は seo-editorial.css の --seo-* 変数を編集する。
正本: docs/seo-editorial-typography.md
"""

from __future__ import annotations

import html
from pathlib import Path

# キャッシュバスター（seo-editorial.css を更新したら必ず上げる）
SEO_EDITORIAL_CSS_VER = "20260603-affiliate-aside-label"

SEO_ARTICLE_BODY_CLASSES = frozenset(
    {
        "guide-article-page",
        "term-article-page",
        "compare-article-page",
        "numbers-article-page",
        "mistakes-article-page",
    }
)

SEO_EDITORIAL_ARTICLE_CLASS = "seo-editorial"


def rel_path_prefix(rel_path: Path) -> str:
    depth = len(rel_path.parent.parts)
    return "/".join([".."] * depth) + "/" if depth else ""


def seo_editorial_head_fonts() -> str:
    """Google Fonts。 serif を足す場合は docs/seo-editorial-typography.md を参照。"""
    return """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&display=swap" rel="stylesheet">"""


def seo_editorial_stylesheet_links(
    rel_path: Path,
    *,
    site_pages_ver: str = "",
) -> str:
    """site-pages → site-theme → seo-editorial の順で読み込む。"""
    prefix = rel_path_prefix(rel_path)
    ver = f"?v={site_pages_ver}" if site_pages_ver else ""
    editorial = f"{prefix}seo-editorial.css?v={SEO_EDITORIAL_CSS_VER}"
    return "\n".join(
        (
            f'<link rel="stylesheet" href="{html.escape(prefix + "site-pages.css" + ver)}">',
            f'<link rel="stylesheet" href="{html.escape(prefix + "site-theme.css")}">',
            f'<link rel="stylesheet" href="{html.escape(editorial)}">',
        )
    )


def seo_editorial_article_class(*, extra: str = "") -> str:
    base = f"seo-article-card article-body {SEO_EDITORIAL_ARTICLE_CLASS}"
    if extra.strip():
        return f"{base} {extra.strip()}"
    return base


def seo_brand_asset_tags(rel_path: Path) -> str:
    from tools.brand_assets import brand_head_markup

    return brand_head_markup(rel_path)
