#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEO 記事・知識ハブ向けの内部リンク生成。"""

from __future__ import annotations

import html
import re
from typing import Any

MIN_AUTO_LINK_TERM_LEN = 2
MAX_AUTO_LINKS_PER_SECTION = 3
MAX_AUTO_LINKS_PER_ARTICLE = 12

GUIDE_HUB_LINKS: tuple[tuple[str, str], ...] = (
    ("../../terms/index.html", "用語解説一覧"),
    ("../../terms/compare/index.html", "比較・整理表"),
    ("../../terms/numbers/index.html", "数値・期限早見表"),
    ("../../terms/mistakes/index.html", "よくある誤答"),
    ("../../index.html#past", "過去問演習"),
)

TERM_NEXT_HUB_LINKS: tuple[tuple[str, str], ...] = (
    ("../compare/index.html", "比較・整理表"),
    ("../numbers/index.html", "数値・期限早見表"),
    ("../mistakes/index.html", "よくある誤答"),
)


def split_semicolon(value: str) -> list[str]:
    return [x.strip() for x in (value or "").split(";") if x.strip()]


def lookup_key(s: str) -> str:
    return re.sub(r"\s+", "", s)


def collect_related_term_link_items(
    related: str,
    term_lookup: dict[str, str],
    *,
    entries: list[dict[str, Any]] | None = None,
    current: dict[str, Any] | None = None,
    limit: int = 6,
) -> list[str]:
    """関連用語リンク `<a>` の HTML 断片リスト（フォールバック付き）。"""
    items: list[str] = []
    seen: set[str] = set()
    entry_terms = {e.get("term") for e in (entries or []) if e.get("term")}

    for label in split_semicolon(related):
        href = term_lookup.get(label) or term_lookup.get(lookup_key(label))
        if href and href not in seen:
            seen.add(href)
            items.append(
                f'<a class="related-link" href="{html.escape(href)}">{html.escape(label)}</a>'
            )
        elif label and label not in entry_terms:
            items.append(f'<span class="related-link related-link-static">{html.escape(label)}</span>')

    if len(items) < 2 and entries and current:
        category = current.get("category") or ""
        current_href = current.get("slug_file") or ""
        for entry in entries:
            if entry.get("slug_file") == current_href:
                continue
            if category and entry.get("category") != category:
                continue
            href = entry.get("slug_file") or ""
            if not href or href in seen:
                continue
            seen.add(href)
            term = entry.get("term") or href
            items.append(
                f'<a class="related-link" href="{html.escape(href)}">{html.escape(term)}</a>'
            )
            if len(items) >= limit:
                break
    return items


def related_terms_box_html(
    related: str,
    term_lookup: dict[str, str],
    *,
    entries: list[dict[str, Any]] | None = None,
    current: dict[str, Any] | None = None,
    href_prefix: str = "",
    box_id: str = "hub-related-title",
    box_title: str = "関連用語",
    limit: int = 6,
) -> str:
    """関連用語ボックス HTML。CSV 不足時は同分野用語で補完。"""
    items = collect_related_term_link_items(
        related,
        term_lookup,
        entries=entries,
        current=current,
        limit=limit,
    )
    if not items:
        return ""
    if href_prefix:
        prefixed: list[str] = []
        for item in items:
            if item.startswith('<a class="related-link" href="') and not item.startswith('<a class="related-link" href="../'):
                prefixed.append(item.replace('href="', f'href="{href_prefix}', 1))
            else:
                prefixed.append(item)
        items = prefixed
    return (
        f'<div class="related-box" aria-labelledby="{html.escape(box_id)}">'
        f'<div id="{html.escape(box_id)}" class="related-box-title">{html.escape(box_title)}</div>'
        f'<div class="related-links term-related-links">{"".join(prefixed)}</div></div>'
    )


