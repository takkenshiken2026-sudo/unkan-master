#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""過去問・実践・一問一答 CSV の解説品質監査（矛盾・重複・デモ行）。"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.q_content_quality import (  # noqa: E402
    build_ichimon_primary_ids,
    dedupe_prose,
    is_demo_past_question_row,
    is_demo_practice_question_row,
)
from tools.q_explanation import (  # noqa: E402
    norm,
    parse_explanation_choices,
    question_ask_mode,
    _parrots_stem,
)
from tools.site_config import is_template_site, excluded_past_exam_years  # noqa: E402

DATA = ROOT / "data"


def _warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def _error(msg: str) -> None:
    print(f"[ERROR] {msg}")


def audit_past() -> tuple[int, int]:
    path = DATA / "past_questions.csv"
    if not path.is_file():
        return 0, 0
    errs = warns = 0
    skip_years = excluded_past_exam_years()
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for idx, row in enumerate(rows, start=2):
        if is_demo_past_question_row(row, excluded_exam_years=skip_years):
            warns += 1
            _warn(f"{path.name}:{idx} デモ・サンプル過去問（静的ページ生成対象外）")
            continue
        summary = norm(row.get("explanation_summary"))
        correct = norm(row.get("explanation_correct"))
        if summary and correct and dedupe_prose(summary) == dedupe_prose(correct):
            warns += 1
            _warn(f"{path.name}:{idx} explanation_summary と explanation_correct が同一")
        stem = norm(row.get("stem"))
        if stem and correct and _parrots_stem(stem, correct):
            warns += 1
            _warn(f"{path.name}:{idx} explanation_correct が設問文の言い換え")
        choices = parse_explanation_choices(norm(row.get("explanation_choices")))
        notes = [v for k, v in choices.items() if k != int(row.get("correct") or 0)]
        if len(notes) >= 2 and len(set(notes)) == 1:
            if is_template_site():
                warns += 1
                _warn(f"{path.name}:{idx} 他肢解説が全肢同一")
            else:
                errs += 1
                _error(f"{path.name}:{idx} 他肢解説が全肢同一")
        body = f"{summary} {correct}"
        mode = question_ask_mode(stem)
        if mode == "most_correct" and re.search(r"誤っている|不適切", body):
            warns += 1
            _warn(f"{path.name}:{idx} 正しいもの問題なのに解説に「誤り」表現")
        if mode == "least_appropriate" and re.search(r"正しいものは", body) and "正答" not in body:
            warns += 1
            _warn(f"{path.name}:{idx} 最も不適切問題の解説表現を要確認")
    return errs, warns


def audit_practice() -> tuple[int, int]:
    path = DATA / "practice_questions.csv"
    if not path.is_file():
        return 0, 0
    errs = warns = 0
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for idx, row in enumerate(rows, start=2):
        if is_demo_practice_question_row(row):
            warns += 1
            _warn(f"{path.name}:{idx} デモ・テンプレ実践演習（静的ページ生成対象外）")
    return errs, warns


def audit_ichimon() -> tuple[int, int]:
    path = DATA / "ichimon_questions.csv"
    if not path.is_file():
        return 0, 0
    errs = warns = 0
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    primary = build_ichimon_primary_ids(rows)
    thin_branches = sum(1 for r in rows if norm(r.get("id")) not in primary)
    if thin_branches:
        _warn(
            f"{path.name}: 選択肢枝番の一問一答 {thin_branches} 行は noindex（元問あたり最小枝番のみ index）"
        )
        warns += thin_branches
    for idx, row in enumerate(rows, start=2):
        ans = norm(row.get("answer"))
        summary = norm(row.get("explanation_summary"))
        correct = norm(row.get("explanation_correct"))
        exp = norm(row.get("explanation"))
        is_true = ans in {"○", "O", "o", "true", "TRUE", "1"}
        is_false = ans in {"×", "x", "X", "false", "FALSE", "0"}
        combined = f"{summary} {correct} {exp}"
        if is_true and re.search(r"誤りです|誤った記述|×\s*が正答", combined):
            errs += 1
            _error(f"{path.name}:{idx} 正答○なのに解説が誤り扱い")
        if is_false and re.search(r"正しい内容です|正当である|○\s*が正答", combined) and "誤" not in summary[:20]:
            errs += 1
            _error(f"{path.name}:{idx} 正答×なのに解説が正しい扱い")
        if summary and correct and dedupe_prose(summary) == dedupe_prose(correct):
            warns += 1
            _warn(f"{path.name}:{idx} explanation_summary と explanation_correct が同一")
    return errs, warns


def main() -> int:
    total_err = total_warn = 0
    for fn in (audit_past, audit_practice, audit_ichimon):
        e, w = fn()
        total_err += e
        total_warn += w
    print(f"Question explanation audit: {total_err} error(s), {total_warn} warning(s)")
    return 1 if total_err else 0


if __name__ == "__main__":
    raise SystemExit(main())
