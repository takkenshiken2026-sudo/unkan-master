#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""slug 単位の手書きリライト辞書を guide_articles.csv に適用（宅建 batch 方式）。"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import sys
from datetime import date
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.rewrite_guide_boilerplate import _csv_fieldnames  # noqa: E402

TODAY = date.today().isoformat()
DEFAULT_REVISION = f"{TODAY}: 手書きリライト"


def load_rewrites_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("guide_rewrite_batch", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "REWRITES"):
        raise ValueError(f"{path} must define REWRITES dict")
    return mod


def apply_rewrites(
    csv_path: Path,
    rewrites: dict[str, dict[str, str]],
    *,
    revision: str = DEFAULT_REVISION,
    dry_run: bool = False,
) -> int:
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8-sig")))
    if not rows:
        return 0
    fieldnames = list(rows[0].keys())
    patched = 0
    for row in rows:
        slug = (row.get("slug") or "").strip()
        if slug not in rewrites:
            continue
        patch = rewrites[slug]
        row["revision_note"] = revision
        row["fact_checked_at"] = TODAY
        row["last_reviewed_at"] = TODAY
        row["source_checked_at"] = TODAY
        note = (row.get("original_note") or "").strip()
        if "手書きリライト" not in note:
            row["original_note"] = f"手書きリライト {TODAY}。" + (note if note else "")
        for key, value in patch.items():
            row[key] = value
        patched += 1
    fieldnames = _csv_fieldnames(fieldnames, rows)
    if patched and not dry_run:
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    return patched


def main() -> int:
    ap = argparse.ArgumentParser(description="手書きリライト batch を CSV に適用")
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--batch", type=Path, required=True, help="REWRITES を定義した .py")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    csv_path = args.root.resolve() / "data" / "guide_articles.csv"
    mod = load_rewrites_module(args.batch.resolve())
    rewrites = getattr(mod, "REWRITES")
    slugs = list(rewrites.keys())
    n = apply_rewrites(csv_path, rewrites, dry_run=args.dry_run)
    mode = "would patch" if args.dry_run else "patched"
    print(f"{mode} {n} rows: {', '.join(slugs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
