#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知識ハブ・用語解説の重複クラスタを監査する。"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.hub_dedup import (  # noqa: E402
    find_angle_batch_clusters,
    find_glossary_paren_clusters,
    find_label_variant_clusters,
    load_csv,
)

DATA = ROOT / "data"
GLOSSARY_CSV = DATA / "glossary_terms.csv"
COMPARE_CSV = DATA / "comparisons.csv"
NUMBERS_CSV = DATA / "numbers.csv"
MISTAKES_CSV = DATA / "mistakes.csv"


def audit_site(site_dir: Path) -> list[dict[str, str]]:
    data = site_dir / "data"
    rows_out: list[dict[str, str]] = []

    if (data / "glossary_terms.csv").is_file():
        _, glossary = load_csv(data / "glossary_terms.csv")
        for base, terms in find_glossary_paren_clusters(glossary):
            rows_out.append(
                {
                    "kind": "glossary_paren",
                    "hub": "glossary",
                    "cluster_key": base,
                    "members": " | ".join(terms),
                    "count": str(len(terms)),
                }
            )

    for hub_name, csv_name in (
        ("compare", "comparisons.csv"),
        ("numbers", "numbers.csv"),
        ("mistakes", "mistakes.csv"),
    ):
        path = data / csv_name
        if not path.is_file():
            continue
        _, hub_rows = load_csv(path)
        for label, items in find_label_variant_clusters(hub_rows):
            rows_out.append(
                {
                    "kind": "label_variant",
                    "hub": hub_name,
                    "cluster_key": label,
                    "members": " | ".join(f"{slug}:{title}" for slug, title in items),
                    "count": str(len(items)),
                }
            )
        for key, items in find_angle_batch_clusters(hub_rows):
            rows_out.append(
                {
                    "kind": "angle_batch",
                    "hub": hub_name,
                    "cluster_key": key,
                    "members": " | ".join(f"{slug}:{title}" for slug, title in items),
                    "count": str(len(items)),
                }
            )

    return rows_out


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit duplicate clusters in knowledge hub CSVs.")
    ap.add_argument("--target", type=Path, default=ROOT, help="Site root (default: cwd repo)")
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "docs" / "hub-duplicate-audit.csv",
        help="TSV/CSV output path",
    )
    args = ap.parse_args()

    rows = audit_site(args.target.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["kind", "hub", "cluster_key", "count", "members"]
    with args.out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print(f"clusters={len(rows)} -> {args.out}")
    by_kind: dict[str, int] = {}
    for row in rows:
        by_kind[row["kind"]] = by_kind.get(row["kind"], 0) + 1
    for kind, count in sorted(by_kind.items()):
        print(f"  {kind}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
