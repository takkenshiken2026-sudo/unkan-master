#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collapse S35+ angle-variant hub rows into one canonical article per topic."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from tools.hub_diversify_content import ANGLE_BY_BATCH, BATCH_EARLY_LABEL

ANGLE_LABELS = frozenset(ANGLE_BY_BATCH.values()) | frozenset(BATCH_EARLY_LABEL.values())
MIN_ANGLE_COLLAPSE_BATCH = 31
BATCH_SLUG_PREFIX = re.compile(r"^s(\d+)-")
BATCH_SLUG_SUFFIX = re.compile(r"-s(\d+)$")
TEMPLATE_SUMMARY_MARKERS = (
    "主体の取り違え・手順の前後逆・数値の単独暗記・記録省略の4型",
    "4型に分けて整理します",
)


def batch_number(slug: str) -> int | None:
    s = slug or ""
    m = BATCH_SLUG_PREFIX.match(s)
    if m:
        return int(m.group(1))
    m = BATCH_SLUG_SUFFIX.search(s)
    return int(m.group(1)) if m else None


def topic_group_key(slug: str) -> str | None:
    b = batch_number(slug)
    if b is None or b < MIN_ANGLE_COLLAPSE_BATCH:
        return None
    if BATCH_SLUG_PREFIX.match(slug):
        return BATCH_SLUG_PREFIX.sub("", slug)
    m = BATCH_SLUG_SUFFIX.search(slug)
    if m:
        return slug[: m.start()]
    return None


def strip_angle_title(title: str) -> tuple[str, str | None]:
    t = (title or "").strip()
    for angle in ANGLE_LABELS:
        suffix = f"（{angle}）"
        if t.endswith(suffix):
            return t[: -len(suffix)].strip(), angle
    return t, None


def angle_from_row(row: dict[str, str]) -> str | None:
    _, angle = strip_angle_title(row.get("title", ""))
    if angle:
        return angle
    b = batch_number(row.get("slug", ""))
    if b is not None:
        return ANGLE_BY_BATCH.get(b)
    return None


def is_template_summary(text: str) -> bool:
    return any(marker in (text or "") for marker in TEMPLATE_SUMMARY_MARKERS)


def _pick_best_text(rows: list[dict[str, str]], field: str) -> str:
    seen: set[str] = set()
    candidates: list[str] = []
    for row in rows:
        val = (row.get(field) or "").strip()
        if not val or val in seen:
            continue
        seen.add(val)
        candidates.append(val)
    if not candidates:
        return ""
    non_template = [c for c in candidates if not is_template_summary(c)]
    pool = non_template or candidates
    return min(pool, key=len)


def _merge_summary(base_title: str, group: list[dict[str, str]]) -> str:
    best = _pick_best_text(group, "summary")
    if best and not is_template_summary(best):
        return best
    return f"「{base_title}」で試験に出やすい誤答パターンを、主体・手順・数値・記録の型別に整理します。"


def _merge_confusion(group: list[dict[str, str]]) -> str:
    return _pick_best_text(group, "confusion_point")


def _merge_patterns(group: list[dict[str, str]]) -> str:
    seen: set[tuple[str, str, str]] = set()
    merged: list[dict[str, str]] = []
    for row in sorted(group, key=lambda r: batch_number(r.get("slug", "")) or 999):
        angle = angle_from_row(row) or ""
        try:
            patterns = json.loads(row.get("pattern_rows") or "[]")
        except json.JSONDecodeError:
            continue
        if not isinstance(patterns, list):
            continue
        for pattern in patterns:
            if not isinstance(pattern, dict):
                continue
            topic = (pattern.get("topic") or "").strip()
            wrong = (pattern.get("wrong") or "").strip()
            correct = (pattern.get("correct") or "").strip()
            if not topic or not wrong or not correct:
                continue
            key = (topic, wrong, correct)
            if key in seen:
                continue
            seen.add(key)
            item = {
                "topic": topic,
                "wrong": wrong,
                "correct": correct,
                "trap": (pattern.get("trap") or "").strip(),
            }
            if angle:
                item["angle"] = angle
            merged.append(item)
    return json.dumps(merged[:20], ensure_ascii=False)


def _merge_item_rows(group: list[dict[str, str]]) -> str:
    seen: set[tuple[str, str, str]] = set()
    merged: list[dict[str, str]] = []
    for row in sorted(group, key=lambda r: batch_number(r.get("slug", "")) or 999):
        angle = angle_from_row(row) or ""
        try:
            items = json.loads(row.get("item_rows") or "[]")
        except json.JSONDecodeError:
            continue
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            label = (item.get("item") or "").strip()
            value = (item.get("value") or "").strip()
            note = (item.get("note") or "").strip()
            if not label or not value:
                continue
            key = (label, value, note)
            if key in seen:
                continue
            seen.add(key)
            row_item = {"item": label, "value": value, "note": note}
            if angle:
                row_item["angle"] = angle
            merged.append(row_item)
    return json.dumps(merged[:20], ensure_ascii=False)


