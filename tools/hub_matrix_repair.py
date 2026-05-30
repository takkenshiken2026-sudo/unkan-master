#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知識ハブ早見表・誤答表 JSON の重複行を整理する。"""

from __future__ import annotations

import json
import re
from typing import Any

GENERIC_NUMBER_ITEMS = frozenset({"関連制度", "記録・保存", "試験の確認点"})
MAX_NUMBER_ITEMS = 12
MAX_PATTERN_ITEMS = 16

BATCH_TOKEN_RE = re.compile(r"^S\d+$", re.I)


def _parse_json_list(raw: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def dedupe_number_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_full: set[tuple[str, str, str]] = set()
    seen_generic: set[tuple[str, str, str]] = set()
    merged: list[dict[str, Any]] = []
    for item in items:
        label = (item.get("item") or "").strip()
        value = (item.get("value") or "").strip()
        note = (item.get("note") or "").strip()
        if not label or not value:
            continue
        key = (label, value, note)
        if key in seen_full:
            continue
        if label in GENERIC_NUMBER_ITEMS:
            if key in seen_generic:
                continue
            seen_generic.add(key)
        seen_full.add(key)
        merged.append(item)
        if len(merged) >= MAX_NUMBER_ITEMS:
            break
    return merged


def dedupe_pattern_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    merged: list[dict[str, Any]] = []
    for item in items:
        topic = (item.get("topic") or "").strip()
        wrong = (item.get("wrong") or "").strip()
        correct = (item.get("correct") or "").strip()
        if not topic or not wrong or not correct:
            continue
        key = (topic, wrong, correct)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
        if len(merged) >= MAX_PATTERN_ITEMS:
            break
    return merged


def repair_item_rows_field(raw: str) -> tuple[str, bool]:
    items = _parse_json_list(raw)
    if not items:
        return raw, False
    deduped = dedupe_number_items(items)
    if len(deduped) == len(items):
        return raw, False
    return json.dumps(deduped, ensure_ascii=False), True


def repair_pattern_rows_field(raw: str) -> tuple[str, bool]:
    items = _parse_json_list(raw)
    if not items:
        return raw, False
    deduped = dedupe_pattern_items(items)
    if len(deduped) == len(items):
        return raw, False
    return json.dumps(deduped, ensure_ascii=False), True


def strip_internal_tags(raw: str) -> tuple[str, bool]:
    parts = [p.strip() for p in re.split(r"[;；]", raw or "") if p.strip()]
    kept = [p for p in parts if not BATCH_TOKEN_RE.fullmatch(p)]
    if kept == parts:
        return raw, False
    return ";".join(kept), True


def repair_hub_matrix_row(row: dict[str, str]) -> bool:
    changed = False
    if "item_rows" in row:
        new_val, did = repair_item_rows_field(row.get("item_rows") or "")
        if did:
            row["item_rows"] = new_val
            changed = True
    if "pattern_rows" in row:
        new_val, did = repair_pattern_rows_field(row.get("pattern_rows") or "")
        if did:
            row["pattern_rows"] = new_val
            changed = True
    if "tags" in row:
        new_val, did = strip_internal_tags(row.get("tags") or "")
        if did:
            row["tags"] = new_val
            changed = True
    return changed


def repair_hub_matrix_rows(rows: list[dict[str, str]]) -> int:
    changed = 0
    for row in rows:
        if repair_hub_matrix_row(row):
            changed += 1
    return changed
