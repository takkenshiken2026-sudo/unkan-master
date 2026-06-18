#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""非アフィリエイト試験ガイドの本文を v4 ゼロ執筆用に一括クリアする。

- 本文・FAQ・メタ等の prose 列を空にする
- published → draft（本番に未完成本文を出さない）
- archived は archived のまま（本文のみクリア）
- アフィリエイト行は触らない
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.editorial_quality import norm  # noqa: E402
from tools.guide_rewrite_rules import is_affiliate_row  # noqa: E402

CSV_PATH = ROOT / "data" / "guide_articles.csv"
V4_PENDING_NOTE = "v4待ち·ゼロ執筆"

PROSE_COLUMNS: tuple[str, ...] = (
    "meta_description",
    "lead",
    "user_intent",
    "action_items",
    "key_points",
    *(f"section_{n}_{kind}" for n in range(1, 8) for kind in ("heading", "body")),
    *(f"faq_{n}_{kind}" for n in range(1, 4) for kind in ("question", "answer")),
)

DATE_COLUMNS: tuple[str, ...] = (
    "fact_checked_at",
    "last_reviewed_at",
    "source_checked_at",
)


def clear_row(row: dict[str, str], *, today: str) -> bool:
    if is_affiliate_row(row):
        return False
    changed = False
    for col in PROSE_COLUMNS:
        if norm(row.get(col)):
            row[col] = ""
            changed = True
    for col in DATE_COLUMNS:
        if norm(row.get(col)):
            row[col] = ""
            changed = True
    status = norm(row.get("content_status")).lower()
    if status in {"", "published", "publish"}:
        row["content_status"] = "draft"
        changed = True
    if norm(row.get("revision_note")) != V4_PENDING_NOTE:
        row["revision_note"] = V4_PENDING_NOTE
        changed = True
    note = norm(row.get("original_note"))
    stamp = f"v4本文クリア {today}。"
    if stamp not in note:
        row["original_note"] = stamp + (note if note else "")
        changed = True
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(description="非アフィリエイトガイド本文を v4 用にクリア")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not CSV_PATH.is_file():
        print(f"missing {CSV_PATH}", file=sys.stderr)
        return 1
    today = date.today().isoformat()
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    cleared = 0
    for row in rows:
        if clear_row(row, today=today):
            cleared += 1
    mode = "would clear" if args.dry_run else "cleared"
    print(f"{mode} {cleared} non-affiliate guide row(s)")
    if not args.dry_run and cleared:
        with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
