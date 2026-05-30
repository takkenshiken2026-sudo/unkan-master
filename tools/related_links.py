#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""related_links 列のトークン解析（https:// は最初の : で分割しない）."""

from __future__ import annotations

import re


def parse_related_link_token(item: str) -> tuple[str, str]:
    """1件分を (target, label) に分解する。外部 URL は target=label=URL。"""
    text = (item or "").strip()
    if not text:
        return "", ""
    if re.match(r"https?://", text, re.I):
        return text, text
    if ":" in text:
        target, label = text.split(":", 1)
        return target.strip(), label.strip()
    return text, text
