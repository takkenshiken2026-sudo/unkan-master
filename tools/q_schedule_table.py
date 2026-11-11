#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""復元した運行計画・勤務状況の問題文を、本物の試験のような罫線付き HTML 表に整形する。

静的ページ（build_past_question_pages / q_stem_format）と SPA データ生成
（csv_to_exam_site_past_js）の双方から同一ロジックで呼び出し、表 HTML を一本化する。
対象外のテキストはそのまま返し、呼び出し側が通常の段落として描画する。
"""

from __future__ import annotations

import html
import re

_LOCATIONS = ("営業所", "宿泊施設", "宿泊所", "休憩施設", "休息施設")
# 所要時間（末尾）: N時間N分 / N時間 / N分
_DUR_RE = re.compile(r"(?:[0-9０-９]+\s*時間)?(?:\s*[0-9０-９]+\s*分)?$")
_DUR_HEAD_RE = re.compile(r"((?:[0-9０-９]+\s*時間)?(?:[0-9０-９]+\s*分)?)$")


def _esc(s: str) -> str:
    return html.escape(s or "")


def _split_label_duration(seg: str) -> tuple[str, str, bool]:
    """1 区画を (ラベル, 所要時間, 地点か) に分解。"""
    seg = seg.strip()
    # 地点（所要時間なし。宿泊所（休憩）等の括弧も許容）
    base = re.sub(r"（[^）]*）", "", seg)
    if base in _LOCATIONS:
        return seg, "", True
    m = _DUR_HEAD_RE.search(seg)
    dur = m.group(1) if m else ""
    label = seg[: len(seg) - len(dur)] if dur else seg
    return label.strip(), dur.strip(), False


def _parse_day_header(head: str) -> list[tuple[str, str]]:
    """「始業6時00分／出庫6時30分／…」を [(見出し, 値)] に。"""
    cells: list[tuple[str, str]] = []
    for part in re.split(r"[／/]", head):
        part = part.strip()
        m = re.match(r"(始業|出庫|出発|到着|終業|帰庫)[：: ]*(.+)", part)
        if m:
            cells.append((m.group(1), m.group(2).strip()))
    return cells


def _render_one_day(title: str, header: str, flow: str) -> str:
    """1 日分を <table> に。"""
    parts: list[str] = []
    hd = _parse_day_header(header)
    if title:
        parts.append(f'<div class="q-plan-day-title">{_esc(title)}</div>')
    if hd:
        th = "".join(f"<th>{_esc(k)}</th>" for k, _ in hd)
        td = "".join(f"<td>{_esc(v)}</td>" for _, v in hd)
        parts.append(
            f'<table class="q-plan-time"><thead><tr>{th}</tr></thead>'
            f"<tbody><tr>{td}</tr></tbody></table>"
        )
    segs = [s for s in re.split(r"\s*→\s*", flow) if s.strip()]
    if segs:
        labels: list[str] = []
        durs: list[str] = []
        for seg in segs:
            label, dur, is_loc = _split_label_duration(seg)
            if is_loc:
                labels.append(f'<td class="loc">{_esc(label)}</td>')
                durs.append("<td></td>")
            else:
                labels.append(f"<td>{_esc(label)}</td>")
                durs.append(f"<td>{_esc(dur)}</td>")
        parts.append(
            '<div class="q-plan-flow-wrap"><table class="q-plan-flow"><tbody>'
            f'<tr class="q-plan-act">{"".join(labels)}</tr>'
            f'<tr class="q-plan-dur">{"".join(durs)}</tr>'
            "</tbody></table></div>"
        )
    return f'<section class="q-plan-day">{"".join(parts)}</section>'


_DAY_LINE_RE = re.compile(
    r"^(?:【([^】]+)】|((?:前日|翌日)))\s*(.*)$"
)


def render_operation_plan(stem: str) -> str | None:
    """復元済み運行計画（【N日目】…→…）を表に。対象外なら None。"""
    if "→" not in stem or ("日目" not in stem and "前日" not in stem):
        return None
    lines = [ln.rstrip() for ln in stem.split("\n")]
    intro: list[str] = []
    blocks: list[str] = []
    i = 0
    started = False
    pending = None  # (title, header)
    note_lines: list[str] = []

    def flush(flow_text: str):
        nonlocal pending
        if pending is not None:
            title, header = pending
            blocks.append(_render_one_day(title, header, flow_text))
            pending = None

    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        m = _DAY_LINE_RE.match(s)
        day_label = None
        rest = ""
        if m:
            day_label = m.group(1) or m.group(2)
            rest = m.group(3)
        if day_label and "日目" in day_label:
            started = True
            # 直前の pending を空フローで流す保険（通常は次行がフロー）
            pending = (f"【{day_label}】", rest)
            continue
        if day_label in ("前日", "翌日"):
            # 注記（休日等）はそのまま小文字表示
            blocks.append(f'<p class="q-plan-note">{_esc(day_label + "：" + rest.lstrip("：:"))}</p>')
            continue
        if pending is not None and "→" in s:
            flush(s)
            continue
        # 注記行（（注）等）や見出し
        if started:
            note_lines.append(s)
        else:
            intro.append(s)
    if not blocks:
        return None
    out: list[str] = []
    if intro:
        out.append(f"<p>{_esc(' '.join(intro))}</p>")
    out.append('<div class="q-plan">' + "".join(blocks) + "</div>")
    for nl in note_lines:
        out.append(f'<p class="q-plan-note">{_esc(nl)}</p>')
    return "".join(out)


_WORK_ENTRY_RE = re.compile(
    r"(月曜|火曜|水曜|木曜|金曜|土曜|日曜|[０-９0-9一二三四五六七八九十]+日目)[：: ]*"
    r"始業\s*([0-9０-９]+時[0-9０-９]*分?)\s*[〜～]\s*終業\s*([0-9０-９]+時[0-9０-９]*分?)"
)
_HOLIDAY_RE = re.compile(r"[（(]([^）)]*休日[^）)]*)[）)]")


def render_work_schedule(stem: str) -> str | None:
    """週間・5日間などの勤務状況（始業〜終業）を表に。対象外なら None。"""
    entries = _WORK_ENTRY_RE.findall(stem)
    if len(entries) < 3:
        return None
    # 前置き（〔…〕見出しより前）と注記
    marker = re.search(r"〔[^〕]*(?:勤務状況|勤務パターン)[^〕]*〕", stem)
    intro = stem[: marker.start()].strip() if marker else ""
    tail = stem[marker.end():] if marker else stem
    holidays = _HOLIDAY_RE.findall(tail)
    notes = re.findall(r"（注[^）]*）", stem)

    head = "".join(f"<th>{_esc(h)}</th>" for h in ("", "始業", "終業"))
    body_rows = []
    for day, start, end in entries:
        body_rows.append(
            f"<tr><th>{_esc(day)}</th><td>{_esc(start)}</td><td>{_esc(end)}</td></tr>"
        )
    table = (
        '<table class="q-work"><thead><tr>'
        f"{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"
    )
    out = []
    if intro:
        out.append(f"<p>{_esc(intro)}</p>")
    out.append('<div class="q-sched">' + table + "</div>")
    for h in holidays:
        out.append(f'<p class="q-plan-note">{_esc(h)}</p>')
    for n in notes:
        out.append(f'<p class="q-plan-note">{_esc(n)}</p>')
    return "".join(out)


_MONTH_WEEK_RE = re.compile(r"第([0-9０-９]+)週\s*(.+)")
_DAY_RUN_RE = re.compile(r"([0-9０-９]+)日[：: ]*(?:運\s*([0-9０-９]+)\s*拘\s*([0-9０-９]+)|(休日(?:労働)?))")


def render_month_daily(stem: str) -> str | None:
    """1ヵ月の日別（運転・拘束時間）を表に。対象外なら None。"""
    lines = [ln.strip() for ln in stem.split("\n") if ln.strip()]
    week_lines = [ln for ln in lines if _MONTH_WEEK_RE.match(ln)]
    if len(week_lines) < 2:
        return None
    marker = re.search(r"〔[^〕]*(?:運転時間|拘束時間|勤務状況)[^〕]*〕", stem)
    intro = stem[: marker.start()].strip() if marker else ""
    rows_html = []
    has_run = "運" in stem
    for ln in lines:
        mw = _MONTH_WEEK_RE.match(ln)
        if mw:
            wk = mw.group(1)
            body = mw.group(2)
            weektotal = ""
            mt = re.search(r"（週計\s*(.+?)）", body)
            if mt:
                weektotal = mt.group(1).strip()
            for d in _DAY_RUN_RE.finditer(body):
                day = d.group(1)
                if d.group(4):  # 休日
                    cells = f'<td class="hol" colspan="2">{_esc(d.group(4))}</td>'
                else:
                    if has_run:
                        cells = f"<td>{_esc(d.group(2))}</td><td>{_esc(d.group(3))}</td>"
                    else:
                        cells = f"<td>{_esc(d.group(2) or d.group(3))}</td>"
                rows_html.append(
                    f'<tr><th>第{_esc(wk)}週</th><td class="d">{_esc(day)}日</td>{cells}</tr>'
                )
            if weektotal:
                span = 2 if has_run else 1
                rows_html.append(
                    f'<tr class="wtot"><th>第{_esc(wk)}週</th><td class="d">週計</td>'
                    f'<td colspan="{span}">{_esc(weektotal)}</td></tr>'
                )
        elif re.match(r"(１|1)ヵ月合計|月合計", ln):
            span = 3 if has_run else 2
            val = ln.split("合計", 1)[1].strip()
            val = re.sub(r"（注[^）]*）.*$", "", val).strip()
            rows_html.append(
                f'<tr class="mtot"><th colspan="2">月合計</th>'
                f'<td colspan="{span-1}">{_esc(val)}</td></tr>'
            )
    if not rows_html:
        return None
    if has_run:
        head = "<tr><th>週</th><th>日</th><th>運転</th><th>拘束</th></tr>"
    else:
        head = "<tr><th>週</th><th>日</th><th>時間</th></tr>"
    table = f'<table class="q-month"><thead>{head}</thead><tbody>{"".join(rows_html)}</tbody></table>'
    notes = re.findall(r"（注[^）]*）", stem)
    out = []
    if intro:
        out.append(f"<p>{_esc(intro)}</p>")
    out.append('<div class="q-sched">' + table + "</div>")
    for n in notes:
        out.append(f'<p class="q-plan-note">{_esc(n)}</p>')
    return "".join(out)


def render_stem_html(stem: str) -> str | None:
    """復元した各種スケジュール問題文を表 HTML に。対象外なら None。"""
    if not stem or not stem.strip():
        return None
    for fn in (render_operation_plan, render_work_schedule, render_month_daily):
        try:
            out = fn(stem)
        except Exception:
            out = None
        if out:
            return out
    return None


if __name__ == "__main__":
    import sys
    sample = (
        "運行管理者は…正しいものをすべて選びなさい。\n"
        "前日：当該運行の前日は休日とする。\n"
        "【１日目】始業6時00分／出庫6時30分／到着20時30分／終業20時45分\n"
        "　営業所 → 乗務前点呼等45分 → 運転1時間 → 荷積み1時間 → 運転3時間 → 宿泊所\n"
        "翌日：当該運行の翌日は休日とする。"
    )
    print(render_operation_plan(sample))
