#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公開済み v4 試験ガイド21本の prose を整形する（例示・日付の過剰を削減）。"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.editorial_quality import norm  # noqa: E402

CSV_PATH = ROOT / "data" / "guide_articles.csv"
WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]
YEAR = 2026

# 令和8年第1回 — 読者が写す正本日付（曜日含む）
OFFICIAL_DATES: dict[tuple[int, int], str] = {
    (6, 15): "月",
    (7, 15): "水",
    (7, 29): "水",
    (8, 7): "金",
    (8, 8): "土",
    (9, 6): "日",
    (9, 24): "木",
}

# 学習計画記事だけCBT例示日を1つ残す
CBT_ANCHOR: tuple[int, int] = (8, 25)

PROSE_COLUMNS: tuple[str, ...] = (
    "lead",
    "user_intent",
    *(f"section_{n}_body" for n in range(1, 8)),
    *(f"faq_{n}_answer" for n in range(1, 4)),
)

ACTION_ITEMS = "action_items"

STUDY_SLUGS = frozenset({"study-plan", "study-plan-3months"})

MAX_EXAMPLES_PER_ARTICLE = 3
MAX_DATES_PER_ARTICLE = 0
MAX_DATES_STUDY_ARTICLE = 0

DATE_MD_RE = re.compile(
    r"(?<!\d)(?:(\d{1,2})月(\d{1,2})日（([月火水木金土日])）|(\d{1,2})/(\d{1,2})（([月火水木金土日])）)"
)
EXAMPLE_MARKER_RE = re.compile(r"例えば|たとえば")

# 先に当てる固定置換（シナリオ日→相対表現）
PHRASE_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (r"例えば6月19日（[月火水木金土日]）に(?:初めて調べる|判定を始める|算定を始める|触れる)なら、", "まず、"),
    (r"例えば6月19日（[月火水木金土日]）に", "まず、"),
    (r"例えば6月20日（[月火水木金土日]）に", ""),
    (r"例えば6月24日（[月火水木金土日]）に", ""),
    (r"例えば6月25日（[月火水木金土日]）に", ""),
    (r"例えば6月26日（[月火水木金土日]）に", ""),
    (r"例えば7月1日（[月火水木金土日]）に(?:Internet)?申請した(?:場合|ら)、", "Internet申請後、"),
    (r"例えば7月1日（[月火水木金土日]）に", "申込送信後、"),
    (r"7月8日（[月火水木金土日]）頃", "審査完了後（7～10日）"),
    (r"7月8日（[月火水木金土日]）", "審査完了後"),
    (r"7月9日（[月火水木金土日]）", "審査完了の翌日"),
    (r"7月10日（[月火水木金土日]）", "申込締切2週前"),
    (r"7月11日（[月火水木金土日]）", "審査完了直後"),
    (r"7月15日（火）", "7月15日（水）"),
    (r"6月24日（[月火水木金土日]）", "申込締切3週前"),
    (r"例えば7月8日（[月火水木金土日]）審査完了メール→7月9日（[月火水木金土日]）会場予約→7月10日（[月火水木金土日]）6,660円支払", "審査完了後24時間以内に会場予約と6,660円支払"),
    (r"たとえば「7月31日（[月火水木金土日]）講習修了→8月1日（[月火水木金土日]）修了証アップロード」", "講習修了日と修了証アップロード期限"),
    (r"たとえば8月20日（[月火水木金土日]）CBTに合わせ7月31日（[月火水木金土日]）講習修了なら、8月1日（[月火水木金土日]）までに", "CBT2週前までに講習を修了し、"),
    (r"例えば実務ルートなら7月10日（[月火水木金土日]）までに承認者へ「7月15日（火）締切前に承認メール送信」を依頼", "実務ルートなら申込締切4週前までに承認者へ承認メール依頼"),
    (r"たとえば「7月10日（[月火水木金土日]）までに承認者へ5項目依頼→7月15日（火）締切前に承認完了」", "申込締切4週前までに承認者へ依頼し、7月15日（水）締切前に承認完了"),
    (r"7月15日（火）17時締切", "7月15日（水）17時締切"),
    (r"7月15日（火）締切", "7月15日（水）締切"),
    (r"9月6日（土）", "9月6日（日）"),
    (r"9月7日（日）", "CBT翌日"),
    (r"例えば2026年4月1日入社なら、2027年3月15日（日）CBTの前日まで", "2026年4月入社なら翌年3月CBT前日まで"),
    (r"7月15日（火）締切なら6月24日（[月火水木金土日]）から", "7月15日（水）締切なら4週前から"),
)

