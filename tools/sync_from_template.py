#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exam-site-shell の共通ファイルを、別ディレクトリの本番サイトへコピーする。

使い方:
  python3 tools/sync_from_template.py --target /path/to/your-site
  python3 tools/sync_from_template.py --target /path/to/your-site --dry-run
  python3 tools/sync_from_template.py --target /path/to/your-site --build

注意:
  - --target は必須。リモート URL や特定リポジトリは自動では触らない。
  - 生成物 (q/, articles/, terms/) はコピーしない。--build で先方の build_all を実行。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.template_sync import sync_to_target  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="テンプレの共通エンジンを本番サイトへ同期")
    ap.add_argument(
        "--target",
        required=True,
        type=Path,
        help="本番サイトのルート（絶対パス推奨）",
    )
    ap.add_argument("--dry-run", action="store_true", help="コピーせず一覧のみ")
    ap.add_argument(
        "--build",
        action="store_true",
        help="同期後に target で python3 tools/build_all.py を実行",
    )
    ap.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "tools" / "template_sync_manifest.txt",
    )
    ap.add_argument(
        "--site-only",
        type=Path,
        default=ROOT / "tools" / "template_site_only.paths",
    )
    args = ap.parse_args()
    target = args.target.resolve()
    if not target.is_dir():
        print(f"error: --target is not a directory: {target}", file=sys.stderr)
        return 1
    if target == ROOT.resolve():
        print("error: --target must not be the template root itself", file=sys.stderr)
        return 1

    copied, skipped, warnings = sync_to_target(
        ROOT,
        target,
        manifest_path=args.manifest.resolve(),
        site_only_path=args.site_only.resolve(),
        dry_run=args.dry_run,
    )
    for w in warnings:
        print(f"warn: {w}", file=sys.stderr)
    print(f"done: copied={copied} unchanged_or_skipped={skipped}")
    if args.dry_run:
        return 0
    if args.build:
        subprocess.run(
            [sys.executable, "tools/build_all.py"],
            cwd=target,
            check=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
