#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write unkan (運行管理者試験) knowledge hub S30 helpers."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

HEADER_COMPARE = [
    "slug", "title", "category", "tags", "summary", "col_labels", "compare_rows",
    "article_title", "article_lead", "exam_points", "common_mistakes", "memory_tip",
    "related_terms", "faq_1_question", "faq_1_answer", "faq_2_question", "faq_2_answer",
    "faq_3_question", "faq_3_answer", "faq_4_question", "faq_4_answer",
]
HEADER_NUMBERS = [
    "slug", "title", "category", "tags", "summary", "highlight", "item_rows",
    "article_title", "article_lead", "exam_points", "common_mistakes", "memory_tip",
    "related_terms", "faq_1_question", "faq_1_answer", "faq_2_question", "faq_2_answer",
    "faq_3_question", "faq_3_answer", "faq_4_question", "faq_4_answer",
]
HEADER_MISTAKES = [
    "slug", "title", "category", "tags", "summary", "confusion_point", "pattern_rows",
    "article_title", "article_lead", "exam_points", "common_mistakes", "memory_tip",
    "related_terms", "faq_1_question", "faq_1_answer", "faq_2_question", "faq_2_answer",
    "faq_3_question", "faq_3_answer", "faq_4_question", "faq_4_answer",
]


def _faq(qa: list[tuple[str, str]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for i, (q, a) in enumerate(qa, start=1):
        out[f"faq_{i}_question"] = q
        out[f"faq_{i}_answer"] = a
    return out


def _rows(*items: dict) -> str:
    return json.dumps(list(items), ensure_ascii=False)