def term_hrefs_for_auto_link(term_lookup: dict[str, str], *, articles_prefix: str = "../../terms/") -> dict[str, str]:
    """用語名 → 記事ページからの相対 href。"""
    out: dict[str, str] = {}
    for key, slug_file in term_lookup.items():
        if not key or len(key) < MIN_AUTO_LINK_TERM_LEN:
            continue
        out[key] = f"{articles_prefix}{slug_file}"
    return out


def link_terms_in_plaintext(
    text: str,
    term_hrefs: dict[str, str],
    linked: set[str],
    *,
    max_new: int = MAX_AUTO_LINKS_PER_SECTION,
) -> str:
    """本文プレーンテキスト中の用語初出を内部リンク化。"""
    if not text.strip() or not term_hrefs or max_new <= 0:
        return html.escape(text).replace("\n", "<br>")

    if len(linked) >= MAX_AUTO_LINKS_PER_ARTICLE:
        return html.escape(text).replace("\n", "<br>")

    terms = sorted(term_hrefs.keys(), key=len, reverse=True)
    matches: list[tuple[int, int, str, str]] = []
    for term in terms:
        if len(matches) >= max_new or len(linked) >= MAX_AUTO_LINKS_PER_ARTICLE:
            break
        if term in linked or len(term) < MIN_AUTO_LINK_TERM_LEN:
            continue
        pos = text.find(term)
        if pos < 0:
            continue
        end = pos + len(term)
        if any(not (end <= start or pos >= stop) for start, stop, _, _ in matches):
            continue
        matches.append((pos, end, term_hrefs[term], term))
        linked.add(term)

    if not matches:
        return html.escape(text).replace("\n", "<br>")

    matches.sort(key=lambda x: x[0])
    parts: list[str] = []
    cursor = 0
    for start, end, href, label in matches:
        parts.append(html.escape(text[cursor:start]))
        parts.append(f'<a href="{html.escape(href)}">{html.escape(label)}</a>')
        cursor = end
    parts.append(html.escape(text[cursor:]))
    return "".join(parts).replace("\n", "<br>")


def guide_knowledge_hub_link_items(
    article: dict[str, str],
    *,
    categories: list[str],
    field_hub_slug_fn,
    field_hub_exists_fn,
) -> list[str]:
    """試験ガイド末尾用：知識ハブ・分野ハブへのリンク。"""
    items: list[str] = []
    seen: set[str] = set()
    for href, label in GUIDE_HUB_LINKS:
        if href in seen:
            continue
        seen.add(href)
        items.append(f'<a class="related-link" href="{html.escape(href)}">{html.escape(label)}</a>')

    blob = f"{article.get('genre', '')} {article.get('tags', '')} {article.get('title', '')}"
    for category in categories:
        if not category or category not in blob:
            continue
        if not field_hub_exists_fn(category):
            continue
        hub = field_hub_slug_fn(category)
        href = f"../../terms/{hub}/index.html"
        if href in seen:
            continue
        seen.add(href)
        items.append(
            f'<a class="related-link" href="{html.escape(href)}">'
            f"{html.escape(category)}の用語一覧</a>"
        )
        break
    return items


def merge_related_boxes(*boxes: str) -> str:
    """複数の related-box を1つにまとめる（空は無視）。"""
    boxes = [b for b in boxes if b.strip()]
    if not boxes:
        return ""
    if len(boxes) == 1:
        return boxes[0]
    links: list[str] = []
    for box in boxes:
        for chunk in re.findall(r'<a class="related-link"[^>]*>.*?</a>', box):
            if chunk not in links:
                links.append(chunk)
        for chunk in re.findall(r'<span class="related-link related-link-static">.*?</span>', box):
            if chunk not in links:
                links.append(chunk)
    if not links:
        return boxes[0]
    return (
        '<div class="related-box"><div class="related-box-title">関連記事・知識ハブ</div>'
        f'<div class="related-links">{"".join(links)}</div></div>'
    )
