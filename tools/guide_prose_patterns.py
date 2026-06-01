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
VAGUE_ACCESS_RE = re.compile(
    r"受験票記載の会場、または.*所在地・交通アクセスを確認|"
    r"会場案内で、所在地・交通"
)
VAGUE_CHECKLIST_RE = re.compile(
    r"禁止物品の有無をチェックリストに書き出|"
    r"持ち物（鉛筆・消しゴム・身分証など）、会場・開始時刻"
)
TAIL_SECTION_REF_RE = re.compile(
    r"「[^」]+」の詳細は[^。]+(?:最新要項|演習解説|受験票)[^。]*(?:確認|照合)"
)
VAGUE_USER_INTENT_RE = re.compile(
    r"行動チェックリストに沿って|"
    r"確認すべき点と、演習・用語解説を使った復習の進め方"
)
SUBJECT_BOILER_RE = re.compile(r"条文や指針の主体（事業者・[^）]+）をセットで")
FAQ_ARROW_RE = re.compile(r"FAQ\d+「」|「[^」]+」→")
BROKEN_FALLBACK_RE = re.compile(r"の要点を。|要点を。\s")
GENERIC_ACTION_RE = re.compile(
    r"混同語を1周|分野タグ付き問題を10問|分野タグ付き(?:の)?演習|似た論点を1周"
)
META_CONFIRM_PAD_RE = re.compile(
    r"学習時は公式要項の最新版と照合してください|"
    r"の要点は[^。]+で確認してください。?$"
)


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
        ("vague_checklist", VAGUE_CHECKLIST_RE),
        ("vague_access", VAGUE_ACCESS_RE),
        ("tail_section_ref", TAIL_SECTION_REF_RE),
        ("vague_user_intent", VAGUE_USER_INTENT_RE),
        ("subject_boiler", SUBJECT_BOILER_RE),
        ("faq_arrow", FAQ_ARROW_RE),
        ("broken_fallback", BROKEN_FALLBACK_RE),
        ("generic_action", GENERIC_ACTION_RE),
        ("meta_confirm_pad", META_CONFIRM_PAD_RE),
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
