#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""site-config からファビコン・OGP 画像を assets/brand/ に生成する。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SHELL = Path(__file__).resolve().parents[1]
if str(SHELL) not in sys.path:
    sys.path.insert(0, str(SHELL))

from tools.brand_assets import assets_ready, write_brand_assets  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="ファビコン・OGP 画像を生成")
    parser.add_argument("--target", type=Path, default=Path.cwd(), help="サイトルート")
    parser.add_argument("--force", action="store_true", help="既存 PNG があっても再生成する")
    args = parser.parse_args()
    target = args.target.resolve()
    if not (target / "site-config.json").is_file():
        print(f"site-config.json not found: {target}", file=sys.stderr)
        return 1
    if assets_ready(target) and not args.force:
        out = target / "assets" / "brand"
        files = sorted(p.name for p in out.iterdir() if p.is_file())
        print(f"Brand assets already exist in {out}: {', '.join(files)}; skip")
        return 0
    out = write_brand_assets(target)
    files = sorted(p.name for p in out.iterdir() if p.is_file())
    print(f"Wrote {len(files)} files to {out}: {', '.join(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
