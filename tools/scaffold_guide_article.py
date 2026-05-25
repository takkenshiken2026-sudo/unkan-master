#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scaffold a new guide article row for data/guide_articles.csv."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.site_config import brand_name, exam_name, guide_article_genres, guide_genre_labels  # noqa: E402

ARTICLES_CSV = ROOT / "data" / "guide_articles.csv"
TEMPLATE_CSV = ROOT / "data" / "templates" / "guide_article_row.template.csv"

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

BODY_PLACEHOLDER = (
    "【本文を記入】◯◯試験の{topic}について、公式情報を確認したうえで整理します。"
    "受験者が迷いやすい点を具体的に説明し、必要に応じてこのサイトの過去問・用語解説への導線を入れてください。"
    "数値・日程・制度名は対象資格の最新情報に差し替えてください。"
)

# ジャンルごとの見出し案（12区分。docs/guide-article-template.md も参照）
GENRE_OUTLINES: dict[str, dict[str, object]] = {
    "試験概要": {
        "title": "◯◯試験の概要と最初に確認するポイント",
        "meta": "◯◯試験の概要、公式情報の確認方法、学習前に押さえる基本事項を整理します。",
        "lead": "◯◯試験の受験を検討し始めた人向けに、最初に確認すべき情報と学習サイトでの進め方をまとめます。",
        "tags": "試験概要;公式情報",
        "sections": ["試験の目的と位置づけ", "まず確認する公式情報", "このサイトでできること", "受験前に押さえる項目", "次に読む記事"],
        "faqs": [
            ("公式情報はどこで確認しますか？", "試験実施団体の公式サイトや受験案内で確認します。非公式情報と異なる場合は公式情報を優先してください。"),
            ("この記事は何に使いますか？", "受験前のチェックリストとして使います。制度情報は対象資格に合わせて差し替えてください。"),
        ],
        "related": "study-plan:学習計画の立て方;past-question-strategy:過去問の使い方",
        "priority": 10,
    },
    "受験・申込": {
        "title": "◯◯試験の受験資格・日程・申込方法",
        "meta": "◯◯試験の受験資格、試験日程、手数料、申込手順を整理します。",
        "lead": "申込前に資格要件とスケジュールを確認したい人向けに、公式情報の見方をまとめます。",
        "tags": "受験資格;申込;公式情報",
        "sections": ["受験資格の確認", "年間スケジュール", "申込期間と手数料", "申込手順と会場", "申込前チェックリスト"],
        "faqs": [
            ("受験資格はどこで確認しますか？", "試験実施団体の受験案内・要項で確認します。最新版を参照してください。"),
            ("申込期限を過ぎたらどうなりますか？", "資格ごとに扱いが異なります。公式の受験案内で確認してください。"),
        ],
        "related": "exam-overview:試験概要;study-plan:学習計画",
        "priority": 15,
    },
    "合格・難易度": {
        "title": "◯◯試験の合格率・難易度の見方",
        "meta": "◯◯試験の合格率、合格点、難易度、統計情報の読み方を整理します。",
        "lead": "合格の見込みや学習期間の目安を知りたい人向けに、数字の確認方法をまとめます。",
        "tags": "合格率;難易度",
        "sections": ["合格率の確認先", "合格点・基準の意味", "難易度の考え方", "統計の読み方", "学習計画への反映"],
        "faqs": [
            ("合格率はどの年度を見ればよいですか？", "直近複数年度を公式情報で確認し、推移も見てください。"),
            ("難易度は高いですか？", "前提知識や学習時間により体感は異なります。公式範囲と過去問で現在地を確認してください。"),
        ],
        "related": "exam-overview:試験概要;study-plan:学習計画",
        "priority": 20,
    },
    "出題・形式": {
        "title": "◯◯試験の出題範囲と試験形式",
        "meta": "◯◯試験の出題範囲、科目構成、試験形式、CBT・記述の有無を整理します。",
        "lead": "何をどこまで学ぶか、当日の形式をつかみたい人向けに、公式範囲の読み方をまとめます。",
        "tags": "出題範囲;試験形式",
        "sections": ["出題範囲の確認先", "範囲の全体像と改定", "科目・配点", "制限時間と出題形式", "過去問との対応"],
        "faqs": [
            ("出題範囲は毎年変わりますか？", "改定がある資格では公式発表を確認してください。"),
            ("試験は何形式ですか？", "公式要項の試験方法・科目を確認し、学習計画に反映してください。"),
        ],
        "related": "exam-overview:試験概要;glossary-how-to:用語整理",
        "priority": 19,
    },
    "学習計画": {
        "title": "◯◯試験の学習計画の立て方",
        "meta": "◯◯試験の学習期間、分野別の進め方、復習サイクルの作り方を解説します。",
        "lead": "合格までの学習を続けるには、出題範囲を分けて演習と復習を定期的に回す計画が重要です。",
        "tags": "学習計画;試験対策",
        "sections": ["全体像を分野に分ける", "学習期間の目安", "週間スケジュールの例", "復習日の入れ方", "直前期の調整"],
        "faqs": [
            ("どのくらいの期間で学習すべきですか？", "前提知識や1日の学習時間により変わります。無理のない期間を設定してください。"),
            ("最初に過去問を解いてもよいですか？", "全体像把握には有効です。弱点は用語・分野別学習に戻って確認します。"),
        ],
        "related": "exam-overview:試験概要;past-question-strategy:過去問の使い方",
        "priority": 25,
    },
    "独学対策": {
        "title": "◯◯試験を独学で進める学習ロードマップ",
        "meta": "◯◯試験を独学で進める人向けに、教材選びから演習・復習までの流れを解説します。",
        "lead": "独学で合格を目指す場合は、教材を増やす前に出題範囲と復習の仕組みを決めておくことが大切です。",
        "tags": "独学;教材;学習計画",
        "sections": ["独学前に公式情報を確認", "教材・参考書の選び方", "過去問で現在地を確認", "復習を計画に入れる", "直前期の絞り込み"],
        "faqs": [
            ("独学では何から始めればよいですか？", "公式情報の確認後、過去問で現在地を把握し、弱点を復習対象に残します。"),
            ("過去問だけで足りますか？", "資格によります。公式範囲・用語理解も合わせて確認してください。"),
        ],
        "related": "exam-overview:試験概要;study-plan:学習計画",
        "priority": 26,
    },
    "過去問活用": {
        "title": "◯◯試験の過去問・模試の使い方",
        "meta": "◯◯試験の過去問・模試を使った演習、解き直し、弱点分析の進め方を整理します。",
        "lead": "過去問と模試は出題傾向を知るだけでなく、理解が曖昧な分野を見つける材料です。",
        "tags": "過去問;模試;復習",
        "sections": ["最初は年度別に解く", "模試・一問一答の位置づけ", "間違いの理由を分類する", "解き直しのタイミング", "用語・分野別学習へ戻る"],
        "faqs": [
            ("過去問だけで合格できますか？", "資格によります。公式範囲・法改正も確認してください。"),
            ("復習では何を見ればよいですか？", "正答だけでなく、他選択肢の違いと混同した用語を確認します。"),
        ],
        "related": "study-plan:学習計画;glossary-how-to:用語整理",
        "priority": 30,
    },
    "分野別対策": {
        "title": "◯◯試験の【分野名】の勉強法",
        "meta": "◯◯試験の【分野名】分野の基礎、頻出論点、過去問の活かし方を整理します。",
        "lead": "特定分野の理解を深めたい人向けに、基礎から演習・復習までの進め方をまとめます。",
        "tags": "分野別;試験対策",
        "sections": ["分野の位置づけ", "押さえる基礎知識", "頻出論点", "過去問での確認方法", "他分野との関連"],
        "faqs": [
            ("苦手分野だけ先に学べますか？", "全体像把握後に集中すると効率が上がります。関連分野のつながりも確認してください。"),
            ("分野別の教材は必要ですか？", "公式範囲と過去問で足りる場合もあります。弱点に応じて追加してください。"),
        ],
        "related": "study-plan:学習計画;past-question-strategy:過去問の使い方",
        "priority": 40,
    },
    "用語整理": {
        "title": "◯◯試験の用語解説を使った知識整理",
        "meta": "◯◯試験の重要用語を効率よく整理するため、用語解説ページの使い方を紹介します。",
        "lead": "用語解説は、過去問で出た語句の意味や似た用語との違いを確認する入口です。",
        "tags": "用語集;知識整理",
        "sections": ["用語集の使い方", "重要度の見方", "数字・期限の整理", "関連用語で回遊する", "過去問との往復"],
        "faqs": [
            ("用語はどこから読めばよいですか？", "過去問で出た語、重要度の高い語から読むと効率的です。"),
            ("関連用語はどう使いますか？", "リンクから似た語句へ進み、セットで理解を深めます。"),
        ],
        "related": "past-question-strategy:過去問の使い方;exam-overview:試験概要",
        "priority": 35,
    },
    "復習・苦手克服": {
        "title": "◯◯試験の復習と苦手克服の進め方",
        "meta": "◯◯試験の復習サイクル、間違いノート、苦手分野の立て直し方を解説します。",
        "lead": "解きっぱなしを防ぎ、得点につながる復習の仕組みを作りたい人向けの記事です。",
        "tags": "復習;苦手克服",
        "sections": ["復習サイクルの作り方", "間違いの分類", "苦手分野の優先順位", "偶然正解の見直し", "直前までの維持"],
        "faqs": [
            ("何度復習すればよいですか？", "間隔を空けた反復が有効です。翌日・数日後・直前で確認します。"),
            ("ノートは必要ですか？", "次に何を見るか分かる短い記録があれば十分です。"),
        ],
        "related": "past-question-strategy:過去問の使い方;study-plan:学習計画",
        "priority": 36,
    },
    "直前・当日": {
        "title": "◯◯試験の直前対策と当日の流れ",
        "meta": "◯◯試験直前の絞り込みと、当日の持ち物・時間配分・会場の流れを整理します。",
        "lead": "試験直前と当日に何を確認すべきかをまとめ、不安を減らして実力を出しやすくします。",
        "tags": "直前対策;試験当日",
        "sections": ["直前1〜2週間の絞り込み", "最終確認リスト", "当日のタイムライン", "持ち物と時間配分", "メンタル・トラブル対応"],
        "faqs": [
            ("直前に新しい教材を増やしてもよいですか？", "基本は絞り込み優先。範囲を限定して追加してください。"),
            ("持ち物で忘れがちなものは？", "受験票・身分証・筆記用具など、公式の指示を再確認してください。"),
        ],
        "related": "past-question-strategy:過去問の使い方;glossary-how-to:用語整理",
        "priority": 70,
    },
    "注意点・更新": {
        "title": "◯◯試験のよくある誤解と制度・合格後の注意点",
        "meta": "◯◯試験の誤解、制度変更、合格後手続き、再受験のポイントを整理します。",
        "lead": "非公式情報で迷わないよう、公式情報の優先と更新の追い方をまとめます。",
        "tags": "誤解;制度変更;合格後",
        "sections": ["よくある誤解", "制度・出題の改定", "合格後の手続き", "不合格後の立て直し", "公式情報の優先"],
        "faqs": [
            ("ネットの体験記だけで判断してよいですか？", "参考程度にし、制度・数値は公式情報で確認してください。"),
            ("去年の教材は使えますか？", "改定範囲を確認し、古い論点が残っていないか注意してください。"),
        ],
        "related": "exam-overview:試験概要;self-study-roadmap:独学ロードマップ",
        "priority": 12,
    },
}

