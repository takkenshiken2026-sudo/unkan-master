#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remove internal batch labels like （S33） / 数値S37 from public hub CSV fields."""

from __future__ import annotations

import re

BATCH_SUFFIX_RE = re.compile(r"（S\d+）|\(S\d+\)")
TRAILING_BATCH_RE = re.compile(r"(?:\s+|｜)?(?:数値|誤答|比較)?S\d+$")
INLINE_BATCH_RE = re.compile(
    r"(?:試験対策[ 　]*(?:数値|誤答|比較)?[ 　]*)?S\d+(?:の|では)?"
    r"|数値S\d+|誤答S\d+|比較S\d+"
)
ARTICLE_PIPE_BATCH_RE = re.compile(
    r"｜(?:試験対策[^｜]*|(?:数値|誤答|比較)?S\d+[^｜]*)$"
)

# slug は内部識別子として -s35 等を残す
_SKIP_KEYS = frozenset({"slug"})


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s{2,}", " ", text).strip()


def strip_batch_suffix(text: str) -> str:
    if not text:
        return text
    cleaned = BATCH_SUFFIX_RE.sub("", text)
    cleaned = ARTICLE_PIPE_BATCH_RE.sub("", cleaned)
    cleaned = INLINE_BATCH_RE.sub("", cleaned)
    cleaned = TRAILING_BATCH_RE.sub("", cleaned)
    cleaned = re.sub(r"｜\s*｜", "｜", cleaned).strip(" ｜")
    if cleaned == text:
        return text
    return _normalize_spaces(cleaned)


def strip_hub_row(row: dict[str, str]) -> dict[str, str]:
    for key, val in row.items():
        if key in _SKIP_KEYS or not isinstance(val, str):
            continue
        row[key] = strip_batch_suffix(val)
    return row


def strip_hub_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    for row in rows:
        strip_hub_row(row)
    return rows
