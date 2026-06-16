#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Insert affiliate product name links into guide section prose."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from tools.affiliate_brief import brief_products, norm, product_affiliate_url
from tools.affiliate_links import is_affiliate_url

_MD_LINK = re.compile(r"\[[^\]]+\]\(https?://[^)\s]+\)")
_A8_NET_URL = re.compile(r"https://px\.a8\.net/svt/ejp\?a8mat=[^\s——]+", re.I)
_AMAZON_URL = re.compile(r"https://www\.amazon\.co\.jp/[^\s——]+", re.I)

AFFILIATE_COURSE_NAMES: tuple[str, ...] = (
    "オンスク衛生管理者講座",
    "オンスク.JP 衛生管理者オンライン通信講座",
    "SMART合格講座（第一種衛生管理者）",
    "SMART合格講座",
)


def affiliate_name_labels(
    brief: dict[str, Any] | None,
    article: dict[str, str] | None = None,
) -> list[str]:
    """本文中で「」括りする商品名・講座名（長い順）。"""
    labels: list[str] = list(AFFILIATE_COURSE_NAMES)
    if brief:
        for product in brief_products(brief):
            name, _url, workbook, _workbook_url = _product_urls(product)
            if name:
                labels.append(name)
            if workbook:
                labels.append(workbook)
            trial = norm(str(product.get("trial_label") or ""))
            if trial:
                labels.append(trial)
    seen: set[str] = set()
    unique: list[str] = []
    for label in sorted(labels, key=len, reverse=True):
        key = norm(label)
        if key and key not in seen:
            seen.add(key)
            unique.append(key)
    return unique


def wrap_affiliate_names_in_quotes(text: str, labels: list[str]) -> str:
    """商品名・講座名を「」で括る（既に括弧付き・リンク内は除外）。"""
    if not text or not labels:
        return text
    out = text
    for label in labels:
        if not label or len(label) < 2:
            continue
        escaped = re.escape(label)
        pattern = rf"(?<![「『\[（]){escaped}(?![」』\]）])"
        out = re.sub(pattern, f"「{label}」", out)
    return out


def prepare_affiliate_prose(
    text: str,
    *,
    brief: dict[str, Any] | None,
    article: dict[str, str] | None,
    apply_links: bool = True,
) -> str:
    """アフィリエイト記事本文：商品名を「」で括り、必要ならリンク化。"""
    from tools.affiliate_links import is_affiliate_article

    if not text or not article or not is_affiliate_article(article):
        return text
    labels = affiliate_name_labels(brief, article)
    out = wrap_affiliate_names_in_quotes(text, labels)
    if apply_links and (brief or article):
        if brief:
            out = inject_affiliate_product_links(out, brief, var_transform=lambda x: x)
            out = replace_brief_affiliate_urls(out, brief)
        if article:
            out = replace_row_affiliate_urls(out, article)
        url_map = {**affiliate_url_labels(brief or {}), **affiliate_url_labels_from_row(article)}
        if url_map:
            from tools.guide_slug_prose import resolve_bare_urls

            out = resolve_bare_urls(out, url_map, link_external=True)
    return out


def _product_urls(product: dict[str, Any]) -> tuple[str, str, str, str]:
    name = norm(str(product.get("name") or ""))
    url = product_affiliate_url(product)
    workbook = norm(str(product.get("workbook_name") or ""))
    workbook_url = norm(str(product.get("workbook_amazon_url") or ""))
    return name, url, workbook, workbook_url


def affiliate_url_label(product: dict[str, Any]) -> str:
    """裸 URL 置換用の短いリンクラベル。"""
    provider = norm(str(product.get("provider") or ""))
    if provider:
        return f"{provider} 公式"
    name = norm(str(product.get("name") or ""))
    if name:
        return f"{name} 公式"
    return "公式サイト"


def affiliate_url_labels_from_row(article: dict[str, Any] | None) -> dict[str, str]:
    """related_links の https://…:ラベル から裸 URL 置換用辞書を作る。"""
    if not article:
        return {}
    from tools.affiliate_links import is_trackable_asp_url, split_semicolon
    from tools.guide_slug_prose import url_label_map_from_sources
    from tools.related_links import parse_related_link_token

    items: list[dict[str, str]] = []
    for token in split_semicolon(str(article.get("related_links") or "")):
        target, label = parse_related_link_token(token)
        if not is_trackable_asp_url(target):
            continue
        items.append({"url": target, "label": label or affiliate_url_label({})})
    return url_label_map_from_sources(items)


