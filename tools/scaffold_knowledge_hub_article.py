#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scaffold a row for comparisons.csv / numbers.csv / mistakes.csv."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.site_config import category_order, exam_name  # noqa: E402

HUB_TYPES = {
    "compare": {
        "csv": ROOT / "data" / "comparisons.csv",
        "template": ROOT / "data" / "templates" / "compare_row.template.csv",
        "label": "比較・整理表",
    },
    "numbers": {
        "csv": ROOT / "data" / "numbers.csv",
        "template": ROOT / "data" / "templates" / "numbers_row.template.csv",
        "label": "数値・期限早見表",
    },
    "mistakes": {
        "csv": ROOT / "data" / "mistakes.csv",
        "template": ROOT / "data" / "templates" / "mistakes_row.template.csv",
        "label": "よくある誤答",
    },
}


def load_fieldnames(hub_type: str) -> list[str]:
    path = HUB_TYPES[hub_type]["csv"]
    if path.is_file():
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                return list(reader.fieldnames)
    raise ValueError(f"CSV not found or empty header: {path}")


def existing_titles(hub_type: str) -> set[str]:
    path = HUB_TYPES[hub_type]["csv"]
    if not path.is_file():
        return set()
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {row.get("title", "").strip() for row in csv.DictReader(f) if row.get("title", "").strip()}


def build_compare_row(title: str, category: str, *, subject_a: str, subject_b: str) -> dict[str, str]:
    exam = exam_name()
    compare_rows = [
        {"axis": "定義", "cols": [f"【{subject_a}の定義】", f"【{subject_b}の定義】"]},
        {"axis": "主な違い", "cols": ["【記入】", "【記入】"]},
        {"axis": "試験での見方", "cols": ["【記入】", "【記入】"]},
        {"axis": "覚え方", "cols": ["【記入】", "【記入】"]},
    ]
    return {
        "slug": "",
        "title": title,
        "category": category,
        "tags": "整理;用語",
        "summary": f"【1文】{subject_a}と{subject_b}の違いを表で整理します。",
        "col_labels": f"{subject_a};{subject_b}",
        "compare_rows": json.dumps(compare_rows, ensure_ascii=False),
        "article_title": f"{title}｜{exam}向け比較",
        "article_lead": (
            f"【リード】{subject_a}と{subject_b}は試験で混同されやすい組み合わせです。"
            "定義だけでなく、使い分けと引っかけポイントを表で確認してください。"
        ),
        "exam_points": "選択肢の言い換えに注意する;数値・期限・主体をセットで確認する",
        "common_mistakes": f"【誤解】{subject_a}と{subject_b}を同じ制度だと思い込むと誤答になりやすいです。",
        "memory_tip": f"【覚え方】{subject_a}と{subject_b}の役割を短いフレーズで対比してください。",
        "related_terms": f"{subject_a};{subject_b}",
        "faq_1_question": f"{subject_a}と{subject_b}の違いは？",
        "faq_1_answer": (
            f"（100字以上）{subject_a}と{subject_b}の定義と、{exam}での位置づけを平易に説明します。"
            "表の「定義」行をベースに、選択肢で問われやすい条件も補足してください。"
        ),
        "faq_2_question": "どちらから覚えるべき？",
        "faq_2_answer": (
            "（100字以上）初見の語は用語解説で意味を確認し、混同しやすい組み合わせは比較表で差分を整理する流れが効率的です。"
        ),
        "faq_3_question": "試験でどう問われますか？",
        "faq_3_answer": (
            "（100字以上）定義の言い換え、数値・期限、主体（誰が・いつ）の取り違えが四択で出やすいです。"
            "過去問の誤答肢をこの表に追加すると復習に使えます。"
        ),
        "faq_4_question": "関連用語はどこで確認？",
        "faq_4_answer": (
            "（100字以上）各項目の用語解説ページと、この比較表をあわせて読むと理解が定着しやすくなります。"
            "演習で間違えた問題も解き直してください。"
        ),
    }


