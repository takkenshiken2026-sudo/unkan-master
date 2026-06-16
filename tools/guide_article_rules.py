#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験ガイド（guide_articles.csv）の編集品質ルール."""

from __future__ import annotations

from tools.editorial_quality import (
    GUIDE_PRO,
    EditorialIssue,
    boilerplate_issues,
    boilerplate_hits,
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
from tools.related_links import parse_related_link_token
from tools.site_config import is_template_site
from tools.guide_coherence_rules import check_guide_row_coherence
from tools.guide_rewrite_rules import (
    rewrite_exempt,
    rewrite_forbidden_hits,
    slug_leaks_in_text,
)

GUIDE_MIN_SECTION_BODY = 180  # ERROR（published）: 専門家解説の目安
GUIDE_MIN_FAQ_ANSWER = 100
GUIDE_ARTICLE_MAX = 50  # テンプレート標準: 試験ガイドは50本以内


def reader_facing_text(
    row: dict[str, str],
    col: str,
    raw: str,
    *,
    slug_titles: dict[str, str] | None = None,
    prefix_labels: dict[str, str] | None = None,
) -> str:
    """ビルド後に読者へ出る本文（sanitize / resolve 後）。"""
    from tools.build_article_pages import resolve_guide_section_body, sanitize_guide_text
    from tools.guide_field_prose import resolve_reader_slug_prose

    slug = norm(row.get("slug"))
    text = norm(raw)
    if not text:
        return text
    if col.startswith("section_") and col.endswith("_body"):
        text = sanitize_guide_text(resolve_guide_section_body(row, text), slug)
    elif col.startswith("faq_"):
        text = sanitize_guide_text(text, slug)
    if slug_titles:
        link_internal = (col.startswith("section_") and col.endswith("_body")) or (
            col.startswith("faq_") and col.endswith("_answer")
        )
        text = resolve_reader_slug_prose(
            text,
            slug_titles=slug_titles,
            current_slug=slug,
            link_internal=link_internal,
            prefix_labels=prefix_labels,
        )
    return text


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
    slug_titles: dict[str, str] | None = None,
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
        raw = norm(row.get(col))
        if not raw:
            continue
        text = reader_facing_text(row, col, raw, slug_titles=slug_titles) if published else raw
        issues.extend(placeholder_issues(raw, col))
        if published:
            issues.extend(readability_issues(text, col))
            issues.extend(generic_issues(text, col))
            if (col.startswith("section_") and col.endswith("_body")) or col.startswith("faq_"):
                if is_template_site():
                    if boilerplate_hits(text):
                        warn(col, "テンプレ用サンプルに量産禁止句が残っています（本番サイトでは ERROR）")
                else:
                    issues.extend(boilerplate_issues(text, col))
            if published and not rewrite_exempt(row):
                forbidden = rewrite_forbidden_hits(text)
                if forbidden:
                    shown = forbidden[0][:32]
                    if is_template_site():
                        warn(
                            col,
                            f"量産テンプレ禁止句「{shown}…」（本番では要手書きリライト）",
                        )
                    else:
                        err(
                            col,
                            f"量産テンプレ禁止句が残っています（{shown}…）。"
                            f"記事固有の手書き本文に差し替えてください",
                        )
            if published and slug_titles:
                for leak in slug_leaks_in_text(text, slug, slug_set=set(slug_titles)):
                    if is_template_site():
                        warn(col, f"本文に内部 slug が露出しています: {leak}")
                    else:
                        err(col, f"本文に内部 slug が露出しています: {leak}")

    sections = [(h, b, body) for h, b, body in section_pairs(row) if body]
    for _h, bcol, body in sections:
        visible = reader_facing_text(row, bcol, body, slug_titles=slug_titles) if published else body
        if published and len(visible) < GUIDE_MIN_SECTION_BODY:
            msg = f"section 本文は {GUIDE_MIN_SECTION_BODY} 文字以上にしてください（現在 {len(visible)} 文字）"
            if is_template_site():
                warn(bcol, msg)
            else:
                err(bcol, msg)
        elif not published and len(body) < 80:
            msg = f"section 本文は 80 文字以上にしてください（現在 {len(body)} 文字）"
            if is_template_site():
                warn(bcol, msg)
            else:
                err(bcol, msg)
        if published:
            for issue in concreteness_issues(visible, bcol):
                issues.append(issue)

    faq_answers: list[str] = []
    faq_questions: list[str] = []
    for n in range(1, 4):
        qcol = f"faq_{n}_question"
        acol = f"faq_{n}_answer"
        q, a = norm(row.get(qcol)), norm(row.get(acol))
        if q:
            if published and q in faq_questions:
                err(qcol, f"FAQ質問が重複しています: {q}")
            faq_questions.append(q)
        if q and not a:
            err(acol, f"{qcol} に対する {acol} が空です")
        visible_a = reader_facing_text(row, acol, a, slug_titles=slug_titles) if published and a else a
        if published and visible_a and len(visible_a) < GUIDE_MIN_FAQ_ANSWER:
            msg = f"FAQ回答は {GUIDE_MIN_FAQ_ANSWER} 文字以上にしてください（現在 {len(visible_a)} 文字）"
            if is_template_site():
                warn(acol, msg)
            else:
                err(acol, msg)
        if a:
            faq_answers.append(visible_a if published else a)
    issues.extend(duplicate_faq_answers(faq_answers))

    related = split_semicolon(norm(row.get("related_links")))
    internal = [
        parse_related_link_token(x)[0]
        for x in related
        if x and not parse_related_link_token(x)[0].startswith(("http://", "https://"))
    ]
    if published and len(internal) < 1:
        warn("related_links", "関連記事（内部 slug）を1件以上入れると回遊と専門性の補強になります")

    if published and row.get("genre") == "用語ハブ活用法":
        for _h, bcol, body in sections:
            if "terms/" not in body and "用語解説" not in body and len(body) > 200:
                warn(
                    bcol,
                    "用語ハブ活用法ジャンルでは用語の定義よりハブの使い方を書き、terms/ または試験ガイドへの導線を入れてください",
                )

    if not published:
        _ = line
        return issues

    # --- プロ水準（published のみ WARN）---
    lead = norm(row.get("lead"))
    if lead and len(lead) < GUIDE_PRO["lead"]:
        warn("lead", f"リードは {GUIDE_PRO['lead']} 文字以上を推奨（現在 {len(lead)} 文字）")
    if lead and len(lead) > GUIDE_PRO["lead_max"]:
        warn(
            "lead",
            f"リードは {GUIDE_PRO['lead_max']} 文字以内を推奨（現在 {len(lead)} 文字。ビルド時に自動短縮されます）",
        )

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

    for issue in check_guide_row_coherence(row, published=published):
        if is_template_site() and issue.level == "ERROR":
            warn(issue.column, f"[整合性] {issue.message}")
        elif issue.level == "ERROR":
            err(issue.column, issue.message)
        else:
            warn(issue.column, issue.message)

    _ = line
    return issues
