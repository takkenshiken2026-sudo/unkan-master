#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared technical SEO helpers (sitemap, content dates, robots)."""

from __future__ import annotations

import re
from pathlib import Path

from tools.knowledge_hub_writing_samples import WRITING_SAMPLE_SLUGS
from tools.sitemap_utils import iso_date

CONTENT_DATE_COLUMNS: tuple[str, ...] = (
    "fact_checked_at",
    "last_reviewed_at",
    "source_checked_at",
)

SITEMAP_EXCLUDED_REL_PREFIXES: tuple[str, ...] = (
    "terms/samples/",
    "terms/diagram-samples/",
    # 廃止知識ハブ（noindex リダイレクトのみ。build_hub_retire_redirects.py）
    "terms/compare/",
    "terms/numbers/",
    "terms/mistakes/",
)

SITEMAP_EXCLUDED_BASENAMES: frozenset[str] = frozenset(
    {
        *WRITING_SAMPLE_SLUGS.values(),
        "g-diagram-demo.html",
    }
)

NOINDEX_ROBOTS_META = '<meta name="robots" content="noindex, follow">'
INDEX_ROBOTS_META = '<meta name="robots" content="index, follow">'

_NOINDEX_RE = re.compile(r"""name\s*=\s*["']robots["'][^>]*content\s*=\s*["'][^"']*noindex""", re.I)
_NOINDEX_RE_ALT = re.compile(r"""content\s*=\s*["'][^"']*noindex[^"']*["'][^>]*name\s*=\s*["']robots["']""", re.I)


def content_date_from_row(row: dict[str, str] | None) -> str | None:
    if not row:
        return None
    for col in CONTENT_DATE_COLUMNS:
        d = iso_date(row.get(col))
        if d:
            return d
    return None


_ARTICLE_DETAIL_INDEX = re.compile(r"^articles/([^/]+)/index\.html$")


def sitemap_loc_rel(rel: str) -> str:
    """Map on-disk HTML path to sitemap loc (canonical-aligned public path).

    Only article *detail* pages (articles/{slug}/index.html) become articles/{slug}/.
    articles/index.html, q/*, terms/* are unchanged.
    """
    normalized = rel.replace("\\", "/").lstrip("/")
    m = _ARTICLE_DETAIL_INDEX.match(normalized)
    if m:
        return f"articles/{m.group(1)}/"
    return normalized


def html_path_for_sitemap_loc(loc_path: str) -> Path:
    """Resolve a sitemap loc path to the on-disk HTML file (for noindex checks)."""
    normalized = loc_path.replace("\\", "/").lstrip("/")
    if normalized.endswith("/"):
        return Path(normalized) / "index.html"
    return Path(normalized)


def is_sitemap_excluded_rel(rel: str) -> bool:
    normalized = rel.replace("\\", "/").lstrip("/")
    for prefix in SITEMAP_EXCLUDED_REL_PREFIXES:
        if normalized.startswith(prefix):
            return True
    return Path(normalized).name in SITEMAP_EXCLUDED_BASENAMES


def is_noindex_html_text(text: str) -> bool:
    return bool(_NOINDEX_RE.search(text) or _NOINDEX_RE_ALT.search(text))


def is_noindex_html(path: Path) -> bool:
    if not path.is_file():
        return False
    return is_noindex_html_text(path.read_text(encoding="utf-8"))


def robots_meta_for_slug(slug_file: str) -> str:
    name = Path(slug_file).name
    if name in SITEMAP_EXCLUDED_BASENAMES:
        return NOINDEX_ROBOTS_META
    return INDEX_ROBOTS_META


def meta_updated_html(updated: str | None) -> str:
    if not updated:
        return ""
    from xml.sax.saxutils import escape as xml_escape

    return f'<span class="meta-updated">更新日：{xml_escape(updated)}</span>'


def json_ld_date_modified(updated: str | None) -> dict[str, str]:
    if not updated:
        return {}
    return {"dateModified": updated}


def latest_content_date(rows: list[dict[str, str]]) -> str | None:
    dates = [d for row in rows if (d := content_date_from_row(row))]
    return max(dates) if dates else None
