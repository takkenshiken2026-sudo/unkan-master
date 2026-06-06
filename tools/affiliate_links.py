#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Detect whether an affiliate guide row has real ASP / product URLs."""

from __future__ import annotations

import re
from typing import Any

from tools.related_links import parse_related_link_token

AFFILIATE_TAG = "アフィリエイト"

# 収益リンクなし・内部導線のみ（docs/affiliate/affiliate-article-rules.md §1 例外）
INTERNAL_AFFILIATE_SLUGS = frozenset({"affiliate-free-vs-paid-study"})

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


def is_internal_affiliate_article(row: dict[str, str]) -> bool:
    """asp=internal テーマ（外部 ASP URL 不要で HTML 生成可）。"""
    slug = norm(row.get("slug"))
    if slug in INTERNAL_AFFILIATE_SLUGS:
        return True
    notes = " ".join(
        norm(row.get(key)) for key in ("original_note", "revision_note") if norm(row.get(key))
    ).lower()
    return "asp=internal" in notes or "内部リンク中心" in notes


def affiliate_article_is_buildable(row: dict[str, str]) -> bool:
    """Affiliate rows without ASP URLs are not published as HTML."""
    if not is_affiliate_article(row):
        return True
    if is_internal_affiliate_article(row):
        return True
    return bool(affiliate_external_links_in_row(row))


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
