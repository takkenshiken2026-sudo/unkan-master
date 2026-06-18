#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ガイド記事本文の例示マーカー（例えば/たとえば）出現回数を記事単位で上限化する。"""

from __future__ import annotations

import re
from typing import Final

MAX_EXAMPLE_MARKERS_PER_ARTICLE: Final[int] = 4
MAX_TATOEBA_PER_ARTICLE: Final[int] = MAX_EXAMPLE_MARKERS_PER_ARTICLE

EXAMPLE_MARKER_RE = re.compile("(?:例えば|たとえば)")
TATOEBA_RE = re.compile("たとえば")
ALT_MARKERS: Final[tuple[str, ...]] = ("",)  # 超過分はマーカー削除（文は残す）

READER_PROSE_FIELD_KEYS: Final[tuple[str, ...]] = (
    "lead",
    "user_intent",
    *(f"section_{idx}_body" for idx in range(1, 9)),
    *(f"faq_{idx}_answer" for idx in range(1, 4)),
)

_READER_HTML_TAGS = ("p", "li", "td", "th", "h2", "h3", "h4", "dd", "div")


class ExampleMarkerBudget:
    """記事内で保持する「例えば/たとえば」の残数。"""

    __slots__ = ("limit", "used")

    def __init__(self, limit: int = MAX_EXAMPLE_MARKERS_PER_ARTICLE) -> None:
        self.limit = max(0, limit)
        self.used = 0

    def process(self, text: str) -> str:
        if not text or not EXAMPLE_MARKER_RE.search(text):
            return text

        def repl(_match: re.Match[str]) -> str:
            if self.used < self.limit:
                self.used += 1
                return _match.group(0)
            return ""

        return EXAMPLE_MARKER_RE.sub(repl, text)


def cap_article_tatoeba_fields(
    article: dict[str, str],
    *,
    limit: int = MAX_EXAMPLE_MARKERS_PER_ARTICLE,
) -> dict[str, str]:
    """読者向け prose 列を読み順どおりに処理し、例示マーカーを上限以内に抑える。"""
    budget = ExampleMarkerBudget(limit)
    out = dict(article)
    for key in READER_PROSE_FIELD_KEYS:
        raw = out.get(key, "")
        if raw:
            out[key] = budget.process(raw)
    return out


def count_example_markers(text: str) -> int:
    return len(EXAMPLE_MARKER_RE.findall(text or ""))


def count_tatoeba(text: str) -> int:
    return len(TATOEBA_RE.findall(text or ""))


def example_markers_in_reader_html(html: str) -> list[str]:
    """生成 HTML の <main> 内に残る例示マーカー（監査用）。"""
    main_m = re.search(r"<main[^>]*>(.*)</main>", html, re.I | re.S)
    if not main_m:
        return []
    chunk = main_m.group(1)
    hits: list[str] = []
    tag_alt = "|".join(_READER_HTML_TAGS)
    for m in re.finditer(rf"<({tag_alt})[^>]*>(.*?)</\1>", chunk, re.I | re.S):
        plain = re.sub(r"<[^>]+>", "", m.group(2))
        for em in EXAMPLE_MARKER_RE.finditer(plain):
            hits.append(em.group(0))
    return hits


def tatoeba_in_reader_html(html: str) -> list[str]:
    """後方互換: 例示マーカー全体を返す。"""
    return example_markers_in_reader_html(html)
