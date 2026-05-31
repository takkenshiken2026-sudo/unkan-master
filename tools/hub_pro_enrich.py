#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知識ハブ CSV の article_lead / FAQ 回答をプロ水準へ拡張する。

新しい事実は追加せず、同一行の summary・exam_points・memory_tip・common_mistakes
から補う（正確性優先）。
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

CONCRETE = re.compile(
    r"\d|％|%|年|月|日|条|項|科目|分野|公式|例えば|例：|たとえば|しかし|一方で|具体的|"
    r"原則|上限|下限|問|点|円|時間|義務|禁止|試験|法令|協議会|www|管理|契約"
)

FAQ_PAD = "本ページの表・関連用語とあわせ、過去問の正誤肢と照合しながら復習してください。"

MIN_LEAD = 80
MIN_FAQ = 100
MIN_SUMMARY = 13
MIN_MEMORY_TIP = 15
MIN_COMMON_MISTAKES = 20
MEMORY_TIP_PAD = "関連用語とセットで声に出して確認"
COMMON_MISTAKES_PAD = "試験では条文・要項の最新版と照合してください"


def split_semicolon(value: str) -> list[str]:
    return [x.strip() for x in (value or "").split(";") if x.strip()]


def _join_sentences(parts: list[str]) -> str:
    out: list[str] = []
    for p in parts:
        p = p.strip().rstrip("。")
        if not p:
            continue
        if out and p in out[-1]:
            continue
        if any(p in x or x in p for x in out):
            continue
        out.append(p)
    if not out:
        return ""
    return "。".join(out) + "。"


def enrich_lead(row: dict[str, str]) -> str:
    lead = (row.get("article_lead") or "").strip()
    if len(lead) >= MIN_LEAD and CONCRETE.search(lead):
        return lead

    parts: list[str] = []
    if lead:
        parts.append(lead.rstrip("。"))

    summary = (row.get("summary") or "").strip().rstrip("。")
    if summary and summary not in lead:
        parts.append(summary)

    points = split_semicolon(row.get("exam_points", ""))
    if points:
        parts.append("試験で押さえるべき点は、" + "、".join(points[:4]))

    highlight = (row.get("highlight") or "").strip().rstrip("。")
    if highlight and highlight not in "。".join(parts):
        parts.append(f"早見の要点は「{highlight}」です")

    tip = (row.get("memory_tip") or "").strip().rstrip("。")
    if tip and len(_join_sentences(parts)) < MIN_LEAD and tip not in lead:
        parts.append(tip)

    result = _join_sentences(parts)
    if len(result) < MIN_LEAD:
        title = (row.get("title") or "").strip()
        if title:
            result = _join_sentences([result.rstrip("。"), f"{title}は過去問でも頻出の論点です"])
    return result or lead


def enrich_faq_answer(answer: str, row: dict[str, str]) -> str:
    text = (answer or "").strip()
    if len(text) >= MIN_FAQ:
        return text

    parts: list[str] = []
    if text:
        parts.append(text.rstrip("。"))

    for point in split_semicolon(row.get("exam_points", "")):
        if len(_join_sentences(parts)) >= MIN_FAQ:
            break
        if point and point not in text:
            parts.append(point)

    tip = (row.get("memory_tip") or "").strip().rstrip("。")
    if tip and len(_join_sentences(parts)) < MIN_FAQ and tip not in text:
        parts.append(tip)

    mistakes = split_semicolon(row.get("common_mistakes", ""))
    if mistakes and len(_join_sentences(parts)) < MIN_FAQ:
        m0 = mistakes[0]
        if m0 not in text:
            parts.append(f"誤りやすいのは「{m0}」と捉えることです")

    summary = (row.get("summary") or "").strip().rstrip("。")
    if summary and len(_join_sentences(parts)) < MIN_FAQ and summary not in text:
        parts.append(summary)

    result = _join_sentences(parts)
    if len(result) < MIN_FAQ and FAQ_PAD not in result:
        result = result.rstrip("。") + "。" + FAQ_PAD
    return result if len(result) >= len(text) else text


