#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知識ハブ一覧の定義・概要（index_summary）を詳細記事ベースで再生成し CSV を更新する。

  python3 tools/refresh_index_summaries.py
  python3 tools/refresh_index_summaries.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.knowledge_index_summary import (  # noqa: E402
    glossary_index_definition,
    hub_index_summary,
    load_glossary_seed_map,
    norm,
)

GLOSSARY_CSV = ROOT / "data" / "glossary_terms.csv"
COMPARE_CSV = ROOT / "data" / "comparisons.csv"
NUMBERS_CSV = ROOT / "data" / "numbers.csv"
MISTAKES_CSV = ROOT / "data" / "mistakes.csv"


def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        return fields, list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def refresh_glossary(*, dry_run: bool) -> int:
    fields, rows = read_csv(GLOSSARY_CSV)
    seed_map = load_glossary_seed_map()
    changed = 0
    for row in rows:
        term = norm(row.get("term"))
        if not term:
            continue
        new_def = glossary_index_definition(row, seed=seed_map.get(term))
        if not new_def:
            continue
        if norm(row.get("short_def")) != new_def:
            changed += 1
            if not dry_run:
                row["short_def"] = new_def
    if not dry_run:
        write_csv(GLOSSARY_CSV, fields, rows)
    print(f"glossary_terms.csv: {changed} 件の short_def（一覧定義）を更新")
    return changed


def refresh_hub_csv(path: Path, *, dry_run: bool) -> int:
    fields, rows = read_csv(path)
    if "summary" not in fields:
        print(f"{path.name}: summary 列がありません", file=sys.stderr)
        return 0
    changed = 0
    for row in rows:
        new_summary = hub_index_summary(row)
        if not new_summary:
            continue
        if norm(row.get("summary")) != new_summary:
            changed += 1
            if not dry_run:
                row["summary"] = new_summary
    if not dry_run:
        write_csv(path, fields, rows)
    print(f"{path.name}: {changed} 件の summary（一覧概要）を更新")
    return changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    n = 0
    n += refresh_glossary(dry_run=args.dry_run)
    n += refresh_hub_csv(COMPARE_CSV, dry_run=args.dry_run)
    n += refresh_hub_csv(NUMBERS_CSV, dry_run=args.dry_run)
    n += refresh_hub_csv(MISTAKES_CSV, dry_run=args.dry_run)

    if args.dry_run:
        print(f"dry-run: 合計 {n} 件が更新対象です")
    else:
        print(f"完了: 合計 {n} 件を更新しました。続けて build_glossary_pages.py 等を実行してください。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
