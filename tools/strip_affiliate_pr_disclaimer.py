#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remove affiliate PR boilerplate from guide_articles.csv text columns."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.guide_content_shared import strip_affiliate_pr_disclaimer  # noqa: E402

ARTICLES_CSV = "data/guide_articles.csv"
TEXT_SUFFIXES = ("lead", "meta_description", "user_intent", "action_items", "original_note", "revision_note")
SECTION_BODY = tuple(f"section_{i}_body" for i in range(1, 8))
FAQ_ANSWER = tuple(f"faq_{i}_answer" for i in range(1, 4))
TEXT_COLUMNS = TEXT_SUFFIXES + SECTION_BODY + FAQ_ANSWER


def strip_row(row: dict[str, str]) -> int:
    changed = 0
    for col in TEXT_COLUMNS:
        if col not in row:
            continue
        before = row.get(col) or ""
        after = strip_affiliate_pr_disclaimer(before)
        if after != before:
            row[col] = after
            changed += 1
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Site root (default: exam-site-shell)",
    )
    args = parser.parse_args()
    path = args.root / ARTICLES_CSV
    if not path.is_file():
        print(f"skip: {path} not found", file=sys.stderr)
        return 1

    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames:
            print("empty CSV", file=sys.stderr)
            return 1
        rows = list(reader)

    total = sum(strip_row(row) for row in rows)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print(f"stripped PR disclaimer from {total} cells in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