def build_numbers_row(title: str, category: str) -> dict[str, str]:
    exam = exam_name()
    item_rows = [
        {"item": "【項目1】", "value": "【数値・期限】", "note": "【補足・条文】"},
        {"item": "【項目2】", "value": "【数値・期限】", "note": "【補足・条文】"},
        {"item": "【項目3】", "value": "【数値・期限】", "note": "【補足・条文】"},
    ]
    return {
        "slug": "",
        "title": title,
        "category": category,
        "tags": "数字;期限",
        "summary": f"【1文】{title}に関する代表的な数値・期限を早見表に整理します。",
        "highlight": "【代表値1】 / 【代表値2】",
        "item_rows": json.dumps(item_rows, ensure_ascii=False),
        "article_title": f"{title}｜数値早見表",
        "article_lead": (
            f"【リード】{exam}で問われる数字・日数・割合を一覧で確認できます。"
            "暗記だけでなく、用語解説とあわせて条件まで押さえてください。"
        ),
        "exam_points": "数字と条件（誰が・いつ）をセットで覚える;公式テキストで最新値を確認する",
        "common_mistakes": "【誤解】似た数字を入れ替えて覚えると一問失点しやすいです。",
        "memory_tip": "【覚え方】短いフレーズ（例: 前8後5）で順序付きに覚えます。",
        "related_terms": "用語1;用語2",
        "faq_1_question": f"{title}の代表的な数字は？",
        "faq_1_answer": (
            "（100字以上）早見表の「数値・期限」列を参照してください。"
            "資格・年度によって異なる場合は試験要項等の公式情報で必ず確認します。"
        ),
        "faq_2_question": "一覧表の使い方は？",
        "faq_2_answer": (
            "（100字以上）学習中の確認と直前の総復習向けです。"
            "各項目の用語解説で根拠条文まで深掘りしてください。"
        ),
        "faq_3_question": "試験でどう問われますか？",
        "faq_3_answer": (
            "（100字以上）数値そのものの暗記、条件の追加（例外・主体）、近い数字との選択が典型です。"
        ),
        "faq_4_question": "数字は暗記だけで足りる？",
        "faq_4_answer": (
            "（100字以上）演習で肢を確認し、公式テキストで裏取りしてください。"
            "誤答パターン記事とセットで読むと定着しやすくなります。"
        ),
    }


def build_mistakes_row(title: str, category: str) -> dict[str, str]:
    exam = exam_name()
    pattern_rows = [
        {
            "topic": "【論点1】",
            "wrong": "【誤答例・引っかけ肢】",
            "correct": "【正解の整理】",
            "trap": "【引っかけポイント】",
        },
        {
            "topic": "【論点2】",
            "wrong": "【誤答例】",
            "correct": "【正解の整理】",
            "trap": "【引っかけポイント】",
        },
    ]
    return {
        "slug": "",
        "title": title,
        "category": category,
        "tags": "誤答;整理",
        "summary": f"【1文】{title}に関する典型の誤答パターンを整理します。",
        "confusion_point": "【混同しやすい点を一言】",
        "pattern_rows": json.dumps(pattern_rows, ensure_ascii=False),
        "article_title": f"{title}｜誤答パターン",
        "article_lead": (
            f"【リード】{exam}の過去問で繰り返し出る引っかけ肢を、誤答例と正解の対比で整理します。"
        ),
        "exam_points": "誤肢の言い換えに慣れる;正解の根拠を一文で言えるようにする",
        "common_mistakes": "【誤解】正しいように見える肢を選んでしまうパターンです。",
        "memory_tip": "【覚え方】誤答例を声に出してから正解と置き換えると記憶に残りやすいです。",
        "related_terms": "用語1;用語2",
        "faq_1_question": f"{title}の典型誤答は？",
        "faq_1_answer": (
            "（100字以上）表の「誤答例」列を参照してください。"
            "自分が過去問で間違えた肢があれば追記して復習に使えます。"
        ),
        "faq_2_question": "比較表との違いは？",
        "faq_2_answer": (
            "（100字以上）比較表は制度の差分整理、誤答パターンは肢の引っかけに焦点を当てます。"
            "両方あわせて読むと理解が定着しやすくなります。"
        ),
        "faq_3_question": "試験対策でどう使う？",
        "faq_3_answer": (
            "（100字以上）過去問演習の前後に読み、間違えた問題の理由と照合してください。"
        ),
        "faq_4_question": "関連用語は？",
        "faq_4_answer": (
            "（100字以上）ページ下部の関連用語リンクから用語解説へ進み、"
            "定義と数字を確認してから解き直してください。"
        ),
    }


