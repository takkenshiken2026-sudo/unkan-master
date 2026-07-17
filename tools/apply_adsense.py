#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""site-config の adsenseClientId を全公開 HTML の <head> に反映する。

生成スクリプトがページを作り直すたびに <head> から広告タグが消えるため、
build_all.py の最後（prepare_public_site.sh の直前）でこのステップを実行して
公開対象の HTML すべてに AdSense ローダーを冪等に差し込む。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.site_config import adsense_client_id  # noqa: E402

CHARSET_ANCHOR = '<meta charset="UTF-8">'
HEAD_ANCHOR = "<head>"
# public_site へコピーされる HTML（prepare_public_site.sh と対応）。
PAGE_DIRS = ("articles", "q", "terms")


def adsense_markup(client_id: str) -> str:
    return (
        '<script async '
        f'src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={client_id}"\n'
        '     crossorigin="anonymous"></script>'
    )


def iter_public_html() -> list[Path]:
    files = sorted(p for p in ROOT.glob("*.html") if p.is_file())
    for name in PAGE_DIRS:
        d = ROOT / name
        if d.is_dir():
            files.extend(sorted(d.rglob("*.html")))
    return files


def inject(html_text: str, snippet: str, client_id: str) -> str:
    if client_id in html_text or "pagead2.googlesyndication.com" in html_text:
        return html_text
    if CHARSET_ANCHOR in html_text:
        return html_text.replace(CHARSET_ANCHOR, CHARSET_ANCHOR + "\n" + snippet, 1)
    if HEAD_ANCHOR in html_text:
        return html_text.replace(HEAD_ANCHOR, HEAD_ANCHOR + "\n" + snippet, 1)
    return html_text


def main() -> int:
    client_id = adsense_client_id()
    if not client_id:
        print("apply_adsense: adsenseClientId が未設定のためスキップします。")
        return 0
    snippet = adsense_markup(client_id)
    changed = 0
    skipped = 0
    for path in iter_public_html():
        text = path.read_text(encoding="utf-8")
        new_text = inject(text, snippet, client_id)
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            changed += 1
        else:
            skipped += 1
    print(
        f"apply_adsense: client={client_id} 反映 {changed} 件 / 既存・対象外 {skipped} 件"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
