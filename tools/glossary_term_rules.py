#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用語詳細記事（glossary_terms.csv）の必須列・最低品質基準."""

from __future__ import annotations

from dataclasses import dataclass

from tools.build_glossary_pages import lookup_key
from tools.editorial_quality import (
    GLOSSARY_PRO,
    concreteness_issues,
    duplicate_faq_answers,
    generic_issues,
    long_sentence_issues,
    placeholder_issues,
    readability_issues,
    split_paragraphs,
)

# 詳細記事として必須の CSV 列（全用語）
GLOSSARY_DETAIL_COLUMNS: tuple[str, ...] = (
    "article_title",
    "article_lead",
    "term_detail_body",
    "exam_points",
    "common_mistakes",
    "memory_tip",
    "example_question",
    "example_answer",
    "faq_1_question",
    "faq_1_answer",
    "faq_2_question",
    "faq_2_answer",
    "faq_3_question",
    "faq_3_answer",
    "faq_4_question",
    "faq_4_answer",
)

GLOSSARY_BASE_REQUIRED: frozenset[str] = frozenset(
    {
        "term",
        "category",
        "tags",
        "short_def",
        "definition",
        "related_terms",
        "legal_basis",
        "importance",
        "explanation",
    }
    | set(GLOSSARY_DETAIL_COLUMNS)
)

# 列ごとの最低文字数（空白除去後）— 専門家×プロライター水準を ERROR で強制
GLOSSARY_MIN_LENGTHS: dict[str, int] = {
    "short_def": 12,
    "definition": 50,
    "explanation": 80,
    "article_title": 10,
    "article_lead": 60,
    "term_detail_body": 180,
    "common_mistakes": 40,
    "memory_tip": 25,
    "example_question": 12,
    "example_answer": 3,
    "faq_1_question": 6,
    "faq_1_answer": 100,
    "faq_2_question": 6,
    "faq_2_answer": 100,
    "faq_3_question": 6,
    "faq_3_answer": 100,
    "faq_4_question": 6,
    "faq_4_answer": 100,
}

GLOSSARY_PRODUCTION_TARGET = 300
GLOSSARY_IMPORTANCE_VALUES = frozenset({"A", "B", "C", "S"})
GLOSSARY_MIN_RELATED_TERMS = 2
GLOSSARY_MIN_EXAM_POINT_ITEMS = 2
GLOSSARY_FAQ_COUNT = 4

# 法令・制度分野で importance A/S のときは根拠列を推奨（警告）
LAW_CATEGORY_KEYWORDS = ("法令", "制度", "法")

def split_semicolon(value: str) -> list[str]:
    return [x.strip() for x in value.split(";") if x.strip()]


def norm(value: object) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class GlossaryRowIssue:
    level: str  # ERROR | WARN
    message: str


def _is_law_heavy(category: str, importance: str) -> bool:
    if importance not in {"A", "S"}:
        return False
    return any(k in category for k in LAW_CATEGORY_KEYWORDS)


