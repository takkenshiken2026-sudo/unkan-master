#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""学習系ガイドへ公開済み affiliate 比較記事の導線を追加する（運管）。"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "guide_articles.csv"

AFFILIATE_TITLES = {
    "affiliate-textbooks-recommend": "運行管理者試験のおすすめテキスト3選【貨物・旅客2026】",
    "affiliate-problem-books": "運行管理者試験のおすすめ問題集3選【過去問2026】",
    "affiliate-mock-exam-materials": "運行管理者試験のCBT対策問題集3選【重要問題・令和8年8月版】",
}

BODY = {
    "affiliate-textbooks-recommend": (
        "テキスト1冊は、[おすすめテキスト3選](../affiliate-textbooks-recommend/) "
        "で貨物・旅客3冊を比較してから固定すると、途中で乗り換えずに済みます。"
    ),
    "affiliate-problem-books": (
        "演習1冊は、[おすすめ問題集3選](../affiliate-problem-books/) "
        "で過去問収録形式を比較してから12/20演習に組み込むと迷いが減ります。"
    ),
    "affiliate-mock-exam-materials": (
        "直前の重要問題演習は、[CBT対策問題集3選](../affiliate-mock-exam-materials/) "
        "で貨物・旅客の違いを確認してからCBT4週前のカレンダーに入れると安全です。"
    ),
}

GUIDE_AFFILIATE: dict[str, tuple[str, int]] = {
    "exam-overview": ("affiliate-textbooks-recommend", 2),
    "textbook-selection": ("affiliate-textbooks-recommend", 2),
    "study-plan": ("affiliate-textbooks-recommend", 2),
    "past-question-strategy": ("affiliate-problem-books", 2),
    "past-questions-by-field": ("affiliate-problem-books", 2),
    "pass-score": ("affiliate-problem-books", 2),
    "retake-strategy": ("affiliate-problem-books", 2),
    "final-day-checklist": ("affiliate-mock-exam-materials", 2),
    "self-study-roadmap": ("affiliate-textbooks-recommend", 2),
    "self-study-start": ("affiliate-textbooks-recommend", 2),
    "study-plan-3months": ("affiliate-textbooks-recommend", 2),
    "study-plan-6months": ("affiliate-textbooks-recommend", 2),
    "study-plan-1year": ("affiliate-textbooks-recommend", 2),
    "study-plan-working": ("affiliate-textbooks-recommend", 2),
    "study-plan-beginner": ("affiliate-textbooks-recommend", 2),
    "time-management": ("affiliate-textbooks-recommend", 2),
    "self-study-without-school": ("affiliate-textbooks-recommend", 2),
    "textbook-vs-past-questions": ("affiliate-textbooks-recommend", 2),
    "past-questions-by-year": ("affiliate-problem-books", 2),
    "past-questions-review-cycle": ("affiliate-problem-books", 2),
    "past-questions-first-attempt": ("affiliate-problem-books", 2),
    "timed-practice": ("affiliate-problem-books", 2),
    "simulation-exam-schedule": ("affiliate-mock-exam-materials", 2),
    "plateau-breakthrough": ("affiliate-problem-books", 2),
}

SECONDARY_AFFILIATE: dict[str, str] = {
    "exam-overview": "affiliate-problem-books",
    "textbook-selection": "affiliate-problem-books",
    "study-plan": "affiliate-problem-books",
    "past-question-strategy": "affiliate-textbooks-recommend",
    "pass-score": "affiliate-mock-exam-materials",
    "retake-strategy": "affiliate-mock-exam-materials",
    "final-day-checklist": "affiliate-problem-books",
    "self-study-roadmap": "affiliate-problem-books",
    "study-plan-working": "affiliate-mock-exam-materials",
    "simulation-exam-schedule": "affiliate-problem-books",
}


def _split_related(value: str) -> list[str]:
    return [x.strip() for x in (value or "").split(";") if x.strip()]


def _append_related(value: str, token: str) -> str:
    parts = _split_related(value)
    slug = token.split(":", 1)[0]
    if any(p.split(":", 1)[0] == slug for p in parts):
        return ";".join(parts)
    parts.append(token)
    return ";".join(parts)


def _append_body(body: str, aff_slug: str) -> str:
    sentence = BODY[aff_slug]
    if aff_slug in (body or "") or sentence in (body or ""):
        return body
    text = (body or "").rstrip()
    if not text:
        return sentence
    if not text.endswith("。"):
        text += "。"
    return text + sentence


def apply_guide_updates(rows: list[dict[str, str]]) -> int:
    by_slug = {r["slug"]: r for r in rows}
    changed = 0
    for slug, (aff_slug, sec_n) in GUIDE_AFFILIATE.items():
        row = by_slug.get(slug)
        if not row or (row.get("content_status") or "").strip() != "published":
            continue
        body_key = f"section_{sec_n}_body"
        old_body = row.get(body_key, "")
        new_body = _append_body(old_body, aff_slug)
        if new_body != old_body:
            row[body_key] = new_body

        token = f"{aff_slug}:{AFFILIATE_TITLES[aff_slug]}"
        new_rl = _append_related(row.get("related_links", ""), token)
        sec = SECONDARY_AFFILIATE.get(slug)
        if sec:
            new_rl = _append_related(new_rl, f"{sec}:{AFFILIATE_TITLES[sec]}")
        if new_rl != row.get("related_links", "") or new_body != old_body:
            row["related_links"] = new_rl
            changed += 1
    return changed


def main() -> None:
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames:
        raise SystemExit("guide_articles.csv: no header")

    changed = apply_guide_updates(rows)

    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Guide funnel: {len(GUIDE_AFFILIATE)} targets, {changed} row(s) updated")


if __name__ == "__main__":
    main()
