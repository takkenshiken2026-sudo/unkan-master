#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collapse S35+ nuance-variant hub rows (のゼロ/の過剰/… slug suffixes) into one row."""

from __future__ import annotations

import json
from collections import defaultdict

from tools.hub_collapse_angles import (
    MIN_ANGLE_COLLAPSE_BATCH,
    _merge_compare_rows,
    _merge_confusion,
    _merge_summary,
    _pick_best_text,
    angle_from_row,
    batch_number,
    strip_angle_title,
)
from tools.hub_diversify_content import TITLE_SUFFIXES

NUANCE_SLUG_TOKENS = frozenset(
    {
        "blind",
        "check",
        "cmp",
        "count",
        "cycle",
        "diff",
        "freq",
        "gokai",
        "haibun",
        "hantei",
        "hikaku",
        "kijun",
        "kongou",
        "kon",
        "kubun",
        "matome",
        "meyasu",
        "mis",
        "noconf",
        "nouse",
        "num",
        "omit",
        "over",
        "point",
        "ratio",
        "reverse",
        "seido",
        "skip",
        "taihi",
        "tejun",
        "time",
        "unyo",
        "zero",
    }
)

NUANCE_SLUG_LABELS: dict[str, str] = {
    "blind": "盲信",
    "check": "確認",
    "cmp": "比較",
    "count": "回数",
    "cycle": "周期",
    "diff": "違い",
    "freq": "頻度",
    "gokai": "誤認",
    "haibun": "配分",
    "hantei": "判定",
    "kon": "混同",
    "kongou": "混同",
    "kubun": "区分",
    "matome": "整理",
    "meyasu": "目安",
    "mis": "誤認",
    "noconf": "未確認",
    "nouse": "未使用",
    "num": "数値",
    "omit": "省略",
    "over": "過剰",
    "point": "要点",
    "ratio": "比率",
    "reverse": "逆転",
    "seido": "制度",
    "skip": "放置",
    "taihi": "対比",
    "tejun": "手順",
    "time": "時間",
    "unyo": "運用",
    "zero": "ゼロ",
}

TITLE_SUFFIX_LABELS: dict[str, str] = {
    "の混同": "混同",
    "の誤認": "誤認",
    "の逆転": "逆転",
    "の省略": "省略",
    "の盲信": "盲信",
    "の過剰": "過剰",
    "の未確認": "未確認",
    "の未使用": "未使用",
    "の放置": "放置",
    "のゼロ": "ゼロ",
    "の比較": "比較",
    "の違い": "違い",
    "の整理": "整理",
    "の要点": "要点",
    "の対比": "対比",
    "の区分": "区分",
    "の手順": "手順",
    "の制度": "制度",
    "の運用": "運用",
    "の判定": "判定",
    "の数値": "数値",
    "の周期": "周期",
    "の目安": "目安",
    "の頻度": "頻度",
    "の時間": "時間",
    "の回数": "回数",
    "の基準": "基準",
    "の比率": "比率",
    "の配分": "配分",
    "の確認": "確認",
}

CANONICAL_NUANCE_ORDER = (
    "kon",
    "gokai",
    "cmp",
    "diff",
    "num",
    "zero",
    "omit",
    "over",
    "nouse",
    "reverse",
    "blind",
    "noconf",
    "skip",
    "matome",
    "point",
    "taihi",
    "kubun",
    "tejun",
    "seido",
    "unyo",
    "hantei",
    "cycle",
    "meyasu",
    "freq",
    "ratio",
    "time",
    "count",
    "kijun",
    "haibun",
    "check",
)


def _slug_stem(slug: str) -> str:
    from tools.hub_collapse_angles import BATCH_SLUG_PREFIX, BATCH_SLUG_SUFFIX

    s = slug or ""
    if BATCH_SLUG_PREFIX.match(s):
        return BATCH_SLUG_PREFIX.sub("", s)
    m = BATCH_SLUG_SUFFIX.search(s)
    if m:
        return s[: m.start()]
    return s


def nuance_from_slug(slug: str) -> str | None:
    stem = _slug_stem(slug)
    parts = stem.rsplit("-", 1)
    if len(parts) == 2 and parts[1] in NUANCE_SLUG_TOKENS:
        return parts[1]
    return None


def series_slug_key(slug: str) -> str | None:
    b = batch_number(slug)
    if b is None or b < MIN_ANGLE_COLLAPSE_BATCH:
        return None
    stem = _slug_stem(slug)
    nuance = nuance_from_slug(slug)
    if nuance:
        return stem[: -(len(nuance) + 1)]
    return stem


def series_title_core(title: str) -> tuple[str, str | None, str | None]:
    base, angle = strip_angle_title(title)
    nuance_label: str | None = None
    for suffix in TITLE_SUFFIXES:
        if base.endswith(suffix):
            base = base[: -len(suffix)].strip()
            nuance_label = TITLE_SUFFIX_LABELS.get(suffix)
            break
    return base, angle, nuance_label


