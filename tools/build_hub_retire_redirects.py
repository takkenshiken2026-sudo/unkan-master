#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
旧知識ハブ URL（terms/compare|numbers|mistakes/）を用語解説一覧へリダイレクトする。

比較・数値早見・よくある誤答タブは廃止。ブックマーク・検索流入用に noindex リダイレクトのみ残す。
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RETIRED_SECTIONS: tuple[str, ...] = ("compare", "numbers", "mistakes")
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
    count = 0
    for section in RETIRED_SECTIONS:
        section_dir = ROOT / "terms" / section
        section_dir.mkdir(parents=True, exist_ok=True)
        seen: set[Path] = set()
        for html_file in sorted(section_dir.glob("*.html")):
            write_redirect(html_file)
            seen.add(html_file.resolve())
            count += 1
        index = section_dir / "index.html"
        if index.resolve() not in seen:
            write_redirect(index)
            count += 1
    print(f"Wrote {count} retired hub redirect(s) under terms/compare|numbers|mistakes/")
    return count


def main() -> int:
    build_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
