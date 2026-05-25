#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit guide articles for freshness, source quality, and update candidates."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "guide_articles.csv"


@dataclass
class Finding:
    level: str
    slug: str
    message: str


def norm(value: object) -> str:
    return str(value or "").strip()


def parse_date(value: str) -> date | None:
    text = norm(value)
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def split_semicolon(value: str) -> list[str]:
    return [item.strip() for item in norm(value).split(";") if item.strip()]


def wordish_len(value: str) -> int:
    return len(norm(value).replace(" ", "").replace("\n", ""))


def section_columns(row: dict[str, str]) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for idx in range(1, 9):
        heading = norm(row.get(f"section_{idx}_heading"))
        body = norm(row.get(f"section_{idx}_body"))
        if heading or body:
            out.append((str(idx), heading, body))
    return out


def audit_row(row: dict[str, str], *, today: date, stale_days: int) -> list[Finding]:
    slug = norm(row.get("slug")) or "(missing slug)"
    findings: list[Finding] = []

    status = norm(row.get("content_status"))
    if status and status not in {"draft", "review_needed", "published", "archived"}:
        findings.append(Finding("WARN", slug, f"content_status が推奨値外です: {status}"))
    if status in {"draft", "review_needed"}:
        findings.append(Finding("REVIEW", slug, f"content_status が {status} です"))

    next_review = parse_date(norm(row.get("next_review_at")))
    if not next_review:
        findings.append(Finding("REVIEW", slug, "next_review_at が未入力または YYYY-MM-DD 形式ではありません"))
    elif next_review <= today:
        findings.append(Finding("REVIEW", slug, f"next_review_at を過ぎています: {next_review.isoformat()}"))

    fact_checked = parse_date(norm(row.get("fact_checked_at")))
    if not fact_checked:
        findings.append(Finding("REVIEW", slug, "fact_checked_at が未入力または YYYY-MM-DD 形式ではありません"))
    elif (today - fact_checked).days >= stale_days:
        findings.append(Finding("REVIEW", slug, f"fact_checked_at から {stale_days} 日以上経過しています: {fact_checked.isoformat()}"))

    source_checked = parse_date(norm(row.get("source_checked_at")))
    if not source_checked:
        findings.append(Finding("REVIEW", slug, "source_checked_at が未入力または YYYY-MM-DD 形式ではありません"))

    sources = norm(row.get("primary_sources"))
    if not sources:
        findings.append(Finding("REVIEW", slug, "primary_sources が未入力です"))
    if "example.com" in sources or "YOUR-DOMAIN.example" in sources:
        findings.append(Finding("REVIEW", slug, "primary_sources がプレースホルダーURLのままです"))

    if not norm(row.get("author_name")):
        findings.append(Finding("REVIEW", slug, "author_name が未入力です"))
    if not norm(row.get("reviewer_name")):
        findings.append(Finding("REVIEW", slug, "reviewer_name が未入力です"))
    if wordish_len(norm(row.get("original_note"))) < 25:
        findings.append(Finding("WARN", slug, "original_note が短く、記事固有の視点が弱い可能性があります"))
    if wordish_len(norm(row.get("user_intent"))) < 25:
        findings.append(Finding("WARN", slug, "user_intent が短く、検索意図との対応が弱い可能性があります"))
    update_policy = norm(row.get("update_policy"))
    if "次回" in update_policy or "予定日" in update_policy:
        findings.append(Finding("WARN", slug, "update_policy には次回確認予定日を書かず、見直し条件だけを書いてください"))
    if update_policy and any(char.isdigit() for char in update_policy) and ("年" in update_policy or "-" in update_policy or "/" in update_policy):
        findings.append(Finding("WARN", slug, "update_policy に日付らしき表記があります。具体的な予定日は next_review_at で内部管理してください"))
    if len(split_semicolon(norm(row.get("action_items")))) < 3:
        findings.append(Finding("WARN", slug, "action_items は3件以上を推奨します"))
    if len(split_semicolon(norm(row.get("related_links")))) < 2:
        findings.append(Finding("WARN", slug, "related_links は2件以上を推奨します"))

    sections = section_columns(row)
    if len(sections) < 5:
        findings.append(Finding("WARN", slug, f"本文見出しが少なめです: {len(sections)} 件"))
    total_body_len = 0
    for idx, heading, body in sections:
        if not heading:
            findings.append(Finding("WARN", slug, f"section_{idx}_heading が空です"))
        body_len = wordish_len(body)
        total_body_len += body_len
        if body_len < 120:
            findings.append(Finding("WARN", slug, f"section_{idx}_body が短めです: {body_len} 文字"))
    if total_body_len < 900:
        findings.append(Finding("WARN", slug, f"本文合計が短めです: {total_body_len} 文字"))

    faq_count = 0
    for idx in range(1, 4):
        if norm(row.get(f"faq_{idx}_question")) and norm(row.get(f"faq_{idx}_answer")):
            faq_count += 1
    if faq_count < 2:
        findings.append(Finding("WARN", slug, f"FAQ は2件以上を推奨します: {faq_count} 件"))

    if not norm(row.get("revision_note")):
        findings.append(Finding("WARN", slug, "revision_note が未入力です"))

    return findings


def load_rows() -> list[dict[str, str]]:
    if not CSV_PATH.is_file():
        raise FileNotFoundError(str(CSV_PATH))
    return list(csv.DictReader(CSV_PATH.read_text(encoding="utf-8-sig").splitlines()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--today", default=date.today().isoformat(), help="Audit date in YYYY-MM-DD format")
    parser.add_argument("--stale-days", type=int, default=90, help="Days until fact_checked_at is considered stale")
    parser.add_argument("--fail-on-review", action="store_true", help="Exit 1 when REVIEW findings exist")
    args = parser.parse_args()

    today = parse_date(args.today)
    if not today:
        raise SystemExit("--today は YYYY-MM-DD 形式で指定してください")

    rows = load_rows()
    findings: list[Finding] = []
    for row in rows:
        findings.extend(audit_row(row, today=today, stale_days=args.stale_days))

    if not findings:
        print(f"Article freshness audit passed: {len(rows)} article(s), no findings")
        return 0

    by_slug: dict[str, list[Finding]] = {}
    for finding in findings:
        by_slug.setdefault(finding.slug, []).append(finding)

    print(f"Article freshness audit: {len(rows)} article(s), {len(findings)} finding(s)")
    for slug, group in by_slug.items():
        print(f"\n[{slug}]")
        for finding in group:
            print(f"- {finding.level}: {finding.message}")

    review_findings = [finding for finding in findings if finding.level == "REVIEW"]
    return 1 if args.fail_on_review and review_findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
