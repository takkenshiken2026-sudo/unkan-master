#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本文・FAQ 向けの軽量インライン markup（Markdown 風リンク）。"""

from __future__ import annotations

import html
import re

_MD_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def render_inline_markup(text: str) -> str:
    """`[ラベル](https://...)` を外部リンク `<a>` に変換する。"""
    if not text or "[" not in text:
        return html.escape(text).replace("\n", "<br>")

    parts: list[str] = []
    last = 0
    for match in _MD_LINK.finditer(text):
        if match.start() > last:
            parts.append(html.escape(text[last : match.start()]))
        label = match.group(1)
        url = match.group(2)
        parts.append(
            f'<a href="{html.escape(url)}" target="_blank" rel="noopener noreferrer">{html.escape(label)}</a>'
        )
        last = match.end()
    parts.append(html.escape(text[last:]))
    return "".join(parts).replace("\n", "<br>")
