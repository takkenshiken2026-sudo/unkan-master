#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配置ずれの自動修正（試験ガイド ↔ 用語解説）。

  # 監査のみ
  python3 tools/fix_content_placement.py --audit

  # 重複ガイドを用語解説への橋渡し記事に変換（ドライラン）
  python3 tools/fix_content_placement.py --bridge-duplicates --dry-run

  # 本適用
  python3 tools/fix_content_placement.py --bridge-duplicates --confidence high
  python3 tools/fix_content_placement.py --clear-glossary-misplaced --dry-run
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.content_placement_rules import (  # noqa: E402
    audit_glossary_rows,
    audit_guide_rows,
    glossary_href,
    glossary_index,
    is_published_guide,
    load_hub_rows,
    match_glossary,
    norm,
)

GUIDE_CSV = ROOT / "data" / "guide_articles.csv"
GLOSSARY_CSV = ROOT / "data" / "glossary_terms.csv"

from tools.migrate_guide_to_hub import (  # noqa: E402
    migrate_compare_guides,
    migrate_numbers_guides,
)

BRIDGE_GENRE = "用語ハブ活用法"
BRIDGE_NOTE = "配置整理: 定義本文は用語解説へ集約。本記事は導線用"
COMPARE_CSV = ROOT / "data" / "comparisons.csv"
NUMBERS_CSV = ROOT / "data" / "numbers.csv"


def load_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        return fields, list(reader)


