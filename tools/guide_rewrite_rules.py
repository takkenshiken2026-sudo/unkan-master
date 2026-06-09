#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験ガイド手書きリライト判定・禁止パターン（全サイト共通）。"""

from __future__ import annotations

import re

from tools.editorial_quality import norm

# 手書きリライト済みとみなす revision_note の印
HAND_REWRITTEN_MARKERS: tuple[str, ...] = (
    "手書きリライト",
    "全面リライト",
    "Amazon URL確定・本文全面リライト",
)

# 量産テンプレ検出（published かつ未リライト → ERROR）
REWRITE_FORBIDDEN_PHRASES: tuple[str, ...] = (
    "の論点の一つです",
    "演習問題の解説と対応づけやすくなります",
    "一人で診断",
    "過度な情報開示",
    "主体を取り違えていないか",
    "FAQ3「本テーマ」",
    "演習→用語解説→1週間後の解き直し",
    "受験資格・日程・合格基準の確認手順と、演習・用語解説を組み合わせた学習の始め方",
    "guide_expert_writer",
    "legacy batch",
    "主体・期限・数値をメモしながら演習問題で定着を確認",
    "合格までの学習を続けるには、出題範囲を分けて、演習と復習を定期的に回す計画が重要",
    "の論点として、公式テキスト該当章",
    "条文の主体・期限・数値を演習問題とセットで押さえる",
    "マ管受験者が現場で迷いやすい論点",
)

# 本文に slug 名が露出（takken-foo 等）
SLUG_IN_BODY_RE = re.compile(r"\b[a-z]{2,}[a-z0-9-]{2,}\b")

SLUG_IN_BODY_ALLOW: frozenset[str] = frozenset(
    {
        "amazon",
        "html",
        "http",
        "https",
        "index",
        "past",
        "terms",
        "articles",
    }
)

# A級: 優先リライト（guide_coherence_rules.TIER_A 相当 + 試験サイト固有）
TIER_A_GENRES: frozenset[str] = frozenset(
    {"受験・申込", "直前・当日", "合格・難易度"}
)

TIER_A_SLUG_RE = re.compile(
    r"(?:^|[-_])(?:schedule|shiken|juken|goukaku|gokaku|eligibility|fee|venue|exam-day|application|shikennichiji)",
    re.I,
)


def is_affiliate_row(row: dict[str, str]) -> bool:
    tags = norm(row.get("tags"))
    return "アフィリエイト" in tags


def is_hand_rewritten(row: dict[str, str]) -> bool:
    note = norm(row.get("revision_note"))
    return any(m in note for m in HAND_REWRITTEN_MARKERS)


def rewrite_exempt(row: dict[str, str]) -> bool:
    """量産テンプレ自動差し替え（rewrite_guide_boilerplate）の対象外。"""
    if is_hand_rewritten(row):
        return True
    if is_affiliate_row(row) and is_hand_rewritten(row):
        return True
    return False


def forbidden_phrase_exempt(row: dict[str, str]) -> bool:
    """禁止句・enrich パターンの監査対象外（原則 False）。"""
    _ = row
    return False


def rewrite_forbidden_hits(text: str) -> list[str]:
    t = norm(text)
    if not t:
        return []
    return [p for p in REWRITE_FORBIDDEN_PHRASES if p in t]


def slug_leaks_in_text(text: str, slug: str, *, slug_set: set[str] | None = None) -> list[str]:
    """本文中の slug 名露出（内部記法）。slug_set があれば既知 slug のみ検出。"""
    t = norm(text)
    if not t:
        return []
    if slug_set:
        from tools.guide_slug_prose import slug_leaks_against_pool

        return slug_leaks_against_pool(t, slug, slug_set)
    hits: list[str] = []
    if slug and slug in t:
        hits.append(slug)
    for m in SLUG_IN_BODY_RE.finditer(t):
        token = m.group(0)
        if token in SLUG_IN_BODY_ALLOW:
            continue
        if "-" in token and len(token) >= 8 and token != slug:
            if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", token):
                hits.append(token)
    return hits


def tier_priority(row: dict[str, str]) -> str:
    slug = norm(row.get("slug"))
    genre = norm(row.get("genre"))
    if genre in TIER_A_GENRES or TIER_A_SLUG_RE.search(slug):
        return "A"
    if genre in {"学習計画", "分野別対策", "過去問活用", "独学対策"}:
        return "B"
    return "C"


def rewrite_status(row: dict[str, str], *, combined_text: str = "") -> str:
    if rewrite_exempt(row):
        return "done"
    if rewrite_forbidden_hits(combined_text):
        return "needs_rewrite"
    if "の論点の一つです" in combined_text:
        return "needs_rewrite"
    return "ok"
