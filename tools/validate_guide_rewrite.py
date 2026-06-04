#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験ガイド手書きリライト進捗チェック（--strict で未完了時 exit 1）。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_guide_rewrite_inventory import audit_site  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--strict", action="store_true", help="needs_rewrite が1件でもあれば exit 1")
    args = ap.parse_args()
    rows = audit_site(args.root.resolve())
    needs = [r for r in rows if r["status"] == "needs_rewrite"]
    done = [r for r in rows if r["status"] == "done"]
    print(
        f"guide rewrite: published={len(rows)} done={len(done)} needs_rewrite={len(needs)}"
    )
    if needs:
        for r in needs[:10]:
            print(f"  NEED  [{r['priority']}] {r['slug']}: {r['forbidden_sample']}")
        if len(needs) > 10:
            print(f"  ... and {len(needs) - 10} more")
    if args.strict and needs:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
