#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験ガイド・用語詳細の編集品質（専門家・プロライター水準）の共通判定."""

from __future__ import annotations

import re
from dataclasses import dataclass

# 専門家記事らしい具体性（数字・期限・条文・例示など）
CONCRETENESS_RE = re.compile(
    r"\d|％|%|年|月|日|条|項|科目|分野|公式|例えば|例：|たとえば|しかし|一方で|具体的"
)

# 公開前に必ず消す雛形マーカー（ERROR）
EDITORIAL_PLACEHOLDER_MARKERS: tuple[str, ...] = (
    "【記入】",
    "【本文を記入】",
    "【リードを記入】",
    "【短い定義】",
    "【定義】",
    "【誤解】",
    "【覚え方】",
    "【例題】",
    "【解説を記入】",
    "【40文字以上】",
    "【選択肢の論点を記入】",
    "【読者が",
    "差し替えてください",
    "プレースホルダ",
)

# 量産・scaffold 後の使い回し禁止（ERROR — published の section / FAQ）
EDITORIAL_BOILERPLATE_PHRASES: tuple[str, ...] = (
    "の観点で整理します",
    "制度・数値・日程は年度や改正で変わるため、学習前と申込前には試験実施団体（公式）の最新情報を確認してください",
    "非公式まとめは参考程度にし、最終判断は必ず公式要項に置きます",
    "このサイトでは過去問・用語解説・比較表を組み合わせ",
    "間違えた問題は理由を短くメモし、関連用語で定義と選択肢の論点を確認してから同分野へ戻ると定着しやすくなります",
    "まず公式要項で最新の制度を確認してください。本サイトでは過去問演習と用語解説で",
    "数値や期限は資格ごとに異なるため、本文の例は必ず公式情報と照合してください",
    "に関する質問「",
    "理解度を具体的に確かめられます",
    "付箋を付けながら読み",
    "演習で同テーマの設問を1問以上解いて確認",
)

# 薄い・AI丸投げっぽい定型（WARN）
EDITORIAL_GENERIC_PHRASES: tuple[str, ...] = (
    "について説明します",
    "について解説します",
    "が重要です",
    "を理解することが大切",
    "押さえておきましょう",
    "覚えておきましょう",
    "確認することが大切",
    "本番前には試験実施団体の公式情報もあわせて確認してください",
    "制度や数値は年度や改正で変わるため",
)

# 読みやすさ（WARN）— glossary_term_rules と共有
READABILITY_FRAGMENTS: tuple[tuple[str, str], ...] = (
    ("当該", "誰・何を指すかを具体的に書く"),
    ("前述", "前の段落を読んでいない読者にも伝わる書き方にする"),
    ("において", "「では」「で」など平易な言い換えを検討する"),
    ("ものとする", "法令原文の写しではなく、自分の言葉で説明する"),
    ("及び", "「と」「や」など日常語に置き換える"),
    ("することができる", "「できます」に簡潔化する"),
    ("することが可能", "「できます」に簡潔化する"),
)

# --- 試験ガイド（published 行の ERROR 下限は guide_article_rules が参照）---
GUIDE_PRO = {
    "lead": 80,
    "lead_max": 200,
    "meta_description_min": 70,
    "meta_description_max": 165,
    "user_intent": 50,
    "action_item_min": 3,
    "action_item_each": 10,
    "section_count": 5,
    "section_body": 180,
    "faq_answer": 100,
    "related_links": 2,
}

# --- 用語詳細（ERROR 下限は glossary_term_rules.GLOSSARY_MIN_LENGTHS が正本）---
GLOSSARY_PRO = {
    "article_lead": 60,
    "term_detail_body": 180,
    "definition": 50,
    "explanation": 80,
    "common_mistakes": 40,
    "memory_tip": 25,
    "faq_answer": 100,
    "exam_points_as": 3,
    "related_terms_as": 3,
    "paragraphs_in_body": 2,
    "max_sentence_chars": 72,
}


@dataclass(frozen=True)
class EditorialIssue:
    level: str  # ERROR | WARN
    column: str
    message: str


