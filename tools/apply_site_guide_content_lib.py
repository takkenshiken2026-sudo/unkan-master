#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guide_articles.csv をサイト別 archive content lib で全面更新。"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.editorial_quality import is_published_guide, norm  # noqa: E402
from tools.fix_guide_duplicate_bodies import (  # noqa: E402
    load_site_lib,
    patch_row_sections,
    repair_coherence_faqs,
)
from tools.guide_rewrite_quality import revision_is_hand  # noqa: E402

TODAY = date.today().isoformat()


def upgrade_meta_row(row: dict[str, str], lib) -> bool:
    changed = False
    topic = lib.topic_from_row(row)
    slug = norm(row.get("slug"))
    genre = norm(row.get("genre"))

    for check, col, fn in (
        (lambda: len(norm(row.get("meta_description"))) < 70 or lib.is_stub(row.get("meta_description", "")), "meta_description", lambda: lib.meta_description_for(row, topic)),
        (lambda: lib.is_stub(row.get("user_intent", "")), "user_intent", lambda: lib.user_intent_for(topic, genre)),
        (lambda: len(norm(row.get("action_items")).split(";")) < 3, "action_items", lambda: lib.action_items_for(topic, slug, genre)),
    ):
        if check():
            row[col] = fn()
            changed = True

    new_lead = lib.lead_for(row, topic)
    if new_lead != norm(row.get("lead")):
        row["lead"] = new_lead
        changed = True
    if not norm(row.get("key_points")):
        row["key_points"] = lib.key_points_for(row, topic)
        changed = True
    return changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-meta", action="store_true", help="section/faq のみ")
    args = ap.parse_args()
    root = args.root.resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    guide_path = root / "data" / "guide_articles.csv"
    if not guide_path.is_file():
        print(f"missing {guide_path}", file=sys.stderr)
        return 1

    lib = load_site_lib(root)
    rows = list(csv.DictReader(guide_path.open(encoding="utf-8-sig")))
    fieldnames = list(rows[0].keys())
    touched = 0
    for row in rows:
        if not is_published_guide(row):
            continue
        if revision_is_hand(row):
            continue
        before = {k: row.get(k) for k in row}
        if not args.skip_meta:
            if upgrade_meta_row(row, lib):
                touched += 1
        patch_row_sections(row, fieldnames, lib)
        if before != {k: row.get(k) for k in row}:
            touched += 1
        row["revision_note"] = f"{TODAY}: content-lib更新（要手書き仕上げ）"
    repair_coherence_faqs(rows, fieldnames, lib)

    if args.dry_run:
        print(f"dry-run: would touch rows in {root.name}")
        return 0

    fieldnames = _csv_fieldnames(fieldnames, rows)
    with guide_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"content-lib upgraded {root.name}: {touched}+ rows touched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
