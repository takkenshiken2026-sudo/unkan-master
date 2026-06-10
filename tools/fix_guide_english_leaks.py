#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ガイド CSV から読者向け不要英文（slug 露出・field-* 等）を一括修正する。

  python3 tools/fix_guide_english_leaks.py --root ~/Projects/eisei2shu-master
  python3 tools/fix_guide_english_leaks.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.editorial_quality import is_published_guide, norm  # noqa: E402
from tools.fix_guide_duplicate_bodies import load_site_lib  # noqa: E402
from tools.guide_field_prose import (  # noqa: E402
    field_prefix_labels,
    resolve_reader_slug_prose,
    scrub_slug_english,
    slug_label,
)

USER_FACING_COLS = (
    "title",
    "meta_description",
    "lead",
    "user_intent",
    "action_items",
    "key_points",
    *(f"section_{n}_heading" for n in range(1, 8)),
    *(f"section_{n}_body" for n in range(1, 8)),
    *(f"faq_{n}_question" for n in range(1, 5)),
    *(f"faq_{n}_answer" for n in range(1, 5)),
)


def _topic_for_row(row: dict[str, str], lib, slug_titles: dict[str, str]) -> str:
    slug = norm(row.get("slug"))
    topic_fn = getattr(lib, "topic_from_row", None)
    if callable(topic_fn):
        try:
            topic = norm(topic_fn(row))
            if topic and not re_fullslug(topic):
                return topic
        except Exception:
            pass
    return slug_label(slug_titles, slug)


def re_fullslug(text: str) -> bool:
    import re

    return bool(re.fullmatch(r"[a-z0-9 -]+", text, re.I))


def fix_cell(
    text: str,
    *,
    slug: str,
    slug_titles: dict[str, str],
    prefix_labels: dict[str, str],
    topic: str,
    link_internal: bool,
) -> str:
    raw = norm(text)
    if not raw:
        return raw
    out = resolve_reader_slug_prose(
        raw,
        slug_titles=slug_titles,
        current_slug=slug,
        link_internal=link_internal,
        prefix_labels=prefix_labels,
    )
    out = scrub_slug_english(out, slug, topic)
    return out


def fix_row(
    row: dict[str, str],
    *,
    slug_titles: dict[str, str],
    prefix_labels: dict[str, str],
    lib,
) -> bool:
    if not is_published_guide(row):
        return False
    slug = norm(row.get("slug"))
    if not slug:
        return False
    topic = _topic_for_row(row, lib, slug_titles)
    changed = False
    for col in USER_FACING_COLS:
        val = row.get(col) or ""
        if not val:
            continue
        link_internal = (col.startswith("section_") and col.endswith("_body")) or (
            col.startswith("faq_") and col.endswith("_answer")
        )
        fixed = fix_cell(
            val,
            slug=slug,
            slug_titles=slug_titles,
            prefix_labels=prefix_labels,
            topic=topic,
            link_internal=link_internal,
        )
        if fixed != norm(val):
            row[col] = fixed
            changed = True
    return changed


def fix_site(root: Path, *, dry_run: bool = False) -> dict:
    guide_csv = root / "data" / "guide_articles.csv"
    if not guide_csv.is_file():
        return {"changed": 0, "error": f"missing {guide_csv}"}
    lib = load_site_lib(root)
    prefix_labels = field_prefix_labels(root)
    with guide_csv.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    slug_titles = {norm(r.get("slug")): norm(r.get("title")) for r in rows if norm(r.get("slug"))}
    changed = sum(
        1
        for row in rows
        if fix_row(row, slug_titles=slug_titles, prefix_labels=prefix_labels, lib=lib)
    )
    if not dry_run and changed:
        with guide_csv.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    return {"changed": changed, "rows": len(rows)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove English slug leaks from guide CSV")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    stats = fix_site(args.root.resolve(), dry_run=args.dry_run)
    if stats.get("error"):
        print(stats["error"], file=sys.stderr)
        return 1
    verb = "would fix" if args.dry_run else "fixed"
    print(f"{verb} {stats['changed']}/{stats['rows']} rows in {args.root.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
