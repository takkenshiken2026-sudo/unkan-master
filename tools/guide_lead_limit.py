#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ガイド記事の冒頭リード文を記事単位で上限文字数に収める。"""

from __future__ import annotations

import html as html_module
import re
from typing import Final

MAX_LEAD_CHARS: Final[int] = 200
_MIN_SENTENCE_BREAK_CHARS: Final[int] = 40
_SENTENCE_END_RE = re.compile(r"[。！？]")
_ARTICLE_LEAD_RE = re.compile(
    r'<p class="article-lead"[^>]*>(.*?)</p>',
    re.I | re.S,
)


def normalize_lead_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def pick_guide_lead_text(lead: str, user_intent: str) -> str:
    """ガイド記事の冒頭1文。lead を優先し、空なら user_intent を要点ボックス用に整えて使う。"""
    primary = normalize_lead_whitespace(lead)
    if primary:
        return cap_lead_text(primary)
    fallback = normalize_lead_whitespace(user_intent)
    if not fallback:
        return ""
    from tools.guide_key_points_prose import normalize_key_points_intro  # noqa: WPS433

    return cap_lead_text(normalize_key_points_intro(fallback))


def cap_lead_text(text: str, *, limit: int = MAX_LEAD_CHARS) -> str:
    """リード文を上限以内に収める。可能なら句点で切る。"""
    one = normalize_lead_whitespace(text)
    if len(one) <= limit:
        return one

    window = one[:limit]
    last_break = -1
    for match in _SENTENCE_END_RE.finditer(window):
        last_break = match.end()
    if last_break >= _MIN_SENTENCE_BREAK_CHARS:
        return one[:last_break].strip()

    trimmed = one[: limit - 1].rstrip("、，, ")
    return f"{trimmed}…"


def lead_plain_text_in_reader_html(page_html: str) -> str:
    """生成 HTML の冒頭リード（article-lead）のプレーンテキスト。"""
    main_m = re.search(r"<main[^>]*>(.*)</main>", page_html, re.I | re.S)
    if not main_m:
        return ""
    lead_m = _ARTICLE_LEAD_RE.search(main_m.group(1))
    if not lead_m:
        return ""
    plain = re.sub(r"<[^>]+>", "", lead_m.group(1))
    return normalize_lead_whitespace(html_module.unescape(plain))


def lead_char_count_in_reader_html(page_html: str) -> int:
    return len(lead_plain_text_in_reader_html(page_html))