def replace_row_affiliate_urls(text: str, article: dict[str, Any] | None) -> str:
    """related_links 内 ASP URL（a8mat / Amazon ASIN 一致）を Markdown 外部リンクへ。"""
    if not text or not article:
        return text
    from tools.affiliate_links import is_trackable_asp_url, split_semicolon
    from tools.related_links import parse_related_link_token

    slots: list[str] = []

    def stash_md(match: re.Match[str]) -> str:
        slots.append(match.group(0))
        return f"\ue000{len(slots) - 1}\ue001"

    out = _MD_LINK.sub(stash_md, text)
    for token in split_semicolon(str(article.get("related_links") or "")):
        target, label = parse_related_link_token(token)
        if not is_trackable_asp_url(target):
            continue
        link_label = label or affiliate_url_label({})
        md = f"[{link_label}]({target})"

        a8mat = re.search(r"a8mat=([^&]+)", target, re.I)
        if a8mat and "px.a8.net" in target.lower():
            token_esc = re.escape(a8mat.group(1))
            pattern = re.compile(
                rf"https://px\.a8\.net/svt/ejp\?a8mat={token_esc}(?:[&][^\s——]*)?",
                re.I,
            )
            out = pattern.sub(md, out)
            continue

        asin = re.search(r"/dp/([A-Z0-9]{10})", target, re.I)
        if asin:
            token_esc = re.escape(asin.group(1))
            pattern = re.compile(
                rf"https://www\.amazon\.co\.jp/[^\s——]*{token_esc}[^\s——]*",
                re.I,
            )
            out = pattern.sub(md, out)

    for i, raw in enumerate(slots):
        out = out.replace(f"\ue000{i}\ue001", raw)
    return out


def affiliate_url_labels(brief: dict[str, Any]) -> dict[str, str]:
    """brief 内 ASP URL → リンクラベル（resolve_bare_urls 用）。"""
    out: dict[str, str] = {}
    for product in brief_products(brief):
        url = product_affiliate_url(product)
        if not is_affiliate_url(url):
            continue
        label = affiliate_url_label(product)
        out[url] = label
        trimmed = url.rstrip("/")
        if trimmed:
            out[trimmed] = label
    return out


def product_link_labels(
    brief: dict[str, Any],
    *,
    var_transform: Callable[[str], str] | None = None,
) -> list[tuple[str, str]]:
    """Return (label, url) pairs longest-first for plain-text replacement."""
    transform = var_transform or (lambda x: x)
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(label: str, url: str) -> None:
        label = norm(label)
        if not label or not is_affiliate_url(url) or label in seen:
            return
        seen.add(label)
        entries.append((label, url))

    for product in brief_products(brief):
        name, url, workbook, workbook_url = _product_urls(product)
        if name:
            name_t = transform(name)
            add(f"「{name_t}」", url)
            add(name_t, url)
            add(f"【{name_t}】", url)
            add(f"『{name_t}』", url)
        if workbook:
            wb_t = transform(workbook)
            add(f"「{wb_t}」", workbook_url)
            add(wb_t, workbook_url)
            add(f"『{wb_t}』", workbook_url)
        trial = norm(str(product.get("trial_label") or ""))
        trial_url = norm(str(product.get("trial_url") or ""))
        if trial and trial_url:
            trial_t = transform(trial)
            add(trial_t, trial_url)

    entries.sort(key=lambda item: len(item[0]), reverse=True)
    return entries


def replace_brief_affiliate_urls(text: str, brief: dict[str, Any]) -> str:
    """brief 内 ASP URL（a8mat / Amazon ASIN 一致）を Markdown 外部リンクへ。"""
    if not text or not brief:
        return text

    slots: list[str] = []

    def stash_md(match: re.Match[str]) -> str:
        slots.append(match.group(0))
        return f"\ue000{len(slots) - 1}\ue001"

    out = _MD_LINK.sub(stash_md, text)

    for product in brief_products(brief):
        url = product_affiliate_url(product)
        if not is_affiliate_url(url):
            continue
        label = affiliate_url_label(product)
        md = f"[{label}]({url})"

        a8mat = re.search(r"a8mat=([^&]+)", url, re.I)
        if a8mat and "px.a8.net" in url.lower():
            token = re.escape(a8mat.group(1))
            pattern = re.compile(
                rf"https://px\.a8\.net/svt/ejp\?a8mat={token}(?:[&][^\s——]*)?",
                re.I,
            )
            out = pattern.sub(md, out)
            continue

        asin = re.search(r"/dp/([A-Z0-9]{10})", url, re.I)
        if asin:
            token = re.escape(asin.group(1))
            pattern = re.compile(
                rf"https://www\.amazon\.co\.jp/[^\s——]*{token}[^\s——]*",
                re.I,
            )
            out = pattern.sub(md, out)

    for i, raw in enumerate(slots):
        out = out.replace(f"\ue000{i}\ue001", raw)
    return out


def inject_affiliate_product_links(
    text: str,
    brief: dict[str, Any] | None,
    *,
    var_transform: Callable[[str], str] | None = None,
) -> str:
    """Turn product names in prose into [name](url) markdown (rendered as inline links)."""
    if not brief or not norm(text):
        return text
    if _MD_LINK.search(text):
        # Respect hand-authored markdown links; still add missing names only.
        pass
    out = text
    for label, url in product_link_labels(brief, var_transform=var_transform):
        md = f"[{label}]({url})"
        if md in out or f"]({url})" in out and label in out:
            continue
        out = out.replace(label, md)
    return out
