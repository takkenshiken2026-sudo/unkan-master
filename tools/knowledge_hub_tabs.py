# -*- coding: utf-8 -*-
"""知識ハブ（用語解説 / 比較 / 数値早見 / よくある誤答）のタブナビ。"""

from __future__ import annotations

import html

HUB_SECTIONS: tuple[str, ...] = ("terms", "compare", "numbers", "mistakes")

HUB_TABS: tuple[tuple[str, str], ...] = (
    ("terms", "用語解説"),
    ("compare", "比較・整理表"),
    ("numbers", "数値・期限早見表"),
    ("mistakes", "よくある誤答"),
)


def knowledge_hub_tab_hrefs(*, here: str) -> dict[str, str]:
    """here: terms / compare / numbers / mistakes（samples 等は terms 配下の sibling として扱う）。"""
    if here not in HUB_SECTIONS:
        return {
            "terms_href": "../index.html",
            "compare_href": "../compare/index.html",
            "numbers_href": "../numbers/index.html",
            "mistakes_href": "../mistakes/index.html",
        }

    out: dict[str, str] = {}
    for section in HUB_SECTIONS:
        key = "terms_href" if section == "terms" else f"{section}_href"
        if section == here:
            out[key] = "index.html"
        elif here == "terms":
            out[key] = "index.html" if section == "terms" else f"{section}/index.html"
        elif section == "terms":
            out[key] = "../index.html"
        else:
            out[key] = f"../{section}/index.html"
    return out


def knowledge_hub_tabs_html(*, current: str, **hrefs: str) -> str:
    """current: HUB_SECTIONS のいずれか。hrefs 未指定時は here=current の相対パスを使う。"""
    if not hrefs:
        hrefs = knowledge_hub_tab_hrefs(here=current)
    valid = {tab_id for tab_id, _ in HUB_TABS}
    if current not in valid:
        raise ValueError(f"unknown tab current: {current!r}")

    defaults = knowledge_hub_tab_hrefs(here=current)
    merged = {**defaults, **hrefs}

    items: list[str] = []
    for tab_id, label in HUB_TABS:
        cls = "q-hub-tab is-current" if tab_id == current else "q-hub-tab"
        href_key = "terms_href" if tab_id == "terms" else f"{tab_id}_href"
        href = merged.get(href_key, defaults.get(href_key, "#"))
        if tab_id == current:
            inner = f'<span class="q-hub-tab-label" aria-current="page">{html.escape(label)}</span>'
        else:
            inner = (
                f'<a class="q-hub-tab-label" href="{html.escape(href)}">'
                f"{html.escape(label)}</a>"
            )
        items.append(f'<li class="{cls}">{inner}</li>')

    note = (
        '<p class="q-study-modes-note">'
        "知識ハブでは、用語の意味・似た制度の比較・数値・誤答パターンなど<strong>試験の知識</strong>を調べられます。"
        "学習計画や申込手続きなど<strong>進め方</strong>は"
        '<a href="../articles/index.html">試験ガイド</a>をご覧ください。'
        "タブから各コンテンツへ移動できます。"
        "</p>"
    )
    nav = (
        '<nav class="q-hub-links q-hub-links--tabs" aria-label="知識コンテンツ">'
        '<ul class="q-hub-tabs-list">'
        + "".join(items)
        + "</ul></nav>"
    )
    return note + nav
