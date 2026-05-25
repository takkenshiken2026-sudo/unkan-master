#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験ガイド（guide_articles.csv）の編集品質ルール."""

from __future__ import annotations

from tools.editorial_quality import (
    GUIDE_PRO,
    EditorialIssue,
    concreteness_issues,
    duplicate_faq_answers,
    generic_issues,
    is_published_guide,
    long_sentence_issues,
    norm,
    placeholder_issues,
    readability_issues,
    split_semicolon,
)

GUIDE_MIN_SECTION_BODY = 180  # ERROR（published）: 専門家解説の目安
GUIDE_MIN_FAQ_ANSWER = 100


def section_pairs(row: dict[str, str]) -> list[tuple[str, str, str]]:
    """(heading_col, body_col, body_text)"""
    out: list[tuple[str, str, str]] = []
    for n in range(1, 8):
        hcol = f"section_{n}_heading"
        bcol = f"section_{n}_body"
        heading = norm(row.get(hcol))
        body = norm(row.get(bcol))
        if heading and body:
            out.append((hcol, bcol, body))
        elif heading and not body:
            out.append((hcol, bcol, ""))
    return out


def check_guide_row(
    row: dict[str, str],
    *,
    slug_set: set[str],
    line: int | None = None,
) -> list[EditorialIssue]:
    issues: list[EditorialIssue] = []
    slug = norm(row.get("slug"))
    if not slug:
        return issues

    published = is_published_guide(row)

    def err(col: str, msg: str) -> None:
        issues.append(EditorialIssue("ERROR", col, msg))

    def warn(col: str, msg: str) -> None:
        issues.append(EditorialIssue("WARN", col, msg))

    # 雛形・禁止マーカー
    text_cols = [
        "title",
        "meta_description",
        "lead",
        "user_intent",
        *(f"section_{n}_body" for n in range(1, 8)),
        *(f"faq_{n}_answer" for n in range(1, 4)),
        *(f"faq_{n}_question" for n in range(1, 4)),
    ]
    for col in text_cols:
        text = norm(row.get(col))
        if not text:
            continue
        issues.extend(placeholder_issues(text, col))
        if published:
            issues.extend(readability_issues(text, col))
            issues.extend(generic_issues(text, col))

    sections = [(h, b, body) for h, b, body in section_pairs(row) if body]
    for _h, bcol, body in sections:
        if published and len(body) < GUIDE_MIN_SECTION_BODY:
            err(
                bcol,
                f"section 本文は {GUIDE_MIN_SECTION_BODY} 文字以上にしてください（現在 {len(body)} 文字）",
            )
        elif not published and len(body) < 80:
            err(bcol, f"section 本文は 80 文字以上にしてください（現在 {len(body)} 文字）")
        if published:
            for issue in concreteness_issues(body, bcol):
                issues.append(issue)

    faq_answers: list[str] = []
    for n in range(1, 4):
        qcol = f"faq_{n}_question"
        acol = f"faq_{n}_answer"
        q, a = norm(row.get(qcol)), norm(row.get(acol))
        if q and not a:
            err(acol, f"{qcol} に対する {acol} が空です")
        if a and len(a) < GUIDE_MIN_FAQ_ANSWER:
            err(acol, f"FAQ回答は {GUIDE_MIN_FAQ_ANSWER} 文字以上にしてください（現在 {len(a)} 文字）")
        if a:
            faq_answers.append(a)
    issues.extend(duplicate_faq_answers(faq_answers))

    related = split_semicolon(norm(row.get("related_links")))
    internal = [
        x.split(":", 1)[0].strip()
        for x in related
        if x and not x.split(":", 1)[0].strip().startswith(("http://", "https://"))
    ]
    if published and len(internal) < 1:
        warn("related_links", "関連記事（内部 slug）を1件以上入れると回遊と専門性の補強になります")

    if not published:
        _ = line
        return issues

    # --- プロ水準（published のみ WARN）---
    lead = norm(row.get("lead"))
    if lead and len(lead) < GUIDE_PRO["lead"]:
        warn("lead", f"リードは {GUIDE_PRO['lead']} 文字以上を推奨（現在 {len(lead)} 文字）")

    meta = norm(row.get("meta_description"))
    if meta:
        if len(meta) < GUIDE_PRO["meta_description_min"]:
            warn("meta_description", f"meta_description は {GUIDE_PRO['meta_description_min']} 文字以上を推奨")
        if len(meta) > GUIDE_PRO["meta_description_max"]:
            warn("meta_description", f"meta_description は {GUIDE_PRO['meta_description_max']} 文字以内を推奨")

    intent = norm(row.get("user_intent"))
    if intent and len(intent) < GUIDE_PRO["user_intent"]:
        warn("user_intent", "読者が得られることを専門家の視点で1段落（50字以上）書いてください")

    actions = split_semicolon(norm(row.get("action_items")))
    if len(actions) < GUIDE_PRO["action_item_min"]:
        warn(
            "action_items",
            f"読後の行動は {GUIDE_PRO['action_item_min']} 項目以上（セミコロン区切り）を推奨",
        )
    for item in actions:
        if len(item) < GUIDE_PRO["action_item_each"]:
            warn("action_items", f"各 action_items は具体的に（{GUIDE_PRO['action_item_each']} 字以上）")

    if len(sections) < GUIDE_PRO["section_count"]:
        warn(
            "section_*_body",
            f"本文見出しは {GUIDE_PRO['section_count']} 個以上を推奨（現在 {len(sections)} 個）",
        )
    for _h, bcol, body in sections:
        issues.extend(long_sentence_issues(body, bcol, max_chars=80))

    for n in range(1, 4):
        a = norm(row.get(f"faq_{n}_answer"))
        if a and len(a) < GUIDE_PRO["faq_answer"] and len(a) >= GUIDE_MIN_FAQ_ANSWER:
            warn(
                f"faq_{n}_answer",
                f"FAQ回答は {GUIDE_PRO['faq_answer']} 文字程度を推奨（検索意図への具体的回答）",
            )

    if len(internal) < GUIDE_PRO["related_links"]:
        warn("related_links", f"関連記事は内部 slug を {GUIDE_PRO['related_links']} 件以上推奨")

    for col in ("author_name", "reviewer_name", "fact_checked_at", "primary_sources"):
        if not norm(row.get(col)):
            err(col, "信頼性（執筆・確認・事実確認日・参照元）は公開記事で必須です")

    sources = norm(row.get("primary_sources"))
    if "example.com" in sources:
        warn("primary_sources", "example.com のままです。公式一次情報の URL に差し替えてください")

    _ = line
    return issues