def check_glossary_row(
    row: dict[str, str],
    *,
    term_lookup: dict[str, str],
    line: int | None = None,
) -> list[GlossaryRowIssue]:
    """1行分の用語詳細記事ルール。validate_csv と scaffold の双方から利用。"""
    issues: list[GlossaryRowIssue] = []
    term = norm(row.get("term"))
    if not term:
        return issues

    def err(msg: str) -> None:
        issues.append(GlossaryRowIssue("ERROR", msg))

    def warn(msg: str) -> None:
        issues.append(GlossaryRowIssue("WARN", msg))

    for col in GLOSSARY_BASE_REQUIRED:
        if col not in row:
            err(f"必須列がありません: {col}")

    answer_symbols = frozenset({"○", "〇", "×", "✕", "╳"})
    for col, min_len in GLOSSARY_MIN_LENGTHS.items():
        text = norm(row.get(col))
        if not text:
            err(f"{col} は必須です（全用語を詳細記事として公開）")
            continue
        if col == "example_answer" and text in answer_symbols:
            continue
        if len(text) < min_len:
            err(f"{col} は {min_len} 文字以上にしてください（現在 {len(text)} 文字）")

    importance = norm(row.get("importance"))
    if not importance:
        err("importance は必須です（A / B / C / S）")
    elif importance not in GLOSSARY_IMPORTANCE_VALUES:
        warn(f"importance は A/B/C/S のいずれかを推奨します: {importance!r}")

    tags = split_semicolon(norm(row.get("tags")))
    if not tags:
        err("tags は1件以上必須です（セミコロン区切り）")

    exam_points = split_semicolon(norm(row.get("exam_points")))
    if len(exam_points) < GLOSSARY_MIN_EXAM_POINT_ITEMS:
        err(
            f"exam_points はセミコロン区切りで {GLOSSARY_MIN_EXAM_POINT_ITEMS} 項目以上必須です"
        )
    else:
        for item in exam_points:
            if len(item) < 8:
                err(f"exam_points の各項目は8文字以上にしてください: {item!r}")

    related_labels = split_semicolon(norm(row.get("related_terms")))
    if len(related_labels) < GLOSSARY_MIN_RELATED_TERMS:
        err(
            f"related_terms は登録済み用語を {GLOSSARY_MIN_RELATED_TERMS} 件以上指定してください"
        )
    for label in related_labels:
        if label == term:
            warn(f"related_terms に自分自身 {term!r} が含まれています")
            continue
        if not (term_lookup.get(label) or term_lookup.get(lookup_key(label))):
            err(
                f"related_terms の {label!r} は用語ページにリンク化されません"
                "（登録済み用語名に直してください）"
            )

    category = norm(row.get("category"))
    legal = norm(row.get("legal_basis"))
    if _is_law_heavy(category, importance) and not legal:
        warn(
            f"{category} かつ importance={importance} の用語は legal_basis の記載を推奨します"
        )

    title = norm(row.get("article_title"))
    if title and term not in title and "とは" not in title:
        warn(f"article_title に用語名 {term!r} または「とは」を含めると SEO 上わかりやすくなります")

    for q_col in tuple(f"faq_{n}_question" for n in range(1, GLOSSARY_FAQ_COUNT + 1)):
        q = norm(row.get(q_col))
        if q and not q.endswith(("？", "?")):
            warn(f"{q_col} は疑問形（？）で終えることを推奨します")

    prose_cols = (
        "short_def",
        "definition",
        "explanation",
        "article_lead",
        "term_detail_body",
        "common_mistakes",
        "memory_tip",
        *(f"faq_{n}_answer" for n in range(1, GLOSSARY_FAQ_COUNT + 1)),
    )
    faq_answers: list[str] = []
    for col in prose_cols:
        text = norm(row.get(col))
        if not text:
            continue
        for issue in placeholder_issues(text, col):
            if issue.level == "ERROR":
                err(issue.message)
            else:
                warn(issue.message)
        for issue in readability_issues(text, col):
            warn(issue.message)
        for issue in generic_issues(text, col):
            warn(issue.message)
        if col.endswith("_answer") and col.startswith("faq_"):
            faq_answers.append(text)

    for issue in duplicate_faq_answers(faq_answers):
        warn(issue.message)

    body = norm(row.get("term_detail_body"))
    if body:
        if len(split_paragraphs(body)) < GLOSSARY_PRO["paragraphs_in_body"]:
            err(
                f"term_detail_body は段落を {GLOSSARY_PRO['paragraphs_in_body']} つ以上"
                "（空行区切り \\n\\n）に分けてください"
            )
        for issue in long_sentence_issues(
            body, "term_detail_body", max_chars=GLOSSARY_PRO["max_sentence_chars"]
        ):
            warn(issue.message)
        for issue in concreteness_issues(body, "term_detail_body"):
            warn(issue.message)

    expl = norm(row.get("explanation"))
    if expl:
        for issue in concreteness_issues(expl, "explanation"):
            warn(issue.message)

    if importance in {"A", "S"}:
        if len(exam_points) < GLOSSARY_PRO["exam_points_as"]:
            warn(
                f"importance={importance} の用語は exam_points を {GLOSSARY_PRO['exam_points_as']} 項目以上推奨"
            )
        if len(related_labels) < GLOSSARY_PRO["related_terms_as"]:
            warn(
                f"importance={importance} の用語は related_terms を {GLOSSARY_PRO['related_terms_as']} 件以上推奨"
            )

    if expl and term not in expl and "選択肢" not in expl and "試験" not in expl:
        warn("explanation に試験での出題・選択肢の論点を明示すると専門性が上がります")

    answer = norm(row.get("example_answer"))
    if answer and answer not in {"○", "〇", "×", "✕", "╳"} and len(answer) < 5:
        err("example_answer は ○/× または5文字以上の解説にしてください")

    _ = line
    return issues
