#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Set content_status=draft on affiliate rows without ASP links (non-public until ready)."""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.affiliate_links import affiliate_external_links_in_row, is_affiliate_article  # noqa: E402

ARTICLES_CSV = "data/guide_articles.csv"
NOTE = "ASPリンク未設定のため draft（非公開）"


def draft_unlinked(rows: list[dict[str, str]]) -> int:
    changed = 0
    today = date.today().isoformat()
    for row in rows:
        if not is_affiliate_article(row):
            continue
        if affiliate_external_links_in_row(row):
            continue
        if (row.get("content_status") or "").strip() != "published":
            continue
        row["content_status"] = "draft"
        note = (row.get("revision_note") or "").strip()
        if NOTE not in note:
            row["revision_note"] = f"{note}; {NOTE} ({today})".strip("; ")
        changed += 1
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    path = args.root / ARTICLES_CSV
    if not path.is_file():
        print(f"skip: {path}", file=sys.stderr)
        return 1
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames:
            return 1
        rows = list(reader)
    n = draft_unlinked(rows)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"drafted {n} unlinked affiliate row(s) in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
