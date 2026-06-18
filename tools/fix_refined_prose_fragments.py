#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""refine_published_guide_prose 後の欠落日付・文断れを手当てする。"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "guide_articles.csv"

PROSE_COLUMNS: tuple[str, ...] = (
    "lead",
    "user_intent",
    *(f"section_{n}_body" for n in range(1, 8)),
    *(f"faq_{n}_answer" for n in range(1, 4)),
    "action_items",
)

GLOBAL_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("CBTならに90分", "CBT2週前なら90分"),
    ("申込なら審査完了後", "申込直後は審査完了まで"),
    ("から（2）4問を12分", "まず（2）4問を12分"),
    ("から（4）6問を18分", "第3週から（4）6問を18分"),
    ("、から分野（1）", "、翌日から分野（1）"),
    ("、から7週間で逆算", "、CBT42日前から7週間で逆算"),
    ("、から7週間で分野", "、CBT42日前から7週間で分野"),
    ("第4週第4週に", "第4週日曜に"),
    ("を検討するか、から弱点", "を検討するか、または第8週から弱点"),
    (
        "に「18/30·8/6·4/3·5/4·6/2·7/3」を記録、（4）（5）②未達のみ+2h、から（4）10問·（5）10問/週に増やしてください。",
        "日曜シートに18/30·8/4/5/6/7行を記録し、（4）（5）が②未達なら翌週から各10問/週に増やしてください。",
    ),
    (
        "例えば開始週計画開始なら要項④転記、",
        "84日前開始なら要項④転記、",
    ),
    (
        "CBT延期か弱点配分強化の2択です。第7週時点で②未達が3分野なら8/25（火）CBTは厳しいため次回回へ延期、または第8週から週12時間·弱点60%に切り替え、社会人計画記事も参照してください。",
        "CBT延期か弱点配分強化の2択です。第7週時点で②未達が3分野なら次回回への延期を検討するか、第8週から週12時間·弱点60%に切り替え、社会人計画記事も参照してください。",
    ),
    (
        "要項·教材·環境·30問計測準備です。開始週～第2週末に要項60分、市販教材決定、第2週末30問90分計測をカレンダー登録してください。演習量より計測と②弱点特定を第1～2週で優先します。",
        "要項·教材·環境·30問計測準備です。第1～2週で要項60分、市販教材決定、第2週末の30問90分計測をカレンダー登録してください。演習量より計測と②弱点特定を優先します。",
    ),
    (
        "いいえ。1回の募集で申し込める試験は貨物か旅客のどちらか一方です。令和8年第1回で貨物30問を受けたら、同じ回で旅客30問は申込めません。両区分が必要なら別回の受験計画が必要です（要項で再確認）。",
        "いいえ。1回の募集で申し込める試験は貨物か旅客のどちらか一方です。令和8年第1回で貨物30問を受けたら、同じ回で旅客30問は申込めません。両区分が必要なら別回の受験計画を立ててください（要項で再確認）。",
    ),
)


def fix_text(text: str) -> str:
    if not text:
        return text
    for old, new in GLOBAL_REPLACEMENTS:
        text = text.replace(old, new)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8-sig")))
    fieldnames = list(rows[0].keys())
    changed = 0
    for row in rows:
        if row.get("content_status") != "published" or "v4" not in (row.get("revision_note") or ""):
            continue
        for col in PROSE_COLUMNS:
            raw = row.get(col, "") or ""
            new = fix_text(raw)
            if new != raw:
                row[col] = new
                changed += 1

    print(f"fixed {changed} field(s)")
    if args.dry_run:
        return 0

    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
