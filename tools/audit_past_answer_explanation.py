#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""past_questions.csv の正答と解説（生成 HTML 含む）の整合を検査する。"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_past_question_pages import page_dict
from tools.q_explanation import (
    build_choice_commentary,
    build_explanation_html,
    norm,
    # 旧名 parse_fullwidth_numbered_explanation は未実装。
    # 全角／半角の「１．…２．…」形式の肢別解説を分解する現行関数を使う。
    parse_numbered_choice_notes as parse_fullwidth_numbered_explanation,
)

DATA_CSV = ROOT / "data" / "past_questions.csv"


def strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def audit_row(row: dict, line_no: int) -> list[str]:
    issues: list[str] = []
    try:
        page = page_dict(row, line_no)
    except ValueError as exc:
        return [str(exc)]

    if page.get("is_invalidated") or page.get("correct") is None:
        return []

    cor = page["correct"]
    exp = norm(row.get("explanation"))
    numbered = parse_fullwidth_numbered_explanation(exp)

    html = build_explanation_html(page, row)
    if "他の選択肢" not in html:
        return issues

    wrong_html = html.split("他の選択肢", 1)[1].split("学習のヒント", 1)[0]
    wrong_nums = {
        int(m) for m in re.findall(r'q-exp-choice-num">（(\d+)）', wrong_html)
    }
    if cor in wrong_nums:
        issues.append(f"生成 HTML の「他の選択肢」に正答（{cor}）が含まれる")

    for n, _opt, note in build_choice_commentary(page, row):
        if "正答になりません" not in note:
            continue
        chunk = numbered.get(n, "")
        if chunk and len(chunk) > 40 and chunk[:48] not in note:
            issues.append(
                f"（{n}）に詳細解説があるのに汎用テンプレが使われている"
            )

    correct_html = strip_html(html.split("他の選択肢", 1)[0])
    if re.search(rf"（{cor}）[^。]{{0,80}}正答になりません", correct_html):
        issues.append("生成 HTML の正解の理由が正答肢を誤りと説明している")

    return issues


def main() -> int:
    if not DATA_CSV.is_file():
        print(f"error: CSV not found: {DATA_CSV}", file=sys.stderr)
        return 1

    rows = list(csv.DictReader(DATA_CSV.read_text(encoding="utf-8-sig").splitlines()))
    total_issues = 0
    for idx, row in enumerate(rows, start=2):
        row_issues = audit_row(row, idx)
        if row_issues:
            year = row.get("exam_year", "?")
            qno = row.get("question_no", "?")
            for msg in row_issues:
                print(f"ERROR {DATA_CSV.name}:{idx} {year}-{qno}: {msg}")
            total_issues += len(row_issues)

    if total_issues:
        print(f"\n{total_issues} issue(s) in past_questions.csv", file=sys.stderr)
        return 1

    print(f"OK: {len(rows)} past questions — answer/explanation consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
