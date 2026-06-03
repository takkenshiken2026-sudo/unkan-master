#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scaffold affiliate guide article: brief YAML + guide_articles.csv row."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.scaffold_guide_article import (  # noqa: E402
    append_row,
    build_row,
    existing_slugs,
    filter_related_links,
    load_fieldnames,
    print_row,
)
from tools.affiliate_links import affiliate_brief_has_links  # noqa: E402

ARTICLES_CSV = ROOT / "data" / "guide_articles.csv"
BRIEFS_DIR = ROOT / "data" / "affiliate-briefs"
TEMPLATE_BRIEF = ROOT / "docs" / "affiliate" / "theme-brief.template.yaml"

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
AFFILIATE_TAG = "アフィリエイト"

AFFILIATE_THEMES: dict[str, dict[str, Any]] = {
    "textbooks-recommend": {
        "slug_default": "affiliate-textbooks-recommend",
        "genre": "独学対策",
        "layout": "product-comparison",
        "asp": "amazon",
        "title": "◯◯試験のおすすめテキスト3選【独学・初心者向け】",
        "meta": "◯◯試験の独学向けおすすめテキストを比較。出版社・価格・向いている人の違いを整理します。",
        "search_intent": "独学で使うおすすめテキストを比較して選びたい",
        "tags": "独学;参考書;アフィリエイト",
        "sections": [
            "テキスト選びの3つのポイント",
            "おすすめテキスト比較の見方",
            "1位のテキストの特徴",
            "2位のテキストの特徴",
            "3位のテキストの特徴",
            "問題集との組み合わせ",
            "無料コンテンツとの併用",
        ],
        "faqs": [
            ("テキストは1冊で足りますか？", "学習段階によります。公式範囲を押さえたうえで、弱点に応じて問題集を追加する場合があります。"),
            ("最新年度版は必要ですか？", "改定がある試験では年度版を確認してください。価格・版は購入前に各販売ページで確認してください。"),
        ],
        "related": "self-study-roadmap:独学の進め方;study-plan:学習計画;../../q/index.html:過去問を解く（無料）",
        "priority": 27,
    },
    "problem-books": {
        "slug_default": "affiliate-problem-books",
        "genre": "過去問活用",
        "layout": "csv",
        "asp": "amazon",
        "title": "◯◯試験のおすすめ問題集・過去問集",
        "meta": "◯◯試験の問題集・過去問集の選び方と、演習の進め方を整理します。",
        "search_intent": "過去問演習に使う問題集を比較して選びたい",
        "tags": "過去問;問題集;アフィリエイト",
        "sections": [
            "問題集選びのポイント",
            "年度別と分野別の使い分け",
            "おすすめ問題集の比較",
            "解き方と復習の回し方",
            "テキストとの併用",
            "このサイトの過去問との組み合わせ",
            "直前期の買い足し",
        ],
        "faqs": [
            ("過去問だけで合格できますか？", "試験によります。出題範囲と用語理解も合わせて確認してください。"),
            ("何年分を揃えればよいですか？", "直近複数年度を公式情報と照らし、演習計画に合わせて選んでください。"),
        ],
        "related": "past-question-strategy:過去問の使い方;study-plan:学習計画;../../q/index.html:過去問を解く（無料）",
        "priority": 31,
    },
    "online-course-compare": {
        "slug_default": "affiliate-online-course-compare",
        "genre": "独学対策",
        "layout": "product-comparison",
        "asp": "a8",
        "title": "◯◯試験のオンライン講座比較【独学との併用】",
        "meta": "◯◯試験向けオンライン講座の比較ポイントと、独学との併用の考え方を整理します。",
        "search_intent": "オンライン講座を比較して独学に組み込みたい",
        "tags": "通信講座;独学;アフィリエイト",
        "sections": [
            "講座を検討するタイミング",
            "比較する項目（カリキュラム・質問・価格）",
            "独学との役割分担",
            "おすすめの選び方",
            "無料体験の活用法",
            "過去問演習との組み合わせ",
            "申込前の確認事項",
        ],
        "faqs": [
            ("独学だけでは不十分ですか？", "学習スタイルによります。弱点の説明や質問対応が必要なら講座を検討してください。"),
            ("キャンペーン価格は信頼できますか？", "申込前に公式案内の通常価格・条件を確認してください。"),
        ],
        "related": "self-study-roadmap:独学の進め方;study-plan:学習計画;exam-overview:試験概要",
        "priority": 28,
    },
    "correspondence-course": {
        "slug_default": "affiliate-correspondence-course",
        "genre": "独学対策",
        "layout": "product-comparison",
        "asp": "a8",
        "title": "◯◯試験の通信講座の選び方",
        "meta": "◯◯試験向け通信講座の選び方、教材セット、サポートの見方を整理します。",
        "search_intent": "通信講座の教材とサポートを比較したい",
        "tags": "通信講座;教材;アフィリエイト",
        "sections": [
            "通信講座が向く人",
            "教材セットの見方",
            "サポート内容の比較",
            "価格と学習期間",
            "独学教材との違い",
            "過去問演習の組み込み",
            "申込前チェックリスト",
        ],
        "faqs": [
            ("仕事しながらでも進められますか？", "週あたりの学習時間とカリキュラムの分量を照らして選んでください。"),
            ("返金保証はありますか？", "各講座の公式条件を申込前に確認してください。"),
        ],
        "related": "self-study-roadmap:独学の進め方;study-plan:学習計画",
        "priority": 29,
    },
    "cram-school": {
        "slug_default": "affiliate-cram-school",
        "genre": "独学対策",
        "layout": "csv",
        "asp": "a8",
        "title": "◯◯試験の予備校・塾の選び方",
        "meta": "◯◯試験向け予備校・オンライン塾の選び方と通学・独学の併用を整理します。",
        "search_intent": "予備校・塾を比較して選びたい",
        "tags": "予備校;塾;アフィリエイト",
        "sections": [
            "予備校を検討するケース",
            "通学とオンラインの違い",
            "比較するポイント",
            "カリキュラムと演習量",
            "独学との併用",
            "費用の考え方",
            "体験・説明会の活用法",
        ],
        "faqs": [
            ("短期集中コースは有効ですか？", "前提知識と残り期間によります。公式範囲との対応を確認してください。"),
            ("地方在住でも受講できますか？", "オンライン完結型があるか各塾の公式情報で確認してください。"),
        ],
        "related": "self-study-roadmap:独学の進め方;study-plan:学習計画",
        "priority": 30,
    },
    "mock-exam-materials": {
        "slug_default": "affiliate-mock-exam-materials",
        "genre": "過去問活用",
        "layout": "csv",
        "asp": "mixed",
        "title": "◯◯試験の模試・直前対策教材の選び方",
        "meta": "◯◯試験の模試・直前教材の選び方と、本番直前の演習の組み立て方を整理します。",
        "search_intent": "直前に買う模試・予想問題を選びたい",
        "tags": "模試;直前対策;アフィリエイト",
        "sections": [
            "直前期に買う教材の役割",
            "模試と予想問題の違い",
            "おすすめの選び方",
            "解き方と復習",
            "本番当日への反映",
            "無料演習との併用",
            "買い足しの判断",
        ],
        "faqs": [
            ("直前に新しい教材を増やしてよいですか？", "基本は絞り込み優先です。追加する場合は範囲を限定してください。"),
            ("模試の点数はどう見ればよいですか？", "弱点の特定に使い、次の復習対象を決めてください。"),
        ],
        "related": "exam-day-checklist:試験当日の流れ;past-question-strategy:過去問の使い方",
        "priority": 71,
    },
    "free-vs-paid-study": {
        "slug_default": "affiliate-free-vs-paid-study",
        "genre": "独学対策",
        "layout": "csv",
        "asp": "internal",
        "title": "◯◯試験の無料学習と有料教材の使い分け",
        "meta": "◯◯試験で無料コンテンツと有料教材をどう組み合わせるかを整理します。",
        "search_intent": "無料だけでどこまでできるか、有料はいつ必要か知りたい",
        "tags": "独学;コスト;アフィリエイト",
        "sections": [
            "無料でできること",
            "有料教材が向く場面",
            "コスト別の学習プラン例",
            "過去問・用語の無料活用",
            "講座を検討する目安",
            "買い足しの優先順位",
            "次に読む記事",
        ],
        "faqs": [
            ("無料だけで合格できますか？", "試験と学習時間によります。公式範囲の確認は必須です。"),
            ("有料教材はいつ買えばよいですか？", "弱点が分かった段階で、1〜2種類に絞って追加するのが効率的です。"),
        ],
        "related": "self-study-roadmap:独学の進め方;../../q/index.html:過去問を解く（無料）;glossary-how-to:用語整理",
        "priority": 26,
    },
    "beginner-material-set": {
        "slug_default": "affiliate-beginner-material-set",
        "genre": "学習計画",
        "layout": "csv",
        "asp": "mixed",
        "title": "◯◯試験の初心者向け教材セットの揃え方",
        "meta": "◯◯試験を初めて学ぶ人向けに、テキスト・問題集・講座の揃え方を整理します。",
        "search_intent": "初心者が最初に揃える教材セットを知りたい",
        "tags": "初学者;教材;アフィリエイト",
        "sections": [
            "初心者が最初に確認すること",
            "最低限揃える3点セット",
            "テキストの選び方",
            "問題集の入れ方",
            "講座を足すタイミング",
            "学習計画への組み込み",
            "コストの目安",
        ],
        "faqs": [
            ("何から買えばよいですか？", "公式情報確認後、テキスト1冊と過去問演習の導線を先に決めると迷いにくいです。"),
            ("全部そろえる必要がありますか？", "最初は最小セットで開始し、弱点に応じて追加してください。"),
        ],
        "related": "study-plan:学習計画;exam-overview:試験概要;self-study-roadmap:独学の進め方",
        "priority": 24,
    },
    "retake-short-course": {
        "slug_default": "affiliate-retake-short-course",
        "genre": "学習計画",
        "layout": "csv",
        "asp": "a8",
        "title": "◯◯試験の再受験向け短期学習プラン",
        "meta": "◯◯試験の再受験者向けに、短期集中の教材・講座の選び方を整理します。",
        "search_intent": "再受験で短期間に点数を上げたい",
        "tags": "再受験;短期;アフィリエイト",
        "sections": [
            "再受験で見直すポイント",
            "短期プランの組み立て",
            "教材の絞り込み",
            "過去問の使い方",
            "講座・塾の活用",
            "直前2週間の配分",
            "メンタルと体調",
        ],
        "faqs": [
            ("前回と同じ教材でよいですか？", "弱点と改定範囲を確認し、足りない部分だけ買い足してください。"),
            ("短期講座は有効ですか？", "残り期間と弱点次第です。公式範囲との対応を確認してください。"),
        ],
        "related": "study-plan:学習計画;past-question-strategy:過去問の使い方",
        "priority": 32,
    },
    "qualification-support-service": {
        "slug_default": "affiliate-qualification-support-service",
        "genre": "受験・申込",
        "layout": "csv",
        "asp": "a8",
        "title": "◯◯試験の受験サポート・申込支援サービスの選び方",
        "meta": "◯◯試験の申込・手続き支援サービスの選び方と公式情報との使い分けを整理します。",
        "search_intent": "申込や手続きを代行・支援してくれるサービスを比較したい",
        "tags": "受験;申込;アフィリエイト",
        "sections": [
            "支援サービスが向くケース",
            "公式手続きとの違い",
            "比較する項目",
            "費用とサポート範囲",
            "申込前の確認事項",
            "個人情報・契約の注意",
            "公式情報の優先",
        ],
        "faqs": [
            ("公式申込と併用できますか？", "サービスごとに異なります。必ず公式の受験案内と照合してください。"),
            ("必須ではありませんか？", "試験によります。不要なら公式手続きのみで問題ない場合もあります。"),
        ],
        "related": "exam-schedule:受験日程・申込;exam-overview:試験概要",
        "priority": 16,
    },
    "custom": {
        "slug_default": "",
        "genre": "独学対策",
        "layout": "csv",
        "asp": "amazon",
        "title": "◯◯試験の【記事テーマを入れる】",
        "meta": "◯◯試験の【テーマ】について、比較のポイントと選び方を整理します。",
        "search_intent": "",
        "tags": "アフィリエイト",
        "sections": [
            "この記事で比較すること",
            "選び方のポイント",
            "おすすめの比較",
            "向いている人の違い",
            "価格・サポートの見方",
            "無料コンテンツとの併用",
            "次のステップ",
        ],
        "faqs": [
            ("何を基準に選べばよいですか？", "公式範囲・学習時間・弱点に合わせて優先順位を決めてください。"),
            ("最新情報はどこで確認しますか？", "試験実施団体の公式サイトと各商品の販売ページで確認してください。"),
        ],
        "related": "self-study-roadmap:独学の進め方;study-plan:学習計画",
        "priority": 50,
    },
}