STUDY_DATE_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (r"例えば6/2（[月火水木金土日]）開始·8/25（火）CBTなら、6/14（日）ベースライン·7/28（火）18/30\+②2連続、を", "CBT日から84日前を開始日に逆算し、第2週末に30問ベースライン、第8週までに18/30+②2連続を"),
    (r"例えば6/2（[月火水木金土日]）開始·8/25（火）CBTなら", "CBT日8/25（火）から84日前開始なら"),
    (r"6/14（[月火水木金土日]）", "第2週末"),
    (r"7/28（[月火水木金土日]）", "第9週"),
    (r"8/18（[月火水木金土日]）", "第12週"),
    (r"6/30（[月火水木金土日]）", "第8週"),
    (r"7/20（[月火水木金土日]）", "第7週"),
    (r"7/14（[月火水木金土日]）", "第8週"),
    (r"7/13（[月火水木金土日]）", "第7週"),
    (r"6/29（[月火水木金土日]）", "第4週"),
    (r"8/4（[月火水木金土日]）", "第10週"),
    (r"8/5（[月火水木金土日]）", "翌週"),
    (r"8/11（[月火水木金土日]）", "CBT2週前"),
    (r"6/16（[月火水木金土日]）", "第3週"),
    (r"6/2（[月火水木金土日]）", "開始週"),
    (r"6/2（[月火水木金土日]）～6/14（[月火水木金土日]）", "第1～2週"),
    (r"たとえば「第7週7/20 （2）0/4·（4）1/6→各\+3h/週」", "第7週時点で（2）0/4·（4）1/6なら各+3h/週"),
)


def _date_key(m: re.Match[str]) -> tuple[int, int]:
    if m.group(1):
        return int(m.group(1)), int(m.group(2))
    return int(m.group(4)), int(m.group(5))


def _date_weekday(m: re.Match[str]) -> str:
    return m.group(3) or m.group(6) or ""