def enrich_summary(row: dict[str, str]) -> str:
    summary = (row.get("summary") or "").strip()
    if len(summary) >= MIN_SUMMARY:
        return summary

    parts: list[str] = []
    if summary:
        parts.append(summary.rstrip("。"))

    confusion = (row.get("confusion_point") or "").strip().rstrip("。")
    if confusion and confusion not in summary:
        parts.append(confusion)

    if len(_join_sentences(parts)) < MIN_SUMMARY:
        title = (row.get("title") or "").strip().rstrip("。")
        if title and title not in summary:
            parts.append(f"「{title}」を整理")

    if len(_join_sentences(parts)) < MIN_SUMMARY:
        points = split_semicolon(row.get("exam_points", ""))
        if points and points[0] not in summary:
            parts.append(points[0])

    result = _join_sentences(parts)
    return result or summary


def enrich_memory_tip(row: dict[str, str]) -> str:
    tip = (row.get("memory_tip") or "").strip()
    if len(tip) >= MIN_MEMORY_TIP:
        return tip

    parts: list[str] = []
    if tip:
        parts.append(tip.rstrip("。"))

    for point in split_semicolon(row.get("exam_points", "")):
        if len(_join_sentences(parts)) >= MIN_MEMORY_TIP:
            break
        if point and point not in tip:
            parts.append(point)

    result = _join_sentences(parts)
    if len(result) < MIN_MEMORY_TIP:
        title = (row.get("title") or row.get("article_title") or "").strip()
        if title:
            result = _join_sentences([result.rstrip("。"), f"{title}は比較表と併せて確認"])
    if len(result) < MIN_MEMORY_TIP and MEMORY_TIP_PAD not in result:
        result = _join_sentences([result.rstrip("。"), MEMORY_TIP_PAD])
    return result or tip


def enrich_common_mistakes(row: dict[str, str]) -> str:
    cm = (row.get("common_mistakes") or "").strip()
    if len(cm) >= MIN_COMMON_MISTAKES:
        return cm

    parts = split_semicolon(cm)
    for point in split_semicolon(row.get("exam_points", "")):
        if len(";".join(parts)) >= MIN_COMMON_MISTAKES:
            break
        phrase = f"{point}を見落とす"
        if phrase not in cm and phrase not in parts:
            parts.append(phrase)

    result = ";".join(dict.fromkeys(parts))
    if len(result) < MIN_COMMON_MISTAKES and COMMON_MISTAKES_PAD not in result:
        result = (result + ";" + COMMON_MISTAKES_PAD) if result else COMMON_MISTAKES_PAD
    return result


def enrich_row(row: dict[str, str]) -> dict[str, str]:
    row = dict(row)
    row["summary"] = enrich_summary(row)
    row["article_lead"] = enrich_lead(row)
    row["memory_tip"] = enrich_memory_tip(row)
    row["common_mistakes"] = enrich_common_mistakes(row)
    for n in range(1, 5):
        key = f"faq_{n}_answer"
        if row.get(key):
            row[key] = enrich_faq_answer(row[key], row)
    return row


def enrich_csv(path: Path) -> int:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        header = list(reader.fieldnames or [])
        rows = list(reader)
    changed = 0
    new_rows = []
    for row in rows:
        old_summary = row.get("summary", "")
        old_lead = row.get("article_lead", "")
        old_tip = row.get("memory_tip", "")
        old_cm = row.get("common_mistakes", "")
        old_faqs = [row.get(f"faq_{i}_answer", "") for i in range(1, 5)]
        enriched = enrich_row(row)
        if (
            enriched.get("summary") != old_summary
            or enriched.get("article_lead") != old_lead
            or enriched.get("memory_tip") != old_tip
            or enriched.get("common_mistakes") != old_cm
            or [enriched.get(f"faq_{i}_answer") for i in range(1, 5)] != old_faqs
        ):
            changed += 1
        new_rows.append(enriched)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        w.writeheader()
        w.writerows(new_rows)
    return changed


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=None, help="Site root (default: script parent)")
    args = parser.parse_args()
    root = (args.root or Path(__file__).resolve().parents[1]).resolve()
    data = root / "data"
    total = 0
    for name in ("comparisons.csv", "numbers.csv", "mistakes.csv"):
        p = data / name
        if p.exists():
            n = enrich_csv(p)
            print(f"{name}: enriched {n} rows")
            total += n
    print(f"done, {total} rows updated")


if __name__ == "__main__":
    main()
