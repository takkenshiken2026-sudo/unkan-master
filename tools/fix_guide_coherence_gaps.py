#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_csv の coherence ERROR（持ち物・アクセス・空 lead 等）を機械修復する。"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.editorial_quality import is_published_guide, norm  # noqa: E402
from tools.guide_coherence_rules import (  # noqa: E402
    check_guide_row_coherence,
    seo_bracket_title,
    short_topic_from_title,
)
from tools.guide_content_shared import (  # noqa: E402
    exam_day_forget_checklist_prose,
    exam_venue_access_prose,
)

ITEM_HINTS = ("持ち", "受験票", "鉛筆", "消しゴム", "禁止", "筆記")
VENUE_WRONG = ("得点率", "参考書を増やさず", "演習で同テーマ", "付箋を付けながら")
PROSE_COLS = (
    "lead",
    "user_intent",
    "meta_description",
    "action_items",
    *(f"section_{n}_body" for n in range(1, 8)),
    *(f"faq_{n}_answer" for n in range(1, 5)),
)


def _load_official(root: Path) -> str:
    cfg = root / "site-config.json"
    if not cfg.is_file():
        return "試験実施団体（公式）"
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
        return norm(data.get("officialOrganization") or "試験実施団体（公式）")
    except json.JSONDecodeError:
        return "試験実施団体（公式）"


def _needs_belongings_body(heading: str, body: str) -> bool:
    if "持ち物" not in norm(heading):
        return False
    return not any(x in norm(body) for x in ITEM_HINTS)


def _needs_venue_body(heading: str, body: str) -> bool:
    h = norm(heading)
    if not any(k in h for k in ("アクセス", "会場")):
        return False
    b = norm(body)
    return any(p in b for p in VENUE_WRONG)


def fix_row(row: dict[str, str], *, official: str) -> bool:
    if not is_published_guide(row):
        return False
    title = norm(row.get("title"))
    topic = short_topic_from_title(title) or title
    before = {k: row.get(k, "") for k in row}

    if not norm(row.get("lead")):
        row["lead"] = (
            f"{topic}について、{official}の要項確認と学習の進め方を整理します。"
            f"受験前に押さえるべきポイントと、このサイトでの演習・用語解説の活用法を解説します。"
        )

    bracket = seo_bracket_title(title)
    if bracket:
        short = short_topic_from_title(title)
        for col in PROSE_COLS:
            text = norm(row.get(col))
            if text and bracket in text and short:
                row[col] = text.replace(bracket, short)

    for idx in range(1, 8):
        hcol = f"section_{idx}_heading"
        bcol = f"section_{idx}_body"
        heading = norm(row.get(hcol))
        body = norm(row.get(bcol))
        if not heading or not body:
            continue
        if _needs_belongings_body(heading, body):
            row[bcol] = exam_day_forget_checklist_prose(official=official, topic=topic)
        elif _needs_venue_body(heading, body):
            row[bcol] = exam_venue_access_prose(official=official, topic=topic)

    return any(before.get(k) != row.get(k, "") for k in row)


def fix_site(root: Path, *, dry_run: bool = False) -> dict:
    guide_csv = root / "data" / "guide_articles.csv"
    if not guide_csv.is_file():
        return {"changed": 0, "error": "missing guide_articles.csv"}
    official = _load_official(root)
    with guide_csv.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    changed = sum(1 for row in rows if fix_row(row, official=official))
    if changed and not dry_run:
        with guide_csv.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    errors = 0
    for row in rows:
        if not is_published_guide(row):
            continue
        for issue in check_guide_row_coherence(row, published=True):
            if issue.level == "ERROR":
                errors += 1
    return {"changed": changed, "rows": len(rows), "coherence_errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description="ガイド coherence ギャップ修復")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    stats = fix_site(args.root.resolve(), dry_run=args.dry_run)
    print(f"fix coherence gaps: {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
