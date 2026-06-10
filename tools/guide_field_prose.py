#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験ガイド本文の field-* / field-{id} 内部記法を読者向けラベルへ置換する。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from tools.editorial_quality import norm
from tools.guide_slug_prose import resolve_bare_urls, resolve_slug_references, slug_link_label

FIELD_WILDCARD_SUBS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"各field-\*"), "各科目の"),
    (re.compile(r"field-\*-calculation"), "分野別計算"),
    (re.compile(r"field-\*頻出論点"), "分野別頻出論点"),
    (re.compile(r"field-\*記事"), "分野別記事"),
    (re.compile(r"field-\*連携"), "分野別記事連携"),
    (re.compile(r"field-\*"), "分野別"),
)


def field_prefix_labels(root: Path) -> dict[str, str]:
    cfg_path = root / "site-config.json"
    if not cfg_path.is_file():
        return {}
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    labels: dict[str, str] = {}
    for f in cfg.get("fields") or []:
        if not isinstance(f, dict):
            continue
        fid = str(f.get("id") or "").strip()
        name = str(f.get("name") or fid).strip()
        if fid:
            labels[f"field-{fid}"] = name
    return labels


def scrub_field_wildcards(text: str) -> str:
    if not text:
        return text
    out = text
    for pat, repl in FIELD_WILDCARD_SUBS:
        out = pat.sub(repl, out)
    return out


def scrub_field_prefixes(text: str, prefix_labels: dict[str, str]) -> str:
    if not text or not prefix_labels:
        return text
    out = text
    ordered = sorted(prefix_labels, key=len, reverse=True)
    for prefix in ordered:
        label = prefix_labels[prefix]
        esc = re.escape(prefix)
        out = re.sub(rf"{esc}用語", f"{label}用語", out)
        out = re.sub(rf"{esc}ハブ", f"{label}ハブ", out)
        out = re.sub(rf"{esc}記事", f"{label}記事", out)
        out = re.sub(rf"(?<![a-z0-9-]){esc}(?![a-z0-9-])", label, out)
    return out


def scrub_slug_english(text: str, slug: str, label: str) -> str:
    if not text or not slug or not label:
        return text
    eng = slug.replace("-", " ")
    if eng == slug or len(eng) < 4:
        return text
    return re.sub(re.escape(eng), label, text, flags=re.I)


def resolve_reader_slug_prose(
    text: str,
    *,
    slug_titles: dict[str, str],
    current_slug: str = "",
    link_internal: bool = False,
    prefix_labels: dict[str, str] | None = None,
    url_labels: dict[str, str] | None = None,
    link_external_urls: bool = True,
) -> str:
    """field 内部記法除去 → bare slug 解決 → 裸 URL ラベル化の順で読者向け prose に整える。"""
    raw = norm(text)
    if not raw:
        return raw
    out = scrub_field_wildcards(raw)
    if slug_titles:
        out = resolve_slug_references(
            out,
            slug_titles,
            current_slug,
            link_internal=link_internal,
        )
    if url_labels:
        out = resolve_bare_urls(
            out,
            url_labels,
            link_external=link_external_urls,
        )
    if prefix_labels:
        out = scrub_field_prefixes(out, prefix_labels)
    return out


def slug_label(slug_titles: dict[str, str], slug: str) -> str:
    title = slug_titles.get(slug, "")
    return slug_link_label(title) or slug.replace("-", " ")


def english_leak_patterns(prefix_labels: dict[str, str]) -> list[tuple[str, re.Pattern[str]]]:
    """監査用: field 内部記法の検出パターン。"""
    ids = "|".join(re.escape(k.removeprefix("field-")) for k in prefix_labels)
    partial = re.compile(rf"\bfield-(?:\*|{ids})(?:-[a-z0-9-]+)?\b") if ids else re.compile(r"field-\*")
    return [
        ("field_wildcard", re.compile(r"field-\*")),
        ("field_prefix", partial),
    ]


def scan_english_leaks(
    text: str,
    *,
    slug: str,
    slug_set: set[str],
    prefix_labels: dict[str, str],
) -> list[tuple[str, str]]:
    """読者向けテキスト中の slug / field 内部記法露出。"""
    from tools.guide_slug_prose import slug_leaks_against_pool

    raw = norm(text)
    if not raw:
        return []
    hits: list[tuple[str, str]] = []
    for name, pat in english_leak_patterns(prefix_labels):
        m = pat.search(raw)
        if m:
            hits.append((name, m.group(0)))
    for leak in slug_leaks_against_pool(raw, slug, slug_set):
        hits.append(("bare_slug", leak))
    eng = slug.replace("-", " ")
    if slug and eng != slug and re.search(rf"(?<![a-z0-9-]){re.escape(eng)}(?![a-z0-9-])", raw, re.I):
        hits.append(("slug_english", eng))
    return hits
