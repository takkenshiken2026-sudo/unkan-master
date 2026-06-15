#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験ガイド本文中の bare slug を読者向けラベル／内部リンクへ解決する。"""

from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import urlparse

from tools.editorial_quality import norm

# 本文中の slug 直書き（mentalhealth batch 等）を検出・置換する。
_SLUG_TOKEN = r"[a-z][a-z0-9-]*"
# URL 本体のみ（直後の日本語句読点や em dash まで食い込まない）
_URL_CHARS = r"[\w\-./?#=%&+~]"
_URL_RE = re.compile(rf"https?://{_URL_CHARS}+", re.I)
_BARE_URL_RE = re.compile(rf"https?://{_URL_CHARS}+", re.I)
_PAREN_URL_RE = re.compile(rf"[（(](https?://{_URL_CHARS}+)[）)]")
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
    t = re.sub(r"\s*【[^】]+】\s*$", "", t).strip()
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


def url_label_map_from_sources(items: list[dict[str, str]]) -> dict[str, str]:
    """primary_sources の label|url から URL・ホスト名 → ラベル辞書を作る。"""
    out: dict[str, str] = {}
    for item in items:
        url = norm(item.get("url", ""))
        label = norm(item.get("label", ""))
        if not url or not label:
            continue
        out[url] = label
        trimmed = url.rstrip("/")
        if trimmed:
            out[trimmed] = label
        host = urlparse(url).netloc
        if host:
            out[host] = label
            if host.startswith("www."):
                out[host[4:]] = label
    return out


def _label_for_url(url: str, url_labels: dict[str, str]) -> str:
    if url in url_labels:
        return url_labels[url]
    trimmed = url.rstrip("/")
    if trimmed in url_labels:
        return url_labels[trimmed]
    host = urlparse(url).netloc
    if host and host in url_labels:
        return url_labels[host]
    return ""


def resolve_bare_urls(
    text: str,
    url_labels: dict[str, str],
    *,
    link_external: bool = True,
) -> str:
    """本文中の裸 URL・ホスト名直書きをラベル（または Markdown 外部リンク）へ。"""
    raw = norm(text)
    if not raw or not url_labels:
        return raw

    slots: list[tuple[str, str]] = []

    def stash_md(match: re.Match[str]) -> str:
        key = f"\ue000{len(slots)}\ue001"
        slots.append((key, match.group(0)))
        return key

    out = _MD_LINK_RE.sub(stash_md, raw)

    def render_url(url: str) -> str:
        label = _label_for_url(url, url_labels)
        if not label:
            return url
        if link_external:
            return f"[{label}]({url})"
        return label

    out = _PAREN_URL_RE.sub(
        lambda m: f"（{_label_for_url(m.group(1), url_labels) or m.group(1)}）",
        out,
    )

    hosts = sorted(
        {k for k in url_labels if k and not k.startswith("http")},
        key=len,
        reverse=True,
    )
    for host in hosts:
        label = url_labels[host]
        http_url = next(
            (u for u in url_labels if u.startswith("http") and urlparse(u).netloc == host),
            "",
        )
        replacement = f"[{label}]({http_url})" if link_external and http_url else label
        out = re.sub(rf"(?<![:/\w.]){re.escape(host)}(?![\w./])", replacement, out)

    out = _BARE_URL_RE.sub(lambda m: render_url(m.group(0)), out)
    return _restore(out, slots)


def scan_bare_url_leaks(text: str) -> list[str]:
    """検証用: 本文中の裸 https:// 露出。"""
    raw = norm(text)
    if not raw:
        return []
    protected, _ = _protect(raw)
    hits: list[str] = []
    for match in _BARE_URL_RE.finditer(protected):
        token = match.group(0)
        if token not in hits:
            hits.append(token)
    return hits


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
