#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テンプレ index.html のマーカー領域だけを本番 index.html へコピーする。

index.html は site-only のため template_sync_manifest では上書きしない。
SPA エンジン（PAGE_SEO・noscript・FIELDS 等）を段階反映するときに使う。

  python3 tools/sync_index_spa_from_template.py --target ~/Projects/mankan-master
  python3 tools/sync_index_spa_from_template.py --target ~/Projects/mankan-master --apply-config
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.index_spa_patch import load_patch_region_names, sync_index_spa_regions  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="index.html SPA マーカー領域の部分同期")
    ap.add_argument("--target", required=True, type=Path, help="本番サイト root")
    ap.add_argument(
        "--template",
        type=Path,
        default=ROOT,
        help="テンプレ root（既定: exam-site-shell）",
    )
    ap.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "tools" / "index_spa_patch_regions.txt",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--apply-config",
        action="store_true",
        help="同期後に target で apply_site_config.py を実行",
    )
    args = ap.parse_args()

    template_root = args.template.resolve()
    target_root = args.target.resolve()
    template_index = template_root / "index.html"
    target_index = target_root / "index.html"

    if not template_index.is_file():
        print(f"error: template index.html not found: {template_index}", file=sys.stderr)
        return 1
    if not target_index.is_file():
        print(f"error: target index.html not found: {target_index}", file=sys.stderr)
        return 1
    if target_root == template_root:
        print("error: --target must not be the template root", file=sys.stderr)
        return 1

    region_names = load_patch_region_names(args.manifest.resolve())
    template_text = template_index.read_text(encoding="utf-8")
    target_text = target_index.read_text(encoding="utf-8")
    patched, updated = sync_index_spa_regions(template_text, target_text, region_names)

    if not updated and not args.apply_config:
        print("no changes (markers missing or already up to date)")
        return 0

    if updated:
        print("patched regions:", ", ".join(updated))
    elif args.apply_config:
        print("no marker regions to sync; running apply_site_config only")

    if args.dry_run:
        print("dry-run: not writing")
        return 0

    if updated:
        target_index.write_text(patched, encoding="utf-8")
        print(f"updated {target_index}")

    if args.apply_config:
        subprocess.run(
            [sys.executable, "tools/apply_site_config.py"],
            cwd=target_root,
            check=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
