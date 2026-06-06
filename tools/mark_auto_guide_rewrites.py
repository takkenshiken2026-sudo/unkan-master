#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""誤って「手書きリライト」になっている自動 prose 行の revision_note を修正。"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_guide_rewrite_inventory import PROSE_COLS, reader_text  # noqa: E402
from tools.editorial_quality import is_published_guide, norm  # noqa: E402
from tools.guide_rewrite_quality import is_auto_prose_text, revision_is_hand  # noqa: E402
from tools.rewrite_guide_boilerplate import _csv_fieldnames  # noqa: E402

TODAY = date.today().isoformat()
AUTO_NOTE = f"{TODAY}: 自動prose差し替え（要手書き）"


def combined_prose(row: dict[str, str]) -> str:
    slug = norm(row.get("slug"))
    parts = [reader_text(row, c, slug) for c in PROSE_COLS]
    return "\n".join(p for p in parts if p)


def mark_csv(csv_path: Path, *, dry_run: bool) -> tuple[int, int]:
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8-sig")))
    if not rows:
        return 0, 0
    fieldnames = list(rows[0].keys())
    marked = 0
    for row in rows:
        if not is_published_guide(row):
            continue
        text = combined_prose(row)
        if not is_auto_prose_text(text) and not revision_is_hand(row):
            continue
        if "自動prose" in norm(row.get("revision_note")):
            continue
        if revision_is_hand(row) or is_auto_prose_text(text):
            row["revision_note"] = AUTO_NOTE
            note = norm(row.get("original_note"))
            row["original_note"] = note.replace("手書きリライト 2026-06-04。", "").replace(
                "手書きリライト 2026-06-04.", ""
            ).strip()
            if row["original_note"] and not row["original_note"].endswith("。"):
                row["original_note"] += "。"
            row["original_note"] = f"自動prose差し替え {TODAY}（要手書き）。" + (row["original_note"] or "")
            marked += 1
    if marked and not dry_run:
        fieldnames = _csv_fieldnames(fieldnames, rows)
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    return marked, len([r for r in rows if is_published_guide(r)])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    csv_path = args.root.resolve() / "data" / "guide_articles.csv"
    marked, pub = mark_csv(csv_path, dry_run=args.dry_run)
    mode = "would mark" if args.dry_run else "marked"
    print(f"{mode} {marked} / {pub} published rows in {args.root.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
