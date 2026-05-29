#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
運行管理者試験（貨物）用 用語集 (data/glossary_terms.csv) ジェネレータ。

人手で書く「最小フィールド」を受け取り、25 カラムのリッチ用語データを
生成して書き出す。テンプレ既定の 12 サンプルは置き換える。

最小フィールド（用語ごとに必要）:
  term, category, importance, short_def, definition, legal_basis,
  exam_points (;区切り), common_mistakes, memory_tip,
  example_question, example_answer, related_terms (;区切り), tags

自動生成:
  explanation, article_title, article_lead, term_detail_body,
  faq_1..4 q/a
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DST = ROOT / "data" / "glossary_terms.csv"

CSV_FIELDS = [
    "term",
    "category",
    "tags",
    "short_def",
    "definition",
    "related_terms",
    "legal_basis",
    "importance",
    "explanation",
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
]


def make_article_title(term: str, category: str) -> str:
    return f"{term}とは｜運行管理者試験（貨物）の{category}で押さえる重要用語"


def make_article_lead(term: str, short_def: str, category: str) -> str:
    return (
        f"{term}は、運行管理者試験（貨物）の「{category}」で頻出する重要用語です。"
        f"このページでは、{term}の定義（{short_def}）、条文上の根拠、試験で問われやすいポイント、"
        f"よくある誤解、記憶のコツ、例題、FAQ までを丁寧に整理します。過去問・実践演習・"
        f"一問一答と組み合わせて、確実に得点源にしましょう。"
    )


def make_explanation(term: str, category: str) -> str:
    return (
        f"{term}は、運行管理者試験（貨物）の{category}でよく問われる用語です。"
        f"四択や○×では、定義の言い換え、主体（誰が）、期限（いつまでに）、"
        f"例外規定の有無が選択肢のすり替えに使われやすいので、本文の「定義」「条文上の根拠」"
        f"「試験で問われやすいポイント」を順に押さえ、関連用語と合わせて理解してください。"
    )


def _ensure_min(text: str, min_len: int, pad: str) -> str:
    text = (text or "").strip()
    if len(text) >= min_len:
        return text
    if text and not text.endswith("。"):
        text += "。"
    while len(text) < min_len:
        text += pad
    return text


def _normalize_exam_points(exam_points: str, term: str) -> str:
    items = [p.strip() for p in (exam_points or "").split(";") if p.strip()]
    normed: list[str] = []
    for item in items:
        if len(item) < 8:
            item = _ensure_min(item, 8, f"（{term}の試験論点）")
        normed.append(item)
    while len(normed) < 2:
        fallback = f"{term}の定義と条文上の位置づけ"
        if len(fallback) < 8:
            fallback = _ensure_min(fallback, 8, "を確認")
        normed.append(fallback)
    return ";".join(normed)


def _normalize_example_question(question: str, term: str) -> str:
    return _ensure_min(
        question,
        12,
        f"（{term}の試験例題）",
    )


def _normalize_example_answer(answer: str) -> str:
    a = (answer or "").strip()
    if a in {"×", "✕", "╳"}:
        return "×（誤り）"
    if a in {"○", "〇"}:
        return "○（正しい）"
    if len(a) < 3:
        return _ensure_min(a or "正しい", 3, "（解説）")
    return a


def _normalize_short_def(short_def: str, term: str) -> str:
    text = (short_def or "").strip()
    if len(text) >= 12 and "運行管理者試験（貨物）で押さえる" not in text:
        return text if text.endswith("。") else f"{text}。"
    return _ensure_min(
        short_def,
        12,
        f"{term}の意味と試験での押さえ方。",
    )


def _normalize_definition(definition: str, term: str, category: str) -> str:
    text = (definition or "").strip()
    tail = f"{term}は「{category}」の重要論点として、条文・告示・実務のいずれかで位置づけられる。"
    if len(text) >= 50 and tail not in text:
        return text if text.endswith("。") else f"{text}。"
    if text and tail not in text:
        pad = tail
        if not text.endswith("。"):
            text += "。"
        combined = text + pad
        if len(combined) >= 50:
            return combined
    return _ensure_min(definition, 50, tail)


def _normalize_common_mistakes(common_mistakes: str, term: str) -> str:
    return _ensure_min(
        common_mistakes,
        40,
        f"類似用語との混同や、{term}の主体・期限・届出要否の取り違えに注意。",
    )


def _normalize_memory_tip(memory_tip: str, term: str) -> str:
    return _ensure_min(
        memory_tip,
        25,
        f"過去問・実践演習で{term}の正誤を繰り返し確認する。",
    )


def _normalize_faq_answer(answer: str, term: str) -> str:
    return _ensure_min(
        answer,
        100,
        f" 本文と関連用語を合わせて{term}の理解を固め、同分野の過去問・実践演習・一問一答で定着させてください。",
    )


