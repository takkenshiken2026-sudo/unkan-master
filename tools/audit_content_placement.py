#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験ガイドと知識ハブ（用語解説等）の配置ずれを監査する。

正本: docs/content-positioning.md

  python3 tools/audit_content_placement.py
  python3 tools/audit_content_placement.py --target /path/to/site --csv out.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.content_placement_rules import (  # noqa: E402
    audit_glossary_rows,
    audit_guide_rows,
    audit_numbers_rows,
    load_hub_rows,
)

GUIDE_CSV = "data/guide_articles.csv"
GLOSSARY_CSV = "data/glossary_terms.csv"


@dataclass
class PlacementFinding:
    level: str  # ERROR | WARN | INFO
    kind: str
    source: str  # guide | glossary | compare | numbers | mistakes
    slug: str
    title: str
    message: str
    target: str = ""
    glossary_term: str = ""
    glossary_slug: str = ""


def audit_site(site_root: Path) -> list[PlacementFinding]:
    guide_path = site_root / GUIDE_CSV
    glossary_path = site_root / GLOSSARY_CSV
    if not guide_path.is_file():
        return [PlacementFinding("ERROR", "missing_csv", "guide", "", "", f"missing {guide_path}")]

    guides = list(csv.DictReader(guide_path.open(encoding="utf-8-sig")))
    glossary = (
        list(csv.DictReader(glossary_path.open(encoding="utf-8-sig")))
        if glossary_path.is_file()
        else []
    )
    hub = load_hub_rows(site_root)

    out: list[PlacementFinding] = []
    for item in audit_guide_rows(guides, glossary, hub):
        out.append(
            PlacementFinding(
                level=item.level,
                kind=item.kind,
                source="guide",
                slug=item.slug,
                title=item.title,
                message=item.message,
                target=item.target,
                glossary_term=item.glossary_term,
                glossary_slug=item.glossary_slug,
            )
        )
    for item in audit_glossary_rows(glossary, guides):
        out.append(
            PlacementFinding(
                level=item.level,
                kind=item.kind,
                source="glossary",
                slug=item.slug,
                title=item.title,
                message=item.message,
                target=item.target,
                glossary_term=item.glossary_term,
                glossary_slug=item.glossary_slug,
            )
        )
    numbers = hub.get("numbers.csv") or []
    for item in audit_numbers_rows(numbers, guides, site_name=site_root.name):
        out.append(
            PlacementFinding(
                level=item.level,
                kind=item.kind,
                source="numbers",
                slug=item.slug,
                title=item.title,
                message=item.message,
                target=item.target,
                glossary_term=item.glossary_term,
                glossary_slug=item.glossary_slug,
            )
        )
    return out


def write_csv(path: Path, findings: list[tuple[str, PlacementFinding]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "site",
                "level",
                "kind",
                "source",
                "slug",
                "title",
                "target",
                "glossary_term",
                "glossary_slug",
                "message",
            ]
        )
        for site, row in findings:
            writer.writerow(
                [
                    site,
                    row.level,
                    row.kind,
                    row.source,
                    row.slug,
                    row.title,
                    row.target,
                    row.glossary_term,
                    row.glossary_slug,
                    row.message,
                ]
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit guide vs knowledge hub content placement")
    parser.add_argument("--target", type=Path, default=ROOT, help="Site root (default: cwd template)")
    parser.add_argument("--csv", type=Path, help="Write findings to CSV")
    parser.add_argument("--strict", action="store_true", help="Treat WARN as failure")
    args = parser.parse_args()

    targets = [args.target.resolve()] if args.target else [ROOT.resolve()]
    all_rows: list[tuple[str, PlacementFinding]] = []
    errors = warns = 0

    for site_root in targets:
        site_name = site_root.name
        findings = audit_site(site_root)
        for f in findings:
            all_rows.append((site_name, f))
            line = (
                f"{site_name}\t{f.level}\t{f.kind}\t{f.source}\t{f.slug}\t"
                f"{f.target}\t{f.message}"
            )
            if f.level == "ERROR":
                errors += 1
                print(line, file=sys.stderr)
            elif f.level == "WARN":
                warns += 1
                print(line)
            else:
                print(line)

    if args.csv:
        write_csv(args.csv, all_rows)
        print(f"Wrote {args.csv} ({len(all_rows)} rows)")

    print(f"summary: ERROR={errors} WARN={warns}", file=sys.stderr)
    if errors:
        return 1
    if args.strict and warns:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
