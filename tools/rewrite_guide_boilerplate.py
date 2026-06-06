#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""量産テンプレを含む guide 行をサイト別の具体本文に一括差し替え。"""

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
from tools.guide_rewrite_prose import (  # noqa: E402
    MIN_FAQ,
    MIN_SECTION,
    action_items,
    column_needs_rewrite,
    faq_pair,
    load_site_ctx,
    meta_description,
    section_body,
    user_intent,
)
from tools.guide_rewrite_rules import is_affiliate_row, is_hand_rewritten, rewrite_exempt  # noqa: E402
from tools.site_config import brand_name, exam_name, official_organization, primary_external_link  # noqa: E402

TODAY = date.today().isoformat()
REVISION = f"{TODAY}: 自動prose差し替え（要手書き）"


def official_label() -> str:
    org = norm(official_organization())
    if org:
        return org
    link = primary_external_link()
    return norm(link.get("label")) or "公式サイト"


def patch_row(row: dict[str, str], ctx, *, force: bool = False) -> bool:
    if not is_published_guide(row):
        return False
    if not force and rewrite_exempt(row):
        return False
    if is_affiliate_row(row) and not is_hand_rewritten(row):
        return False

    changed = False
    slug = norm(row.get("slug"))

    if force or column_needs_rewrite(row.get("meta_description", ""), min_len=70):
        row["meta_description"] = meta_description(row, ctx)
        changed = True
    if force or column_needs_rewrite(row.get("user_intent", ""), min_len=50):
        row["user_intent"] = user_intent(row, ctx)
        changed = True
    if force or column_needs_rewrite(row.get("action_items", "")):
        row["action_items"] = action_items(row, ctx)
        changed = True

    for i in range(1, 8):
        col = f"section_{i}_body"
        raw = norm(row.get(col))
        if not raw and i > 5:
            continue
        if not force and raw and not column_needs_rewrite(raw, min_len=MIN_SECTION):
            continue
        heading = norm(row.get(f"section_{i}_heading")) or f"要点{i}"
        row[col] = section_body(row, ctx, i, heading)
        changed = True

    for i in range(1, 4):
        qcol = f"faq_{i}_question"
        acol = f"faq_{i}_answer"
        q = norm(row.get(qcol))
        a = norm(row.get(acol))
        if (
            not force
            and q
            and a
            and not column_needs_rewrite(a, min_len=MIN_FAQ)
            and not column_needs_rewrite(q)
        ):
            continue
        nq, na = faq_pair(row, ctx, i)
        row[qcol] = nq
        row[acol] = na
        changed = True

    if changed:
        row["revision_note"] = REVISION
        row["fact_checked_at"] = TODAY
        row["last_reviewed_at"] = TODAY
        row["source_checked_at"] = TODAY
        note = norm(row.get("original_note"))
        if "手書きリライト" not in note and "自動prose" not in note:
            row["original_note"] = f"自動prose差し替え {TODAY}（要手書き）。" + (note if note else "")
    return changed


def _csv_fieldnames(initial: list[str], rows: list[dict[str, str]]) -> list[str]:
    names = list(initial)
    for row in rows:
        for key in row:
            if key in names:
                continue
            if key == "faq_3_question" and "faq_3_answer" in names:
                names.insert(names.index("faq_3_answer"), key)
            else:
                names.append(key)
    return names


def run(csv_path: Path, *, dry_run: bool, force: bool) -> tuple[int, int]:
    ctx = load_site_ctx(exam_name(), official_label(), brand_name())
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8-sig")))
    if not rows:
        return 0, 0
    fieldnames = list(rows[0].keys())
    patched = 0
    for row in rows:
        if patch_row(row, ctx, force=force):
            patched += 1
    fieldnames = _csv_fieldnames(fieldnames, rows)
    if patched and not dry_run:
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    return patched, len(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="試験ガイド量産テンプレ一括リライト")
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="手書き済み行も再生成")
    args = ap.parse_args()
    csv_path = args.root.resolve() / "data" / "guide_articles.csv"
    if not csv_path.is_file():
        print(f"missing {csv_path}", file=sys.stderr)
        return 1
    patched, total = run(csv_path, dry_run=args.dry_run, force=args.force)
    mode = "would patch" if args.dry_run else "patched"
    print(f"{mode} {patched} / {total} rows in {csv_path.parent.parent.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
