#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知識ハブ3種（比較・数値・誤答）CSV の件数目標と行品質基準."""

from __future__ import annotations

import json
from dataclasses import dataclass

from tools.editorial_quality import placeholder_issues, split_semicolon

# 本番ボリューム目標（各 CSV 独立）— S30〜S44 展開後は 150 件/種
HUB_PRODUCTION_TARGET_MIN = 150
HUB_PRODUCTION_TARGET_MAX = 153

HUB_LABELS: dict[str, str] = {
    "compare": "比較・整理表",
    "numbers": "数値・期限早見表",
    "mistakes": "よくある誤答",
}

HUB_CSV_NAMES: dict[str, str] = {
    "compare": "comparisons.csv",
    "numbers": "numbers.csv",
    "mistakes": "mistakes.csv",
}

HUB_MIN_LENGTHS: dict[str, int] = {
    "title": 4,
    "summary": 8,
    "article_title": 10,
    "article_lead": 30,
    "common_mistakes": 15,
    "memory_tip": 10,
    "faq_answer": 40,
}

HUB_MIN_EXAM_POINTS = 2
HUB_MIN_RELATED_TERMS = 2
HUB_MIN_FAQ_COUNT = 4


@dataclass
class HubIssue:
    level: str
    column: str
    message: str


def _norm(value: str | None) -> str:
    return (value or "").strip()


def _len(value: str | None) -> int:
    return len(_norm(value))


def _parse_json_array(raw: str, *, column: str) -> tuple[list | None, str | None]:
    text = _norm(raw)
    if not text:
        return None, f"{column} が空です"
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"{column} の JSON が不正です: {exc}"
    if not isinstance(data, list) or not data:
        return None, f"{column} は空でない JSON 配列にしてください"
    return data, None


def _check_shared_fields(
    row: dict[str, str],
    *,
    term_lookup: dict[str, str],
    line: int | None = None,
) -> list[HubIssue]:
    issues: list[HubIssue] = []
    prefix = f"行{line}: " if line else ""

    for col, min_len in HUB_MIN_LENGTHS.items():
        if col == "faq_answer":
            continue
        if _len(row.get(col)) < min_len:
            issues.append(
                HubIssue("ERROR", col, f"{prefix}{col} は {min_len} 文字以上にしてください")
            )

    points = split_semicolon(_norm(row.get("exam_points")))
    if len(points) < HUB_MIN_EXAM_POINTS:
        issues.append(
            HubIssue(
                "ERROR",
                "exam_points",
                f"{prefix}exam_points は {HUB_MIN_EXAM_POINTS} 項目以上（`;` 区切り）にしてください",
            )
        )

    related = split_semicolon(_norm(row.get("related_terms")))
    if len(related) < HUB_MIN_RELATED_TERMS:
        issues.append(
            HubIssue(
                "ERROR",
                "related_terms",
                f"{prefix}related_terms は {HUB_MIN_RELATED_TERMS} 件以上にしてください",
            )
        )
    else:
        for term in related:
            if term not in term_lookup:
                issues.append(
                    HubIssue(
                        "ERROR",
                        "related_terms",
                        f"{prefix}related_terms の用語が glossary_terms.csv にありません: {term!r}",
                    )
                )

    faq_count = 0
    for n in range(1, HUB_MIN_FAQ_COUNT + 1):
        q = _norm(row.get(f"faq_{n}_question"))
        a = _norm(row.get(f"faq_{n}_answer"))
        if q or a:
            faq_count += 1
        if q and _len(q) < 6:
            issues.append(HubIssue("ERROR", f"faq_{n}_question", f"{prefix}FAQ 質問は 6 文字以上"))
        if a and _len(a) < HUB_MIN_LENGTHS["faq_answer"]:
            issues.append(
                HubIssue(
                    "WARN",
                    f"faq_{n}_answer",
                    f"{prefix}FAQ 回答は {HUB_MIN_LENGTHS['faq_answer']} 文字以上推奨（プロ水準は 100 字以上）",
                )
            )
    if faq_count < HUB_MIN_FAQ_COUNT:
        issues.append(
            HubIssue("ERROR", "faq", f"{prefix}FAQ は {HUB_MIN_FAQ_COUNT} 件必須です")
        )

    for col in ("article_lead", "common_mistakes", "memory_tip", "summary"):
        text = _norm(row.get(col))
        if not text:
            continue
        for issue in placeholder_issues(text, col):
            if issue.level == "ERROR":
                issues.append(HubIssue("ERROR", col, f"{prefix}{issue.message}"))

    return issues


