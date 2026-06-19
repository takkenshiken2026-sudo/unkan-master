#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ガイド記事 prose から不要なカレンダー日付を除去する。

方針:
- 日付の正本は受験案内PDF。本文では繰り返し書かない。
- exam-schedule / application-deadline-checklist の「締切一覧表」1箇所だけ日付を残す。
- それ以外は「申込締切」「CBT予定日」等のラベルか相対表現に置換。
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "guide_articles.csv"

PROSE_COLUMNS: tuple[str, ...] = (
    "lead",
    "user_intent",
    *(f"section_{n}_heading" for n in range(1, 8)),
    *(f"section_{n}_body" for n in range(1, 8)),
    *(f"faq_{n}_answer" for n in range(1, 4)),
    "action_items",
)

# 締切一覧表だけ日付を残す (slug -> 列名の set)
DATE_TABLE_FIELDS: dict[str, frozenset[str]] = {
    "exam-schedule": frozenset({"section_1_body"}),
    "application-deadline-checklist": frozenset({"section_1_body"}),
}

DATE_MD_RE = re.compile(
    r"(?<!\d)(?:(\d{1,2})月(\d{1,2})日（[月火水木金土日]）|(\d{1,2})/(\d{1,2})（[月火水木金土日]）)"
)

# 長いパターンから順に（範囲→単日）
DATE_TO_LABEL: tuple[tuple[str, str], ...] = (
    (r"6月15日（[月火水木金土日]）～7月15日（[月火水木金土日]）", "申込期間（PDF参照）"),
    (r"8月8日（[月火水木金土日]）～9月6日（[月火水木金土日]）", "CBT期間（PDF参照）"),
    (r"6月15日（[月火水木金土日]）", "申込開始日"),
    (r"7月15日（[月火水木金土日]）", "申込締切"),
    (r"7月29日（[月火水木金土日]）", "提出·承認締切"),
    (r"8月7日（[月火水木金土日]）", "会場予約締切"),
    (r"8月8日（[月火水木金土日]）", "CBT開始日"),
    (r"9月6日（[月火水木金土日]）", "CBT終了日"),
    (r"9月24日（[月火水木金土日]）（予定）", "結果公表日（予定）"),
    (r"9月24日（[月火水木金土日]）", "結果公表日"),
    (r"8/25（[月火水木金土日]）", "CBT予定日"),
    (r"7/1（[月火水木金土日]）", "申込期間中"),
    (r"7/15（[月火水木金土日]）", "申込締切"),
    (r"8/7（[月火水木金土日]）", "会場予約締切"),
    (r"9/10（[月火水木金土日]）", "試験期間後半"),
)

HEADING_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (r"7月1日（[月火水木金土日]） — 申請締切14日前の下準備", "14日前 — 下準備"),
    (r"7月8日（[月火水木金土日]） — 申請送信と審査待ちの1週間", "7日前 — 申請送信と審査待ち"),
    (r"8月7日（[月火水木金土日]）前 — 予約と6,660円を同日で", "予約締切前 — 予約と6,660円を同日で"),
    (r"STEP1申請 — 7月15日（[月火水木金土日]）締切までに送る内容", "STEP1申請 — 申込締切までに送る内容"),
    (r"7/8起点 — 8/25（[月火水木金土日]）CBTまでの分野ローテ", "CBT42日前 — 分野ローテ"),
    (r"7/7起点 — 8/25（[月火水木金土日]）CBTまで週10時間", "CBT42日前 — 週10時間"),
    (r"7/1（[月火水木金土日]）·申込前 — 改定確認の3点差分", "申込前 — 改定確認の3点差分"),
    (r"定員制と満席 — 8/7（[月火水木金土日]）締切までの逆算", "定員制と満席 — 予約締切までの逆算"),
)

PROSE_CLEANUPS: tuple[tuple[str, str], ...] = (
    ("会場予約締切予約締切", "会場予約締切"),
    ("会場予約締切締切", "会場予約締切"),
    ("申込締切申請", "申込完了"),
    ("たとえば時点で", "中間時点で"),
    ("、に承認者", "、承認者"),
    ("たとえばに審査", "審査"),
)

LEAD_CLEANUPS: tuple[tuple[str, str], ...] = (
    (
        r"受験案内PDFから6月15日（[月火水木金土日]）申請開始と8月7日（[月火水木金土日]）会場予約締切の2行",
        "受験案内PDFの申込期間と4締切の表",
    ),
    (
        r"令和8年第1回では7月15日（[月火水木金土日]）申請締切と8月7日（[月火水木金土日]）会場予約締切が3週間以上離れます",
        "令和8年第1回では申込締切と会場予約締切が3週間以上離れます",
    ),
    (
        r"8/25（[月火水木金土日]）CBT",
        "CBT予定日",
    ),
    (
        r"8/25（[月火水木金土日]）",
        "CBT予定日",
    ),
)


def _is_table_line(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.count("|") >= 2


def replace_calendar_dates(text: str, *, is_heading: bool = False) -> str:
    if is_heading:
        for pat, label in HEADING_REPLACEMENTS:
            text = re.sub(pat, label, text)
    for pat, label in DATE_TO_LABEL:
        text = re.sub(pat, label, text)
    for old, new in PROSE_CLEANUPS:
        text = text.replace(old, new)
    return text


def trim_field(text: str, *, slug: str, col: str) -> str:
    if not text:
        return text

    if col == "action_items":
        parts = [
            replace_calendar_dates(p.strip()) for p in text.split(";") if p.strip()
        ]
        return ";".join(cleanup_prose(p) for p in parts if p)

    is_heading = col.endswith("_heading")
    if is_heading:
        return cleanup_prose(replace_calendar_dates(text, is_heading=True))

    preserve_table = col in DATE_TABLE_FIELDS.get(slug, frozenset())
    if col == "lead":
        for pat, rep in LEAD_CLEANUPS:
            text = re.sub(pat, rep, text)

    out_lines: list[str] = []
    for line in text.split("\n"):
        if preserve_table and _is_table_line(line):
            out_lines.append(line)
        else:
            out_lines.append(replace_calendar_dates(line))
    return cleanup_prose("\n".join(out_lines))


def cleanup_prose(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"、+", "、", text)
    text = re.sub(r"、。", "。", text)
    text = re.sub(r"（PDF参照）（PDF参照）", "（PDF参照）", text)
    return text.strip()


def should_process(row: dict[str, str]) -> bool:
    return row.get("content_status") == "published" and "v4" in (row.get("revision_note") or "")


def trim_row(row: dict[str, str]) -> bool:
    slug = row["slug"]
    changed = False
    for col in PROSE_COLUMNS:
        raw = row.get(col, "") or ""
        new = trim_field(raw, slug=slug, col=col)
        if new != raw:
            row[col] = new
            changed = True
    if changed:
        note = (row.get("revision_note") or "").strip()
        if "日付整理" not in note:
            row["revision_note"] = note + "·日付整理"
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(description="ガイド prose から不要なカレンダー日付を除去")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8-sig")))
    fieldnames = list(rows[0].keys())
    changed: list[str] = []
    for row in rows:
        if should_process(row) and trim_row(row):
            changed.append(row["slug"])

    print(f"trimmed {len(changed)} row(s)")
    for slug in changed:
        print(f"  {slug}")

    if args.dry_run:
        return 0

    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
