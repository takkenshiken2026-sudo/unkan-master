#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""運行管理者試験（貨物）実践演習 CSV → data/practice_questions.csv に取り込む。

入力 (運行管理者試験センター形式・25 列・過去問と同スキーマ)。
出力 (本番拡張形式・24 列):
  data/practice_questions.csv

採用ポリシーは tools/import_unkan_freight_csv.py と同一（全形式取り込み）。
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DEFAULT_SOURCE = Path.home() / "Desktop" / "運行管理者試験_実践演習500問.csv"

OUT_CSV = DATA_DIR / "practice_questions.csv"
SOURCE_COPY = DATA_DIR / "source_unkan_freight_practice.csv"

OUT_HEADERS = [
    "question_no", "type", "category", "tags",
    "stem", "preamble",
    "statement_a", "statement_b", "statement_c", "statement_d",
    "choice_1", "choice_2", "choice_3", "choice_4",
    "choice_5", "choice_6", "choice_7", "choice_8",
    "correct",
    "explanation", "explanation_summary", "explanation_correct",
    "explanation_choices", "explanation_point",
]

# import_unkan_freight_csv のロジックを共有
sys.path.insert(0, str(ROOT))
from tools.import_unkan_freight_csv import (  # noqa: E402
    QTYPE_MAP, collect_choices, norm, normalize_correct,
)


def convert_row(row: dict, *, line: int, log_skip: list[str]) -> dict | None:
    src_qtype = norm(row.get("question_type"))
    qtype = QTYPE_MAP.get(src_qtype)
    if not qtype:
        log_skip.append(f"line {line}: skip qtype={src_qtype!r}")
        return None

    choices = collect_choices(row)
    if len(choices) < 2:
        log_skip.append(f"line {line}: skip choices<2 ({len(choices)})")
        return None

    correct = normalize_correct(qtype, row.get("correct_answer", ""), len(choices))
    if correct is None:
        log_skip.append(
            f"line {line}: skip type={qtype} correct={row.get('correct_answer')!r}"
        )
        return None

    qno = int(norm(row.get("question_no")) or 0)
    if qno <= 0:
        log_skip.append(f"line {line}: skip qno={row.get('question_no')!r}")
        return None

    out = {h: "" for h in OUT_HEADERS}
    out["question_no"] = str(qno)
    out["type"] = qtype
    out["category"] = norm(row.get("section_name"))
    out["tags"] = ""
    out["stem"] = norm(row.get("prompt"))
    out["preamble"] = ""
    for idx, value in enumerate(choices, start=1):
        if idx <= 8:
            out[f"choice_{idx}"] = value
    out["correct"] = correct
    out["explanation"] = norm(row.get("explanation"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="運管・貨物の実践演習 CSV を取り込む")
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                    help=f"入力 CSV (default: {DEFAULT_SOURCE})")
    ap.add_argument("--keep-source-copy", action="store_true",
                    help=f"オリジナル CSV を {SOURCE_COPY} にコピー保存")
    args = ap.parse_args()

    src: Path = args.source
    if not src.is_file():
        print(f"error: source not found: {src}", file=sys.stderr)
        return 1

    text = src.read_text(encoding="utf-8-sig")
    rows = list(csv.DictReader(text.splitlines()))

    converted: list[dict] = []
    skipped: list[str] = []
    qtype_counter = Counter()
    out_qtype_counter = Counter()

    for i, row in enumerate(rows, start=2):
        qtype_counter[norm(row.get("question_type"))] += 1
        out = convert_row(row, line=i, log_skip=skipped)
        if out is None:
            continue
        converted.append(out)
        out_qtype_counter[out["type"]] += 1

    seen: set[int] = set()
    deduped: list[dict] = []
    for r in converted:
        key = int(r["question_no"])
        if key in seen:
            skipped.append(f"dup qno={key}")
            continue
        seen.add(key)
        deduped.append(r)

    deduped.sort(key=lambda r: int(r["question_no"]))

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_HEADERS)
        writer.writeheader()
        writer.writerows(deduped)

    if args.keep_source_copy:
        SOURCE_COPY.write_text(text, encoding="utf-8")

    print(f"source: {src}")
    print(f"output: {OUT_CSV} ({len(deduped)} rows)")
    print("question_type counts in source:")
    for qt, n in qtype_counter.most_common():
        print(f"  {n:>5}  {qt}")
    print("normalized type counts in output:")
    for qt, n in out_qtype_counter.most_common():
        print(f"  {n:>5}  {qt}")
    print(f"skipped: {len(rows) - len(deduped)} (parse error / dup)")
    if skipped:
        print("first 10 skip reasons:")
        for s in skipped[:10]:
            print(f"  {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
