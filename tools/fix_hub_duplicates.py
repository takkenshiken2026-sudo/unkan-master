#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知識ハブ重複の自動修正（カッコ付き用語 merge・角度バッチ統合+redirect・表記ゆれ merge）。

  python3 tools/fix_hub_duplicates.py --dry-run
  python3 tools/fix_hub_duplicates.py --apply
  python3 tools/fix_hub_duplicates.py --apply --rebuild
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.hub_dedup import (  # noqa: E402
    apply_glossary_related_term_fixup,
    apply_term_remap_to_rows,
    dedup_hub_rows,
    load_csv,
    load_hub_redirects,
    merge_glossary_paren_rows,
    write_csv,
    write_hub_redirects,
)

DATA = ROOT / "data"
GLOSSARY_CSV = DATA / "glossary_terms.csv"
COMPARE_CSV = DATA / "comparisons.csv"
NUMBERS_CSV = DATA / "numbers.csv"
MISTAKES_CSV = DATA / "mistakes.csv"


def fix_site(*, apply: bool, rebuild: bool, root: Path) -> dict[str, int]:
    data = root / "data"
    glossary_csv = data / "glossary_terms.csv"
    compare_csv = data / "comparisons.csv"
    numbers_csv = data / "numbers.csv"
    mistakes_csv = data / "mistakes.csv"
    stats = {
        "glossary_before": 0,
        "glossary_after": 0,
        "compare_before": 0,
        "compare_after": 0,
        "numbers_before": 0,
        "numbers_after": 0,
        "mistakes_before": 0,
        "mistakes_after": 0,
        "redirects": 0,
    }

    term_remap: dict[str, str] = {}
    glossary_fields: list[str] = []
    glossary_rows: list[dict[str, str]] = []

    if glossary_csv.is_file():
        glossary_fields, glossary_rows = load_csv(glossary_csv)
        stats["glossary_before"] = len(glossary_rows)
        merged_glossary, term_remap = merge_glossary_paren_rows(glossary_rows)
        stats["glossary_after"] = len(merged_glossary)
        glossary_rows = merged_glossary

    compare_fields: list[str] = []
    compare_rows: list[dict[str, str]] = []
    numbers_fields: list[str] = []
    numbers_rows: list[dict[str, str]] = []
    mistakes_fields: list[str] = []
    mistakes_rows: list[dict[str, str]] = []

    if compare_csv.is_file():
        compare_fields, compare_rows = load_csv(compare_csv)
        stats["compare_before"] = len(compare_rows)
    if numbers_csv.is_file():
        numbers_fields, numbers_rows = load_csv(numbers_csv)
        stats["numbers_before"] = len(numbers_rows)
    if mistakes_csv.is_file():
        mistakes_fields, mistakes_rows = load_csv(mistakes_csv)
        stats["mistakes_before"] = len(mistakes_rows)

    apply_term_remap_to_rows(glossary_rows, term_remap)
    apply_term_remap_to_rows(compare_rows, term_remap)
    apply_term_remap_to_rows(numbers_rows, term_remap)
    apply_term_remap_to_rows(mistakes_rows, term_remap)
    apply_glossary_related_term_fixup(glossary_rows, glossary_rows)
    apply_glossary_related_term_fixup(compare_rows, glossary_rows)
    apply_glossary_related_term_fixup(numbers_rows, glossary_rows)
    apply_glossary_related_term_fixup(mistakes_rows, glossary_rows)

    existing = load_hub_redirects(data)
    compare_rows, numbers_rows, mistakes_rows, redirects = dedup_hub_rows(
        compare_rows,
        numbers_rows,
        mistakes_rows,
        existing_redirects=existing,
    )
    stats["compare_after"] = len(compare_rows)
    stats["numbers_after"] = len(numbers_rows)
    stats["mistakes_after"] = len(mistakes_rows)
    stats["redirects"] = sum(len(v) for v in redirects.values())

    print(
        "glossary "
        f"{stats['glossary_before']}->{stats['glossary_after']} "
        f"compare {stats['compare_before']}->{stats['compare_after']} "
        f"numbers {stats['numbers_before']}->{stats['numbers_after']} "
        f"mistakes {stats['mistakes_before']}->{stats['mistakes_after']} "
        f"redirects={stats['redirects']}"
    )

    if not apply:
        print("(dry-run: no files written)")
        return stats

    if glossary_csv.is_file() and glossary_fields:
        write_csv(glossary_csv, glossary_fields, glossary_rows)
    if compare_csv.is_file() and compare_fields:
        write_csv(compare_csv, compare_fields, compare_rows)
    if numbers_csv.is_file() and numbers_fields:
        write_csv(numbers_csv, numbers_fields, numbers_rows)
    if mistakes_csv.is_file() and mistakes_fields:
        write_csv(mistakes_csv, mistakes_fields, mistakes_rows)
    write_hub_redirects(data, redirects)

    if rebuild:
        subprocess.run([sys.executable, "tools/build_glossary_pages.py"], cwd=root, check=True)
        subprocess.run([sys.executable, "tools/build_compare_pages.py"], cwd=root, check=True)
        subprocess.run([sys.executable, "tools/build_numbers_mistakes_pages.py"], cwd=root, check=True)

    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=Path, default=ROOT, help="Site root")
    ap.add_argument("--apply", action="store_true", help="Write CSV / hub_redirects.json")
    ap.add_argument("--dry-run", action="store_true", help="Report only (default)")
    ap.add_argument("--rebuild", action="store_true", help="Rebuild hub HTML after apply")
    args = ap.parse_args()
    apply = args.apply and not args.dry_run
    fix_site(apply=apply, rebuild=args.rebuild and apply, root=args.target.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