def check_compare_row(
    row: dict[str, str],
    *,
    term_lookup: dict[str, str],
    line: int | None = None,
) -> list[HubIssue]:
    issues = _check_shared_fields(row, term_lookup=term_lookup, line=line)
    labels = split_semicolon(_norm(row.get("col_labels")))
    if len(labels) < 2:
        issues.append(
            HubIssue("ERROR", "col_labels", "col_labels は比較対象を 2 件以上（`;` 区切り）")
        )
    data, err = _parse_json_array(_norm(row.get("compare_rows")), column="compare_rows")
    if err:
        issues.append(HubIssue("ERROR", "compare_rows", err))
    elif data:
        for i, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                issues.append(HubIssue("ERROR", "compare_rows", f"compare_rows[{i}] がオブジェクトではありません"))
                continue
            cols = item.get("cols")
            if not isinstance(cols, list) or len(cols) != len(labels):
                issues.append(
                    HubIssue(
                        "ERROR",
                        "compare_rows",
                        f"compare_rows[{i}].cols の列数が col_labels と一致しません",
                    )
                )
    return issues


def check_numbers_row(
    row: dict[str, str],
    *,
    term_lookup: dict[str, str],
    line: int | None = None,
) -> list[HubIssue]:
    issues = _check_shared_fields(row, term_lookup=term_lookup, line=line)
    if _len(row.get("highlight")) < 3:
        issues.append(HubIssue("ERROR", "highlight", "highlight を入力してください"))
    data, err = _parse_json_array(_norm(row.get("item_rows")), column="item_rows")
    if err:
        issues.append(HubIssue("ERROR", "item_rows", err))
    elif data:
        for i, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                issues.append(HubIssue("ERROR", "item_rows", f"item_rows[{i}] がオブジェクトではありません"))
                continue
            for key in ("item", "value"):
                if not _norm(str(item.get(key, ""))):
                    issues.append(
                        HubIssue("ERROR", "item_rows", f"item_rows[{i}] に {key} がありません")
                    )
    return issues


def check_mistakes_row(
    row: dict[str, str],
    *,
    term_lookup: dict[str, str],
    line: int | None = None,
) -> list[HubIssue]:
    issues = _check_shared_fields(row, term_lookup=term_lookup, line=line)
    if _len(row.get("confusion_point")) < 4:
        issues.append(HubIssue("ERROR", "confusion_point", "confusion_point を入力してください"))
    data, err = _parse_json_array(_norm(row.get("pattern_rows")), column="pattern_rows")
    if err:
        issues.append(HubIssue("ERROR", "pattern_rows", err))
    elif data:
        for i, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                issues.append(HubIssue("ERROR", "pattern_rows", f"pattern_rows[{i}] がオブジェクトではありません"))
                continue
            for key in ("topic", "wrong", "correct", "trap"):
                if not _norm(str(item.get(key, ""))):
                    issues.append(
                        HubIssue("ERROR", "pattern_rows", f"pattern_rows[{i}] に {key} がありません")
                    )
    return issues


def production_count_message(hub_type: str, count: int) -> str | None:
    label = HUB_LABELS[hub_type]
    csv_name = HUB_CSV_NAMES[hub_type]
    if count < HUB_PRODUCTION_TARGET_MIN:
        return (
            f"{label}（{csv_name}）は本番目標 **{HUB_PRODUCTION_TARGET_MIN}〜{HUB_PRODUCTION_TARGET_MAX} 件** "
            f"（現在 {count} 件）。docs/knowledge-hub-article-templates.md を参照して拡充してください。"
        )
    if count > HUB_PRODUCTION_TARGET_MAX:
        return (
            f"{label}（{csv_name}）が {count} 件あります（目安は {HUB_PRODUCTION_TARGET_MAX} 件前後）。"
            " 検索意図の重複と更新負荷がないか確認してください。"
        )
    return None
