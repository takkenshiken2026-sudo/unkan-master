#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""exam-venue-and-region / shiken-kaijo 等の会場ハブ記事に公式リンクを載せる。"""

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
    HUB_SLUGS,
    md_link,
    primary_sources_for_hub,
    venue_official_md,
)
from tools.fix_guide_duplicate_bodies import load_site_lib  # noqa: E402
from tools.guide_coherence_rules import check_guide_row_coherence, short_topic_from_title  # noqa: E402
from tools.guide_exam_day_faq import faq_answer_for_belongings_question  # noqa: E402

HUB_FAQ_ACCESS = (
    "会場の住所やアクセスはどこで確認しますか？",
    "{venue_md}の受験案内および会場案内で、会場名・所在地・アクセスを確認してください。"
    "本人に割り当てられた試験会場の正式名称・住所は受験票の表記が正本です。"
    "試験日が近づいたら前日までにルートと所要時間を確定し、"
    "当日は開始時刻の30分前到着を目安に余裕を持って向かってください。",
)


def is_hub_article(slug: str) -> bool:
    return slug in HUB_SLUGS or slug.startswith("exam-venue")


def patch_hub_row(
    row: dict[str, str],
    fieldnames: list[str],
    *,
    site_root: Path,
    lib,
) -> dict[str, str]:
    row = {k: row.get(k, "") for k in fieldnames}
    slug = (row.get("slug") or "").strip()
    title = (row.get("title") or "").strip()
    topic = short_topic_from_title(title) or title.split("【", 1)[0].strip()
    venue_md = venue_official_md(site_root)

    if "primary_sources" in fieldnames:
        row["primary_sources"] = primary_sources_for_hub(slug, site_root)

    for idx in range(1, 9):
        hcol = f"section_{idx}_heading"
        bcol = f"section_{idx}_body"
        heading = (row.get(hcol) or "").strip()
        if not heading or bcol not in fieldnames:
            continue
        if slug == "shiken-kaijo" and heading == "全国9センターの一覧":
            from tools.guide_content_shared import jissh_center_list_prose

            row[bcol] = jissh_center_list_prose(official=lib.OFFICIAL if hasattr(lib, "OFFICIAL") else "安全衛生技術試験協会（公式）")
        elif heading == "申込手順と会場":
            body = lib.section_body_for("申込手順と会場", topic, slug, row.get("genre") or "", {})
            if not body:
                body = lib.section_body_for("申込手順会場", topic, slug, row.get("genre") or "", {})
            if body:
                row[bcol] = body

    q_access, a_access = HUB_FAQ_ACCESS
    for idx in range(1, 4):
        qcol = f"faq_{idx}_question"
        acol = f"faq_{idx}_answer"
        q = (row.get(qcol) or "").strip()
        if not q:
            continue
        if "アクセス" in q or "住所" in q or "会場" in q:
            row[acol] = a_access.format(venue_md=venue_md)
        elif "持ち物" in q:
            official = getattr(lib, "OFFICIAL", "公式サイト")
            override = faq_answer_for_belongings_question(q, official=official)
            if override:
                row[acol] = override

    return row


def norm(s: str | None) -> str:
    return (s or "").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="会場ハブ記事に公式会場リンクを載せる")
    parser.add_argument("--target", type=Path, required=True, help="サイトルート")
    parser.add_argument("--slug", action="append")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    site_root = args.target.resolve()
    guide_csv = site_root / "data" / "guide_articles.csv"
    if not guide_csv.is_file():
        print(f"missing {guide_csv}", file=sys.stderr)
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
        if not targets and not is_hub_article(slug):
            continue
        rows[i] = patch_hub_row(row, fieldnames, site_root=site_root, lib=lib)
        patched.append(slug)

    if not patched:
        print("No hub venue articles matched.", file=sys.stderr)
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
        if not [x for x in issues if x.level == "ERROR"]:
            ok += 1
    print(f"Patched {len(patched)} hub articles in {guide_csv} ({ok} pass coherence)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
