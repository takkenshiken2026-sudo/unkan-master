#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知識ハブ CSV の内部バッチ表記（S37 等）と早見表重複を一括修正する。"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.hub_dedup import load_csv, write_csv  # noqa: E402
from tools.hub_matrix_repair import repair_hub_matrix_rows  # noqa: E402
from tools.hub_strip_batch_suffix import strip_hub_rows  # noqa: E402

HUB_FILES = ("comparisons.csv", "numbers.csv", "mistakes.csv")


def fix_site(*, apply: bool, rebuild: bool, root: Path) -> dict[str, int]:
    data = root / "data"
    stats = {"batch_fields": 0, "matrix_rows": 0}

    for filename in HUB_FILES:
        path = data / filename
        if not path.is_file():
            continue
        fields, rows = load_csv(path)
        before_batch = sum(
            1
            for row in rows
            for key, val in row.items()
            if key != "slug" and isinstance(val, str) and ("S37" in val or "数値S" in val or "誤答S" in val)
        )
        strip_hub_rows(rows)
        matrix_changed = repair_hub_matrix_rows(rows)
        after_batch = sum(
            1
            for row in rows
            for key, val in row.items()
            for _ in [0]
            if key != "slug" and isinstance(val, str) and ("S37" in val or "数値S" in val or "誤答S" in val)
        )
        stats["batch_fields"] += max(0, before_batch - after_batch)
        stats["matrix_rows"] += matrix_changed
        print(
            f"{filename}: batch-like fields {before_batch}->{after_batch}, "
            f"matrix rows repaired={matrix_changed}"
        )
        if apply:
            write_csv(path, fields, rows)

    if apply and rebuild:
        subprocess.run([sys.executable, "tools/build_compare_pages.py"], cwd=root, check=True)
        subprocess.run([sys.executable, "tools/build_numbers_mistakes_pages.py"], cwd=root, check=True)

    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=Path, default=ROOT)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args()
    apply = args.apply and not args.dry_run
    fix_site(apply=apply, rebuild=args.rebuild and apply, root=args.target.resolve())
    if not apply:
        print("(dry-run: no files written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
