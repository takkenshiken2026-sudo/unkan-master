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
# サイト確認用メタタグの識別子（冪等挿入・除去の判定に使う）。
ADSENSE_META_MARKER = 'name="google-adsense-account"'
# public_site へコピーされる HTML（prepare_public_site.sh と対応）。
PAGE_DIRS = ("articles", "q", "terms")


def adsense_markup(client_id: str) -> str:
    return (
        '<script async '
        f'src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={client_id}"\n'
        '     crossorigin="anonymous"></script>'
    )


def adsense_meta_markup(client_id: str) -> str:
    """AdSense サイト確認用メタタグ（審査時のサイト所有確認に使われる）。"""
    return f'<meta name="google-adsense-account" content="{client_id}">'


def ads_txt_line(client_id: str) -> str:
    """AdSense の ads.txt 行。client_id は "ca-pub-XXXX" 形式を想定。

    ads.txt では "pub-XXXX" 形式のパブリッシャー ID を用いる。
    f08c47fec0942fa0 は Google の認証局 ID（全 AdSense 共通の固定値）。
    """
    publisher_id = client_id[3:] if client_id.startswith("ca-") else client_id
    return f"google.com, {publisher_id}, DIRECT, f08c47fec0942fa0"


def write_ads_txt(client_id: str) -> bool:
    """公開ルートに ads.txt を冪等に書き出す。変更があれば True。

    ads.txt が「不明（Not found）」のままだと AdSense の収益化が保留されるため、
    公開ディメインの直下（GitHub Pages では public_site/ 直下）に必ず配置する。
    """
    ads_path = ROOT / "ads.txt"
    desired = ads_txt_line(client_id) + "\n"
    current = ads_path.read_text(encoding="utf-8") if ads_path.exists() else None
    if current == desired:
        return False
    ads_path.write_text(desired, encoding="utf-8")
    return True


def iter_public_html() -> list[Path]:
    files = sorted(p for p in ROOT.glob("*.html") if p.is_file())
    for name in PAGE_DIRS:
        d = ROOT / name
        if d.is_dir():
            files.extend(sorted(d.rglob("*.html")))
    return files


def is_redirect_stub(html_text: str) -> bool:
    """noindex のメタリフレッシュ移動ページ（実質コンテンツ無し）か判定する。

    こうした移動用スタブに広告コードを載せると「コンテンツのない
    ページへの広告掲載」として AdSense の品質評価で不利になるため、
    掲載対象から除外する。

    判定は移動用スタブ固有の <meta http-equiv="refresh"> のみで行う。
    SPA（index.html 等）は本文の JavaScript で location.replace() を
    使うことがあり、これを条件に含めると実コンテンツページを誤って
    スタブ扱いしてしまうため、location.replace は判定に用いない。
    """
    return 'http-equiv="refresh"' in html_text.lower()


def _strip_block(html_text: str, block: str) -> str:
    """<head> へ差し込んだブロックを冪等に取り除く。"""
    for needle in (CHARSET_ANCHOR + "\n" + block, "\n" + block, block):
        if needle in html_text:
            return html_text.replace(
                needle,
                CHARSET_ANCHOR if needle.startswith(CHARSET_ANCHOR) else "",
                1,
            )
    return html_text


def _insert_after_head(html_text: str, block: str) -> str:
    """<head> 直後（charset の後）にブロックを差し込む。"""
    if CHARSET_ANCHOR in html_text:
        return html_text.replace(CHARSET_ANCHOR, CHARSET_ANCHOR + "\n" + block, 1)
    if HEAD_ANCHOR in html_text:
        return html_text.replace(HEAD_ANCHOR, HEAD_ANCHOR + "\n" + block, 1)
    return html_text


def strip_adsense(html_text: str, snippet: str) -> str:
    """移動用スタブ等から AdSense ローダーと確認メタタグを冪等に取り除く。"""
    text = _strip_block(html_text, snippet)
    text = _strip_block(text, ADSENSE_META_MARKER)
    return text


def inject(html_text: str, snippet: str, client_id: str) -> str:
    # 中身のない移動用スタブには広告コード・確認タグを載せない。
    if is_redirect_stub(html_text):
        return strip_adsense(html_text, snippet)
    text = html_text
    # AdSense ローダー（既存判定は URL で行う）。
    if "pagead2.googlesyndication.com" not in text:
        text = _insert_after_head(text, snippet)
    # サイト確認用メタタグ（ローダーとは独立に冪等挿入）。
    if ADSENSE_META_MARKER not in text:
        text = _insert_after_head(text, adsense_meta_markup(client_id))
    return text


def main() -> int:
    client_id = adsense_client_id()
    if not client_id:
        print("apply_adsense: adsenseClientId が未設定のためスキップします。")
        return 0
    snippet = adsense_markup(client_id)
    if write_ads_txt(client_id):
        print(f"apply_adsense: ads.txt を更新しました（{ads_txt_line(client_id)}）")
    else:
        print("apply_adsense: ads.txt は最新です")
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
