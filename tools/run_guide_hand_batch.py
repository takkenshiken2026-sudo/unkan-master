#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""5本 batch を apply → strip → 検証（enrich なし）。"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.apply_guide_rewrite_batch import apply_rewrites, load_rewrites_module  # noqa: E402
from tools.strip_generic_guide_padding import strip_row  # noqa: E402
from tools.validate_guide_hand_batch import validate_rewrites  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="手書き batch 適用パイプライン（enrich なし）")
    ap.add_argument("--batch", type=Path, required=True)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--skip-apply", action="store_true", help="strip/validate のみ")
    args = ap.parse_args()
    root = args.root.resolve()
    batch = args.batch.resolve()
    mod = load_rewrites_module(batch)
    rewrites = getattr(mod, "REWRITES")
    slugs = set(rewrites.keys())

    pre = validate_rewrites(rewrites, root=root)
    if pre:
        print("batch validation failed (fix REWRITES before apply):", file=sys.stderr)
        for msg in pre[:20]:
            print(f"  {msg}", file=sys.stderr)
        return 1

    csv_path = root / "data" / "guide_articles.csv"
    if not args.skip_apply:
        n = apply_rewrites(csv_path, rewrites)
        print(f"applied {n} slugs from {batch.name}")

    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    changed = 0
    for row in rows:
        if (row.get("slug") or "").strip() in slugs and strip_row(row):
            changed += 1
    if changed:
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    print(f"stripped padding on {changed} rows")

    py = sys.executable
    slug_arg = ",".join(sorted(slugs))
    steps = [
        [py, "tools/validate_csv.py", "--scope", "guide"],
        [py, "tools/audit_guide_prose_quality.py", "--root", str(root), "--strict"],
    ]
    for cmd in steps:
        print("+", " ".join(cmd))
        subprocess.run(cmd, cwd=root, check=True)
    print(f"OK: batch {batch.name} ({len(slugs)} slugs) passed gates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
