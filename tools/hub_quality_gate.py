#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quality gate for knowledge hub CSVs after rebuild."""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

try:
    from tools.hub_collapse_angles import topic_group_key, is_template_summary
    from tools.hub_collapse_series import series_group_key
except ImportError:
    topic_group_key = None  # type: ignore[assignment]
    is_template_summary = None  # type: ignore[assignment]
    series_group_key = None  # type: ignore[assignment]

BATCH_SUFFIX_RE = re.compile(r"（S\d+）|\(S\d+\)")
TRAILING_BATCH_RE = re.compile(r"\s+S\d+$")
BATCH_SLUG_SUFFIX_RE = re.compile(r"-s(\d+)$")
BATCH_SLUG_PREFIX_RE = re.compile(r"^s(\d+)-")

FORBIDDEN_PHRASES = (
    "手順と主体の混同。",
    "（S35）",
    "（S40）",
)

GENERIC_FAQ = "試験論点・条文・数値の対応を比較表に整理し、過去問で正誤の型を分類してください。"
GENERIC_NUMBER_HIGHLIGHT = "代表値は要項・法令で確認"


def _read(name: str) -> list[dict[str, str]]:
    path = DATA / name
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _batch(slug: str) -> int | None:
    s = slug or ""
    m = BATCH_SLUG_SUFFIX_RE.search(s)
    if m:
        return int(m.group(1))
    m = BATCH_SLUG_PREFIX_RE.search(s)
    return int(m.group(1)) if m else None


def _strip_core(label: str) -> str:
    return re.sub(r"（[^）]*）$", "", (label or "").strip()).strip()


