#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Detect whether an affiliate guide row has real ASP / product URLs."""

from __future__ import annotations

import re
from typing import Any

from tools.related_links import parse_related_link_token

AFFILIATE_TAG = "アフィリエイト"

# Placeholder / sample URLs — not counted as ready affiliate links.
AFFILIATE_URL_PLACEHOLDER_HINTS = (
    "example.com",
    "example-affiliate",
    "your-domain.example",
    "amzn.to/xxxx",
    "amzn.to/yyyy",
    "amzn.to/zzzz",
    "placeholder",
)

_AFFILIATE_URL_IN_TEXT_RE = re.compile(r"https?://[^\s;\"'<>]+", re.I)


def split_semicolon(value: str) -> list[str]:
    return [x.strip() for x in (value or "").split(";") if x.strip()]


def norm(value: str | None) -> str:
    return (value or "").strip()


def is_affiliate_url(url: str) -> bool:
    """True when URL looks like a real external affiliate / product link."""
    u = norm(url)
    if not u.lower().startswith(("http://", "https://")):
        return False
    lower = u.lower()
    return not any(hint in lower for hint in AFFILIATE_URL_PLACEHOLDER_HINTS)


def affiliate_urls_in_text(text: str) -> list[str]:
    found: list[str] = []
    for match in _AFFILIATE_URL_IN_TEXT_RE.finditer(text or ""):
        url = match.group(0).rstrip(".,)")
        if is_affiliate_url(url):
            found.append(url)
    return found


def affiliate_external_links_in_row(row: dict[str, str]) -> list[str]:
    """Collect non-placeholder https links from related_links and prose columns."""
    links: list[str] = []
    for item in split_semicolon(row.get("related_links", "")):
        target, _label = parse_related_link_token(item)
        if is_affiliate_url(target):
            links.append(target)
    for key, value in row.items():
        if not value:
            continue
        if key == "related_links" or not (
            key.startswith("section_")
            or key.startswith("faq_")
            or key in {"lead", "meta_description", "user_intent"}
        ):
            continue
        links.extend(affiliate_urls_in_text(value))
    # Preserve order, drop duplicates.
    return list(dict.fromkeys(links))


def is_affiliate_article(row: dict[str, str]) -> bool:
    tags = split_semicolon(norm(row.get("tags")))
    return AFFILIATE_TAG in tags


def affiliate_article_is_buildable(row: dict[str, str]) -> bool:
    """Affiliate rows without ASP URLs are not published as HTML."""
    if not is_affiliate_article(row):
        return True
    if affiliate_external_links_in_row(row):
        return True
    slug = norm(row.get("slug"))
    if not slug:
        return False
    try:
        from tools.affiliate_brief import brief_link_config, load_affiliate_brief

        brief = load_affiliate_brief(slug)
        if brief and affiliate_brief_has_links(brief_link_config(brief)):
            return True
    except Exception:
        pass
    return False


def affiliate_urls_in_brief(config: dict[str, Any]) -> list[str]:
    links: list[str] = []
    for product in config.get("products") or []:
        if not isinstance(product, dict):
            continue
        for key in ("amazon_url", "workbook_amazon_url", "affiliate_url", "url", "a8_url", "afb_url"):
            url = norm(str(product.get(key) or ""))
            if is_affiliate_url(url):
                links.append(url)
    related = config.get("related") or ""
    if isinstance(related, str):
        items = split_semicolon(related)
    else:
        items = [str(x) for x in related]
    for item in items:
        target, _label = parse_related_link_token(item)
        if is_affiliate_url(target):
            links.append(target)
    return list(dict.fromkeys(links))


def affiliate_brief_has_links(config: dict[str, Any]) -> bool:
    if norm(str(config.get("asp") or "")).lower() == "internal":
        return True
    return bool(affiliate_urls_in_brief(config))


AFFILIATE_SKIP_SECTION_HEADINGS = frozenset({"この記事でわかること"})


def is_affiliate_skip_section(article: dict[str, str], heading: str) -> bool:
    if not is_affiliate_article(article):
        return False
    return norm(heading) in AFFILIATE_SKIP_SECTION_HEADINGS


def affiliate_product_key_points(brief: dict[str, Any] | None, *, max_items: int = 5) -> list[str]:
    if not brief:
        return []
    names: list[str] = []
    for product in brief.get("products") or []:
        if not isinstance(product, dict):
            continue
        name = norm(str(product.get("name") or ""))
        if name:
            names.append(name)
    return names[:max_items]


AFFILIATE_RELATED_MAX_TOTAL = 6
AFFILIATE_RELATED_MAX_PER_KIND = 3


def is_affiliate_related_slug(slug: str, by_slug: dict[str, dict[str, str]]) -> bool:
    if slug.startswith("affiliate-"):
        return True
    row = by_slug.get(slug)
    return bool(row and is_affiliate_article(row))


def affiliate_related_box_html(
    value: str,
    by_slug: dict[str, dict[str, str]],
    article: dict[str, str],
    *,
    label_fn: Any | None = None,
) -> str:
    """アフィリエイト記事末尾：関連6件（非アフィリエイト3 + アフィリエイト3）。"""
    import html

    from tools.related_links import resolve_related_link_label

    def label_text(text: str) -> str:
        return label_fn(text) if label_fn else text

    current = norm(article.get("slug", ""))
    affiliate_items: list[str] = []
    other_items: list[str] = []
    seen: set[str] = set()

    for item in split_semicolon(value):
        target, label = parse_related_link_token(item)
        target = norm(target)
        if not target or target == current or target in seen:
            continue
        if target.startswith(("http://", "https://")):
            continue

        if target.startswith("../"):
            text_label = label_text(label or target)
            chunk = (
                f'<a class="related-link" href="{html.escape(target)}">'
                f"{html.escape(text_label)}</a>"
            )
            seen.add(target)
            if len(other_items) < AFFILIATE_RELATED_MAX_PER_KIND:
                other_items.append(chunk)
            continue

        if target not in by_slug:
            continue
        seen.add(target)
        text_label = label_text(
            resolve_related_link_label(target, label, by_slug[target]["title"])
        )
        href = f"../{target}/"
        chunk = (
            f'<a class="related-link" href="{html.escape(href)}">'
            f"{html.escape(text_label)}</a>"
        )
        if is_affiliate_related_slug(target, by_slug):
            if len(affiliate_items) < AFFILIATE_RELATED_MAX_PER_KIND:
                affiliate_items.append(chunk)
        elif len(other_items) < AFFILIATE_RELATED_MAX_PER_KIND:
            other_items.append(chunk)

    links = (other_items[:AFFILIATE_RELATED_MAX_PER_KIND] + affiliate_items[:AFFILIATE_RELATED_MAX_PER_KIND])[
        :AFFILIATE_RELATED_MAX_TOTAL
    ]
    if not links:
        return ""
    return (
        '<div class="related-box"><div class="related-box-title">関連記事・知識ハブ</div>'
        f'<div class="related-links">{"".join(links)}</div></div>'
    )