DEFAULT_OUTLINE = GENRE_OUTLINES["学習計画"]

FIELDNAMES: list[str] | None = None


def load_fieldnames() -> list[str]:
    global FIELDNAMES
    if FIELDNAMES is None:
        with ARTICLES_CSV.open(encoding="utf-8-sig", newline="") as f:
            FIELDNAMES = list(csv.DictReader(f).fieldnames or [])
    if not FIELDNAMES:
        raise ValueError(f"CSV header missing: {ARTICLES_CSV}")
    return FIELDNAMES


def existing_slugs() -> set[str]:
    with ARTICLES_CSV.open(encoding="utf-8-sig", newline="") as f:
        return {row["slug"].strip() for row in csv.DictReader(f) if row.get("slug")}


def next_priority(genre: str) -> int:
    outline = GENRE_OUTLINES.get(genre, DEFAULT_OUTLINE)
    return int(outline.get("priority", 50))


def filter_related_links(value: str) -> str:
    """Keep only slugs that exist in guide_articles.csv; ensure at least two links."""
    slugs = existing_slugs()
    kept: list[str] = []
    for item in value.split(";"):
        item = item.strip()
        if not item:
            continue
        slug = item.split(":", 1)[0].strip()
        if slug in slugs:
            kept.append(item)
    fallbacks = [
        "exam-overview:試験概要",
        "study-plan:学習計画",
        "past-question-strategy:過去問の使い方",
        "glossary-how-to:用語整理",
        "self-study-roadmap:独学ロードマップ",
    ]
    for fb in fallbacks:
        if len(kept) >= 2:
            break
        slug = fb.split(":", 1)[0]
        if slug in slugs and fb not in kept:
            kept.append(fb)
    return ";".join(kept[:4])


