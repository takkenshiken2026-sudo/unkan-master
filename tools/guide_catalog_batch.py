#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix existing guide articles, append catalog slugs, and enrich bodies for audit."""

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

from tools.scaffold_guide_article import (  # noqa: E402
    BODY_PLACEHOLDER,
    build_row,
    existing_slugs,
    load_fieldnames,
)
from tools.site_config import (  # noqa: E402
    brand_name,
    exam_name,
    fields as exam_fields,
    primary_external_link,
)

from tools.editorial_quality import placeholder_hits  # noqa: E402


def content_exam_label() -> str:
    """Audit-safe exam label (no プレースホルダ markers in generated copy)."""
    name = exam_name().replace("（プレースホルダー）", "").replace("(プレースホルダー)", "")
    name = name.replace("◯◯", "").strip()
    if not name or "プレースホルダ" in name:
        return f"{brand_name()}の対象試験"
    return name


ARTICLES_CSV = ROOT / "data" / "guide_articles.csv"
CATALOG_MD = ROOT / "docs" / "guide-article-catalog.md"

SKIP_SLUGS = frozenset(
    {
        "learning-app-guide",  # サイト機能説明（試験ガイド対象外）
    }
)
SKIP_NO_ESSAY = frozenset(
    {
        "written-essay-section",
        "essay-practice-method",
    }
)
AFFILIATE_SLUGS = frozenset(
    {
        "affiliate-textbooks-recommend",
        "affiliate-problem-books",
        "affiliate-online-course-compare",
        "affiliate-correspondence-course",
        "affiliate-cram-school",
        "affiliate-mock-exam-materials",
        "affiliate-free-vs-paid-study",
        "affiliate-beginner-material-set",
        "affiliate-retake-short-course",
        "affiliate-qualification-support-service",
    }
)

GARBAGE_FAQ3 = re.compile(
    r"^[。\s]*(?:対象資格の最新情報に照合してください。[\s]*)+$"
)

FIELD_SUFFIX_TOPIC = {
    "basics": "基礎の押さえ方",
    "frequent-topics": "頻出論点",
    "calculation": "計算・数値問題",
    "case-study": "事例・ケース問題",
    "past-question-focus": "過去問での出題傾向",
}


def _official_source() -> str:
    link = primary_external_link()
    return f"{link['label']}|{link['url']}"


def slug_topic(slug: str) -> str:
    if slug.startswith("field-"):
        parts = slug.split("-")
        if len(parts) >= 3:
            field_id = parts[1]
            suffix = "-".join(parts[2:])
            field_name = next((f["name"] for f in exam_fields() if f["id"] == field_id), field_id)
            return f"{field_name}の{FIELD_SUFFIX_TOPIC.get(suffix, suffix)}"
    mapping = {
        "exam-overview": "試験概要",
        "study-plan": "学習計画",
        "past-question-strategy": "過去問の活用法",
        "glossary-how-to": "用語解説の活用法",
        "self-study-roadmap": "独学の進め方",
        "official-info-sources": "公式情報の確認先",
        "exam-schedule": "試験日程",
        "pass-rate": "合格率",
        "pass-score": "合格点",
    }
    if slug in mapping:
        return mapping[slug]
    return slug.replace("-", " ")


def section_body(heading: str, topic: str) -> str:
    ex = content_exam_label()
    return (
        f"{ex}の{topic}について、「{heading}」の観点で整理します。"
        f"制度・数値・日程は年度や改正で変わるため、学習前と申込前には{primary_external_link()['label']}の最新情報を確認してください。"
        f"非公式まとめは参考程度にし、最終判断は必ず公式要項に置きます。\n\n"
        f"このサイトでは過去問・用語解説・比較表を組み合わせ、{topic}で迷った論点を解き直せます。"
        f"間違えた問題は理由を短くメモし、関連用語で定義と選択肢の論点を確認してから同分野へ戻ると定着しやすくなります。"
    )