def fix_official_weekdays(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        key = _date_key(m)
        wd = _date_weekday(m)
        if key in OFFICIAL_DATES:
            mo, d = key
            return f"{mo}月{d}日（{OFFICIAL_DATES[key]}）"
        if key == CBT_ANCHOR:
            mo, d = key
            actual = WEEKDAY_JP[datetime(YEAR, mo, d).weekday()]
            return f"{mo}/{d}（{actual}）" if "/" in m.group(0) else f"{mo}月{d}日（{actual}）"
        # 2026年として曜日だけ正す
        mo, d = key
        try:
            actual = WEEKDAY_JP[datetime(YEAR, mo, d).weekday()]
        except ValueError:
            return m.group(0)
        if actual == wd:
            return m.group(0)
        if "月" in m.group(0):
            return f"{mo}月{d}日（{actual}）"
        return f"{mo}/{d}（{actual}）"

    return DATE_MD_RE.sub(repl, text)


def apply_phrase_replacements(text: str, *, study: bool) -> str:
    for pat, rep in PHRASE_REPLACEMENTS:
        text = re.sub(pat, rep, text)
    if study:
        for pat, rep in STUDY_DATE_REPLACEMENTS:
            text = re.sub(pat, rep, text)
    return text


def _is_table_line(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.count("|") >= 2


def _keep_date(key: tuple[int, int], *, study: bool, kept_anchor: bool) -> bool:
    if key in OFFICIAL_DATES:
        return True
    if study and key == CBT_ANCHOR:
        return True
    if study and not kept_anchor and key == CBT_ANCHOR:
        return True
    return False


def trim_dates(text: str, *, study: bool, budget: list[int]) -> str:
    """記事全体の日付上限内で、非正本のカレンダー日を削る。"""

    lines_out: list[str] = []
    anchor_kept = False

    for line in text.split("\n"):
        if _is_table_line(line):
            # 表内の日付レンジは週番号表現へ（学習計画）
            if study:
                line = re.sub(r"\d{1,2}/\d{1,2}～\d{1,2}/\d{1,2}", "（CBT日から逆算）", line)
                line = re.sub(r"\d{1,2}/\d{1,2}", "第N週", line)
                line = re.sub(r"\d{1,2}月\d{1,2}日", "第N週", line)
            lines_out.append(line)
            continue

        def repl(m: re.Match[str]) -> str:
            nonlocal anchor_kept
            key = _date_key(m)
            if _keep_date(key, study=study, kept_anchor=anchor_kept):
                if key == CBT_ANCHOR:
                    anchor_kept = True
                return m.group(0)
            if budget[0] <= 0:
                return ""
            budget[0] -= 1
            return ""

        line = DATE_MD_RE.sub(repl, line)
        line = re.sub(r"[、,]{2,}", "、", line)
        line = re.sub(r"^[、,]\s*", "", line)
        line = re.sub(r"\s{2,}", " ", line)
        lines_out.append(line)

    return "\n".join(lines_out)


def cap_example_markers(text: str, budget: list[int]) -> str:
    """例えば/たとえば を記事上限以内に抑え、超過分はマーカーだけ除去。"""

    def repl(m: re.Match[str]) -> str:
        if budget[0] > 0:
            budget[0] -= 1
            return m.group(0)
        return ""

    return EXAMPLE_MARKER_RE.sub(repl, text)


def cleanup_prose(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" +", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[。]{2,}", "。", text)
    text = re.sub(r"、+", "、", text)
    text = re.sub(r"、。", "。", text)
    text = re.sub(r"。\s*、", "。", text)
    text = re.sub(r"、から", "、", text)
    text = re.sub(r"、に、", "、", text)
    text = re.sub(r"ならに", "なら", text)
    return text.strip()


def refine_field(text: str, *, study: bool, example_budget: list[int], date_budget: list[int]) -> str:
    if not text:
        return text
    text = apply_phrase_replacements(text, study=study)
    text = fix_official_weekdays(text)
    text = trim_dates(text, study=study, budget=date_budget)
    text = cap_example_markers(text, example_budget)
    return cleanup_prose(text)


def refine_action_items(text: str, *, study: bool) -> str:
    if not text:
        return text
    parts = [p.strip() for p in text.split(";") if p.strip()]
    out: list[str] = []
    for part in parts:
        part = apply_phrase_replacements(part, study=study)
        part = fix_official_weekdays(part)
        if study:
            for pat, rep in STUDY_DATE_REPLACEMENTS:
                part = re.sub(pat, rep, part)
            part = DATE_MD_RE.sub(lambda m: "" if _date_key(m) not in OFFICIAL_DATES and _date_key(m) != CBT_ANCHOR else m.group(0), part)
        part = EXAMPLE_MARKER_RE.sub("", part)
        part = cleanup_prose(part)
        if part:
            out.append(part)
    return ";".join(out)


def refine_row(row: dict[str, str]) -> bool:
    if row.get("content_status") != "published":
        return False
    if "v4" not in (row.get("revision_note") or ""):
        return False

    study = row["slug"] in STUDY_SLUGS
    max_dates = MAX_DATES_STUDY_ARTICLE if study else MAX_DATES_PER_ARTICLE
    example_budget = [MAX_EXAMPLES_PER_ARTICLE]
    date_budget = [max_dates]

    changed = False
    for col in PROSE_COLUMNS:
        raw = row.get(col, "") or ""
        new = refine_field(raw, study=study, example_budget=example_budget, date_budget=date_budget)
        if new != raw:
            row[col] = new
            changed = True

    raw_ai = row.get(ACTION_ITEMS, "") or ""
    new_ai = refine_action_items(raw_ai, study=study)
    if new_ai != raw_ai:
        row[ACTION_ITEMS] = new_ai
        changed = True

    if changed:
        note = norm(row.get("revision_note"))
        if "文体整形" not in note:
            row["revision_note"] = note + "·文体整形"
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(description="公開 v4 ガイド21本の prose を整形")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8-sig")))
    if not rows:
        print("empty csv", file=sys.stderr)
        return 1
    fieldnames = list(rows[0].keys())

    changed_slugs: list[str] = []
    for row in rows:
        if refine_row(row):
            changed_slugs.append(row["slug"])

    print(f"refined {len(changed_slugs)} row(s)")
    for slug in changed_slugs:
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
