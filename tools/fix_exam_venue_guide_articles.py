#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""*-center 等の会場ガイド記事を専用テンプレで差し替える（eisei2shu 向け）。"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SHELL = Path.home() / "Projects" / "exam-site-shell"
if str(SHELL) not in sys.path:
    sys.path.insert(0, str(SHELL))

from tools.guide_coherence_rules import is_tier_a_slug, short_topic_from_title  # noqa: E402
from tools.guide_coherence_rules import check_guide_row_coherence  # noqa: E402
from tools.editorial_quality import is_published_guide  # noqa: E402

GUIDE_CSV = ROOT / "data" / "guide_articles.csv"
OFFICIAL_URL = "安全衛生技術試験協会（公式）|https://www.jissh.or.jp/"

VENUE_SECTIONS = [
    "基本情報",
    "アクセス方法",
    "試験日程の確認方法",
    "申込の注意点",
    "試験当日の持ち物",
    "まとめ",
]

VENUE_FAQ = [
    (
        "この会場で受験する人はこの記事を読むべきですか？",
        "該当地域で第二種衛生管理者試験を受験する予定の方は、受験地選択と会場アクセスの確認に本記事が役立ちます。"
        "試験範囲の学習は公式テキストと演習問題で進め、日程・会場・持ち物だけは安全衛生技術試験協会（公式）で最新情報を確認してください。",
    ),
    (
        "会場の住所やアクセスはどこで確認しますか？",
        "会場の所在地・交通手段・アクセス方法は安全衛生技術試験協会（公式）の受験案内および各安全衛生技術センターの案内ページで確認してください。"
        "試験日が近づいたら前日までにルートと所要時間を確定し、当日は開始時刻の30分前到着を目安に余裕を持って向かってください。",
    ),
    (
        "試験当日の持ち物は何を準備すればよいですか？",
        "受験要項および受験票に記載された持ち物（鉛筆・消しゴム・身分証など）を前日に準備してください。"
        "禁止物品（スマートフォン、参考書など）は要項どおりに守り、筆記用具は予備があると当日のトラブルを減らせます。",
    ),
]


def _load_lib():
    try:
        from tools.archive.eisei2shu_guide_content_lib import (  # noqa: E402
            action_items_for,
            lead_for,
            meta_description_for,
            section_body_for,
            user_intent_for,
            key_points_for,
        )

        return section_body_for, lead_for, meta_description_for, user_intent_for, action_items_for, key_points_for
    except ImportError as exc:
        raise SystemExit(
            "eisei2shu_guide_content_lib が見つかりません。"
            " exam-site-shell を PYTHONPATH に含めて実行してください。"
        ) from exc


def is_venue_article(slug: str, title: str) -> bool:
    if not is_tier_a_slug(slug):
        return False
    if slug.endswith("-center"):
        return True
    return "安全衛生技術センター" in title or "試験会場" in title


def patch_venue_row(row: dict[str, str], fieldnames: list[str]) -> dict[str, str]:
    section_body_for, lead_for, meta_description_for, user_intent_for, action_items_for, key_points_for = _load_lib()
    row = {k: row.get(k, "") for k in fieldnames}
    slug = (row.get("slug") or "").strip()
    title = (row.get("title") or "").strip()
    topic = short_topic_from_title(title)
    if not topic:
        topic = title.split("【", 1)[0].strip()

    row["meta_description"] = meta_description_for({**row, "lead": ""}, topic)
    row["lead"] = lead_for({**row, "lead": ""}, topic)
    row["user_intent"] = user_intent_for(topic, row.get("genre") or "")
    row["action_items"] = action_items_for(topic, slug, row.get("genre") or "")
    row["key_points"] = key_points_for(row, topic)
    if "primary_sources" in fieldnames and not norm(row.get("primary_sources")):
        row["primary_sources"] = OFFICIAL_URL

    ctx: dict = {}
    for idx, heading in enumerate(VENUE_SECTIONS, start=1):
        hcol = f"section_{idx}_heading"
        bcol = f"section_{idx}_body"
        if hcol in fieldnames:
            row[hcol] = heading
        if bcol in fieldnames:
            row[bcol] = section_body_for(heading, topic, slug, row.get("genre") or "", ctx)

    for idx in range(len(VENUE_SECTIONS) + 1, 9):
        for suffix in ("heading", "body"):
            col = f"section_{idx}_{suffix}"
            if col in fieldnames:
                row[col] = ""

    for idx, (question, answer) in enumerate(VENUE_FAQ, start=1):
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
    parser.add_argument("--slug", action="append", help="対象 slug（省略時は *-center 全件）")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with GUIDE_CSV.open(encoding="utf-8-sig", newline="") as f:
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
        if not targets and not is_venue_article(slug, norm(row.get("title"))):
            continue
        rows[i] = patch_venue_row(row, fieldnames)
        patched.append(slug)

    if not patched:
        print("No venue articles matched.", file=sys.stderr)
        return 1

    if args.dry_run:
        print("Would patch:", ", ".join(patched))
        return 0

    with GUIDE_CSV.open("w", encoding="utf-8-sig", newline="") as f:
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
    print(f"Patched {len(patched)} venue articles in {GUIDE_CSV} ({ok} pass coherence)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