def norm(value: object) -> str:
    return str(value or "").strip()


def split_semicolon(value: str) -> list[str]:
    return [x.strip() for x in value.split(";") if x.strip()]


def split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n{2,}", norm(text)) if p.strip()]


def placeholder_hits(text: str) -> list[str]:
    return [m for m in EDITORIAL_PLACEHOLDER_MARKERS if m in text]


def generic_phrase_hits(text: str) -> list[str]:
    return [p for p in EDITORIAL_GENERIC_PHRASES if p in text]


def readability_issues(text: str, column: str) -> list[EditorialIssue]:
    issues: list[EditorialIssue] = []
    for fragment, hint in READABILITY_FRAGMENTS:
        if fragment in text:
            issues.append(EditorialIssue("WARN", column, f"読みにくい表現「{fragment}」: {hint}"))
    return issues


def placeholder_issues(text: str, column: str) -> list[EditorialIssue]:
    hits = placeholder_hits(text)
    if not hits:
        return []
    shown = "、".join(hits[:3])
    return [
        EditorialIssue(
            "ERROR",
            column,
            f"未執筆の雛形マーカーが残っています（{shown}）。専門家レベルの本文に差し替えてください",
        )
    ]


def boilerplate_hits(text: str) -> list[str]:
    return [p for p in EDITORIAL_BOILERPLATE_PHRASES if p in text]


def boilerplate_issues(text: str, column: str) -> list[EditorialIssue]:
    """量産テンプレ・記事間コピペの禁止句。"""
    hits = boilerplate_hits(text)
    if not hits:
        return []
    shown = "、".join(f"「{h[:24]}…」" if len(h) > 24 else f"「{h}」" for h in hits[:3])
    return [
        EditorialIssue(
            "ERROR",
            column,
            f"機械的な共通文が含まれています（{shown}）。記事固有のオリジナル文に全面差し替えてください",
        )
    ]


def generic_issues(text: str, column: str, *, min_hits: int = 2) -> list[EditorialIssue]:
    hits = generic_phrase_hits(text)
    if len(hits) < min_hits:
        return []
    return [
        EditorialIssue(
            "WARN",
            column,
            f"汎用・定型表現が多すぎます（{len(hits)}件）。資格固有の具体例・数値・手続に置き換えてください",
        )
    ]


def long_sentence_issues(text: str, column: str, *, max_chars: int) -> list[EditorialIssue]:
    issues: list[EditorialIssue] = []
    for para in split_paragraphs(text) or [text]:
        for sent in re.split(r"[。！？\n]", para):
            s = sent.strip()
            if len(s) > max_chars:
                issues.append(
                    EditorialIssue(
                        "WARN",
                        column,
                        f"1文が長すぎます（{len(s)}字）。{max_chars}字以内に分割すると読みやすくなります",
                    )
                )
                break
    return issues


def concreteness_issues(text: str, column: str) -> list[EditorialIssue]:
    if not text or CONCRETENESS_RE.search(text):
        return []
    return [
        EditorialIssue(
            "WARN",
            column,
            "具体性が不足しています。数字・期限・条文・例示・試験での見方のいずれかを入れてください",
        )
    ]


def duplicate_faq_answers(answers: list[str]) -> list[EditorialIssue]:
    normed = [re.sub(r"\s+", "", a) for a in answers if a]
    if len(normed) < 2:
        return []
    for i, a in enumerate(normed):
        for b in normed[i + 1 :]:
            if not a or not b:
                continue
            shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
            if shorter in longer or _similar_ratio(shorter, longer) > 0.72:
                return [
                    EditorialIssue(
                        "WARN",
                        "faq_*_answer",
                        "FAQの回答が互いに似ています。定義・誤解・試験・次の行動で内容を分けてください",
                    )
                ]
    return []


def _similar_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    common = sum(1 for ch in a if ch in b)
    return common / max(len(a), len(b))


def is_published_guide(row: dict[str, str]) -> bool:
    status = norm(row.get("content_status")).lower()
    return status in {"", "published", "publish"}
