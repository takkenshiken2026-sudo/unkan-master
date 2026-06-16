#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ガイド記事本文の「たとえば」出現回数を記事単位で上限化する。"""

from __future__ import annotations

import re
from typing import Final

MAX_TATOEBA_PER_ARTICLE: Final[int] = 3
TATOEBA_RE = re.compile("たとえば")
ALT_MARKERS: Final[tuple[str, ...]] = ("具体例として", "一例として", "例として")

READER_PROSE_FIELD_KEYS: Final[tuple[str, ...]] = (
    "lead",
    "user_intent",
    *(f"section_{idx}_body" for idx in range(1, 9)),
    *(f"faq_{idx}_answer" for idx in range(1, 4)),
)

_READER_HTML_TAGS = ("p", "li", "td", "th", "h2", "h3", "h4", "dd", "div")


class TatoebaBudget:
    """記事内で保持する「たとえば」の残数。"""

    __slots__ = ("limit", "used", "_alt_idx")

    def __init__(self, limit: int = MAX_TATOEBA_PER_ARTICLE) -> None:
        self.limit = max(0, limit)
        self.used = 0
        self._alt_idx = 0

    def process(self, text: str) -> str:
        if not text or "たとえば" not in text:
            return text

        def repl(_match: re.Match[str]) -> str:
            if self.used < self.limit:
                self.used += 1
                return "たとえば"
            alt = ALT_MARKERS[self._alt_idx % len(ALT_MARKERS)]
            self._alt_idx += 1
            return alt

        return TATOEBA_RE.sub(repl, text)


def cap_article_tatoeba_fields(
    article: dict[str, str],
    *,
    limit: int = MAX_TATOEBA_PER_ARTICLE,
) -> dict[str, str]:
    """読者向け prose 列を読み順どおりに処理し、記事全体で「たとえば」を上限以内に抑える。"""
    budget = TatoebaBudget(limit)
    out = dict(article)
    for key in READER_PROSE_FIELD_KEYS:
        raw = out.get(key, "")
        if raw:
            out[key] = budget.process(raw)
    return out


def count_tatoeba(text: str) -> int:
    return len(TATOEBA_RE.findall(text or ""))


def tatoeba_in_reader_html(html: str) -> list[str]:
    """生成 HTML の <main> 内に残る「たとえば」（監査用）。"""
    main_m = re.search(r"<main[^>]*>(.*)</main>", html, re.I | re.S)
    if not main_m:
        return []
    chunk = main_m.group(1)
    hits: list[str] = []
    tag_alt = "|".join(_READER_HTML_TAGS)
    for m in re.finditer(rf"<({tag_alt})[^>]*>(.*?)</\1>", chunk, re.I | re.S):
        plain = re.sub(r"<[^>]+>", "", m.group(2))
        for _ in TATOEBA_RE.finditer(plain):
            hits.append("たとえば")
    return hits
