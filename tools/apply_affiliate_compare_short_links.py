#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公開済み affiliate 比較記事の本文 bare slug を短ラベル Markdown リンクへ一括変換。"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.affiliate_compare_short_links import (  # noqa: E402
    bare_affiliate_slugs,
    labels_for_site,
    replace_bare_slugs,
)
from tools.affiliate_links import is_affiliate_article  # noqa: E402


def detect_site_id(target: Path) -> str:
    cfg = target / "site-config.json"
    if cfg.exists():
        import json

        data = json.loads(cfg.read_text(encoding="utf-8"))
        sid = (data.get("siteId") or data.get("site_id") or "").strip()
        if sid:
            return sid
    return target.name


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=ROOT / "data" / "guide_articles.csv")
    ap.add_argument("--site-id", default="", help="短ラベル辞書用（省略時は site-config.json）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--include-draft", action="store_true")
    args = ap.parse_args()

    csv_path = args.csv.resolve()
    site_id = args.site_id or detect_site_id(ROOT)
    labels = labels_for_site(site_id)

    rows: list[dict[str, str]] = []
    changed_slugs: list[str] = []

    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames:
            print("ERROR: empty CSV", file=sys.stderr)
            return 1
        for row in reader:
            if not is_affiliate_article(row):
                rows.append(row)
                continue
            status = row.get("content_status") or ""
            if status != "published" and not args.include_draft:
                rows.append(row)
                continue
            slug = row["slug"]
            row_changed = False
            for key in fieldnames:
                if not key.endswith("_body") or not key.startswith("section_") or not row.get(key):
                    continue
                before = row[key]
                after = replace_bare_slugs(before, labels)
                if after != before:
                    row[key] = after
                    row_changed = True
            if row_changed:
                changed_slugs.append(slug)
            rows.append(row)

    if not changed_slugs:
        print(f"OK: no bare affiliate slugs to fix ({site_id})")
        return 0

    print(f"{'DRY-RUN: ' if args.dry_run else ''}fix {len(changed_slugs)} article(s): {', '.join(changed_slugs)}")
    if args.dry_run:
        return 0

    orig_lines = sum(1 for _ in csv_path.open(encoding="utf-8-sig"))
    fd, tmp = tempfile.mkstemp(suffix=".csv", dir=csv_path.parent)
    try:
        with open(fd, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        new_lines = sum(1 for _ in open(tmp, encoding="utf-8"))
        if new_lines != orig_lines:
            print(f"ERROR: line count {orig_lines} -> {new_lines}", file=sys.stderr)
            return 1
        shutil.move(tmp, csv_path)
    finally:
        if Path(tmp).exists():
            Path(tmp).unlink()

    print(f"OK: short links applied ({site_id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
