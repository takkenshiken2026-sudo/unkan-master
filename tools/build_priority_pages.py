#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
旧「頻出・得点源」URL（terms/priority/）を用語解説一覧へリダイレクトする。

タブは廃止。ブックマーク・検索流入用に noindex リダイレクトのみ残す。
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIORITY_DIR = ROOT / "terms" / "priority"
TARGET = "../index.html"

REDIRECT_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="0;url={url}">
<link rel="canonical" href="{url}">
<meta name="robots" content="noindex, follow">
<title>用語解説へ移動中…</title>
<script>location.replace({url_js});</script>
</head>
<body>
<p>用語解説一覧へ移動します。<a href="{url}">こちら</a></p>
</body>
</html>
"""


def write_redirect(path: Path, target: str = TARGET) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    esc = html.escape(target, quote=True)
    path.write_text(
        REDIRECT_HTML.format(url=esc, url_js=repr(target)),
        encoding="utf-8",
    )


def build_all() -> int:
    write_redirect(PRIORITY_DIR / "index.html")
    count = 1
    for old in sorted(PRIORITY_DIR.glob("p-*.html")):
        write_redirect(old)
        count += 1
    print(f"Wrote {count} priority redirect(s) under {PRIORITY_DIR}")
    return count


def main() -> int:
    build_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
