#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""q/ 以下の静的 HTML に正しい BRAND_ASSET_HEAD（OGP 含む）を再注入する。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.brand_assets import inject_brand_head  # noqa: E402


def main() -> int:
    q_root = ROOT / "q"
    if not q_root.is_dir():
        print("skip: q/ not found")
        return 0
    updated = 0
    for path in sorted(q_root.rglob("*.html")):
        old = path.read_text(encoding="utf-8")
        new = inject_brand_head(old, path.relative_to(ROOT), site_root=ROOT)
        if new != old:
            path.write_text(new, encoding="utf-8")
            updated += 1
    print(f"Patched brand head on {updated} q/ HTML file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
