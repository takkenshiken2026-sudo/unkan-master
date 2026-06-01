#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ガイド section 見出しの共通エイリアス → content lib 関数解決。"""

from __future__ import annotations

from types import ModuleType

# CSV 実見出し → content lib 内関数名（サイト共通パターン）
HEADING_FUNC_ALIASES: dict[str, str] = {
    "試験の目的と位置づけ": "_heading_試験目的",
    "まず確認する公式情報": "_heading_独学前に公式情報を確認",
    "このサイトでできること": "_heading_サイトでできること",
    "受験前に押さえる項目": "_heading_受験前押さえる",
    "次に読む記事": "_heading_次に読む記事",
    "当日の持ち物・注意": "_heading_持ち物と時間配分",
    "試験当日の持ち物": "_heading_試験当日持ち物",
    "必ず持参するもの": "_heading_試験当日持ち物",
    "持ち込み禁止のもの": "_heading_持込禁止",
    "試験当日のタイムライン": "_heading_当日タイムライン",
    "センターへのアクセス注意点": "_heading_試験会場アクセス",
    "試験当日の忘れ物チェックリスト": "_heading_最終確認リスト",
    "最初に確認すること": "_heading_受験資格",
    "全体像・前提を分けて理解する": "_heading_分野位置づけ",
    "具体的な進め方": "_heading_サイト学習",
    "注意点": "_heading_よくある誤解",
    "つまずきやすいポイント": "_heading_よくある誤解",
    "次にやること": "_heading_次に読む記事",
    "復習・確認方法": "_heading_復習計画",
    "この記事でわかること": "_heading_分野位置づけ",
    "学習チェックリスト": "_heading_最終確認リスト",
}

# 関数が無い lib 向けの代替関数名
FUNC_FALLBACKS: dict[str, tuple[str, ...]] = {
    "_heading_サイトでできること": ("_heading_サイト学習",),
    "_heading_受験前押さえる": ("_heading_申込前チェック", "_heading_申込前チェックリスト"),
    "_heading_次に読む記事": ("_heading_サイト学習",),
    "_heading_試験当日持ち物": ("_heading_持ち物と時間配分",),
    "_heading_持込禁止": ("_heading_持ち物と時間配分",),
    "_heading_試験会場アクセス": ("_heading_申込手順会場",),
    "_heading_最終確認リスト": ("_heading_申込前チェック",),
}


def _call_heading_fn(lib: ModuleType, func_name: str, topic: str, slug: str, genre: str, ctx: dict):
    fn = getattr(lib, func_name, None)
    if callable(fn):
        return fn(topic, slug, genre, ctx)
    for alt in FUNC_FALLBACKS.get(func_name, ()):
        fn = getattr(lib, alt, None)
        if callable(fn):
            return fn(topic, slug, genre, ctx)
    return None


def section_body_from_lib(
    lib: ModuleType,
    heading: str,
    topic: str,
    slug: str,
    genre: str,
    ctx: dict,
) -> str:
    """HEADING_MAP → 共通エイリアス → section_body_for の順で本文を取得。"""
    key = (heading or "").strip()
    heading_map = getattr(lib, "HEADING_MAP", None)
    if isinstance(heading_map, dict) and key in heading_map:
        return heading_map[key](topic, slug, genre, ctx)

    func_name = HEADING_FUNC_ALIASES.get(key)
    if func_name:
        body = _call_heading_fn(lib, func_name, topic, slug, genre, ctx)
        if body:
            return body

    return lib.section_body_for(key, topic, slug, genre, ctx)