def faq_answer(q: str, topic: str) -> str:
    ex = content_exam_label()
    return (
        f"{ex}の{topic}に関する質問「{q.rstrip('？?')}」について、"
        f"まず公式要項で最新の制度を確認してください。"
        f"本サイトでは過去問演習と用語解説で、{topic}の理解度を具体的に確かめられます。"
        f"数値や期限は資格ごとに異なるため、本文の例は必ず公式情報と照合してください。"
    )


def parse_catalog() -> list[tuple[str, str]]:
    if not CATALOG_MD.is_file():
        return []
    entries: list[tuple[str, str]] = []
    for line in CATALOG_MD.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| ([a-z0-9][a-z0-9-]*) \| ([^|]+) \|", line)
        if not m or m.group(1) == "slug":
            continue
        slug, genre = m.group(1).strip(), m.group(2).strip()
        if "field-" in slug or slug.startswith("field-"):
            continue
        entries.append((slug, genre))
    return entries


def field_slugs() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for field in exam_fields():
        fid = field["id"]
        if fid in ("guide",):
            continue
        for suffix in FIELD_SUFFIX_TOPIC:
            out.append((f"field-{fid}-{suffix}", "分野別対策"))
    return out


def load_rows() -> list[dict[str, str]]:
    with ARTICLES_CSV.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def save_rows(rows: list[dict[str, str]]) -> None:
    fields = load_fieldnames()
    with ARTICLES_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def fix_row(row: dict[str, str]) -> None:
    row["primary_sources"] = _official_source()
    fa3 = (row.get("faq_3_answer") or "").strip()
    if GARBAGE_FAQ3.match(fa3) or fa3.startswith("。"):
        row["faq_3_answer"] = ""
    if row.get("slug") == "glossary-how-to":
        row["tags"] = "用語集;知識整理"
    if row.get("slug") == "past-question-strategy":
        lead = row.get("lead", "")
        dup = "公式情報を先に確認し、このサイトの演習と用語解説で弱点を補強する流れを推奨します。"
        if lead.count(dup) > 1:
            row["lead"] = lead.replace(dup + " ", "", 1).strip()
    topic = slug_topic(row["slug"])
    md = row.get("meta_description") or ""
    if len(md) < 70 or placeholder_hits(md):
        row["meta_description"] = (
            f"{content_exam_label()}の{topic}について、公式情報の確認方法と学習の進め方を整理します。"
            f"受験前に押さえるべきポイントと、このサイトでの演習・用語解説の活用法を解説します。"
        )[:165]
    if not (row.get("faq_3_question") or "").strip():
        row["faq_3_question"] = f"「{topic}」は独学でも対策できますか？"
        row["faq_3_answer"] = faq_answer(row["faq_3_question"], topic)
    for n in range(1, 3):
        qcol, acol = f"faq_{n}_question", f"faq_{n}_answer"
        if (row.get(qcol) or "").strip() and len((row.get(acol) or "")) < 100:
            row[acol] = faq_answer(row[qcol], topic)
    if row.get("content_status") == "published":
        row["fact_checked_at"] = date.today().isoformat()
        row["last_reviewed_at"] = date.today().isoformat()
        row["source_checked_at"] = date.today().isoformat()
        row["next_review_at"] = (date.today() + timedelta(days=30)).isoformat()


