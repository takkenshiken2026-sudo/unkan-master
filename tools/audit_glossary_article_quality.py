#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用語詳細 CSV の独自性・定型文率を集計する（文字数ではなく中身の品質確認用）。"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "glossary_terms.csv"

try:
    from tools.enrich_o4_glossary_details import (
        BOILERPLATE_PHRASES,
        KEEP_TERMS,
        META_STUDY_TERMS,
        is_boilerplate_sentence,
    )
except ImportError:
    sys.path.insert(0, str(ROOT))
    from tools.enrich_o4_glossary_details import (
        BOILERPLATE_PHRASES,
        KEEP_TERMS,
        META_STUDY_TERMS,
        is_boilerplate_sentence,
    )

SKIP_CHOICE_CHECK = KEEP_TERMS | META_STUDY_TERMS | frozenset({"ひっかけ問題"})


def norm(s: str | None) -> str:
    return (s or "").strip()


def split_paras(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n{2,}", norm(text)) if p.strip()]


def boilerplate_hits(text: str) -> list[str]:
    return [p for p in BOILERPLATE_PHRASES if p in text]


def score_row(row: dict[str, str]) -> dict[str, object]:
    term = norm(row.get("term"))
    body = norm(row.get("term_detail_body"))
    expl = norm(row.get("explanation"))
    combined = f"{body}\n{expl}\n{norm(row.get('article_lead'))}"
    paras = split_paras(body)
    bp = boilerplate_hits(combined)
    generic_paras = sum(1 for p in paras if is_boilerplate_sentence(p))
    has_practice_tag = "実践演習連動" in norm(row.get("tags"))
    choice_like = (
        sum(
            1
            for p in paras
            if "誤り。" in p or p.startswith(("正しい", "誤答", "×", "○"))
        )
        + (1 if "誤り。" in body or "正しい。" in body else 0)
    )
    return {
        "term": term,
        "body_len": len(body),
        "para_count": len(paras),
        "choice_insights": choice_like,
        "practice_linked": has_practice_tag,
        "boilerplate_phrases": len(bp),
        "generic_paras": generic_paras,
    }


def main() -> int:
    if not CSV_PATH.is_file():
        print(f"missing: {CSV_PATH}", file=sys.stderr)
        return 1
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8-sig")))
    scores = [score_row(r) for r in rows if norm(r.get("term"))]

    no_practice = sum(
        1 for s in scores if not s["practice_linked"] and s["term"] not in SKIP_CHOICE_CHECK
    )
    thin_body = sum(
        1
        for s in scores
        if s["body_len"] < 120 and s["term"] not in SKIP_CHOICE_CHECK
    )
    no_choice = sum(
        1
        for s in scores
        if s["choice_insights"] == 0
        and s["practice_linked"]
        and s["term"] not in SKIP_CHOICE_CHECK
    )
    high_bp = sum(
        1
        for s in scores
        if s["boilerplate_phrases"] >= 2 and s["term"] not in SKIP_CHOICE_CHECK
    )

    print(f"用語数: {len(scores)}")
    print(f"実践演習未連動: {no_practice}")
    print(f"本文が120字未満（内容薄）: {thin_body}")
    print(f"演習連動だが選択肢根拠風の段落なし: {no_choice}")
    print(f"定型フレーズ2件以上含有: {high_bp}")

    warn = [
        s
        for s in scores
        if s["term"] not in SKIP_CHOICE_CHECK
        and (
            s["boilerplate_phrases"] >= 3
            or (s["practice_linked"] and s["choice_insights"] == 0 and s["body_len"] < 200)
        )
    ]
    if warn:
        print("\n改善優先（内容の独自性が弱い候補）:")
        for s in warn[:15]:
            print(
                f"  - {s['term']}: 定型{s['boilerplate_phrases']} / "
                f"選択肢根拠{s['choice_insights']} / 本文{s['body_len']}字"
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