def save_rows(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    # CSV 列の揺れ（faq 列順など）を吸収
    all_keys: list[str] = list(fields)
    for row in rows:
        for key in row:
            if key not in all_keys:
                all_keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def bridge_guide_row(
    row: dict[str, str],
    gloss: dict[str, str],
    *,
    exam_label: str,
) -> dict[str, str]:
    term = norm(gloss.get("term"))
    href = glossary_href(gloss)
    title = norm(row.get("title"))
    short_title = term or title_term_short(title)

    row = dict(row)
    row["genre"] = BRIDGE_GENRE
    row["revision_note"] = BRIDGE_NOTE
    row["lead"] = (
        f"「{short_title}」の定義・試験論点・よくある誤解は **用語解説（知識ハブ）** に集約しています。"
        f"本ページでは、用語を確認したあと試験ガイドと演習へ進む流れだけを案内します。"
    )
    row["user_intent"] = (
        f"{short_title}の意味を試験対策用に押さえ、関連する過去問・学習計画へつなげたい読者向け。"
        f"定義の詳細は用語解説ページを正本とします。"
    )
    row["action_items"] = (
        f"用語解説で{short_title}の定義と試験ポイントを読む;"
        f"関連用語を2件以上たどって混同を解消する;"
        f"過去問演習で4択の言い換えに慣れる;"
        f"学習計画・分野別対策のガイドで次の行動を決める"
    )
    row["section_1_heading"] = "用語解説で確認する内容"
    row["section_1_body"] = (
        f"{exam_label}では、{short_title}は定義・要件・試験での引っかけがセットで問われます。"
        f"長文の定義やFAQは <a href=\"{href}\">用語解説「{term}」</a> にまとめています。"
        f"試験ガイド本文に同じ定義を繰り返さないのが、このサイトの配置ルールです。"
    )
    row["section_2_heading"] = "試験ガイドとの使い分け"
    row["section_2_body"] = (
        f"用語解説は「{short_title}**とは何か**」を答える場所です。"
        f"一方、勉強の進め方・申込・直前対策・再受験は <a href=\"/articles/index.html\">試験ガイド</a> 側で扱います。"
        f"定義を読んだら、弱点分野のガイドか過去問演習へ進んでください。"
    )
    row["section_3_heading"] = "おすすめの学習順"
    row["section_3_body"] = (
        f"① <a href=\"{href}\">用語解説</a> で定義と誤答パターンを確認。"
        f"② 関連用語リンクから混同語を1周。"
        f"③ 過去問で該当分野を解き、間違えた選択肢を用語解説で照合。"
        f"④ 必要なら学習計画・分野別対策ガイドで復習サイクルを組みます。"
    )
    for n in range(4, 8):
        row[f"section_{n}_heading"] = ""
        row[f"section_{n}_body"] = ""

    row["faq_1_question"] = f"{short_title}の意味はどこで詳しく読めますか？"
    row["faq_1_answer"] = (
        f"<a href=\"{href}\">用語解説「{term}」</a> が正本です。"
        f"定義・試験論点・FAQ・例題を1ページにまとめています。"
        f"試験ガイド側には同じ本文を載せないため、リンクから知識ハブへ移動してください。"
    )
    row["faq_2_question"] = "用語を読んだあと何をすればよいですか？"
    row["faq_2_answer"] = (
        f"関連用語を2件以上確認したうえで、過去問演習に進むのが基本です。"
        f"学習全体の設計は試験ガイドの「学習計画」「分野別対策」を参照してください。"
        f"直前・再受験の悩みは注意点・更新ジャンルの記事が該当します。"
    )
    row["faq_3_question"] = "試験ガイドと用語解説の違いは？"
    row["faq_3_answer"] = (
        f"用語解説は知識（What）、試験ガイドは進め方（How/When）です。"
        f"{short_title} のような用語の意味は用語解説、"
        f"勉強スケジュールや申込手続きは試験ガイドに置きます。"
    )
    row["faq_4_question"] = f"{short_title}と混同しやすい用語は？"
    row["faq_4_answer"] = (
        f"用語解説ページ内の related_terms と比較表タブを参照してください。"
        f"似た語を別ページで定義し直さず、リンクで行き来するのが効率的です。"
    )
    return row


def title_term_short(title: str) -> str:
    import re

    t = re.sub(r"^【[^】]+】", "", title)
    t = re.sub(r"^[^｜\|]+[｜\|]", "", t)
    t = re.split(r"とは[？?]?", t)[0].strip()
    return t or title[:30]


def cmd_bridge_duplicates(
    *,
    dry_run: bool,
    confidence: str,
    exam_label: str,
) -> int:
    if not GUIDE_CSV.is_file():
        print(f"missing {GUIDE_CSV}", file=sys.stderr)
        return 1

    fields, rows = load_rows(GUIDE_CSV)
    glossary = list(csv.DictReader(GLOSSARY_CSV.open(encoding="utf-8-sig"))) if GLOSSARY_CSV.is_file() else []
    by_slug, by_term = glossary_index(glossary)
    _ = by_term

    changed = 0
    for i, row in enumerate(rows):
        if not is_published_guide(row):
            continue
        matched = match_glossary(row, by_slug, by_term)
        if not matched:
            continue
        kind, gloss = matched
        conf = "high" if kind in {"slug", "term_exact", "term_prefix", "term_contains", "slug_related"} else "medium"
        if confidence == "high" and conf != "high":
            continue

        slug = norm(row.get("slug"))
        new_row = bridge_guide_row(row, gloss, exam_label=exam_label)
        print(f"bridge {slug} -> {glossary_href(gloss)} ({conf})")
        if not dry_run:
            rows[i] = new_row
        changed += 1

    if changed and not dry_run:
        save_rows(GUIDE_CSV, fields, rows)
        print(f"Updated {changed} guide rows in {GUIDE_CSV}")
    elif dry_run:
        print(f"dry-run: would update {changed} rows")
    else:
        print("No rows to update")
    return 0


def cmd_draft_duplicates(*, dry_run: bool, confidence: str) -> int:
    fields, rows = load_rows(GUIDE_CSV)
    glossary = list(csv.DictReader(GLOSSARY_CSV.open(encoding="utf-8-sig"))) if GLOSSARY_CSV.is_file() else []
    by_slug, by_term = glossary_index(glossary)

    changed = 0
    for i, row in enumerate(rows):
        if not is_published_guide(row):
            continue
        matched = match_glossary(row, by_slug, by_term)
        if not matched:
            continue
        kind, _gloss = matched
        conf = "high" if kind in {"slug", "term_exact", "term_prefix", "term_contains", "slug_related"} else "medium"
        if confidence == "high" and conf != "high":
            continue
        slug = norm(row.get("slug"))
        print(f"draft {slug} ({conf})")
        if not dry_run:
            rows[i]["content_status"] = "draft"
            rows[i]["revision_note"] = BRIDGE_NOTE + "（draft）"
        changed += 1

    if changed and not dry_run:
        save_rows(GUIDE_CSV, fields, rows)
        print(f"Drafted {changed} rows")
    else:
        print(f"dry-run: would draft {changed} rows" if dry_run else "No rows")
    return 0


def cmd_clear_glossary_misplaced(*, dry_run: bool) -> int:
    if not GLOSSARY_CSV.is_file():
        return 0
    fields, rows = load_rows(GLOSSARY_CSV)
    guides = list(csv.DictReader(GUIDE_CSV.open(encoding="utf-8-sig"))) if GUIDE_CSV.is_file() else []
    findings = {f.slug: f for f in audit_glossary_rows(rows, guides) if f.kind == "glossary_should_be_guide"}

    changed = 0
    kept: list[dict[str, str]] = []
    for row in rows:
        term = norm(row.get("term"))
        slug = norm(row.get("url_slug")) or norm(row.get("slug")) or term
        if slug in findings or term in findings:
            print(f"remove glossary misplaced: {term!r}")
            if not dry_run:
                changed += 1
                continue
            changed += 1
        kept.append(row)

    if changed and not dry_run:
        save_rows(GLOSSARY_CSV, fields, kept)
        print(f"Removed {changed} glossary rows")
    elif dry_run:
        print(f"dry-run: would clear {changed} rows")
    return 0


def cmd_migrate_to_hub(*, dry_run: bool, exam_label: str) -> int:
    if not GUIDE_CSV.is_file():
        return 1
    fields, rows = load_rows(GUIDE_CSV)
    c_changed = n_changed = 0
    if not dry_run:
        rows, c_changed = migrate_compare_guides(rows, COMPARE_CSV, exam_label=exam_label)
        rows, n_changed = migrate_numbers_guides(rows, NUMBERS_CSV, exam_label=exam_label)
        save_rows(GUIDE_CSV, fields, rows)
    print(f"migrated compare={c_changed} numbers={n_changed}")
    return 0


def cmd_audit() -> int:
    guides = list(csv.DictReader(GUIDE_CSV.open(encoding="utf-8-sig"))) if GUIDE_CSV.is_file() else []
    glossary = list(csv.DictReader(GLOSSARY_CSV.open(encoding="utf-8-sig"))) if GLOSSARY_CSV.is_file() else []
    hub = load_hub_rows(ROOT)
    n = 0
    for item in audit_guide_rows(guides, glossary, hub):
        print(f"{item.level}\t{item.kind}\t{item.slug}\t{item.confidence}\t{item.message}")
        n += 1
    for item in audit_glossary_rows(glossary, guides):
        print(f"{item.level}\t{item.kind}\t{item.slug}\t{item.confidence}\t{item.message}")
        n += 1
    print(f"total {n}", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix guide vs glossary content placement")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--bridge-duplicates", action="store_true")
    parser.add_argument("--draft-duplicates", action="store_true")
    parser.add_argument("--clear-glossary-misplaced", action="store_true")
    parser.add_argument("--migrate-to-hub", action="store_true", help="Move compare/numbers guides to hub CSV")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--confidence",
        choices=("high", "medium", "all"),
        default="high",
        help="auto-fix threshold (default: high = slug or exact term match only)",
    )
    parser.add_argument(
        "--exam-label",
        default="対象試験",
        help="Exam name inserted into bridge copy",
    )
    args = parser.parse_args()

    if args.audit:
        return cmd_audit()
    if args.bridge_duplicates:
        return cmd_bridge_duplicates(
            dry_run=args.dry_run,
            confidence=args.confidence,
            exam_label=args.exam_label,
        )
    if args.draft_duplicates:
        return cmd_draft_duplicates(dry_run=args.dry_run, confidence=args.confidence)
    if args.clear_glossary_misplaced:
        return cmd_clear_glossary_misplaced(dry_run=args.dry_run)
    if args.migrate_to_hub:
        return cmd_migrate_to_hub(dry_run=args.dry_run, exam_label=args.exam_label)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
