#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知識ハブ（numbers.csv）の試験申込・日程・手数料案内を試験ガイドへ移管する。

正本: docs/content-positioning.md — 申込・日程・手数料の確認手順は guide_articles.csv

  python3 tools/migrate_hub_admin_to_guide.py --dry-run
  python3 tools/migrate_hub_admin_to_guide.py
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.content_placement_rules import (  # noqa: E402
    hub_exam_admin_kind,
    is_hub_exam_admin_row,
    norm,
    resolve_guide_admin_slug,
)

NUMBERS_CSV = ROOT / "data" / "numbers.csv"
GUIDE_CSV = ROOT / "data" / "guide_articles.csv"
REDIRECTS_JSON = ROOT / "data" / "hub_redirects.json"
MIGRATION_NOTE = "配置整理: 試験申込・日程・手数料の正本は試験ガイド"


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        return fields, list(reader)


def save_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    all_keys = list(fields)
    for row in rows:
        for key in row:
            if key not in all_keys:
                all_keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_redirects(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {"compare": {}, "numbers": {}, "mistakes": {}}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"compare": {}, "numbers": {}, "mistakes": {}}
    out: dict[str, dict[str, str]] = {}
    for key in ("compare", "numbers", "mistakes"):
        section = raw.get(key)
        out[key] = {str(k): str(v) for k, v in section.items()} if isinstance(section, dict) else {}
    return out


def save_redirects(path: Path, redirects: dict[str, dict[str, str]]) -> None:
    path.write_text(json.dumps(redirects, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def guide_href(slug: str) -> str:
    return f"/articles/{slug}.html"


def migrate_hub_admin_to_guide(
    *,
    site_root: Path | None = None,
    dry_run: bool = False,
) -> tuple[int, int]:
    root = site_root or ROOT
    numbers_path = root / "data" / "numbers.csv"
    guide_path = root / "data" / "guide_articles.csv"
    redirects_path = root / "data" / "hub_redirects.json"
    site_name = root.name

    if not numbers_path.is_file() or not guide_path.is_file():
        return 0, 0

    num_fields, numbers = load_csv(numbers_path)
    _guide_fields, guides = load_csv(guide_path)
    redirects = load_redirects(redirects_path)

    removed = 0
    redirected = 0
    kept: list[dict[str, str]] = []

    for row in numbers:
        slug = norm(row.get("slug"))
        if not is_hub_exam_admin_row(row):
            kept.append(row)
            continue
        kind = hub_exam_admin_kind(row)
        if not kind:
            kept.append(row)
            continue
        target = resolve_guide_admin_slug(kind, guides, site_name=site_name)
        if not target:
            print(f"skip {slug}: no guide target for {kind}", file=sys.stderr)
            kept.append(row)
            continue

        title = norm(row.get("title"))
        href = guide_href(target)
        print(f"remove numbers/{slug} ({title}) -> guide/{target}")
        if not dry_run:
            redirects["numbers"][slug] = href
        removed += 1
        redirected += 1

    if removed and not dry_run:
        save_csv(numbers_path, num_fields, kept)
        save_redirects(redirects_path, redirects)
        print(f"Updated {numbers_path} (-{removed} rows)")
        print(f"Updated {redirects_path} (+{redirected} guide redirects)")

    return removed, redirected


def main() -> int:
    parser = argparse.ArgumentParser(description="Move exam admin rows from numbers.csv to guide")
    parser.add_argument("--target", type=Path, default=ROOT, help="Site root")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    removed, _ = migrate_hub_admin_to_guide(site_root=args.target.resolve(), dry_run=args.dry_run)
    if args.dry_run:
        print(f"dry-run: would remove {removed} numbers rows")
    elif removed == 0:
        print("No rows to migrate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