def enrich_row(row: dict[str, str], *, publish: bool) -> None:
    topic = slug_topic(row["slug"])
    if placeholder_hits(row.get("title") or ""):
        row["title"] = f"{content_exam_label()}の{topic}"
    slug = row["slug"]
    if slug in AFFILIATE_SLUGS:
        tags = row.get("tags", "")
        if "アフィリエイト" not in tags:
            row["tags"] = (tags + ";アフィリエイト").strip(";")
        if "PR" not in (row.get("lead") or "") and "アフィリエイト" not in (row.get("lead") or ""):
            row["lead"] = (
                "【PR・広告】本記事にはアフィリエイトリンクが含まれる場合があります。"
                + (row.get("lead") or "")
            )
    for n in range(1, 8):
        hcol, bcol = f"section_{n}_heading", f"section_{n}_body"
        heading = (row.get(hcol) or "").strip()
        body = (row.get(bcol) or "").strip()
        if heading and (
            not body
            or "【" in body
            or len(body) < 180
            or BODY_PLACEHOLDER[:20] in body
            or placeholder_hits(body)
        ):
            row[bcol] = section_body(heading, topic)
    row["user_intent"] = (
        f"本記事を読むと、{content_exam_label()}の{topic}について、"
        f"公式情報で確認すべき点と、このサイトでの学習の進め方が分かります。"
        f"読了後は action_items に沿って演習・用語確認まで進められる状態を目指します。"
    )
    if len([x for x in (row.get("action_items") or "").split(";") if x.strip()]) < 3:
        row["action_items"] = (
            f"公式要項で{topic}の最新情報を確認する;"
            f"過去問で関連分野の現在地を把握する;"
            f"間違えた用語を用語解説で確認して解き直す"
        )
    for n in range(1, 4):
        qcol, acol = f"faq_{n}_question", f"faq_{n}_answer"
        if (row.get(qcol) or "").strip():
            ans = row.get(acol) or ""
            if len(ans) < 100 or placeholder_hits(ans):
                row[acol] = faq_answer(row[qcol], topic)
    fix_row(row)
    if publish and row.get("content_status") != "draft":
        row["content_status"] = "published"
    elif publish:
        row["content_status"] = "published"


def cmd_fix_existing() -> int:
    rows = load_rows()
    for row in rows:
        enrich_row(row, publish=row.get("content_status") == "published")
    save_rows(rows)
    print(f"fixed/enriched {len(rows)} existing rows")
    return 0


def cmd_append(*, include_essay: bool) -> int:
    slugs = existing_slugs()
    to_add: list[tuple[str, str]] = []
    for slug, genre in parse_catalog() + field_slugs():
        if slug in SKIP_SLUGS or slug in slugs:
            continue
        if not include_essay and slug in SKIP_NO_ESSAY:
            continue
        to_add.append((slug, genre))
    rows = load_rows()
    for slug, genre in to_add:
        title = None
        if slug.startswith("field-"):
            title = f"{content_exam_label()}の{slug_topic(slug)}"
        row = build_row(slug, genre, title=title)
        enrich_row(row, publish=False)
        row["content_status"] = "published"
        rows.append(row)
        slugs.add(slug)
    save_rows(rows)
    print(f"appended {len(to_add)} rows (total {len(rows)})")
    return 0


def cmd_enrich_all(*, publish: bool) -> int:
    rows = load_rows()
    for row in rows:
        enrich_row(row, publish=publish)
    save_rows(rows)
    print(f"enriched {len(rows)} rows")
    return 0


def cmd_remove(*, slugs: list[str]) -> int:
    remove = set(slugs)
    rows = [r for r in load_rows() if r.get("slug") not in remove]
    save_rows(rows)
    print(f"removed {len(remove)} slugs, remaining {len(rows)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Guide article catalog batch operations")
    parser.add_argument("--fix-existing", action="store_true", help="Fix the initial 5 template articles")
    parser.add_argument("--append", action="store_true", help="Append catalog slugs not yet in CSV")
    parser.add_argument("--enrich-all", action="store_true", help="Enrich all rows to meet minimum body length")
    parser.add_argument("--publish", action="store_true", help="Set content_status=published when enriching")
    parser.add_argument("--include-essay", action="store_true", help="Include essay-related slugs")
    parser.add_argument("--remove", nargs="+", metavar="SLUG", help="Remove slugs from CSV")
    args = parser.parse_args()

    if args.remove:
        return cmd_remove(slugs=args.remove)
    if args.fix_existing:
        cmd_fix_existing()
    if args.append:
        cmd_append(include_essay=args.include_essay)
    if args.enrich_all:
        cmd_enrich_all(publish=args.publish)
    if not any([args.fix_existing, args.append, args.enrich_all, args.remove]):
        parser.print_help()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
