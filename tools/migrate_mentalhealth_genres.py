#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mentalhealth-master の guide_articles.csv genre を 12 区分へ移行する。"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

GENRE_MAP = {
    "学習法": "独学対策",
    "制度理解": "試験概要",
    "受験情報": "受験・申込",
    "受験要項": "受験・申込",
    "直前対策": "直前・当日",
    "出題範囲": "出題・形式",
    "復職支援": "分野別対策",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    path = args.target.resolve() / "data" / "guide_articles.csv"
    if not path.is_file():
        print(f"error: missing {path}", flush=True)
        return 1

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames or "genre" not in fieldnames:
            print("error: genre column missing", flush=True)
            return 1
        rows = list(reader)

    changed = 0
    for row in rows:
        old = (row.get("genre") or "").strip()
        new = GENRE_MAP.get(old, old)
        if new != old:
            row["genre"] = new
            changed += 1
            print(f"  {old} -> {new} ({row.get('slug', '')})")

    print(f"summary: changed={changed} total={len(rows)}")
    if args.dry_run or changed == 0:
        return 0

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