def build_row(slug: str, genre: str, title: str | None = None) -> dict[str, str]:
    if genre not in guide_genre_labels():
        raise ValueError(f"未知の genre: {genre!r}。site-config.json の guideArticleGenres を確認してください。")
    if not SLUG_RE.fullmatch(slug):
        raise ValueError(f"slug は半角英小文字・数字・ハイフン: {slug!r}")

    outline = GENRE_OUTLINES.get(genre, DEFAULT_OUTLINE)
    today = date.today().isoformat()
    next_month = (date.today() + timedelta(days=30)).isoformat()
    sections: list[str] = list(outline["sections"])  # type: ignore[arg-type]
    faqs: list[tuple[str, str]] = list(outline["faqs"])  # type: ignore[arg-type]

    row = {k: "" for k in load_fieldnames()}
    row.update(
        {
            "slug": slug,
            "genre": genre,
            "title": title or str(outline["title"]),
            "meta_description": str(outline["meta"]),
            "lead": str(outline["lead"]),
            "priority": str(next_priority(genre)),
            "tags": str(outline["tags"]),
            "author_name": f"{brand_name()}編集部",
            "author_profile": "資格学習サイトの編集チーム",
            "reviewer_name": "公式情報確認担当",
            "reviewer_profile": "公開前に一次情報との照合を行う担当者",
            "fact_checked_at": today,
            "primary_sources": "試験実施団体（公式）|https://example.com/",
            "original_note": f"{genre}向けテンプレートから作成。公開前に本文・参照URL・関連リンクを差し替える。",
            "user_intent": "【読者がこの記事で得たいことを1文で記入】",
            "action_items": "【行動1】;【行動2】;【行動3】",
            "update_policy": "試験要項・公式ページ更新時に本文と参照元を見直す。",
            "last_reviewed_at": today,
            "next_review_at": next_month,
            "source_checked_at": today,
            "content_status": "draft",
            "revision_note": f"scaffold_guide_article.py で {today} 作成。",
        }
    )
    for i, heading in enumerate(sections[:7], start=1):
        row[f"section_{i}_heading"] = heading
        row[f"section_{i}_body"] = BODY_PLACEHOLDER.format(topic=heading)
    for i, (q, a) in enumerate(faqs[:2], start=1):
        row[f"faq_{i}_question"] = q
        row[f"faq_{i}_answer"] = a
    row["related_links"] = filter_related_links(str(outline.get("related", "exam-overview:試験概要")))
    return row


