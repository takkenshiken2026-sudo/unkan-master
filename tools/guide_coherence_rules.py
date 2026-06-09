#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験ガイドの意味整合・信頼性チェック（量産テンプレ崩れの検出）。"""

from __future__ import annotations

import re
from typing import Iterable

from tools.editorial_quality import EditorialIssue, norm

# A級: 事実誤りが信頼を直接損なう記事（自動量産禁止）
TIER_A_SLUG_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"-center$"),
    re.compile(r"^exam-day-"),
    re.compile(r"^application-"),
    re.compile(r"^exam-schedule"),
    re.compile(r"^fee-"),
    re.compile(r"^eligibility-"),
    re.compile(r"^official-info"),
    re.compile(r"^exam-venue"),
)

INTERNAL_MARKER_RE = re.compile(r"（記事:[^）]+）")

INCOMPLETE_TAIL_RE = re.compile(r"の「[^」]+」(?:では|で)[。、,]?")

# 見出し「持ち物」なのに直前対策テンプレが混入
STUDY_PREP_PHRASES = (
    "参考書を増やさず",
    "得点率が低い",
    "用語10語",
    "演習20問",
    "3分野のうち",
    "10分野のうち",
)

# 会場記事に学習テンプレが混入
VENUE_WRONG_PHRASES = (
    "現場判断と3分野",
    "現場判断と4分野",
    "現場判断と5分野",
    "現場判断と10分野",
    "演習で同テーマの設問を1問以上",
    "付箋を付けながら読み",
    "の観点で整理します",
)

BROKEN_LIST_ITEM_RE = re.compile(r"<li>[^<]*（(?![^<]*）)")

HEADING_BODY_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...], str], ...] = (
    (
        ("持ち物",),
        STUDY_PREP_PHRASES,
        "見出しが持ち物なのに直前対策・学習絞り込みの文が含まれています",
    ),
    (
        ("アクセス", "会場"),
        ("得点率", "参考書を増やさず"),
        "見出しがアクセス・会場なのに学習対策の文が含まれています",
    ),
)


def is_tier_a_slug(slug: str) -> bool:
    s = norm(slug)
    return any(p.search(s) for p in TIER_A_SLUG_PATTERNS)


def short_topic_from_title(title: str) -> str:
    t = norm(title)
    if not t:
        return t
    m = re.match(r"^(.+?)【[^】]+】$", t)
    if m:
        return m.group(1).strip()
    return re.sub(r"^【[^】]+】", "", t).strip()


def seo_bracket_title(title: str) -> str | None:
    m = re.match(r"^(.+?)【([^】]+)】$", norm(title))
    if not m:
        return None
    return m.group(0)


def internal_marker_issues(text: str, column: str) -> list[EditorialIssue]:
    if INTERNAL_MARKER_RE.search(text or ""):
        return [
            EditorialIssue(
                "ERROR",
                column,
                "内部用マーカー（記事:slug 等）が読者向け本文に残っています",
            )
        ]
    return []


def long_seo_title_issues(title: str, text: str, column: str) -> list[EditorialIssue]:
    bracket = seo_bracket_title(title)
    if not bracket or len(bracket) < 20:
        return []
    if (text or "").count(bracket) >= 1:
        short = short_topic_from_title(title)
        if short and short != bracket:
            return [
                EditorialIssue(
                    "ERROR",
                    column,
                    f"SEO用長タイトル「{bracket[:40]}…」が本文にそのまま使われています。短いトピック名に直してください",
                )
            ]
    return []


def heading_body_issues(heading: str, body: str, column: str) -> list[EditorialIssue]:
    issues: list[EditorialIssue] = []
    h = norm(heading)
    b = norm(body)
    if not h or not b:
        return issues
    for keys, forbidden, msg in HEADING_BODY_RULES:
        if not any(k in h for k in keys):
            continue
        if any(p in b for p in forbidden):
            issues.append(EditorialIssue("ERROR", column, msg))
    if "持ち物" in h:
        item_hints = ("持ち", "受験票", "鉛筆", "消しゴム", "禁止", "筆記")
        if not any(x in b for x in item_hints):
            issues.append(
                EditorialIssue(
                    "ERROR",
                    column,
                    "見出しが持ち物なのに、持ち物に関する具体記述がありません",
                )
            )
    return issues


def tier_a_content_issues(slug: str, row: dict[str, str]) -> list[EditorialIssue]:
    if not is_tier_a_slug(slug):
        return []
    issues: list[EditorialIssue] = []
    title = norm(row.get("title"))
    for col in ("lead", "user_intent", "meta_description", "action_items"):
        text = norm(row.get(col))
        if text:
            issues.extend(long_seo_title_issues(title, text, col))
    return issues


