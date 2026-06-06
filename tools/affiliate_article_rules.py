#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""アフィリエイト試験ガイドの品質ルール（docs/affiliate/affiliate-article-rules.md 正本）。"""

from __future__ import annotations

from tools.affiliate_links import (
    affiliate_external_links_in_row,
    is_affiliate_article,
    is_internal_affiliate_article,
)
from tools.editorial_quality import EditorialIssue, norm, split_semicolon
from tools.related_links import parse_related_link_token
from tools.site_config import is_template_site

# 手書きリライトキャンペーンとは別系統の「編集合格」印
AFFILIATE_HAND_MARKERS: tuple[str, ...] = (
    "Amazon URL確定・本文全面リライト",
    "アフィリエイト記事として編集合格",
    "全面リライト（アフィリエイト）",
)

# scaffold / 自動 prose の残り（アフィリエイト公開ゲート）
AFFILIATE_TEMPLATE_FORBIDDEN: tuple[str, ...] = (
    "の論点の一つです",
    "演習問題の解説と対応づけやすくなります",
    "一人で診断",
    "過度な情報開示",
    "主体を取り違えていないか",
    "について【行動",
    "【行動1】",
    "ガイド記事テンプレート で",
    "独学対策向けテンプレートから作成",
    "学習計画向けテンプレートから作成",
    "受験・申込向けテンプレートから作成",
    "過去問活用向けテンプレートから作成",
)

PR_DISCLAIMER_FRAGMENTS: tuple[str, ...] = (
    "【PR・広告】",
    "【PR】",
    "本記事にはアフィリエイトリンクが含まれる場合があります",
)

# 商品比較 UI が本文を補うため、通常ガイドより緩め
AFFILIATE_MIN_SECTION_BODY = 80
AFFILIATE_MIN_FAQ_ANSWER = 80

AFFILIATE_GENRES = frozenset({"独学対策", "過去問活用", "学習計画", "受験・申込"})

TEXT_COLS = (
    "title",
    "meta_description",
    "lead",
    "user_intent",
    *(f"section_{n}_body" for n in range(1, 8)),
    *(f"faq_{n}_answer" for n in range(1, 5)),
    *(f"faq_{n}_question" for n in range(1, 5)),
)


def affiliate_template_hits(text: str) -> list[str]:
    t = norm(text)
    if not t:
        return []
    return [p for p in AFFILIATE_TEMPLATE_FORBIDDEN if p in t]


def affiliate_is_hand_complete(row: dict[str, str]) -> bool:
    note = norm(row.get("revision_note"))
    return any(m in note for m in AFFILIATE_HAND_MARKERS)


def affiliate_quality_status(row: dict[str, str], combined_text: str) -> str:
    """affiliate_ok | affiliate_pending | affiliate_template | affiliate_needs_links"""
    if affiliate_template_hits(combined_text):
        return "affiliate_template"
    if norm(row.get("content_status")) == "published":
        if not is_internal_affiliate_article(row) and not affiliate_external_links_in_row(row):
            return "affiliate_needs_links"
    if affiliate_is_hand_complete(row):
        return "affiliate_ok"
    note = norm(row.get("revision_note"))
    if "自動prose" in note or "content-lib更新" in note or "要手書き" in note:
        return "affiliate_pending"
    if affiliate_template_hits(combined_text):
        return "affiliate_template"
    return "affiliate_pending"


def check_affiliate_row(
    row: dict[str, str],
    *,
    slug_set: set[str],
    line: int | None = None,
) -> list[EditorialIssue]:
    """通常ガイドの手書きリライトルールの代わりに適用。"""
    from tools.guide_article_rules import reader_facing_text, section_pairs

    issues: list[EditorialIssue] = []
    slug = norm(row.get("slug"))
    published = norm(row.get("content_status")) == "published"

    def err(col: str, msg: str) -> None:
        issues.append(EditorialIssue("ERROR", col, msg))

    def warn(col: str, msg: str) -> None:
        issues.append(EditorialIssue("WARN", col, msg))

    if not is_affiliate_article(row):
        return issues

    genre = norm(row.get("genre"))
    if genre and genre not in AFFILIATE_GENRES:
        warn("genre", f"アフィリエイト記事の genre は {sorted(AFFILIATE_GENRES)} のいずれかを推奨（現在: {genre!r}）")

    for col in TEXT_COLS:
        raw = norm(row.get(col))
        if not raw:
            continue
        text = reader_facing_text(row, col, raw) if published else raw
        for frag in PR_DISCLAIMER_FRAGMENTS:
            if frag in text:
                err(col, f"アフィリエイト記事の公開本文に PR 定型文が残っています: {frag}")
        for hit in affiliate_template_hits(text):
            shown = hit[:32]
            msg = (
                f"アフィリエイト scaffold 禁止句「{shown}…」。"
                f"docs/affiliate/affiliate-article-rules.md §3-B に沿ってオリジナル執筆してください"
            )
            if not published:
                continue
            if is_template_site():
                warn(col, msg)
            else:
                err(col, msg)

    if published:
        if not is_internal_affiliate_article(row) and not affiliate_external_links_in_row(row):
            err(
                "related_links",
                "published アフィリエイト記事に ASP / 商品 URL がありません。"
                " URL 確定まで draft にしてください（affiliate-article-rules.md §1）",
            )

        internal = 0
        related = split_semicolon(norm(row.get("related_links")))
        for item in related:
            target, _label = parse_related_link_token(item)
            if target and not target.startswith(("http://", "https://")):
                if target not in slug_set:
                    err("related_links", f"related_links の slug が存在しません: {target!r}")
                else:
                    internal += 1
        if internal < 2:
            warn(
                "related_links",
                "アフィリエイト記事の related_links には内部 slug を2件以上推奨（affiliate-article-rules.md §3）",
            )

        for _h, bcol, body in section_pairs(row):
            if not body:
                continue
            visible = reader_facing_text(row, bcol, body)
            if len(visible) < AFFILIATE_MIN_SECTION_BODY:
                msg = (
                    f"section 本文は {AFFILIATE_MIN_SECTION_BODY} 文字以上にしてください"
                    f"（現在 {len(visible)} 文字）"
                )
                if is_template_site():
                    warn(bcol, msg)
                else:
                    err(bcol, msg)

        for n in range(1, 4):
            acol = f"faq_{n}_answer"
            a = norm(row.get(acol))
            if not a:
                continue
            visible = reader_facing_text(row, acol, a)
            if len(visible) < AFFILIATE_MIN_FAQ_ANSWER:
                msg = f"FAQ回答は {AFFILIATE_MIN_FAQ_ANSWER} 文字以上にしてください（現在 {len(visible)} 文字）"
                if is_template_site():
                    warn(acol, msg)
                else:
                    err(acol, msg)

        for col in ("author_name", "reviewer_name", "fact_checked_at", "primary_sources"):
            if not norm(row.get(col)):
                err(col, "信頼性（執筆・確認・事実確認日・参照元）は公開記事で必須です")

    _ = line
    _ = slug
    return issues
