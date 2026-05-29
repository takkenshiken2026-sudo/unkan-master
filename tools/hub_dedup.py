#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知識ハブ・用語解説の重複整理（表記ゆれ・角度バッチ・カッコ付き用語）."""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from tools.hub_collapse_angles import (
    _merge_group,
    batch_number,
    collapse_finalized_hubs,
    strip_angle_title,
    write_hub_redirects,
)
from tools.hub_collapse_series import merge_redirect_maps

PAREN_RE = re.compile(r"[（(][^）)]*[）)]")

TEXT_MERGE_FIELDS = (
    "definition",
    "explanation",
    "term_detail_body",
    "exam_points",
    "common_mistakes",
    "memory_tip",
    "summary_points",
    "article_lead",
    "short_def",
)

GLOSSARY_FAQ_FIELDS = tuple(
    f"faq_{i}_{kind}" for i in range(1, 5) for kind in ("question", "answer")
)


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        return fields, [dict(row) for row in reader]


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def base_term_name(term: str) -> str:
    return PAREN_RE.sub("", (term or "").strip()).strip()


def normalize_hub_label(title: str) -> str:
    base, _ = strip_angle_title(title or "")
    base = re.sub(r"日間$", "日", base.strip())
    return re.sub(r"\s+", "", base)


def _row_richness(row: dict[str, str]) -> int:
    parts = [
        row.get("summary") or "",
        row.get("item_rows") or "",
        row.get("pattern_rows") or "",
        row.get("compare_rows") or "",
        row.get("term_detail_body") or "",
        row.get("article_lead") or "",
    ]
    return sum(len(p) for p in parts)


def _canonical_sort_key(row: dict[str, str]) -> tuple[int, int, int, str]:
    slug = row.get("slug") or ""
    batch = batch_number(slug)
    has_batch = 1 if batch is not None else 0
    return (has_batch, batch or 999, -_row_richness(row), slug)


def collapse_label_variants(
    rows: list[dict[str, str]],
    *,
    hub_kind: str,
    min_group_size: int = 2,
) -> tuple[list[dict[str, str]], dict[str, str]]:
    redirects: dict[str, str] = {}
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        label = normalize_hub_label(row.get("title", ""))
        if label:
            groups[label].append(row)

    merged_by_slug: dict[str, dict[str, str]] = {}
    skip_slugs: set[str] = set()

    for group in groups.values():
        if len(group) < min_group_size:
            continue
        slugs = {row.get("slug", "") for row in group if row.get("slug")}
        if len(slugs) < 2:
            continue

        ordered = sorted(group, key=_canonical_sort_key)
        merged = _merge_group(ordered, hub_kind=hub_kind)
        canon_slug = ordered[0].get("slug", "") or merged.get("slug", "")
        if canon_slug:
            merged["slug"] = canon_slug
        if not canon_slug:
            continue

        merged_by_slug[canon_slug] = merged
        for row in group:
            slug = row.get("slug", "")
            if slug and slug != canon_slug:
                redirects[slug] = canon_slug
                skip_slugs.add(slug)

    out: list[dict[str, str]] = []
    emitted: set[str] = set()
    for row in rows:
        slug = row.get("slug", "")
        if slug in skip_slugs:
            continue
        if slug in merged_by_slug:
            if slug in emitted:
                continue
            out.append(merged_by_slug[slug])
            emitted.add(slug)
            continue
        out.append(row)

    return out, redirects


