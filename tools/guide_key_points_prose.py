#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ガイド記事「この記事の要点」ボックスの読者向け prose を整える。"""

from __future__ import annotations

import html as html_module
import re
from typing import Final

_VAGUE_INTRO_TAIL_RE = re.compile(
    r"読了後は行動チェックリストに沿って(?:演習[・と]用語確認|演習と用語確認)まで"
    r"進められる状態を目指します。?\s*$"
)
_BROKEN_POINTS_RE = re.compile(r"の要点を。\s*|要点を。\s*")
_SENTENCE_END_RE = re.compile(r"(する|できる|ます|ない|確認する|押さえる|メモする|整理する|把握する|進める|読む)$")
_KEY_POINTS_BOX_RE = re.compile(r'class="seo-key-points-box".*?</section>', re.I | re.S)
_KEY_POINTS_INTRO_RE = re.compile(r"<p>(.*?)</p>", re.I | re.S)
_KEY_POINTS_ITEM_RE = re.compile(r"<li>(.*?)</li>", re.I | re.S)

_NUMERIC_CHIP_RE = re.compile(
    r"\d|·|％|/|円|問|分|週|点|月|日|年|％|ライン|足切り"
)


def repair_broken_points(text: str) -> str:
    if not text:
        return text
    out = _BROKEN_POINTS_RE.sub("の要点は、", text)
    return out


def normalize_key_points_intro(text: str) -> str:
    """要点ボックス冒頭（user_intent）を自然な1文に整える。"""
    one = re.sub(r"\s+", " ", (text or "").strip())
    if not one:
        return one
    one = repair_broken_points(one)
    one = _VAGUE_INTRO_TAIL_RE.sub("", one).strip()
    if one and not one.endswith(("。", "！", "？")):
        one += "。"
    return one


def looks_like_key_point_sentence(text: str) -> bool:
    """要点リスト1行が読者向けの文・句として成立するか。"""
    t = (text or "").strip()
    if not t:
        return False
    if t.endswith(("。", "！", "？")):
        return True
    if t.startswith("「") and "」" in t:
        return True
    if len(t) >= 18 and any(marker in t for marker in ("—", "：", "→", "・")):
        return True
    if "「" in t and len(t) >= 16:
        return True
    if _SENTENCE_END_RE.search(t):
        return True
    if len(t) >= 28 and any(marker in t for marker in ("確認", "把握", "整理", "進め", "押さえ", "メモ")):
        return True
    return False


def normalize_key_point_item(text: str) -> str:
    """短い chip 形式の要点を、リスト向けの短い文に整える。"""
    t = (text or "").strip()
    if not t or looks_like_key_point_sentence(t):
        if t and not t.endswith(("。", "！", "？")) and len(t) >= 18 and any(
            marker in t for marker in ("—", "：", "→")
        ):
            return f"{t}。"
        return t
    if t.startswith("「") or ("」" in t and len(t) > 6):
        return t
    if t.endswith("逆算"):
        return f"{t}の目安を押さえる"
    if "ライン" in t or "足切り" in t:
        return f"{t}の基準を確認する"
    if _NUMERIC_CHIP_RE.search(t):
        return f"{t}をメモする"
    if len(t) <= 14:
        return f"{t}の要点を確認する"
    return f"{t}を押さえる"


def normalize_key_points_items(items: list[str]) -> list[str]:
    return [normalize_key_point_item(item) for item in items if (item or "").strip()]


def key_points_plain_in_reader_html(page_html: str) -> tuple[str, list[str]]:
    """生成 HTML の要点ボックスから intro と list 項目を抽出。"""
    box_m = _KEY_POINTS_BOX_RE.search(page_html)
    if not box_m:
        return "", []
    block = box_m.group(0)
    intro = ""
    intro_m = _KEY_POINTS_INTRO_RE.search(block)
    if intro_m:
        intro = html_module.unescape(re.sub(r"<[^>]+>", "", intro_m.group(1)))
        intro = re.sub(r"\s+", " ", intro).strip()
    items: list[str] = []
    for li_m in _KEY_POINTS_ITEM_RE.finditer(block):
        plain = html_module.unescape(re.sub(r"<[^>]+>", "", li_m.group(1)))
        plain = re.sub(r"\s+", " ", plain).strip()
        if plain:
            items.append(plain)
    return intro, items


def key_points_prose_issues(page_html: str) -> list[str]:
    """要点ボックスの prose 問題（監査・validate 用）。"""
    intro, items = key_points_plain_in_reader_html(page_html)
    issues: list[str] = []
    if intro:
        if _VAGUE_INTRO_TAIL_RE.search(intro):
            issues.append("要点イントロに抽象テンプレ尾が残っています")
        if _BROKEN_POINTS_RE.search(intro):
            issues.append("要点イントロに述語欠落（要点を。）があります")
    for idx, item in enumerate(items, start=1):
        if not looks_like_key_point_sentence(item):
            sample = item[:40] + ("…" if len(item) > 40 else "")
            issues.append(f"要点リスト{idx}件目が文として不自然です: {sample}")
    return issues