def load_simple_yaml(path: Path) -> dict[str, Any]:
    """Parse flat YAML (no PyYAML): keys, multiline | blocks, simple lists."""
    data: dict[str, Any] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    current_list: str | None = None
    current_product: dict[str, Any] | None = None
    operator_lines: list[str] | None = None

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        if stripped == "operator_note: |":
            operator_lines = []
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or not lines[i].strip()):
                if lines[i].strip():
                    operator_lines.append(lines[i].strip())
                i += 1
            data["operator_note"] = "\n".join(operator_lines)
            operator_lines = None
            continue

        if line.startswith("  - rank:") or (line.startswith("  - ") and "name:" in line):
            if current_product:
                data.setdefault("products", []).append(current_product)
            current_product = {}
            current_list = "products"
            rest = line.strip()[2:].strip()
            if rest.startswith("- "):
                rest = rest[2:].strip()
            if ":" in rest:
                k, v = rest.split(":", 1)
                current_product[k.strip()] = v.strip()
            i += 1
            continue

        if current_list == "products" and line.startswith("    ") and ":" in line:
            k, v = line.strip().split(":", 1)
            if current_product is not None:
                current_product[k.strip()] = v.strip()
            i += 1
            continue

        if line.startswith("  - ") and current_list == "related_links":
            data.setdefault("related_links", []).append(line.strip()[2:].strip())
            i += 1
            continue

        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            key = k.strip()
            val = v.strip()
            if key == "related_links" and not val:
                current_list = "related_links"
                data["related_links"] = []
            elif key == "products" and not val:
                current_list = "products"
                data["products"] = []
                current_product = None
            else:
                current_list = None
                current_product = None
                if val:
                    data[key] = val
            i += 1
            continue

        i += 1

    if current_product:
        data.setdefault("products", []).append(current_product)
    return data