def _pick_longest(values: Iterable[str]) -> str:
    seen: set[str] = set()
    best = ""
    for val in values:
        text = (val or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        if len(text) > len(best):
            best = text
    return best


def _merge_semicolon(values: Iterable[str]) -> str:
    seen: set[str] = set()
    merged: list[str] = []
    for val in values:
        for part in re.split(r"[;；]", val or ""):
            item = part.strip()
            if not item or item in seen:
                continue
            seen.add(item)
            merged.append(item)
    return ";".join(merged)


def merge_glossary_group(group: list[dict[str, str]]) -> dict[str, str]:
    no_paren = [row for row in group if not PAREN_RE.search(row.get("term") or "")]
    if no_paren:
        pool = sorted(no_paren, key=lambda row: (-_row_richness(row), row.get("term") or ""))
        canonical = dict(pool[0])
    else:
        ordered = sorted(group, key=lambda row: (-_row_richness(row), row.get("term") or ""))
        canonical = dict(ordered[0])
        base = base_term_name(canonical.get("term", ""))
        if base:
            canonical["term"] = base

    for field in TEXT_MERGE_FIELDS:
        best = _pick_longest(row.get(field, "") for row in group)
        if best:
            canonical[field] = best

    for field in GLOSSARY_FAQ_FIELDS:
        best = _pick_longest(row.get(field, "") for row in group)
        if best:
            canonical[field] = best

    canonical["related_terms"] = _merge_semicolon(row.get("related_terms", "") for row in group)
    canonical["tags"] = _merge_semicolon(row.get("tags", "") for row in group)
    canonical["legal_basis"] = _pick_longest(row.get("legal_basis", "") for row in group)
    return canonical


def merge_glossary_paren_rows(
    rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], dict[str, str]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        base = base_term_name(row.get("term", ""))
        if base:
            groups[base].append(row)

    term_remap: dict[str, str] = {}
    merged_rows: list[dict[str, str]] = []

    for base, group in sorted(groups.items()):
        if len(group) == 1:
            merged_rows.append(group[0])
            continue
        merged = merge_glossary_group(group)
        merged_rows.append(merged)
        canon_term = merged.get("term", "")
        for row in group:
            old_term = (row.get("term") or "").strip()
            if old_term and old_term != canon_term:
                term_remap[old_term] = canon_term
            if base != canon_term:
                term_remap[base] = canon_term

    return merged_rows, term_remap


def build_glossary_lookup(rows: list[dict[str, str]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for row in rows:
        term = (row.get("term") or "").strip()
        if not term:
            continue
        lookup[term] = term
        base = base_term_name(term)
        if base and base not in lookup:
            lookup[base] = term
    return lookup


def resolve_glossary_term(ref: str, lookup: dict[str, str]) -> str:
    item = (ref or "").strip()
    if not item:
        return item
    if item in lookup:
        return lookup[item]
    base = base_term_name(item)
    if base in lookup:
        return lookup[base]
    return item


def remap_related_terms_field(value: str, term_remap: dict[str, str]) -> str:
    if not value:
        return value
    parts = re.split(r"[;；]", value)
    out: list[str] = []
    seen: set[str] = set()
    for part in parts:
        item = part.strip()
        if not item:
            continue
        item = term_remap.get(item, item)
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return ";".join(out)


def apply_glossary_related_term_fixup(
    rows: list[dict[str, str]],
    glossary_rows: list[dict[str, str]],
    *,
    fields: tuple[str, ...] = ("related_terms",),
) -> None:
    lookup = build_glossary_lookup(glossary_rows)
    for row in rows:
        for field in fields:
            if field not in row:
                continue
            parts = re.split(r"[;；]", row.get(field, ""))
            fixed = [
                resolve_glossary_term(part.strip(), lookup)
                for part in parts
                if part.strip()
            ]
            deduped: list[str] = []
            seen: set[str] = set()
            for item in fixed:
                if item in seen:
                    continue
                seen.add(item)
                deduped.append(item)
            row[field] = ";".join(deduped)


def apply_term_remap_to_rows(
    rows: list[dict[str, str]],
    term_remap: dict[str, str],
    *,
    fields: tuple[str, ...] = ("related_terms",),
) -> None:
    if not term_remap:
        return
    for row in rows:
        for field in fields:
            if field in row:
                row[field] = remap_related_terms_field(row.get(field, ""), term_remap)


def load_hub_redirects(data_dir: Path) -> dict[str, dict[str, str]]:
    path = data_dir / "hub_redirects.json"
    empty = {"compare": {}, "numbers": {}, "mistakes": {}}
    if not path.is_file():
        return empty
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return empty
    out = dict(empty)
    for key in out:
        section = raw.get(key)
        if isinstance(section, dict):
            out[key] = {str(k): str(v) for k, v in section.items()}
    return out


def dedup_hub_rows(
    comparisons: list[dict[str, str]],
    numbers: list[dict[str, str]],
    mistakes: list[dict[str, str]],
    *,
    existing_redirects: dict[str, dict[str, str]] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], dict[str, dict[str, str]]]:
    comparisons, numbers, mistakes, angle_redirects = collapse_finalized_hubs(
        comparisons, numbers, mistakes
    )

    comparisons, compare_labels = collapse_label_variants(comparisons, hub_kind="compare")
    numbers, numbers_labels = collapse_label_variants(numbers, hub_kind="numbers")
    mistakes, mistakes_labels = collapse_label_variants(mistakes, hub_kind="mistakes")

    redirects = {
        "compare": merge_redirect_maps(
            (existing_redirects or {}).get("compare", {}),
            angle_redirects.get("compare", {}),
            compare_labels,
        ),
        "numbers": merge_redirect_maps(
            (existing_redirects or {}).get("numbers", {}),
            angle_redirects.get("numbers", {}),
            numbers_labels,
        ),
        "mistakes": merge_redirect_maps(
            (existing_redirects or {}).get("mistakes", {}),
            angle_redirects.get("mistakes", {}),
            mistakes_labels,
        ),
    }
    return comparisons, numbers, mistakes, redirects


def find_label_variant_clusters(rows: list[dict[str, str]]) -> list[tuple[str, list[tuple[str, str]]]]:
    groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for row in rows:
        label = normalize_hub_label(row.get("title", ""))
        slug = row.get("slug", "")
        if label and slug:
            groups[label].append((slug, row.get("title", "")))
    return [(label, items) for label, items in sorted(groups.items()) if len(items) >= 2]


def find_angle_batch_clusters(rows: list[dict[str, str]]) -> list[tuple[str, list[tuple[str, str]]]]:
    from tools.hub_collapse_angles import topic_group_key

    groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for row in rows:
        slug = row.get("slug", "")
        key = topic_group_key(slug)
        if key is None:
            continue
        groups[key].append((slug, row.get("title", "")))
    return [(key, items) for key, items in sorted(groups.items()) if len({s for s, _ in items}) >= 2]


def find_glossary_paren_clusters(rows: list[dict[str, str]]) -> list[tuple[str, list[str]]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        base = base_term_name(row.get("term", ""))
        term = (row.get("term") or "").strip()
        if base:
            groups[base].append(term)
    return [(base, terms) for base, terms in sorted(groups.items()) if len(terms) >= 2]
