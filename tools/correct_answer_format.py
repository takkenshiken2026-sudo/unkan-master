#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""運行管理者など、correct 列が単一整数以外のサイト向け検証."""

from __future__ import annotations

import re


def norm(value: object) -> str:
    return str(value or "").strip()


def collect_choice_texts(row: dict, *, max_slots: int = 8) -> list[str]:
    """choice_1..N の非空選択肢を順に返す（最大 max_slots 列）。"""
    out: list[str] = []
    for i in range(1, max_slots + 1):
        text = norm(row.get(f"choice_{i}"))
        if text:
            out.append(text)
    return out


def detect_correct_format(raw: str) -> str:
    """正答文字列の型（single / multi / combination / truefalse_group）。"""
    raw = norm(raw)
    if not raw:
        return ""
    if re.fullmatch(r"[A-Za-zア-オ甲乙①-⑫]-\d+(;[A-Za-zア-オ甲乙①-⑫]-\d+)*", raw):
        return "combination"
    if ";" in raw and re.fullmatch(r"[^,\d;]+-\d+(,\d+)*(;[^,\d;]+-\d+(,\d+)*)+", raw):
        return "truefalse_group"
    if re.fullmatch(r"\d+(,\d+)+", raw):
        return "multi"
    if re.fullmatch(r"\d+", raw):
        return "single"
    return ""


def parse_correct_js_index(raw: str, *, extended: bool = False, max_choice: int = 5) -> int | None:
    """exam-site-data-past.js 用の 0 始まり正答インデックス。multi は先頭肢（レガシー互換）。"""
    raw = norm(raw)
    if not raw:
        return None
    if extended:
        if not is_valid_correct(raw, max_choice=max_choice):
            return None
        fmt = detect_correct_format(raw)
        if fmt == "multi":
            n = int(raw.split(",")[0].strip())
            return n - 1 if 1 <= n <= max_choice else None
        if fmt == "single":
            n = int(raw)
            return n - 1 if 1 <= n <= max_choice else None
        return None
    try:
        n = int(raw)
    except ValueError:
        return None
    if 1 <= n <= max_choice:
        return n - 1
    return None


def parse_correct_page_value(raw: str, *, extended: bool = False, max_choice: int = 5) -> int | str | None:
    """過去問 HTML 用。1 始まり整数、multi のカンマ区切り、または複合型の生文字列。"""
    raw = norm(raw)
    if not raw:
        return None
    if extended:
        if not is_valid_correct(raw, max_choice=max_choice):
            return None
        fmt = detect_correct_format(raw)
        if fmt in {"multi", "combination", "truefalse_group"}:
            return raw
        if fmt == "single":
            n = int(raw)
            return n if 1 <= n <= max_choice else None
        return None
    try:
        n = int(raw)
    except ValueError:
        return None
    if 1 <= n <= max_choice:
        return n
    return None


def is_valid_correct(raw: str, *, max_choice: int = 5) -> bool:
    """拡張正答形式を含めて妥当か。"""
    raw = norm(raw)
    if not raw:
        return False
    qtype = detect_correct_format(raw)
    if not qtype:
        return False
    if qtype == "single":
        n = int(raw)
        return 1 <= n <= max_choice
    if qtype == "multi":
        nums = [int(s) for s in raw.split(",") if s.strip()]
        return bool(nums) and all(1 <= n <= max_choice for n in nums)
    if qtype == "combination":
        for p in raw.split(";"):
            p = p.strip()
            if not p:
                continue
            m = re.match(r"^([A-Za-z①-⑫ア-オ甲乙])-(\d+)$", p)
            if not m or not 1 <= int(m.group(2)) <= max_choice:
                return False
        return True
    if qtype == "truefalse_group":
        used: set[int] = set()
        for g in raw.split(";"):
            g = g.strip()
            if not g:
                continue
            m = re.match(r"^([^-]+)-(.+)$", g)
            if not m:
                return False
            try:
                nums = {int(s.strip()) for s in m.group(2).split(",") if s.strip()}
            except ValueError:
                return False
            if not nums or any(n < 1 or n > max_choice for n in nums):
                return False
            if any(n in used for n in nums):
                return False
            used |= nums
        return bool(used)
    return False
