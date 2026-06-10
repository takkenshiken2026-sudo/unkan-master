#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""過去問などの問題文を読みやすく整形する（運行計画表など）。"""

from __future__ import annotations

import html
import re

_TIME_HEADER = "始業時刻出庫時刻到着時刻終業時刻"
_TIME_HEADER_CELLS = ("始業時刻", "出庫時刻", "到着時刻", "終業時刻")
_PLAN_MARKER_RE = re.compile(r"＜[^＞]*運行計画[^＞]*＞")
_DAY_LABEL_RE = re.compile(r"(?<![の])(前日|翌日|[０-９]+日目)")
_TIME_CELL_RE = re.compile(r"[０-９\d]+\s*時\s*[０-９\d]+\s*分")
_ACTIVITY_LABELS = (
    "乗務前",
    "乗務後",
    "宿泊所",
    "中間点呼",
    "点呼等",
    "フェリー乗船",
    "荷積み",
    "荷下ろし",
    "休憩",
    "運転",
)


def _norm(value: object) -> str:
    return (value or "").strip() if value is not None else ""


def _find_plan_marker(raw: str) -> re.Match[str] | None:
    """本文中の参照用マーカーではなく、表が続くマーカーを選ぶ。"""
    candidates = list(_PLAN_MARKER_RE.finditer(raw))
    if not candidates:
        return None
    for m in reversed(candidates):
        after = raw[m.end() :].lstrip()
        if _DAY_LABEL_RE.match(after):
            return m
    return candidates[-1]


def _split_activity_labels(text: str) -> list[str]:
    if not text:
        return []
    parts: list[str] = []
    i = 0
    while i < len(text):
        matched = None
        for label in _ACTIVITY_LABELS:
            if text.startswith(label, i):
                matched = label
                break
        if matched is None:
            i += 1
            continue
        parts.append(matched)
        i += len(matched)
    return parts


def _format_times_table(body: str) -> tuple[str, str]:
    """始業時刻行以降を表 HTML に。戻り値は (表HTML, 表より前の前置き)。"""
    idx = body.find(_TIME_HEADER)
    if idx < 0:
        return "", body

    prefix = body[:idx].strip()
    rest = body[idx + len(_TIME_HEADER) :]
    times = _TIME_CELL_RE.findall(rest)
    if len(times) < 4:
        return "", body

    time_row = times[:4]
    after_times = rest
    for t in time_row:
        pos = after_times.find(t)
        if pos >= 0:
            after_times = after_times[pos + len(t) :]

    activities = _split_activity_labels(after_times.strip())
    header_cells = "".join(f"<th>{html.escape(h)}</th>" for h in _TIME_HEADER_CELLS)
    time_cells = "".join(f"<td>{html.escape(t)}</td>" for t in time_row)
    table_html = (
        '<table class="q-run-times"><thead><tr>'
        f"{header_cells}</tr></thead><tbody><tr>{time_cells}</tr></tbody></table>"
    )
    if activities:
        act_cells = "".join(
            f'<span class="q-run-act">{html.escape(a)}</span>' for a in activities
        )
        table_html += f'<div class="q-run-activities">{act_cells}</div>'
    return table_html, prefix


def _format_day_block(day: str, body: str) -> str:
    text = _norm(body)
    if not text:
        return ""

    table_html, prefix = _format_times_table(text)
    parts: list[str] = []
    if table_html:
        if prefix:
            parts.append(f'<p class="q-run-day-note">{html.escape(prefix)}</p>')
        parts.append(table_html)
    else:
        parts.append(f'<p class="q-run-day-note">{html.escape(text)}</p>')

    inner = "\n".join(parts)
    return (
        f'<section class="q-run-day">'
        f'<h3 class="q-run-day-label">{html.escape(day)}</h3>'
        f'<div class="q-run-day-body">{inner}</div>'
        f"</section>"
    )


def format_operation_plan_stem(stem: str) -> str | None:
    """運行計画つき問題文を HTML ブロックに整形。対象外なら None。"""
    raw = _norm(stem)
    if "運行計画" not in raw or _TIME_HEADER not in raw:
        return None

    m = _find_plan_marker(raw)
    if not m:
        return None

    intro = raw[: m.start()].strip()
    marker = m.group(0)
    plan = raw[m.end() :].strip()

    chunks = _DAY_LABEL_RE.split(plan)
    if len(chunks) < 3:
        return None

    day_blocks: list[str] = []
    i = 1
    while i < len(chunks):
        day = chunks[i].strip()
        body = chunks[i + 1] if i + 1 < len(chunks) else ""
        block = _format_day_block(day, body)
        if block:
            day_blocks.append(block)
        i += 2

    if not day_blocks:
        return None

    intro_html = f"<p>{html.escape(intro)}</p>" if intro else ""
    marker_html = f'<p class="q-run-plan-marker">{html.escape(marker)}</p>'
    plan_html = '<div class="q-stem-operation-plan">' + "\n".join(day_blocks) + "</div>"
    return intro_html + marker_html + plan_html


def format_past_stem_html(stem: str) -> str:
    """問題文プレーンテキストを表示用 HTML に。"""
    raw = _norm(stem)
    if not raw:
        return ""
    op = format_operation_plan_stem(raw)
    if op:
        return op
    br = "<br>\n"
    return f"<p>{html.escape(raw).replace(chr(10), br)}</p>"