def faq_coherence_issues(row: dict[str, str]) -> list[EditorialIssue]:
    issues: list[EditorialIssue] = []
    for n in range(1, 5):
        q = norm(row.get(f"faq_{n}_question"))
        a = norm(row.get(f"faq_{n}_answer"))
        if not q or not a:
            continue
        acol = f"faq_{n}_answer"
        if "持ち物" in q or "持参" in q:
            if not any(x in a for x in ("持ち", "受験票", "鉛筆", "消しゴム", "禁止", "筆記", "要項")):
                issues.append(
                    EditorialIssue("ERROR", acol, "FAQの質問が持ち物なのに、回答が持ち物の話になっていません")
                )
        if "アクセス" in q or "住所" in q:
            if not any(x in a for x in ("アクセス", "所在地", "交通", "公式", "案内", "ルート")):
                issues.append(
                    EditorialIssue("ERROR", acol, "FAQの質問がアクセスなのに、回答がアクセスの話になっていません")
                )
        if "独学" in q and "演習" in a and "持ち物" not in q and "アクセス" not in q:
            pass  # ok
        elif "読了後" in a and "分野タグ" in a and ("持ち物" in q or "アクセス" in q):
            issues.append(
                EditorialIssue("ERROR", acol, "FAQの回答が汎用テンプレ（読了後は演習…）のままです")
            )
    return issues


def prose_pattern_issues(
    text: str,
    column: str,
    *,
    slug: str = "",
    skip_patterns: frozenset[str] = frozenset(),
) -> list[EditorialIssue]:
    from tools.build_article_pages import sanitize_guide_text
    from tools.guide_prose_patterns import scan_prose_text

    cleaned = sanitize_guide_text(text, slug)
    issues: list[EditorialIssue] = []
    for hit in scan_prose_text(cleaned, column=column):
        if hit.pattern in skip_patterns:
            continue
        issues.append(
            EditorialIssue(
                "ERROR",
                column,
                f"読者向け本文に品質問題（{hit.pattern}）: …{hit.snippet[:72]}…",
            )
        )
    return issues


def check_guide_row_coherence(row: dict[str, str], *, published: bool) -> list[EditorialIssue]:
    if not published:
        return []
    slug = norm(row.get("slug"))
    if not slug:
        return []
    from tools.guide_rewrite_rules import rewrite_exempt

    tier_a = is_tier_a_slug(slug)
    issues: list[EditorialIssue] = []
    title = norm(row.get("title"))
    skip_prose = frozenset({"week_template"}) if rewrite_exempt(row) else frozenset()

    text_cols = [
        "meta_description",
        "lead",
        "user_intent",
        "action_items",
        *(f"section_{n}_body" for n in range(1, 8)),
        *(f"faq_{n}_answer" for n in range(1, 5)),
        *(f"faq_{n}_question" for n in range(1, 5)),
    ]
    for col in text_cols:
        text = norm(row.get(col))
        if not text:
            continue
        issues.extend(internal_marker_issues(text, col))
        issues.extend(prose_pattern_issues(text, col, slug=slug, skip_patterns=skip_prose))
        if tier_a:
            issues.extend(long_seo_title_issues(title, text, col))

    for hcol, bcol, body in _section_pairs(row):
        heading = norm(row.get(hcol))
        # 見出しと本文の食い違い（持ち物・会場）は全 published 記事で ERROR
        issues.extend(heading_body_issues(heading, body, bcol))
        if tier_a and any(p in body for p in VENUE_WRONG_PHRASES):
            issues.append(
                EditorialIssue(
                    "ERROR",
                    bcol,
                    "会場・申込系（A級）記事に学習量産テンプレの定型句が含まれています",
                )
            )
        if any(p in body for p in VENUE_WRONG_PHRASES):
            issues.append(
                EditorialIssue(
                    "ERROR",
                    bcol,
                    "節本文に量産テンプレの定型句（現場判断とN分野等）が含まれています",
                )
            )

    if tier_a:
        issues.extend(tier_a_content_issues(slug, row))

    issues.extend(faq_coherence_issues(row))
    return issues


def _section_pairs(row: dict[str, str]) -> Iterable[tuple[str, str, str]]:
    for n in range(1, 8):
        hcol = f"section_{n}_heading"
        bcol = f"section_{n}_body"
        heading = norm(row.get(hcol))
        body = norm(row.get(bcol))
        if heading and body:
            yield hcol, bcol, body


def audit_article_html(slug: str, html: str) -> list[str]:
    """生成 HTML の整合性。記事本文部分を対象。"""
    issues: list[str] = []
    if INTERNAL_MARKER_RE.search(html):
        issues.append("内部マーカー（記事:slug）が HTML に残っています")
    if BROKEN_LIST_ITEM_RE.search(html):
        issues.append("括弧が閉じていない壊れた箇条書き（<li>）があります")
    if INCOMPLETE_TAIL_RE.search(html):
        issues.append("テンプレ末尾の「…で。」だけの不完全文が残っています")
    study_in_items = False
    for sec in re.finditer(
        r'<section class="seo-article-section" aria-labelledby="article-sec-\d+"[^>]*>(.*?)</section>',
        html,
        re.DOTALL,
    ):
        block = sec.group(1)
        heading_m = re.search(r"<h2[^>]*>.*?</h2>", block, re.DOTALL)
        if not heading_m:
            continue
        heading_text = re.sub(r"<[^>]+>", "", heading_m.group(0))
        if "持ち物" not in heading_text:
            continue
        if any(p in block for p in STUDY_PREP_PHRASES):
            issues.append("持ち物セクションに直前対策テンプレの文が含まれています")
            break
    return issues