def build_row(hub_type: str, title: str, category: str, **kwargs: str) -> dict[str, str]:
    if hub_type == "compare":
        return build_compare_row(
            title,
            category,
            subject_a=kwargs.get("subject_a") or "項目A",
            subject_b=kwargs.get("subject_b") or "項目B",
        )
    if hub_type == "numbers":
        return build_numbers_row(title, category)
    if hub_type == "mistakes":
        return build_mistakes_row(title, category)
    raise ValueError(f"unknown type: {hub_type}")


def write_template_csv(hub_type: str) -> None:
    path = HUB_TYPES[hub_type]["template"]
    path.parent.mkdir(parents=True, exist_ok=True)
    cat = category_order()[0] if category_order() else "法令・制度"
    if hub_type == "compare":
        row = build_compare_row("項目Aと項目Bの違い", cat, subject_a="項目A", subject_b="項目B")
    elif hub_type == "numbers":
        row = build_numbers_row("【早見表タイトル】数値・期限一覧", cat)
    else:
        row = build_mistakes_row("【パターン名】の取り違え", cat)
    fieldnames = load_fieldnames(hub_type)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in fieldnames})


def append_row(hub_type: str, row: dict[str, str]) -> None:
    path = HUB_TYPES[hub_type]["csv"]
    title = row["title"]
    if title in existing_titles(hub_type):
        raise ValueError(f"title already exists in {path.name}: {title!r}")
    fieldnames = load_fieldnames(hub_type)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.is_file() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in fieldnames})


def print_row(row: dict[str, str], fieldnames: list[str]) -> None:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writerow({k: row.get(k, "") for k in fieldnames})
    sys.stdout.write(buf.getvalue())


def main() -> int:
    ap = argparse.ArgumentParser(description="Scaffold knowledge hub CSV rows (compare / numbers / mistakes)")
    ap.add_argument("--type", choices=sorted(HUB_TYPES), help="Hub content type")
    ap.add_argument("--title", help="Article title (compare/numbers/mistakes)")
    ap.add_argument("--category", help="Category label (must match site-config fields)")
    ap.add_argument("--subject-a", help="Compare: first column label")
    ap.add_argument("--subject-b", help="Compare: second column label")
    ap.add_argument("--append", action="store_true", help="Append to CSV")
    ap.add_argument("--list-types", action="store_true", help="List hub types")
    ap.add_argument("--list-categories", action="store_true", help="List categories from site-config")
    ap.add_argument("--write-template-csv", action="store_true", help="Refresh data/templates/*_row.template.csv")
    args = ap.parse_args()

    if args.list_types:
        for key, meta in HUB_TYPES.items():
            print(f"{key}\t{meta['label']}\t{meta['csv'].relative_to(ROOT)}")
        return 0

    if args.list_categories:
        for cat in category_order():
            print(cat)
        return 0

    if args.write_template_csv:
        for hub_type in HUB_TYPES:
            write_template_csv(hub_type)
            print(f"Wrote {HUB_TYPES[hub_type]['template']}")
        return 0

    if not args.type or not args.title:
        ap.error("--type and --title are required (or use --list-types / --write-template-csv)")

    category = args.category or (category_order()[0] if category_order() else "法令・制度")
    row = build_row(
        args.type,
        args.title.strip(),
        category.strip(),
        subject_a=(args.subject_a or "").strip(),
        subject_b=(args.subject_b or "").strip(),
    )
    fieldnames = load_fieldnames(args.type)

    if args.append:
        append_row(args.type, row)
        print(f"Appended to {HUB_TYPES[args.type]['csv']}: {args.title}")
    else:
        print_row(row, fieldnames)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
