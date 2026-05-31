#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A級ガイド記事（または内部マーカー付き行）の CSV 本文を sanitize する（全サイト共通）。"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_article_pages import sanitize_guide_text  # noqa: E402
from tools.editorial_quality import is_published_guide  # noqa: E402
from tools.guide_coherence_rules import INTERNAL_MARKER_RE, is_tier_a_slug  # noqa: E402

GUIDE_CSV = ROOT / "data" / "guide_articles.csv"

TEXT_COLUMNS = (
    "lead",
    "user_intent",
    "meta_description",
    "action_items",
    *(f"section_{n}_heading" for n in range(1, 8)),
    *(f"section_{n}_body" for n in range(1, 8)),
    *(f"faq_{n}_question" for n in range(1, 5)),
    *(f"faq_{n}_answer" for n in range(1, 5)),
)


def norm(s: str | None) -> str:
    return (s or "").strip()


def row_has_marker(row: dict[str, str]) -> bool:
    for col in TEXT_COLUMNS:
        if INTERNAL_MARKER_RE.search(norm(row.get(col))):
            return True
    return False


def should_patch(row: dict[str, str], *, all_published: bool) -> bool:
    slug = norm(row.get("slug"))
    if not slug or not is_published_guide(row):
        return False
    if all_published:
        return True
    if is_tier_a_slug(slug):
        return True
    return row_has_marker(row)


def patch_row(row: dict[str, str], fieldnames: list[str]) -> bool:
    slug = norm(row.get("slug"))
    changed = False
    for col in TEXT_COLUMNS:
        if col not in fieldnames:
            continue
        val = norm(row.get(col))
        if not val:
            continue
        cleaned = sanitize_guide_text(val, slug)
        if cleaned != val:
            row[col] = cleaned
            changed = True
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="ガイド CSV の A級／マーカー行を sanitize")
    parser.add_argument("--all-published", action="store_true", help="公開記事すべてを対象")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not GUIDE_CSV.is_file():
        print(f"missing {GUIDE_CSV}", file=sys.stderr)
        return 1

    with GUIDE_CSV.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    patched = 0
    for i, row in enumerate(rows):
        if not should_patch(row, all_published=args.all_published):
            continue
        if patch_row(rows[i], fieldnames):
            patched += 1

    if patched == 0:
        print("No rows needed sanitize.", file=sys.stderr)
        return 0

    if args.dry_run:
        print(f"Would sanitize {patched} rows in {GUIDE_CSV}")
        return 0

    with GUIDE_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Sanitized {patched} rows in {GUIDE_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