def _merge_compare_rows(group: list[dict[str, str]]) -> str:
    canonical = group[0]
    try:
        axes = json.loads(canonical.get("compare_rows") or "[]")
    except json.JSONDecodeError:
        return canonical.get("compare_rows") or "[]"
    if not isinstance(axes, list):
        return canonical.get("compare_rows") or "[]"
    return json.dumps(axes, ensure_ascii=False)


def _merge_group(group: list[dict[str, str]], *, hub_kind: str) -> dict[str, str]:
    group = sorted(group, key=lambda r: batch_number(r.get("slug", "")) or 999)
    canonical = dict(group[0])
    base_title, _ = strip_angle_title(canonical.get("title", ""))
    if not base_title:
        base_title = canonical.get("title", "").strip()
    canonical["title"] = base_title
    canonical["summary"] = _merge_summary(base_title, group)

    if hub_kind == "mistakes":
        canonical["confusion_point"] = _merge_confusion(group)
        canonical["pattern_rows"] = _merge_patterns(group)
    elif hub_kind == "numbers":
        highlight = _pick_best_text(group, "highlight")
        if highlight:
            canonical["highlight"] = highlight
        canonical["item_rows"] = _merge_item_rows(group)
    elif hub_kind == "compare":
        col_labels = _pick_best_text(group, "col_labels")
        if col_labels:
            canonical["col_labels"] = col_labels
        canonical["compare_rows"] = _merge_compare_rows(group)

    article_title = (canonical.get("article_title") or "").strip()
    if article_title:
        for angle in ANGLE_LABELS:
            article_title = article_title.replace(f"（{angle}）", "")
        canonical["article_title"] = article_title.strip()

    article_lead = _pick_best_text(group, "article_lead")
    if article_lead:
        canonical["article_lead"] = article_lead

    return canonical


def collapse_hub_rows(
    rows: list[dict[str, str]],
    *,
    hub_kind: str,
    min_group_size: int = 2,
) -> tuple[list[dict[str, str]], dict[str, str]]:
    redirects: dict[str, str] = {}
    passthrough: list[dict[str, str]] = []
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        key = topic_group_key(row.get("slug", ""))
        if key is None:
            passthrough.append(row)
        else:
            groups[key].append(row)

    collapsed = list(passthrough)
    for _key, group in groups.items():
        if len(group) < min_group_size:
            collapsed.extend(group)
            continue

        bases = {strip_angle_title(r.get("title", ""))[0] for r in group}
        if len(bases) > 1:
            collapsed.extend(group)
            continue

        merged = _merge_group(group, hub_kind=hub_kind)
        canon_slug = merged.get("slug", "")
        for row in group:
            slug = row.get("slug", "")
            if slug and slug != canon_slug:
                redirects[slug] = canon_slug
        collapsed.append(merged)

    return collapsed, redirects


def collapse_finalized_hubs(
    comparisons: list[dict[str, str]],
    numbers: list[dict[str, str]],
    mistakes: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], dict[str, dict[str, str]]]:
    from tools.hub_collapse_series import collapse_series_rows, merge_redirect_maps

    comparisons, compare_series = collapse_series_rows(comparisons, hub_kind="compare")
    numbers, numbers_series = collapse_series_rows(numbers, hub_kind="numbers")
    mistakes, mistakes_series = collapse_series_rows(mistakes, hub_kind="mistakes")

    comparisons, compare_angle = collapse_hub_rows(comparisons, hub_kind="compare")
    numbers, numbers_angle = collapse_hub_rows(numbers, hub_kind="numbers")
    mistakes, mistakes_angle = collapse_hub_rows(mistakes, hub_kind="mistakes")

    redirects = {
        "compare": merge_redirect_maps(compare_series, compare_angle),
        "numbers": merge_redirect_maps(numbers_series, numbers_angle),
        "mistakes": merge_redirect_maps(mistakes_series, mistakes_angle),
    }
    return comparisons, numbers, mistakes, redirects


def write_hub_redirects(data_dir: Path, redirects: dict[str, dict[str, str]]) -> None:
    path = data_dir / "hub_redirects.json"
    path.write_text(json.dumps(redirects, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_hub_redirects(data_dir: Path) -> dict[str, str]:
    path = data_dir / "hub_redirects.json"
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    hub = raw.get("mistakes") or {}
    if isinstance(hub, dict):
        return {str(k): str(v) for k, v in hub.items()}
    return {}


def redirect_page_html(target_slug_file: str, *, title: str, analytics_html: str = "") -> str:
    import html as html_mod

    target = html_mod.escape(target_slug_file)
    safe_title = html_mod.escape(title)
    analytics_block = f"\n{analytics_html}\n" if analytics_html else ""
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{safe_title}（移動中）</title>
<meta http-equiv="refresh" content="0; url={target}">
<link rel="canonical" href="{target}">
<meta name="robots" content="noindex, follow">
<script>location.replace("{target}");</script>
</head>
<body>
<p>ページを移動しています。<a href="{target}">こちら</a>をクリックしてください。</p>{analytics_block}</body>
</html>
"""
