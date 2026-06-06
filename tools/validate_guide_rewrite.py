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


from tools.guide_rewrite_rules import is_affiliate_row  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--strict", action="store_true", help="needs_rewrite が1件でもあれば exit 1")
    args = ap.parse_args()
    rows = audit_site(args.root.resolve())
    guide_rows = [r for r in rows if not (r.get("affiliate") == "yes")]
    needs = [
        r
        for r in guide_rows
        if r["status"] in {"needs_rewrite", "auto_pending", "ok"}
    ]
    hand = [r for r in guide_rows if r["status"] == "hand_done"]
    forbid = [r for r in guide_rows if r["status"] == "needs_rewrite"]
    aff = [r for r in rows if r.get("affiliate") == "yes"]
    print(
        f"guide rewrite: guide_published={len(guide_rows)} hand_done={len(hand)} "
        f"pending={len(needs)} forbidden={len(forbid)} affiliate={len(aff)}"
    )
    pending = [r for r in guide_rows if r["status"] != "hand_done"]
    if pending:
        for r in pending[:10]:
            print(f"  PENDING [{r['priority']}] {r['slug']}: {r['status']}")
        if len(pending) > 10:
            print(f"  ... and {len(pending) - 10} more")
    if args.strict and pending:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