def make_term_detail_body(
    term: str,
    category: str,
    definition: str,
    legal_basis: str,
    exam_points: str,
    common_mistakes: str,
    memory_tip: str,
) -> str:
    points_list = [p.strip() for p in (exam_points or "").split(";") if p.strip()]
    bullets = "".join(f"・{p}\n" for p in points_list) if points_list else ""
    legal = legal_basis or "本用語に固有の単独条文は無く、関連法令の総則・施行規則・告示で位置づけられます。"
    return (
        f"定義\n{definition}\n\n"
        f"条文上の根拠\n{legal}\n\n"
        f"試験で問われやすいポイント\n{bullets}\n"
        f"よくある誤解\n{common_mistakes}\n\n"
        f"記憶のコツ\n{memory_tip}\n\n"
        f"関連分野\n本用語は「{category}」の中核論点に位置づけられます。"
        f"類似用語との対比を意識し、過去問・実践演習・一問一答で繰り返し確認してください。"
    )


def make_faqs(term: str, category: str, short_def: str, exam_points: str) -> list[tuple[str, str]]:
    points_list = [p.strip() for p in (exam_points or "").split(";") if p.strip()]
    p0 = points_list[0] if len(points_list) >= 1 else "定義と主体・期限・例外規定"
    p1 = points_list[1] if len(points_list) >= 2 else "条文上の数値や用語の言い換え"
    return [
        (
            f"{term}とは何ですか？",
            f"{term}は、{short_def} 運行管理者試験では「{category}」の重要用語として、"
            "定義の言い換えや関連条文との関係が選択肢で問われます。本文の「定義」と「条文上の根拠」を最初に確認してください。",
        ),
        (
            f"{term}でよくある誤解は？",
            f"類似用語との混同や、「届出／許可」「あらかじめ／遅滞なく」「主体（事業者／運行管理者／運転者）」"
            "の取り違えが典型的な誤りです。本文の「よくある誤解」と例題で、どこで間違えやすいかを確認してください。"
            "過去問では、似た用語を並べた選択肢で差がつきやすいので、定義の一言メモを作っておくと得点源になります。",
        ),
        (
            f"{term}は試験でどう問われますか？",
            f"四択・○×のいずれでも、選択肢中の「{p0}」「{p1}」が判断の決め手になりやすいです。"
            "本文の「試験で問われやすいポイント」を一読し、過去問・実践演習で同分野の問題を解いて理解を固めてください。",
        ),
        (
            f"{term}を学んだあとに確認すべきことは？",
            "関連用語の定義を 2 件以上読み比べ、同分野の過去問・実践演習・一問一答を解いてください。"
            "迷った問題は復習にブックマークし、数日後に解き直すと記憶が定着します。"
            "条文番号と数値（期限・保存年数・人数等）を自分の言葉で言えるかも、最終確認のチェック項目に入れてください。",
        ),
    ]


def expand_term(seed: dict) -> dict:
    """最小フィールドから 25 カラムの完全レコードを派生生成する。"""
    term = seed["term"]
    category = seed["category"]
    short_def = _normalize_short_def(seed.get("short_def", ""), term)
    definition = _normalize_definition(seed.get("definition", ""), term, category)
    legal_basis = seed.get("legal_basis", "")
    exam_points = _normalize_exam_points(seed.get("exam_points", ""), term)
    common_mistakes = _normalize_common_mistakes(seed.get("common_mistakes", ""), term)
    memory_tip = _normalize_memory_tip(seed.get("memory_tip", ""), term)
    related_terms = seed.get("related_terms", "")
    importance = seed.get("importance", "A")
    tags = seed.get("tags", "")
    example_answer = _normalize_example_answer(seed.get("example_answer", ""))
    example_question = _normalize_example_question(seed.get("example_question", ""), term)

    faqs = make_faqs(term, category, short_def, exam_points)
    faqs = [(q, _normalize_faq_answer(a, term)) for q, a in faqs]

    row = {
        "term": term,
        "category": category,
        "tags": tags,
        "short_def": short_def,
        "definition": definition,
        "related_terms": related_terms,
        "legal_basis": legal_basis,
        "importance": importance,
        "explanation": make_explanation(term, category),
        "article_title": make_article_title(term, category),
        "article_lead": make_article_lead(term, short_def, category),
        "term_detail_body": make_term_detail_body(
            term, category, definition, legal_basis, exam_points,
            common_mistakes, memory_tip,
        ),
        "exam_points": exam_points,
        "common_mistakes": common_mistakes,
        "memory_tip": memory_tip,
        "example_question": example_question,
        "example_answer": example_answer,
        "faq_1_question": faqs[0][0],
        "faq_1_answer": faqs[0][1],
        "faq_2_question": faqs[1][0],
        "faq_2_answer": faqs[1][1],
        "faq_3_question": faqs[2][0],
        "faq_3_answer": faqs[2][1],
        "faq_4_question": faqs[3][0],
        "faq_4_answer": faqs[3][1],
    }
    return row


def main() -> int:
    import subprocess
    import sys
    script = ROOT / "tools" / "generate_glossary_step1.py"
    return subprocess.call([sys.executable, str(script)])


if __name__ == "__main__":
    raise SystemExit(main())
