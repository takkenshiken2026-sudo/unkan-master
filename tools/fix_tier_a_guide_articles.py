#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A級ガイド記事の量産テンプレ崩れ（内部マーカー・見出し不一致）を修復する。"""

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

from tools.build_article_pages import sanitize_guide_text  # noqa: E402
from tools.editorial_quality import is_published_guide  # noqa: E402
from tools.guide_coherence_rules import (  # noqa: E402
    INTERNAL_MARKER_RE,
    check_guide_row_coherence,
    is_tier_a_slug,
    short_topic_from_title,
)

GUIDE_CSV = ROOT / "data" / "guide_articles.csv"
OFFICIAL_URL = "安全衛生技術試験協会（公式）|https://www.jissh.or.jp/"

GARBAGE_PHRASES = (
    "の観点で整理します",
    "現場判断と3分野",
    "付箋を付けながら読み",
    "演習で同テーマの設問を1問以上",
)

PLACEHOLDER_ACTION = re.compile(r"^【行動\d+】")


def norm(s: str | None) -> str:
    return (s or "").strip()


def _load_lib():
    try:
        from tools.archive.eisei2shu_guide_content_lib import (  # noqa: E402
            action_items_for,
            faq_answer_for,
            is_stub,
            key_points_for,
            lead_for,
            meta_description_for,
            section_body_for,
            user_intent_for,
        )

        return (
            section_body_for,
            lead_for,
            meta_description_for,
            user_intent_for,
            action_items_for,
            key_points_for,
            faq_answer_for,
            is_stub,
        )
    except ImportError as exc:
        raise SystemExit(
            "eisei2shu_guide_content_lib が見つかりません。"
            " exam-site-shell を PYTHONPATH に含めて実行してください。"
        ) from exc


def is_venue_slug(slug: str) -> bool:
    return slug.endswith("-center")


def row_needs_patch(row: dict[str, str], is_stub) -> bool:
    slug = norm(row.get("slug"))
    if not slug or not is_tier_a_slug(slug) or is_venue_slug(slug):
        return False
    for col in list(row.keys()):
        if not col.endswith("_body") and col not in ("lead", "user_intent", "action_items"):
            continue
        text = norm(row.get(col))
        if not text:
            continue
        if INTERNAL_MARKER_RE.search(text):
            return True
        if any(p in text for p in GARBAGE_PHRASES):
            return True
        if is_stub(text):
            return True
        if col == "action_items" and PLACEHOLDER_ACTION.search(text):
            return True
    for n in range(1, 8):
        heading = norm(row.get(f"section_{n}_heading"))
        body = norm(row.get(f"section_{n}_body"))
        if not heading or not body:
            continue
        if "持ち物" in heading and any(
            p in body for p in ("参考書を増やさず", "得点率が低い", "用語10語", "演習20問")
        ):
            return True
    return False


def patch_row(row: dict[str, str], fieldnames: list[str], lib) -> dict[str, str]:
    (
        section_body_for,
        lead_for,
        meta_description_for,
        user_intent_for,
        action_items_for,
        key_points_for,
        faq_answer_for,
        _is_stub,
    ) = lib
    row = {k: row.get(k, "") for k in fieldnames}
    slug = norm(row.get("slug"))
    title = norm(row.get("title"))
    topic = short_topic_from_title(title) or topic_from_title_fallback(title)
    genre = norm(row.get("genre"))
    ctx: dict = {}

    row["meta_description"] = meta_description_for({**row, "lead": ""}, topic)
    row["lead"] = lead_for({**row, "lead": ""}, topic)
    row["user_intent"] = user_intent_for(topic, genre)
    if PLACEHOLDER_ACTION.search(norm(row.get("action_items"))) or not norm(row.get("action_items")):
        row["action_items"] = action_items_for(topic, slug, genre)
    row["key_points"] = key_points_for(row, topic)
    if "primary_sources" in fieldnames and not norm(row.get("primary_sources")):
        row["primary_sources"] = OFFICIAL_URL

    for idx in range(1, 9):
        hcol = f"section_{idx}_heading"
        bcol = f"section_{idx}_body"
        heading = norm(row.get(hcol))
        if not heading:
            if bcol in fieldnames:
                row[bcol] = ""
            continue
        if bcol in fieldnames:
            body = section_body_for(heading, topic, slug, genre, ctx)
            row[bcol] = sanitize_guide_text(body, slug)

    for idx in range(1, 5):
        qcol = f"faq_{idx}_question"
        acol = f"faq_{idx}_answer"
        question = norm(row.get(qcol))
        if not question:
            continue
        if acol in fieldnames:
            answer = faq_answer_for(question, topic, slug, row, faq_index=idx)
            row[acol] = sanitize_guide_text(answer, slug)

    return row


def topic_from_title_fallback(title: str) -> str:
    t = norm(title)
    for prefix in ("第二種衛生管理者試験の", "第二種衛生管理者試験｜"):
        if t.startswith(prefix):
            t = t[len(prefix) :].strip()
    return t.split("【", 1)[0].strip() or t


def main() -> int:
    parser = argparse.ArgumentParser(description="A級ガイド記事のテンプレ崩れを修復")
    parser.add_argument("--slug", action="append", help="対象 slug（省略時は要修復の A級全件）")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    lib = _load_lib()

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
        if not targets and not row_needs_patch(row, lib[7]):
            continue
        if is_venue_slug(slug):
            continue
        rows[i] = patch_row(row, fieldnames, lib)
        patched.append(slug)

    if not patched:
        print("No tier-A articles matched.", file=sys.stderr)
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
            print(f"WARN post-patch {slug}: {len(errs)} coherence errors", file=sys.stderr)
            for e in errs[:3]:
                print(f"  {e.column}: {e.message}", file=sys.stderr)
        else:
            ok += 1
    print(f"Patched {len(patched)} tier-A articles in {GUIDE_CSV} ({ok} pass coherence)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