def nuance_label_for_row(row: dict[str, str]) -> str:
    slug = row.get("slug", "")
    token = nuance_from_slug(slug)
    if token:
        return NUANCE_SLUG_LABELS.get(token, token)
    _, _, title_nuance = series_title_core(row.get("title", ""))
    return title_nuance or ""


def series_group_key(row: dict[str, str]) -> str | None:
    slug_key = series_slug_key(row.get("slug", ""))
    if slug_key is None:
        return None
    core, angle, _ = series_title_core(row.get("title", ""))
    if not core:
        core = row.get("title", "").strip()
    angle = angle or angle_from_row(row) or ""
    return f"{slug_key}\0{core}\0{angle}"


def _canonical_sort_key(row: dict[str, str]) -> tuple[int, int, str]:
    token = nuance_from_slug(row.get("slug", "")) or ""
    try:
        nuance_rank = CANONICAL_NUANCE_ORDER.index(token)
    except ValueError:
        nuance_rank = len(CANONICAL_NUANCE_ORDER)
    batch = batch_number(row.get("slug", "")) or 999
    return (nuance_rank, batch, row.get("slug", ""))


def _merged_title(core: str, *, hub_kind: str, angle: str | None) -> str:
    if hub_kind == "mistakes":
        title = f"{core}の典型誤答" if core else "典型誤答"
    elif hub_kind == "numbers":
        title = f"{core}の数値整理" if core else "数値整理"
    elif hub_kind == "compare":
        title = f"{core}の比較整理" if core else "比較整理"
    else:
        title = core
    if angle:
        title = f"{title}（{angle}）"
    return title


def _merge_patterns(group: list[dict[str, str]]) -> str:
    seen: set[tuple[str, str, str, str]] = set()
    merged: list[dict[str, str]] = []
    for row in sorted(group, key=_canonical_sort_key):
        nuance = nuance_label_for_row(row)
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
            key = (nuance, topic, wrong, correct)
            if key in seen:
                continue
            seen.add(key)
            item = {
                "topic": topic,
                "wrong": wrong,
                "correct": correct,
                "trap": (pattern.get("trap") or "").strip(),
            }
            if nuance:
                item["nuance"] = nuance
            angle = (pattern.get("angle") or "").strip() or angle_from_row(row) or ""
            if angle:
                item["angle"] = angle
            merged.append(item)
    return json.dumps(merged[:25], ensure_ascii=False)


def _merge_item_rows(group: list[dict[str, str]]) -> str:
    seen: set[tuple[str, str, str, str]] = set()
    merged: list[dict[str, str]] = []
    for row in sorted(group, key=_canonical_sort_key):
        nuance = nuance_label_for_row(row)
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
            key = (nuance, label, value, note)
            if key in seen:
                continue
            seen.add(key)
            row_item = {"item": label, "value": value, "note": note}
            if nuance:
                row_item["nuance"] = nuance
            angle = (item.get("angle") or "").strip() or angle_from_row(row) or ""
            if angle:
                row_item["angle"] = angle
            merged.append(row_item)
    return json.dumps(merged[:25], ensure_ascii=False)


def _merge_group(group: list[dict[str, str]], *, hub_kind: str) -> dict[str, str]:
    canonical = dict(sorted(group, key=_canonical_sort_key)[0])
    core, angle, _ = series_title_core(canonical.get("title", ""))
    if not core:
        core, angle, _ = series_title_core(_pick_best_text(group, "title"))
    canonical["title"] = _merged_title(core, hub_kind=hub_kind, angle=angle)
    canonical["summary"] = _merge_summary(core or canonical["title"], group)

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
        for suffix in TITLE_SUFFIXES:
            if article_title.endswith(suffix):
                article_title = article_title[: -len(suffix)]
                break
        canonical["article_title"] = article_title.strip()

    article_lead = _pick_best_text(group, "article_lead")
    if article_lead:
        canonical["article_lead"] = article_lead

    return canonical


def collapse_series_rows(
    rows: list[dict[str, str]],
    *,
    hub_kind: str,
    min_group_size: int = 2,
) -> tuple[list[dict[str, str]], dict[str, str]]:
    redirects: dict[str, str] = {}
    passthrough: list[dict[str, str]] = []
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        key = series_group_key(row)
        if key is None:
            passthrough.append(row)
        else:
            groups[key].append(row)

    collapsed = list(passthrough)
    for group in groups.values():
        if len(group) < min_group_size:
            collapsed.extend(group)
            continue

        cores = {series_title_core(r.get("title", ""))[0] for r in group}
        if len(cores) > 1:
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


def flatten_redirects(redirects: dict[str, str]) -> dict[str, str]:
    flat: dict[str, str] = {}
    for source, target in redirects.items():
        seen: set[str] = set()
        current = target
        while current in redirects and current not in seen:
            seen.add(current)
            current = redirects[current]
        flat[source] = current
    return flat


def merge_redirect_maps(*maps: dict[str, str]) -> dict[str, str]:
    combined: dict[str, str] = {}
    for mapping in maps:
        combined.update(mapping)
    return flatten_redirects(combined)
