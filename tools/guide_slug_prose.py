#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験ガイド本文中の bare slug を読者向けラベル／内部リンクへ解決する。"""

from __future__ import annotations

import re
from collections.abc import Callable

from tools.editorial_quality import norm

# 本文中の slug 直書き（mentalhealth batch 等）を検出・置換する。
_SLUG_TOKEN = r"[a-z][a-z0-9-]*"
_URL_RE = re.compile(r"https?://[^\s\])）】\]]+", re.I)
_MD_LINK_RE = re.compile(r"\[[^\]]+\]\([^)]+\)")
_SLUG_BEFORE = r"(?<![a-z0-9-])"
_SLUG_AFTER = r"(?![a-z0-9-])"


def slug_link_label(title: str) -> str:
    """記事タイトルからリンク表示用の短いラベルを作る。"""
    t = norm(title)
    if not t:
        return ""
    if "｜" in t:
        t = t.split("｜", 1)[0].strip()
    t = re.sub(r"^【[^】]+】\s*", "", t).strip()
    return t or norm(title)


def _slug_alternation(slugs: list[str]) -> str:
    return "|".join(re.escape(s) for s in sorted(set(slugs), key=len, reverse=True))


_SLOT_RE = re.compile(r"\ue000\d+\ue001")


def _stash_slots(text: str) -> tuple[str, list[str]]:
    keys: list[str] = []

    def repl(match: re.Match[str]) -> str:
        keys.append(match.group(0))
        return f"\ue002{len(keys) - 1}\ue003"

    return _SLOT_RE.sub(repl, text), keys


def _unstash_slots(text: str, keys: list[str]) -> str:
    out = text
    for i, key in enumerate(keys):
        out = out.replace(f"\ue002{i}\ue003", key)
    return out


def _protect(text: str) -> tuple[str, list[tuple[str, str]]]:
    """URL と既存 Markdown リンクをプレースホルダー退避。"""
    slots: list[tuple[str, str]] = []

    def stash(match: re.Match[str]) -> str:
        key = f"\ue000{len(slots)}\ue001"
        slots.append((key, match.group(0)))
        return key

    out = _MD_LINK_RE.sub(stash, text)
    out = _URL_RE.sub(stash, out)
    return out, slots


def _restore(text: str, slots: list[tuple[str, str]]) -> str:
    out = text
    for key, raw in slots:
        out = out.replace(key, raw)
    return out


def _replace_slug_paths(
    text: str,
    slug_titles: dict[str, str],
    *,
    current_slug: str,
    render: Callable[[str, str], str],
) -> str:
    if not slug_titles or "/" not in text:
        return text
    alts = _slug_alternation(list(slug_titles))
    path_re = re.compile(rf"{_SLUG_BEFORE}(?:{alts})(?:/(?:{alts}))+")
    known = set(slug_titles)

    def repl(match: re.Match[str]) -> str:
        parts = match.group(0).split("/")
        if not all(p in known for p in parts):
            return match.group(0)
        rendered = [render(p, slug_titles[p]) for p in parts]
        return "・".join(rendered)

    return path_re.sub(repl, text)


def _replace_bare_slugs(
    text: str,
    slug_titles: dict[str, str],
    *,
    current_slug: str,
    render: Callable[[str, str], str],
) -> str:
    if not slug_titles:
        return text
    out = text
    ordered = sorted(slug_titles, key=len, reverse=True)
    alts = _slug_alternation(ordered)

    def slug_render(slug: str) -> str:
        title = slug_titles[slug]
        if slug == current_slug:
            return "本記事"
        return render(slug, title)

    if alts:
        out = re.sub(
            rf"{_SLUG_BEFORE}({alts})記事{_SLUG_AFTER}",
            lambda m: f"{slug_render(m.group(1))}の記事",
            out,
        )
        if current_slug:
            out = re.sub(
                rf"{_SLUG_BEFORE}{re.escape(current_slug)}（本記事）",
                "本記事",
                out,
            )

    if not alts:
        return out

    masked, slot_keys = _stash_slots(out)
    masked, extra_slots = _protect(masked)
    masked = re.sub(
        rf"{_SLUG_BEFORE}({alts}){_SLUG_AFTER}",
        lambda m: slug_render(m.group(1)),
        masked,
    )
    out = _restore(masked, extra_slots)
    return _unstash_slots(out, slot_keys)


def plain_text_from_reader_prose(text: str) -> str:
    """Markdown 内部リンクをラベルだけのプレーンテキストへ。"""
    if not text:
        return text
    return re.sub(r"\[([^\]]+)\]\(\.\./[^)]+\)", r"\1", text)


def resolve_slug_references(
    text: str,
    slug_titles: dict[str, str],
    current_slug: str = "",
    *,
    link_internal: bool = False,
) -> str:
    """bare slug を記事タイトル（または内部 Markdown リンク）へ置換する。"""
    raw = norm(text)
    if not raw or not slug_titles:
        return raw

    def render(slug: str, _title: str) -> str:
        lbl = slug_link_label(slug_titles.get(slug, "")) or slug
        if slug == current_slug:
            return "本記事"
        if link_internal:
            return f"[{lbl}](../{slug}/)"
        return lbl

    protected, slots = _protect(raw)
    out = _replace_slug_paths(
        protected,
        slug_titles,
        current_slug=current_slug,
        render=render,
    )
    out, md_slots = _protect(out)
    slots.extend(md_slots)
    out = _replace_bare_slugs(
        out,
        slug_titles,
        current_slug=current_slug,
        render=render,
    )
    return _restore(out, slots)


def slug_leaks_against_pool(text: str, slug: str, slug_set: set[str]) -> list[str]:
    """既知 slug プールに対する bare slug 露出（検証用）。"""
    raw = norm(text)
    if not raw or not slug_set:
        return []
    protected, _ = _protect(raw)
    hits: list[str] = []
    alts = _slug_alternation(sorted(slug_set))
    if not alts:
        return hits
    token_re = re.compile(rf"{_SLUG_BEFORE}(?:{alts}){_SLUG_AFTER}")
    for match in token_re.finditer(protected):
        token = match.group(0)
        if token == slug:
            continue
        if token not in hits:
            hits.append(token)
    path_re = re.compile(rf"{_SLUG_BEFORE}(?:{alts})(?:/(?:{alts}))+")
    for match in path_re.finditer(protected):
        for part in match.group(0).split("/"):
            if part != slug and part not in hits:
                hits.append(part)
    return hits
