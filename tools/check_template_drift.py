#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テンプレと本番サイトの「共通エンジン」差分を一覧する（デプロイ前チェック用）。

  python3 tools/check_template_drift.py --target /path/to/your-site
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.template_sync import collect_drift  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="テンプレと本番のファイル差分を検出")
    ap.add_argument("--target", required=True, type=Path)
    ap.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "tools" / "template_sync_manifest.txt",
    )
    ap.add_argument(
        "--fail-on-drift",
        action="store_true",
        help="different / missing があると終了コード 1",
    )
    args = ap.parse_args()
    target = args.target.resolve()
    if not target.is_dir():
        print(f"error: not a directory: {target}", file=sys.stderr)
        return 1

    rows = collect_drift(ROOT, target, manifest_path=args.manifest.resolve())
    problems = [r for r in rows if r[1] not in ("ok",)]
    for rel, status in rows:
        if status != "ok":
            print(f"{status}: {rel}")
    ok_n = sum(1 for _, s in rows if s == "ok")
    print(f"summary: ok={ok_n} drift={len(problems)} total={len(rows)}")
    if args.fail_on_drift and problems:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
