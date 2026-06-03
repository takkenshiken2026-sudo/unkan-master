#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply affiliate article template (guide-row.yaml) to data/guide_articles.csv."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML が必要です: pip install pyyaml") from exc

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEMPLATES_DIR = ROOT / "docs" / "affiliate" / "templates"
ARTICLES_CSV = ROOT / "data" / "guide_articles.csv"


def load_template(name: str) -> dict:
    path = TEMPLATES_DIR / name / "guide-row.yaml"
    if not path.is_file():
        raise FileNotFoundError(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"invalid template: {path}")
    return data


def norm_block(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def apply_template(row: dict[str, str], tpl: dict, fieldnames: list[str]) -> None:
    slug = tpl["slug"]
    if row.get("slug") != slug:
        return
    for key in ("genre", "title", "meta_description", "lead", "tags", "priority", "content_status"):
        if key in tpl and tpl[key] is not None and key in fieldnames:
            row[key] = norm_block(tpl[key])
    for key in ("user_intent", "action_items", "related_links", "revision_note", "original_note"):
        if key in tpl and tpl[key] is not None and key in fieldnames:
            row[key] = norm_block(tpl[key]).replace("\n", " ").replace("  ", " ")
    sections = tpl.get("sections") or []
    for i, sec in enumerate(sections[:7], start=1):
        h, b = f"section_{i}_heading", f"section_{i}_body"
        if h in fieldnames:
            row[h] = norm_block(sec.get("heading"))
        if b in fieldnames:
            row[b] = norm_block(sec.get("body"))
    for i in range(len(sections) + 1, 8):
        h, b = f"section_{i}_heading", f"section_{i}_body"
        if h in fieldnames:
            row[h] = ""
        if b in fieldnames:
            row[b] = ""
    faqs = tpl.get("faqs") or []
    for i, faq in enumerate(faqs[:3], start=1):
        q, a = f"faq_{i}_question", f"faq_{i}_answer"
        if q in fieldnames:
            row[q] = norm_block(faq.get("question"))
        if a in fieldnames:
            row[a] = norm_block(faq.get("answer"))
    for i in range(len(faqs) + 1, 4):
        q, a = f"faq_{i}_question", f"faq_{i}_answer"
        if q in fieldnames:
            row[q] = ""
        if a in fieldnames:
            row[a] = ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--template",
        default="affiliate-textbooks-recommend",
        help="docs/affiliate/templates/{name}/guide-row.yaml",
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()

    tpl = load_template(args.template)
    slug = tpl["slug"]
    csv_path = args.root / "data" / "guide_articles.csv"
    if not csv_path.is_file():
        print(f"skip: {csv_path}", file=sys.stderr)
        return 1

    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames:
            return 1
        rows = list(reader)

    hit = False
    for row in rows:
        if row.get("slug") == slug:
            apply_template(row, tpl, list(fieldnames))
            hit = True
            break

    if not hit:
        print(f"slug not found in CSV: {slug!r}", file=sys.stderr)
        return 1

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows({k: row.get(k, "") for k in fieldnames} for row in rows)

    brief_src = TEMPLATES_DIR / args.template / "brief.yaml"
    brief_dst = args.root / "data" / "affiliate-briefs" / f"{slug}.yaml"
    if brief_src.is_file():
        brief_dst.parent.mkdir(parents=True, exist_ok=True)
        brief_dst.write_text(brief_src.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"applied template {args.template!r} to {csv_path}")
    if brief_src.is_file():
        print(f"copied brief → {brief_dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
