#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一問一答 id → 静的 URL パス（数値 id / カタカナ枝番 / 和暦スラッグ id 共通）。"""

from __future__ import annotations

import re

_ID_PATH = re.compile(r"^(\d{4})-(\d+)-(\d+|[アイウエ])$")


def norm(s: str | None) -> str:
    return (s or "").strip()


def slug_key(key: str) -> str:
    """HTML id / URL セグメント用（記号はハイフンに）。"""
    s = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", str(key)).strip("-")
    return s or "other"


def ichimon_path_info(row_id: str) -> dict[str, str | int]:
    rid = norm(row_id)
    if not rid:
        raise ValueError("一問一答 id が空")
    m = _ID_PATH.match(rid)
    if m:
        y, mo, seq = int(m.group(1)), int(m.group(2)), m.group(3)
        href_rel = f"y{y}/i{mo:02d}-{seq}/index.html"
        return {"rel_path": f"q/ichimon/{href_rel}", "href_rel": href_rel, "year": y}
    slug = slug_key(rid)
    href_rel = f"s/{slug}/index.html"
    return {"rel_path": f"q/ichimon/{href_rel}", "href_rel": href_rel, "year": 0}


def ichimon_rel_path(row_id: str) -> str:
    return str(ichimon_path_info(row_id)["rel_path"])
