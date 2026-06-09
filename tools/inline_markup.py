#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本文・FAQ 向けの軽量インライン markup（Markdown 風リンク）。"""

from __future__ import annotations

import html
import re

_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def _link_html(label: str, url: str) -> str:
    if url.startswith("../") or url.startswith("/articles/"):
        return (
            f'<a class="related-link" href="{html.escape(url)}">{html.escape(label)}</a>'
        )
    return (
        f'<a href="{html.escape(url)}" target="_blank" rel="noopener noreferrer">'
        f"{html.escape(label)}</a>"
    )


def render_inline_markup(text: str) -> str:
    """`[ラベル](URL)` を `<a>` に変換する（https:// と ../slug/ 形式）。"""
    if not text or "[" not in text:
        return html.escape(text).replace("\n", "<br>")

    parts: list[str] = []
    last = 0
    for match in _MD_LINK.finditer(text):
        if match.start() > last:
            parts.append(html.escape(text[last : match.start()]))
        parts.append(_link_html(match.group(1), match.group(2)))
        last = match.end()
    parts.append(html.escape(text[last:]))
    return "".join(parts).replace("\n", "<br>")
