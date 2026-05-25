#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scaffold a new glossary term row for data/glossary_terms.csv."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.glossary_term_rules import GLOSSARY_BASE_REQUIRED  # noqa: E402
from tools.site_config import category_order, exam_name  # noqa: E402

GLOSSARY_CSV = ROOT / "data" / "glossary_terms.csv"
TEMPLATE_CSV = ROOT / "data" / "templates" / "glossary_term_row.template.csv"

BODY_PLACEHOLDER = (
    "【本文を記入】{term}の定義と試験での位置づけを、対象資格の公式情報・演習解説に沿って整理します。"
    "120文字以上。数値・期限・主体（誰が・いつ・何を）を具体的に書いてください。"
)
LEAD_PLACEHOLDER = (
    "【リードを記入】{term}は{exam}で押さえたい用語です。"
    "この記事では意味・試験での見方・混同しやすい点を整理します。"
)
EXPL_PLACEHOLDER = (
    "【選択肢の論点を記入】{term}が出る問題では、定義の言い換え・例外・似た用語との違いが問われやすいです。"
    "演習で見た誤答パターンを1〜2点書いてください。"
)


def load_fieldnames() -> list[str]:
    if GLOSSARY_CSV.is_file():
        with GLOSSARY_CSV.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                return list(reader.fieldnames)
    return sorted(GLOSSARY_BASE_REQUIRED)


def existing_terms() -> set[str]:
    if not GLOSSARY_CSV.is_file():
        return set()
    with GLOSSARY_CSV.open(encoding="utf-8-sig", newline="") as f:
        return {row.get("term", "").strip() for row in csv.DictReader(f) if row.get("term", "").strip()}


def build_row(
    term: str,
    category: str,
    *,
    related: str = "",
    importance: str = "B",
    tags: str = "用語",
) -> dict[str, str]:
    exam = exam_name()
    related_val = related or "過去問;用語解説"
    row: dict[str, str] = {col: "" for col in load_fieldnames()}
    row.update(
        {
            "term": term,
            "category": category,
            "tags": tags,
            "short_def": f"【短い定義】{term}の要点を1文で。",
            "definition": f"【定義】{term}の意味と試験での位置づけを2〜3文で。",
            "related_terms": related_val,
            "legal_basis": "",
            "importance": importance,
            "explanation": EXPL_PLACEHOLDER.format(term=term),
            "article_title": f"{term}とは？意味・試験ポイント",
            "article_lead": LEAD_PLACEHOLDER.format(term=term, exam=exam),
            "term_detail_body": BODY_PLACEHOLDER.format(term=term),
            "exam_points": "試験で問われる条件を確認する;似た用語との違いを整理する",
            "common_mistakes": f"【誤解】{term}について受験者が混同しやすい点を1〜2文で。",
            "memory_tip": f"【覚え方】{term}を関連語とセットで覚えるコツを1文で。",
            "example_question": f"【例題】{term}に関する正誤または空欄問題を1文で。",
            "example_answer": "×。【解説を記入】",
            "faq_1_question": f"{term}は何ですか？",
            "faq_1_answer": (
                f"（100字以上で記入）{term}の定義と、{exam}での位置づけを平易に説明します。"
                "選択肢の言い換えに備え、キーワードと条件を短く整理してください。"
            ),
            "faq_2_question": f"{term}でよくある誤解は？",
            "faq_2_answer": (
                "（100字以上で記入）受験者が混同しやすい点と、過去問で出やすい誤答パターンを"
                "具体例付きで説明してください。似た用語がある場合は違いも一言で補足します。"
            ),
            "faq_3_question": f"{term}は試験でどう問われますか？",
            "faq_3_answer": (
                "（100字以上で記入）四択で問われやすい条件・数値・例外・主体を整理してください。"
                "演習解説で正解と誤答の根拠を比較する観点を書きます。"
            ),
            "faq_4_question": f"{term}を学んだあとに何を確認しますか？",
            "faq_4_answer": (
                "（100字以上で記入）関連用語・該当する過去問・公式要項のどれを見るか、"
                "次の学習行動を具体的に示してください。"
            ),
        }
    )
    return row


def write_template_csv() -> None:
    TEMPLATE_CSV.parent.mkdir(parents=True, exist_ok=True)
    row = build_row("用語名", category_order()[0] if category_order() else "法令・制度")
    row["term"] = "用語名"
    with TEMPLATE_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=load_fieldnames(), lineterminator="\n")
        writer.writeheader()
        writer.writerow(row)


def append_row(row: dict[str, str]) -> None:
    terms = existing_terms()
    term = row["term"]
    if term in terms:
        raise ValueError(f"term が既に存在します: {term}")
    with GLOSSARY_CSV.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=load_fieldnames(), lineterminator="\n")
        writer.writerow(row)


def print_row(row: dict[str, str]) -> None:
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=load_fieldnames(), lineterminator="\n")
    writer.writeheader()
    writer.writerow(row)
    print(buf.getvalue(), end="")


def main() -> int:
    parser = argparse.ArgumentParser(description="用語詳細記事の CSV 行テンプレートを生成します。")
    parser.add_argument("--term", help="用語名（CSV の term 列）")
    parser.add_argument("--category", help="分野名（site-config の fields / category）")
    parser.add_argument("--related", help="related_terms（セミコロン区切り、2件以上）")
    parser.add_argument("--importance", default="B", help="A / B / C / S（既定: B）")
    parser.add_argument("--tags", default="用語", help="tags（セミコロン区切り）")
    parser.add_argument("--append", action="store_true", help="data/glossary_terms.csv の末尾に追記")
    parser.add_argument("--write-template-csv", action="store_true", help="data/templates/glossary_term_row.template.csv を更新")
    parser.add_argument("--list-categories", action="store_true", help="利用可能な category 一覧")
    args = parser.parse_args()

    if args.list_categories:
        for cat in category_order():
            print(cat)
        return 0

    if args.write_template_csv:
        write_template_csv()
        print(f"Wrote {TEMPLATE_CSV}")
        return 0

    if not args.term or not args.category:
        parser.error("--term と --category が必要です（--list-categories / --write-template-csv は別）")

    row = build_row(
        args.term,
        args.category,
        related=args.related or "",
        importance=args.importance,
        tags=args.tags,
    )
    if args.append:
        append_row(row)
        print(f"Appended term={args.term!r} category={args.category!r} to {GLOSSARY_CSV}")
        print("Next: プレースホルダを差し替え → python3 tools/validate_csv.py → python3 tools/build_all.py")
    else:
        print_row(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