def write_template_csv() -> None:
    TEMPLATE_CSV.parent.mkdir(parents=True, exist_ok=True)
    row = build_row("your-article-slug", "学習計画", title="◯◯試験の【記事タイトル】")
    row["slug"] = "your-article-slug"
    row["content_status"] = "draft"
    row["revision_note"] = "テンプレート行。guide_articles.csv にコピーして編集する（この行はビルド対象に含めない）。"
    with TEMPLATE_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=load_fieldnames(), lineterminator="\n")
        writer.writeheader()
        writer.writerow(row)


def append_row(row: dict[str, str]) -> None:
    slugs = existing_slugs()
    if row["slug"] in slugs:
        raise ValueError(f"slug が既に存在します: {row['slug']}")
    with ARTICLES_CSV.open("a", encoding="utf-8", newline="") as f:
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
    parser = argparse.ArgumentParser(description="試験ガイド記事の CSV 行テンプレートを生成します。")
    parser.add_argument("--slug", help="記事 slug（半角英小文字・ハイフン）")
    parser.add_argument("--genre", help="guideArticleGenres の label（例: 学習計画）")
    parser.add_argument("--title", help="タイトル（省略時はジャンル別の雛形）")
    parser.add_argument("--append", action="store_true", help="data/guide_articles.csv の末尾に追記")
    parser.add_argument("--write-template-csv", action="store_true", help="data/templates/guide_article_row.template.csv を更新")
    parser.add_argument("--list-genres", action="store_true", help="利用可能な genre 一覧")
    args = parser.parse_args()

    if args.list_genres:
        for g in guide_article_genres():
            hint = f" — {g['hint']}" if g.get("hint") else ""
            print(f"{g['label']}{hint}")
        return 0

    if args.write_template_csv:
        write_template_csv()
        print(f"Wrote {TEMPLATE_CSV}")
        return 0

    if not args.slug or not args.genre:
        parser.error("--slug と --genre が必要です（--list-genres / --write-template-csv は別）")

    row = build_row(args.slug, args.genre, title=args.title)
    if args.append:
        append_row(row)
        print(f"Appended slug={args.slug!r} genre={args.genre!r} to {ARTICLES_CSV}")
        print("Next: 本文を差し替え → python3 tools/validate_csv.py → python3 tools/build_all.py")
    else:
        print_row(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