def theme_from_brief(brief: dict[str, Any]) -> str:
    return str(brief.get("theme_key") or brief.get("theme") or "custom").strip()


def resolve_config(
    theme_key: str,
    *,
    slug: str | None = None,
    title: str | None = None,
    search_intent: str | None = None,
    asp: str | None = None,
    layout: str | None = None,
    genre: str | None = None,
    brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = dict(AFFILIATE_THEMES.get(theme_key, AFFILIATE_THEMES["custom"]))
    if brief:
        if brief.get("title"):
            base["title"] = brief["title"]
        if brief.get("genre"):
            base["genre"] = brief["genre"]
        if brief.get("layout"):
            base["layout"] = brief["layout"]
        if brief.get("asp_primary"):
            base["asp"] = brief["asp_primary"]
        if brief.get("search_intent"):
            base["search_intent"] = brief["search_intent"]
        if brief.get("related_links"):
            base["related"] = ";".join(brief["related_links"])
    cfg = base
    use_slug = slug or (brief or {}).get("slug") or cfg.get("slug_default") or ""
    if not use_slug:
        raise ValueError("slug が必要です（--slug またはブリーフの slug）")
    if not SLUG_RE.fullmatch(use_slug):
        raise ValueError(f"slug は半角英小文字・数字・ハイフン: {use_slug!r}")
    si = search_intent or cfg.get("search_intent") or "【検索意図を記入】"
    if theme_key == "custom" and si.startswith("【"):
        raise ValueError("custom テーマでは --search-intent またはブリーフの search_intent が必要です")
    return {
        "theme_key": theme_key,
        "slug": use_slug,
        "title": title or cfg.get("title"),
        "genre": genre or cfg.get("genre", "独学対策"),
        "layout": layout or cfg.get("layout", "csv"),
        "asp": asp or cfg.get("asp", "amazon"),
        "search_intent": si,
        "meta": cfg.get("meta", ""),
        "tags": cfg.get("tags", f"{AFFILIATE_TAG}"),
        "sections": list(cfg.get("sections", [])),
        "faqs": list(cfg.get("faqs", [])),
        "related": cfg.get("related", ""),
        "priority": int(cfg.get("priority", 50)),
        "products": (brief or {}).get("products", []),
        "operator_note": (brief or {}).get("operator_note", ""),
    }


def affiliate_lead(search_intent: str) -> str:
    exam = exam_name()
    return (
        f"{exam}を受験予定で、{search_intent}人向けに、比較のポイントと選び方をまとめました。"
        "価格・版・キャンペーンは購入前に各販売ページでご確認ください。"
    )


def section_body_placeholder(heading: str, search_intent: str) -> str:
    return (
        f"【{heading}の本文を記入】{exam_name()}の受験者が「{search_intent}」ときに役立つ内容を、"
        "公式情報を確認したうえで180〜300文字程度で書いてください。"
        "比較表・商品名・価格は fact_checked_at と整合させ、断定しすぎない表現にしてください。"
    )


def build_affiliate_row(config: dict[str, Any]) -> dict[str, str]:
    row = build_row(config["slug"], config["genre"], title=config["title"])
    row["meta_description"] = str(config["meta"])
    row["lead"] = affiliate_lead(config["search_intent"])
    tags = config["tags"]
    if AFFILIATE_TAG not in tags.split(";"):
        tags = f"{tags};{AFFILIATE_TAG}" if tags else AFFILIATE_TAG
    row["tags"] = tags
    row["priority"] = str(config["priority"])
    row["user_intent"] = f"{exam_name()}の受験者が、{config['search_intent']}ための比較と次の行動が分かる。"
    row["action_items"] = (
        "比較ポイントを確認する;"
        "公式範囲と照らして候補を絞る;"
        "このサイトの過去問・用語で理解度を確認する"
    )
    asp = config["asp"]
    layout = config["layout"]
    op = config.get("operator_note") or ""
    row["original_note"] = (
        f"アフィリエイト記事テーマ={config['theme_key']}; layout={layout}; asp={asp}. "
        f"ブリーフ: data/affiliate-briefs/{config['slug']}.yaml. "
        f"{op}"
    ).strip()
    row["revision_note"] = (
        f"scaffold_affiliate_article.py で {date.today().isoformat()} 作成（テーマ={config['theme_key']}）。"
        "公開前に本文・商品URL・画像を差し替える。"
    )
    row["content_status"] = "draft"

    sections: list[str] = config["sections"]
    for i, heading in enumerate(sections[:7], start=1):
        row[f"section_{i}_heading"] = heading
        row[f"section_{i}_body"] = section_body_placeholder(heading, config["search_intent"])

    faqs: list[tuple[str, str]] = config["faqs"]
    for i, (q, a) in enumerate(faqs[:2], start=1):
        row[f"faq_{i}_question"] = q
        row[f"faq_{i}_answer"] = a

    row["related_links"] = filter_related_links(str(config.get("related", "")))
    return row


def format_brief_yaml(config: dict[str, Any]) -> str:
    lines = [
        f"# Generated by scaffold_affiliate_article.py on {date.today().isoformat()}",
        f"slug: {config['slug']}",
        f"theme_key: {config['theme_key']}",
        f"search_intent: {config['search_intent']}",
        f"title: {config['title']}",
        f"genre: {config['genre']}",
        f"layout: {config['layout']}",
        f"asp_primary: {config['asp']}",
        "products:",
    ]
    products = config.get("products") or []
    if not products:
        lines.append("  - rank: 1")
        lines.append("    name: 【商品名を記入】")
        lines.append("    publisher: 【出版社】")
        lines.append("    image_file: exam-product-1-2026.webp")
        lines.append("    amazon_url: https://amzn.to/xxxxxxxx")
        lines.append("    for_who: 【向いている人】")
    else:
        for p in products:
            lines.append(f"  - rank: {p.get('rank', '')}")
            for key in (
                "name",
                "publisher",
                "image_file",
                "amazon_url",
                "workbook_name",
                "workbook_image_file",
                "workbook_amazon_url",
                "for_who",
            ):
                if p.get(key):
                    lines.append(f"    {key}: {p[key]}")
    lines.append("related_links:")
    for link in str(config.get("related", "")).split(";"):
        link = link.strip()
        if link:
            lines.append(f"  - {link}")
    lines.append("operator_note: |")
    note = config.get("operator_note") or f"ASP: {config['asp']}\n公開前に商品URL・画像・報酬条件を記入"
    for part in note.split("\n"):
        lines.append(f"  {part}")
    lines.append("")
    return "\n".join(lines)


def write_brief(config: dict[str, Any], force: bool = False) -> Path:
    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    path = BRIEFS_DIR / f"{config['slug']}.yaml"
    if path.exists() and not force:
        return path
    path.write_text(format_brief_yaml(config), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="アフィリエイト試験ガイドのブリーフ YAML と CSV 行を生成します。")
    parser.add_argument("--theme", help="テーマキー（--list-themes 参照）")
    parser.add_argument("--slug", help="記事 slug")
    parser.add_argument("--title", help="タイトル上書き")
    parser.add_argument("--search-intent", help="検索意図（custom 必須）")
    parser.add_argument("--asp", choices=["amazon", "a8", "afb", "internal", "mixed"], help="主ASP")
    parser.add_argument("--layout", choices=["csv", "product-comparison"], help="レイアウト種別")
    parser.add_argument("--genre", help="guideArticleGenres の label")
    parser.add_argument("--from-brief", type=Path, help="既存ブリーフ YAML から生成")
    parser.add_argument("--append", action="store_true", help="guide_articles.csv に追記")
    parser.add_argument("--write-brief", action="store_true", help="data/affiliate-briefs/{slug}.yaml を書く")
    parser.add_argument("--force-brief", action="store_true", help="既存ブリーフを上書き")
    parser.add_argument("--list-themes", action="store_true", help="テーマキー一覧")
    args = parser.parse_args()

    if args.list_themes:
        for key, cfg in AFFILIATE_THEMES.items():
            if key == "custom":
                continue
            print(f"{key:32} slug={cfg.get('slug_default')} asp={cfg.get('asp')} layout={cfg.get('layout')}")
        print(f"{'custom':32} slug=(要指定) asp=(要指定)")
        return 0

    brief_data: dict[str, Any] | None = None
    if args.from_brief:
        if not args.from_brief.is_file():
            parser.error(f"ブリーフが見つかりません: {args.from_brief}")
        brief_data = load_simple_yaml(args.from_brief)
        theme_key = theme_from_brief(brief_data)
        slug = args.slug or str(brief_data.get("slug", "")).strip()
    else:
        if not args.theme:
            parser.error("--theme または --from-brief が必要です")
        theme_key = args.theme.strip()
        if theme_key not in AFFILIATE_THEMES:
            parser.error(f"未知の theme: {theme_key!r}（--list-themes）")
        slug = args.slug

    config = resolve_config(
        theme_key,
        slug=slug,
        title=args.title,
        search_intent=args.search_intent,
        asp=args.asp,
        layout=args.layout,
        genre=args.genre,
        brief=brief_data,
    )

    row = build_affiliate_row(config)
    brief_path = write_brief(config, force=args.force_brief or args.write_brief)

    if args.write_brief and not args.append:
        print(f"Wrote brief {brief_path}")
        return 0

    if args.append:
        if not affiliate_brief_has_links(config):
            parser.error(
                "アフィリエイトリンク未設定のため guide_articles.csv に追記しません。"
                " brief の products.*_url または related_links に ASP URL を入れてから --append してください。"
                " （内部リンク中心の free-vs-paid-study のみ asp=internal で例外）"
            )
        append_row(row)
        write_brief(config, force=True)
        print(f"Appended slug={config['slug']!r} theme={theme_key!r} to {ARTICLES_CSV}")
        print(f"Brief: {brief_path}")
        print("Next: 本文・商品をブリーフに沿って完成 → python3 tools/build_all.py")
    else:
        if args.write_brief or args.force_brief:
            print(f"Brief: {brief_path}")
        print_row(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
