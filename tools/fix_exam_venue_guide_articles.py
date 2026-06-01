#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""*-center 等の会場ガイド記事を専用テンプレで差し替える。"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

SHELL = Path(__file__).resolve().parents[1]
if str(SHELL) not in sys.path:
    sys.path.insert(0, str(SHELL))

from tools.editorial_quality import is_published_guide  # noqa: E402
from tools.exam_venue_official_links import (  # noqa: E402
    is_exam_center_slug,
    md_link,
    primary_sources_for_venue,
    venue_page_for_slug,
    venue_official_md,
)
from tools.fix_guide_duplicate_bodies import load_site_lib  # noqa: E402
from tools.guide_coherence_rules import check_guide_row_coherence, short_topic_from_title  # noqa: E402
from tools.guide_exam_day_faq import faq_answer_for_belongings_question  # noqa: E402

VENUE_SECTIONS = [
    "基本情報",
    "アクセス方法",
    "試験日程の確認方法",
    "申込の注意点",
    "試験当日の持ち物",
    "まとめ",
]


def venue_faq(topic: str, slug: str, *, site_root: Path, lib) -> list[tuple[str, str]]:
    page = venue_page_for_slug(slug)
    venue_md = md_link(*page) if page else venue_official_md(site_root)
    portal_md = venue_official_md(site_root)
    exam = getattr(lib, "EXAM", "試験")
    return [
        (
            "この会場で受験する人はこの記事を読むべきですか？",
            f"該当地域で{exam}を受験する予定の方は、受験地選択と会場アクセスの確認に本記事が役立ちます。"
            f"試験範囲の学習は公式テキストと演習問題で進め、日程・会場・持ち物だけは"
            f"{portal_md}や{venue_md}で最新情報を確認してください。",
        ),
        (
            "会場の住所やアクセスはどこで確認しますか？",
            f"会場の所在地・交通手段・アクセス方法は{venue_md}の「アクセスマップ」"
            f"および{portal_md}の受験案内で確認してください。"
            "本人に割り当てられた会場名・住所は受験票が正本です。"
            "試験日が近づいたら前日までにルートと所要時間を確定し、"
            "当日は開始時刻の30分前到着を目安に余裕を持って向かってください。",
        ),
        (
            "試験当日の持ち物は何を準備すればよいですか？",
            faq_answer_for_belongings_question(
                "試験当日の持ち物は何を準備すればよいですか？",
                official=getattr(lib, "OFFICIAL", "公式サイト"),
            )
            or (
                "受験要項および受験票に記載された持ち物（鉛筆・消しゴム・身分証など）を前日に準備してください。"
                "禁止物品（スマートフォン、参考書など）は要項どおりに守り、筆記用具は予備があると当日のトラブルを減らせます。"
            ),
        ),
    ]


def is_venue_center_article(slug: str, title: str) -> bool:
    if is_exam_center_slug(slug):
        return True
    if slug.endswith("-center"):
        return True
    return "安全衛生技術センター" in title


def patch_venue_row(
    row: dict[str, str],
    fieldnames: list[str],
    *,
    site_root: Path,
    lib,
) -> dict[str, str]:
    row = {k: row.get(k, "") for k in fieldnames}
    slug = (row.get("slug") or "").strip()
    title = (row.get("title") or "").strip()
    topic = short_topic_from_title(title)
    if not topic:
        topic = title.split("【", 1)[0].strip()

    row["meta_description"] = lib.meta_description_for({**row, "lead": ""}, topic)
    row["lead"] = lib.lead_for({**row, "lead": ""}, topic)
    row["user_intent"] = lib.user_intent_for(topic, row.get("genre") or "")
    row["action_items"] = lib.action_items_for(topic, slug, row.get("genre") or "")
    row["key_points"] = lib.key_points_for(row, topic)
    if "primary_sources" in fieldnames:
        row["primary_sources"] = primary_sources_for_venue(slug, site_root)

    ctx: dict = {}
    for idx, heading in enumerate(VENUE_SECTIONS, start=1):
        hcol = f"section_{idx}_heading"
        bcol = f"section_{idx}_body"
        if hcol in fieldnames:
            row[hcol] = heading
        if bcol in fieldnames:
            row[bcol] = lib.section_body_for(heading, topic, slug, row.get("genre") or "", ctx)

    for idx in range(len(VENUE_SECTIONS) + 1, 9):
        for suffix in ("heading", "body"):
            col = f"section_{idx}_{suffix}"
            if col in fieldnames:
                row[col] = ""

    for idx, (question, answer) in enumerate(venue_faq(topic, slug, site_root=site_root, lib=lib), start=1):
        qcol = f"faq_{idx}_question"
        acol = f"faq_{idx}_answer"
        if qcol in fieldnames:
            row[qcol] = question
        if acol in fieldnames:
            row[acol] = answer

    for idx in range(4, 5):
        for suffix in ("question", "answer"):
            col = f"faq_{idx}_{suffix}"
            if col in fieldnames:
                row[col] = ""

    return row


def norm(s: str | None) -> str:
    return (s or "").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="会場ガイド記事（*-center）を専用テンプレで修復")
    parser.add_argument("--target", type=Path, required=True, help="サイトルート")
    parser.add_argument("--slug", action="append", help="対象 slug（省略時は *-center 全件）")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    site_root = args.target.resolve()
    guide_csv = site_root / "data" / "guide_articles.csv"
    if not guide_csv.is_file():
        print(f"guide_articles.csv not found: {guide_csv}", file=sys.stderr)
        return 1

    lib = load_site_lib(site_root)
    with guide_csv.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    targets = set(args.slug or [])
    patched: list[str] = []
    for i, row in enumerate(rows):
        slug = norm(row.get("slug"))
        if not slug:
            continue
        if targets and slug not in targets:
            continue
        if not targets and not is_venue_center_article(slug, norm(row.get("title"))):
            continue
        rows[i] = patch_venue_row(row, fieldnames, site_root=site_root, lib=lib)
        patched.append(slug)

    if not patched:
        print("No venue center articles matched.", file=sys.stderr)
        return 1

    if args.dry_run:
        print("Would patch:", ", ".join(patched))
        return 0

    with guide_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    ok = 0
    for row in rows:
        slug = norm(row.get("slug"))
        if slug not in patched:
            continue
        issues = check_guide_row_coherence(row, published=is_published_guide(row))
        errs = [x for x in issues if x.level == "ERROR"]
        if errs:
            print(f"WARN post-patch {slug}: {len(errs)} coherence errors remain", file=sys.stderr)
        else:
            ok += 1
    print(f"Patched {len(patched)} venue center articles in {guide_csv} ({ok} pass coherence)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