def run_gate() -> tuple[int, dict[str, int]]:
    errors: list[str] = []
    metrics: dict[str, int] = {}

    for name in ("comparisons.csv", "numbers.csv", "mistakes.csv"):
        rows = _read(name)
        metrics[f"{name}_rows"] = len(rows)

        batch_hits = 0
        forbidden = 0
        for row in rows:
            for key, val in row.items():
                if not isinstance(val, str):
                    continue
                if BATCH_SUFFIX_RE.search(val):
                    batch_hits += 1
                if TRAILING_BATCH_RE.search(val):
                    batch_hits += 1
                for ph in FORBIDDEN_PHRASES:
                    if ph in val:
                        forbidden += 1
        metrics[f"{name}_batch_suffix_fields"] = batch_hits
        metrics[f"{name}_forbidden_phrase_hits"] = forbidden
        if batch_hits:
            errors.append(f"{name}: batch suffix in {batch_hits} fields")
        if forbidden:
            errors.append(f"{name}: forbidden phrase in {forbidden} fields")

    mistakes = _read("mistakes.csv")
    cp_by_batch: dict[int, Counter[str]] = defaultdict(Counter)
    for row in mistakes:
        b = _batch(row.get("slug", ""))
        if b is None or b < 35:
            continue
        cp_by_batch[b][row.get("confusion_point", "")] += 1
    dup_cp = sum(1 for c in cp_by_batch.values() for _, n in c.items() if n > 1)
    metrics["mistakes_duplicate_confusion_in_batch"] = dup_cp
    if dup_cp >= 5:
        errors.append(f"mistakes: {dup_cp} duplicate confusion_point values within S35+ batches")

    generic_cp = sum(1 for r in mistakes if r.get("confusion_point") == "手順と主体の混同。")
    metrics["mistakes_generic_confusion"] = generic_cp
    if generic_cp:
        errors.append(f"mistakes: {generic_cp} rows still use generic confusion_point")

    faq_generic = 0
    faq_generic_s35 = 0
    for name in ("comparisons.csv", "numbers.csv", "mistakes.csv"):
        for row in _read(name):
            for i in range(1, 5):
                ans = row.get(f"faq_{i}_answer", "")
                if GENERIC_FAQ in ans:
                    faq_generic += 1
                    b = _batch(row.get("slug", ""))
                    if b is not None and b >= 35:
                        faq_generic_s35 += 1
    metrics["faq_boilerplate_answers"] = faq_generic
    metrics["faq_boilerplate_s35plus"] = faq_generic_s35
    if faq_generic_s35:
        errors.append(f"FAQ: {faq_generic_s35} boilerplate answers on S35+ rows")

    # pattern_rows identical within batch (S35+ mistakes)
    pat_by_batch: dict[int, Counter[str]] = defaultdict(Counter)
    for row in mistakes:
        b = _batch(row.get("slug", ""))
        if b is None or b < 35:
            continue
        pat_by_batch[b][row.get("pattern_rows", "")] += 1
    dup_pat = sum(1 for c in pat_by_batch.values() for _, n in c.items() if n > 1)
    metrics["mistakes_duplicate_patterns_in_batch"] = dup_pat
    if dup_pat >= 10:
        errors.append(f"mistakes: {dup_pat} duplicate pattern_rows within S35+ batches")

    comparisons = _read("comparisons.csv")
    cmp_titles = Counter()
    cmp_labels = Counter()
    for row in comparisons:
        b = _batch(row.get("slug", ""))
        if b is None or b < 35:
            continue
        cmp_titles[row.get("title", "")] += 1
        cmp_labels[row.get("col_labels", "")] += 1
    dup_cmp_titles = sum(1 for _, n in cmp_titles.items() if n > 1)
    dup_cmp_labels = sum(1 for _, n in cmp_labels.items() if n > 1)
    index_keys = Counter(
        (row.get("title", ""), row.get("col_labels", ""))
        for row in comparisons
        if (_batch(row.get("slug", "")) or 0) >= 35
    )
    dup_index = sum(1 for _, n in index_keys.items() if n > 1)
    metrics["comparisons_duplicate_titles_s35plus"] = dup_cmp_titles
    metrics["comparisons_duplicate_col_labels_s35plus"] = dup_cmp_labels
    metrics["comparisons_duplicate_index_rows"] = dup_index
    if dup_cmp_titles:
        errors.append(f"comparisons: {dup_cmp_titles} duplicate titles among S35+ rows")
    if dup_index:
        errors.append(f"comparisons: {dup_index} identical index rows (title+col_labels) among S35+")

    cmp_self = 0
    for row in comparisons:
        if (_batch(row.get("slug", "")) or 0) < 35:
            continue
        parts = [_strip_core(p) for p in (row.get("col_labels") or "").split(";") if p.strip()]
        if len(parts) >= 2 and parts[0] == parts[1]:
            cmp_self += 1
    metrics["comparisons_self_compare_col_labels"] = cmp_self
    if cmp_self:
        errors.append(f"comparisons: {cmp_self} rows with identical compare subjects in col_labels")

    num_titles = Counter(
        r.get("title", "")
        for r in _read("numbers.csv")
        if (_batch(r.get("slug", "")) or 0) >= 35
    )
    dup_num_titles = sum(1 for _, n in num_titles.items() if n > 1)
    metrics["numbers_duplicate_titles_s35plus"] = dup_num_titles
    if dup_num_titles:
        errors.append(f"numbers: {dup_num_titles} duplicate titles among S35+ rows")

    numbers = _read("numbers.csv")
    generic_hl = sum(1 for r in numbers if (r.get("highlight") or "").strip() == GENERIC_NUMBER_HIGHLIGHT)
    hl_counter = Counter((r.get("highlight") or "").strip() for r in numbers if (r.get("highlight") or "").strip())
    dup_hl = sum(1 for _, n in hl_counter.items() if n >= 8)
    metrics["numbers_generic_highlight"] = generic_hl
    metrics["numbers_duplicate_highlight_values"] = dup_hl
    if generic_hl:
        errors.append(f"numbers: {generic_hl} rows still use generic highlight")

    item_by_batch: dict[int, Counter[str]] = defaultdict(Counter)
    for row in numbers:
        b = _batch(row.get("slug", ""))
        if b is None or b < 35:
            continue
        item_by_batch[b][row.get("item_rows", "")] += 1
    num_item_dup = sum(1 for c in item_by_batch.values() for _, n in c.items() if n > 1)
    metrics["numbers_duplicate_item_rows_in_batch"] = num_item_dup
    if num_item_dup:
        errors.append(f"numbers: {num_item_dup} duplicate item_rows within S35+ batches")

    reader_noise = 0
    slug_in_label = re.compile(r"[a-z]+-[a-z0-9-]+", re.I)
    noise_phrases = ("制度整理", "誤答整理", "数値整理")
    for row in comparisons:
        blob = row.get("col_labels", "") + row.get("title", "")
        if slug_in_label.search(row.get("col_labels", "")):
            reader_noise += 1
        elif any(p in blob for p in noise_phrases):
            reader_noise += 1
    metrics["comparisons_reader_noise"] = reader_noise
    if reader_noise:
        errors.append(f"comparisons: {reader_noise} rows with reader-noise in col_labels/title")

    mis_titles = Counter(
        r.get("title", "")
        for r in mistakes
        if (_batch(r.get("slug", "")) or 0) >= 35
    )
    dup_mis_titles = sum(1 for _, n in mis_titles.items() if n > 1)
    metrics["mistakes_duplicate_titles_s35plus"] = dup_mis_titles
    if dup_mis_titles:
        errors.append(f"mistakes: {dup_mis_titles} duplicate titles among S35+ rows")

    if topic_group_key is not None:
        for csv_name, rows in (
            ("comparisons", comparisons),
            ("numbers", numbers),
            ("mistakes", mistakes),
        ):
            groups: dict[str, list[dict[str, str]]] = defaultdict(list)
            for row in rows:
                key = topic_group_key(row.get("slug", ""))
                if key:
                    groups[key].append(row)
            uncollapsed = sum(1 for group in groups.values() if len(group) >= 2)
            metrics[f"{csv_name}_uncollapsed_angle_groups"] = uncollapsed
            if uncollapsed:
                errors.append(f"{csv_name}: {uncollapsed} uncollapsed angle-variant groups remain")

    if series_group_key is not None:
        for csv_name, rows in (
            ("comparisons", comparisons),
            ("numbers", numbers),
            ("mistakes", mistakes),
        ):
            series_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
            for row in rows:
                key = series_group_key(row)
                if key:
                    series_groups[key].append(row)
            uncollapsed_series = sum(1 for group in series_groups.values() if len(group) >= 2)
            metrics[f"{csv_name}_uncollapsed_series_groups"] = uncollapsed_series
            if uncollapsed_series:
                errors.append(f"{csv_name}: {uncollapsed_series} uncollapsed nuance-variant groups remain")

    if is_template_summary is not None:
        template_summaries = sum(
            1 for r in mistakes if is_template_summary(r.get("summary", ""))
        )
        metrics["mistakes_template_summaries"] = template_summaries
        if template_summaries >= 5:
            errors.append(f"mistakes: {template_summaries} rows still use template summaries")

    if errors:
        print("QUALITY GATE FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1, metrics
    print("QUALITY GATE OK", json.dumps(metrics, ensure_ascii=False))
    return 0, metrics


if __name__ == "__main__":
    code, _ = run_gate()
    raise SystemExit(code)
