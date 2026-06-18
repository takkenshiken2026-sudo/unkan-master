#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""非アフィリエイト試験ガイドを v4 執筆対象45本 + archived 91本に整理する。"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.editorial_quality import norm  # noqa: E402
from tools.guide_rewrite_rules import is_affiliate_row  # noqa: E402

CSV_PATH = ROOT / "data" / "guide_articles.csv"
RETIRED_JSON = ROOT / "data" / "guide_retired.json"

# v4 執筆対象（非アフィリエイト45本）
V4_KEEP_SLUGS: frozenset[str] = frozenset(
    {
        # Tier A — 制度・申込（15）
        "exam-overview",
        "official-info-sources",
        "exam-eligibility",
        "work-experience-requirement",
        "exam-schedule",
        "exam-fees",
        "exam-application-flow",
        "application-deadline-checklist",
        "exam-venue-and-region",
        "pass-score",
        "pass-rate",
        "exam-difficulty",
        "exam-format-overview",
        "subject-breakdown",
        "exam-scope-overview",
        # Tier B — 学習・演習（20）
        "syllabus-how-to-read",
        "weight-by-topic",
        "time-limit-strategy",
        "scope-vs-past-questions",
        "study-plan",
        "study-plan-3months",
        "study-plan-6months",
        "study-plan-working",
        "study-plan-beginner",
        "self-study-start",
        "self-study-mistakes",
        "textbook-vs-past-questions",
        "past-question-strategy",
        "past-questions-by-field",
        "timed-practice",
        "field-jigyo-basics",
        "field-vehicle-basics",
        "field-traffic-basics",
        "field-labor-basics",
        "field-practice-basics",
        # Tier C — 直前・横断（10）
        "review-cycle-spaced",
        "glossary-how-to",
        "final-day-checklist",
        "exam-day-items",
        "exam-day-flow",
        "retake-strategy",
        "after-pass-procedure",
        "pass-only-past-questions-myth",
        "syllabus-update-tracker",
        "registration-after-pass",
    }
)

# draft→archived 化する21本のリダイレクト先
NEW_ARCHIVED_REDIRECTS: dict[str, str] = {
    "note-taking-method": "review-cycle-spaced",
    "pass-announcement-guide": "after-pass-procedure",
    "past-questions-by-year": "past-question-strategy",
    "past-questions-first-attempt": "past-question-strategy",
    "past-questions-latest-year": "past-question-strategy",
    "past-questions-review-cycle": "review-cycle-spaced",
    "past-questions-score-analysis": "past-question-strategy",
    "past-questions-wrong-reasons": "past-question-strategy",
    "plateau-breakthrough": "review-cycle-spaced",
    "scope-revision-history": "syllabus-update-tracker",
    "score-gap-analysis": "retake-strategy",
    "self-study-environment": "self-study-start",
    "self-study-motivation": "self-study-start",
    "self-study-roadmap": "self-study-start",
    "self-study-schedule": "self-study-start",
    "self-study-without-school": "self-study-start",
    "simulation-exam-schedule": "timed-practice",
    "study-hours-myth": "study-plan",
    "study-plan-1year": "study-plan-6months",
    "textbook-selection": "textbook-vs-past-questions",
    "time-management": "study-plan-working",
}

V4_DRAFT_NOTE = "v4待ち·ゼロ執筆"
V4_ARCHIVED_NOTE = "archived·v4整理45本"


def _ensure_retire_redirect(note: str, target: str) -> str:
    token = f"retire_redirect:{target}"
    n = norm(note)
    if token in n:
        return n
    parts = [p.strip() for p in n.split(";") if p.strip()]
    parts = [p for p in parts if not p.startswith("retire_redirect:")]
    parts.append(token)
    return ";".join(parts)


def _merge_retired_json(extra: dict[str, str], *, today: str, dry_run: bool) -> int:
    data: dict = {"updated": today, "redirects": {}}
    if RETIRED_JSON.is_file():
        data = json.loads(RETIRED_JSON.read_text(encoding="utf-8"))
    redirects: dict[str, str] = dict(data.get("redirects") or {})
    added = 0
    for slug, target in extra.items():
        if redirects.get(slug) != target:
            redirects[slug] = target
            added += 1
    # 退役先が archived になった slug の参照を修正
    if redirects.get("problem-book-selection") == "textbook-selection":
        redirects["problem-book-selection"] = "textbook-vs-past-questions"
        added += 1
    data["redirects"] = dict(sorted(redirects.items()))
    data["updated"] = today
    if not dry_run:
        RETIRED_JSON.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return added


def curate_rows(rows: list[dict[str, str]], *, today: str) -> dict[str, int]:
    stats = {"keep_draft": 0, "archived": 0, "affiliate_skip": 0, "errors": 0}
    for row in rows:
        slug = norm(row.get("slug"))
        if not slug:
            stats["errors"] += 1
            continue
        if is_affiliate_row(row):
            stats["affiliate_skip"] += 1
            continue
        if slug in V4_KEEP_SLUGS:
            if norm(row.get("content_status")).lower() != "draft":
                row["content_status"] = "draft"
            row["revision_note"] = V4_DRAFT_NOTE
            stats["keep_draft"] += 1
            continue
        row["content_status"] = "archived"
        row["revision_note"] = V4_ARCHIVED_NOTE
        target = NEW_ARCHIVED_REDIRECTS.get(slug)
        if target:
            row["original_note"] = _ensure_retire_redirect(row.get("original_note") or "", target)
        stats["archived"] += 1
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description="試験ガイドを v4 45本 + archived に整理")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not CSV_PATH.is_file():
        print(f"missing {CSV_PATH}", file=sys.stderr)
        return 1
    today = date.today().isoformat()
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    non_aff = [r for r in rows if not is_affiliate_row(r)]
    missing_keep = sorted(V4_KEEP_SLUGS - {norm(r.get("slug")) for r in non_aff})
    if missing_keep:
        print("missing keep slugs in CSV:", missing_keep, file=sys.stderr)
        return 1
    stats = curate_rows(rows, today=today)
    retired_added = _merge_retired_json(NEW_ARCHIVED_REDIRECTS, today=today, dry_run=args.dry_run)
    mode = "would write" if args.dry_run else "wrote"
    print(
        f"{mode}: keep_draft={stats['keep_draft']} archived={stats['archived']} "
        f"affiliate_unchanged={stats['affiliate_skip']} retired_json_updates={retired_added}"
    )
    if not args.dry_run:
        with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
