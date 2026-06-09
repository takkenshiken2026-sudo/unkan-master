#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験ガイド手書き品質の判定（自動 prose 差し替え vs 本当の手書き）。"""

from __future__ import annotations

from tools.editorial_quality import norm

# rewrite_guide_boilerplate / guide_rewrite_prose が全記事に埋め込む汎用フレーズ
AUTO_PROSE_SIGNATURES: tuple[str, ...] = (
    "演習10問で定着させてください",
    "50％を下回る分野から優先復習",
    "テキスト1章→演習10問→誤答を用語解説で確認",
    "演習10問→誤答分析→用語10語→1週間後解き直し",
    "比較表・よくある誤答で混同語を整理する",
    "主体・期限・手順は",
    "主体・期限・数値をメモしながら演習問題で定着を確認",
    "と公式テキストで必ず照合してください。",
    "に向けた学習計画の立て方を説明します",
)

AUTO_REVISION_MARKERS: tuple[str, ...] = (
    "自動prose差し替え",
    "自動 prose",
)

HAND_REVISION_MARKERS: tuple[str, ...] = (
    "手書きリライト",
    "全面リライト",
    "Amazon URL確定・本文全面リライト",
)


def auto_prose_hit_count(text: str) -> int:
    t = norm(text)
    if not t:
        return 0
    return sum(1 for sig in AUTO_PROSE_SIGNATURES if sig in t)


def is_auto_prose_text(text: str, *, threshold: int = 2) -> bool:
    return auto_prose_hit_count(text) >= threshold


def revision_is_auto(row: dict[str, str]) -> bool:
    note = norm(row.get("revision_note"))
    return any(m in note for m in AUTO_REVISION_MARKERS)


def revision_is_hand(row: dict[str, str]) -> bool:
    note = norm(row.get("revision_note"))
    if revision_is_auto(row):
        return False
    return any(m in note for m in HAND_REVISION_MARKERS)


def prose_quality_status(row: dict[str, str], combined_text: str) -> str:
    """hand_done | auto_pending | affiliate_pending | needs_rewrite | ok"""
    from tools.guide_rewrite_rules import (
        is_affiliate_row,
        is_hand_rewritten,
        rewrite_forbidden_hits,
    )

    tags = norm(row.get("tags"))
    if "アフィリエイト" in tags and not revision_is_hand(row):
        return "affiliate_pending"
    if rewrite_forbidden_hits(combined_text):
        return "needs_rewrite"
    if revision_is_hand(row) and not is_auto_prose_text(combined_text):
        return "hand_done"
    if revision_is_hand(row) and is_auto_prose_text(combined_text):
        return "auto_pending"
    if is_auto_prose_text(combined_text) or revision_is_auto(row):
        return "auto_pending"
    if is_hand_rewritten(row):
        return "hand_done"
    return "ok"
