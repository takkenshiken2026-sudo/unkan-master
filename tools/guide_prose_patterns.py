#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ガイド記事 prose 品質問題の検出パターン（監査・coherence 共通）."""

from __future__ import annotations

import re
from dataclasses import dataclass

from tools.editorial_quality import norm

SLUG_META_RE = re.compile(r"記事\s+[a-z0-9-]+\s*「")
BROKEN_SECTION_NO_RE = re.compile(r"第\d+。節|（。第\d+節）")
INCOMPLETE_ABOUT_RE = re.compile(r"「[^」]+」では、[^。]+について。")
FIELD_BOILER_RE = re.compile(
    r"現場判断と\d+分野|"
    r"の観点で整理します|"
    r"演習で同テーマの設問を1問以上|"
    r"付箋を付けながら読み"
)
OLD_META_TAIL_RE = re.compile(r"の要点を、.*演習解説で照合しながら整理します")
INTERNAL_MARKER_RE = re.compile(r"（記事:[^）]+）")
DUP_OFFICIAL_RE = re.compile(r"（公式）で[^。]{0,24}（公式）")


@dataclass(frozen=True)
class ProseHit:
    pattern: str
    column: str
    snippet: str


def exam_dup_re(exam: str, exam_short: str) -> re.Pattern[str] | None:
    """試験名＋短称の不当な連続（例: 二衛試験の二衛 試験当日…）のみ検出。"""
    if not exam or not exam_short or exam_short == exam:
        return None
    parts = [rf"{re.escape(exam)}の{re.escape(exam_short)}\s+"]
    if exam_short in exam and exam != exam_short:
        parts.append(rf"{re.escape(exam)}の{re.escape(exam_short)}試験")
    if len(exam) > len(exam_short):
        parts.append(rf"{re.escape(exam)}の{re.escape(exam)}")
    return re.compile("|".join(parts))


def scan_prose_text(
    text: str,
    *,
    column: str,
    exam: str = "",
    exam_short: str = "",
) -> list[ProseHit]:
    t = norm(text)
    if not t:
        return []
    hits: list[ProseHit] = []
    checks: list[tuple[str, re.Pattern[str]]] = [
        ("slug_meta", SLUG_META_RE),
        ("broken_section_no", BROKEN_SECTION_NO_RE),
        ("incomplete_about", INCOMPLETE_ABOUT_RE),
        ("field_boiler", FIELD_BOILER_RE),
        ("old_meta_tail", OLD_META_TAIL_RE),
        ("internal_marker", INTERNAL_MARKER_RE),
        ("dup_official", DUP_OFFICIAL_RE),
    ]
    dup = exam_dup_re(exam, exam_short)
    if dup:
        checks.append(("exam_dup", dup))
    for name, pat in checks:
        m = pat.search(t)
        if m:
            start = max(0, m.start() - 20)
            end = min(len(t), m.end() + 40)
            hits.append(ProseHit(name, column, t[start:end].replace("\n", " ")))
    return hits


PROSE_COLUMNS = (
    "lead",
    "user_intent",
    "meta_description",
    "action_items",
    *(f"section_{n}_body" for n in range(1, 8)),
    *(f"faq_{n}_answer" for n in range(1, 5)),
)
