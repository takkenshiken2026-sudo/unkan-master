# -*- coding: utf-8 -*-
"""知識ハブ（用語解説）のリード文。"""

from __future__ import annotations

import html

HUB_SECTIONS: tuple[str, ...] = ("terms",)


def articles_guide_href(*, here: str) -> str:
    """試験ガイド index への相対 href（terms 配下の深さに応じる）。"""
    if here == "terms":
        return "../articles/index.html"
    if here in ("field", "samples", "diagram-samples"):
        return "../../articles/index.html"
    return "../../articles/index.html"


def knowledge_hub_tab_hrefs(*, here: str) -> dict[str, str]:
    """互換用。用語解説のみ残す。"""
    if here == "field":
        return {"terms_href": "../index.html"}
    if here in ("samples", "diagram-samples"):
        return {"terms_href": "../index.html"}
    if here == "terms":
        return {"terms_href": "index.html"}
    return {"terms_href": "../index.html"}


def knowledge_hub_tabs_html(*, current: str, **hrefs: str) -> str:
    """比較・数値・誤答タブは廃止。用語解説ページ向けのリード文のみ返す。"""
    here = "field" if current == "field" else current
    if here not in ("terms", "field", "samples", "diagram-samples"):
        here = "terms"
    guide_href = articles_guide_href(here=here)
    return (
        '<p class="q-study-modes-note">'
        "用語解説では、試験で押さえる用語の意味と関連条文を調べられます。"
        "学習計画や申込手続きなど<strong>進め方</strong>は"
        f'<a href="{html.escape(guide_href)}">試験ガイド</a>をご覧ください。'
        "</p>"
    )
