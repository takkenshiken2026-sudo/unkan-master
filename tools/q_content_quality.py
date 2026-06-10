#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""過去問・実践・一問一答の品質判定（デモ行除外・一問一答 SEO・本文重複除去）。"""

from __future__ import annotations

import re

from tools.seo_utils import INDEX_ROBOTS_META, NOINDEX_ROBOTS_META

_ICHIMON_ID_NUMERIC = re.compile(r"^(\d{4})-(\d+)-(\d+)$")
_ICHIMON_ID_KANA = re.compile(r"^(\d{4}-\d+)-([アイウエオ])$")
_ICHIMON_ID_EXAM = re.compile(r"^(.+-\d+)-(\d+)$")
_ICHIMON_ID_JA = re.compile(r"^(.+_問\d+)_選択肢(\d+)$")
_KANA_BRANCH_ORDER = "アイウエオ"
_DEMO_STEM_RE = re.compile(
    r"Sample試験|テンプレートの使い方|生成済みJS|CSV.*build_all|列名は自由|ドメイン設定は不要"
)


def norm(value: object) -> str:
    return (value or "").strip() if value is not None else ""


def dedupe_prose(text: str) -> str:
    """段落・文の重複を除去（GSC 重複コンテンツ対策）。"""
    raw = norm(text)
    if not raw:
        return raw
    paras = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    seen_para: set[str] = set()
    kept_paras: list[str] = []
    for para in paras:
        key = re.sub(r"\s+", "", para)
        if key in seen_para:
            continue
        seen_para.add(key)
        sents = re.split(r"(?<=[。！？!?])\s*", para)
        seen_sent: set[str] = set()
        kept_sents: list[str] = []
        for sent in sents:
            s = sent.strip()
            if not s:
                continue
            sk = re.sub(r"\s+", "", s)
            if sk in seen_sent:
                continue
            seen_sent.add(sk)
            kept_sents.append(s)
        if kept_sents:
            kept_paras.append("".join(kept_sents))
    return "\n\n".join(kept_paras)


def is_demo_past_question_row(
    row: dict[str, str],
    *,
    excluded_exam_years: set[str] | None = None,
) -> bool:
    wareki = norm(row.get("exam_wareki"))
    stem = norm(row.get("stem"))
    exam_year = norm(row.get("exam_year"))
    if excluded_exam_years and exam_year in excluded_exam_years:
        return True
    if "サンプル" in wareki:
        return True
    if _DEMO_STEM_RE.search(stem):
        return True
    return False


def is_demo_practice_question_row(row: dict[str, str]) -> bool:
    stem = norm(row.get("stem"))
    if _DEMO_STEM_RE.search(stem):
        return True
    c1 = norm(row.get("choice_1"))
    if "data/past_questions.csv" in c1 or "build_all.py" in c1:
        return True
    return False


_ichimon_primary_cache: set[str] | None = None


def ichimon_id_parts(row_id: str) -> tuple[int, int, int] | None:
    m = _ICHIMON_ID_NUMERIC.match(norm(row_id))
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def ichimon_group_branch(row_id: str) -> tuple[str, int] | None:
    """一問一答 ID から (元問キー, 枝番) を返す。単独ページは None。"""
    rid = norm(row_id)
    m = _ICHIMON_ID_NUMERIC.match(rid)
    if m:
        return f"{m.group(1)}-{m.group(2)}", int(m.group(3))
    m = _ICHIMON_ID_KANA.match(rid)
    if m:
        return m.group(1), _KANA_BRANCH_ORDER.index(m.group(2))
    m = _ICHIMON_ID_JA.match(rid)
    if m:
        return m.group(1), int(m.group(2))
    m = _ICHIMON_ID_EXAM.match(rid)
    if m:
        return m.group(1), int(m.group(2))
    return None


def build_ichimon_primary_ids(rows: list[dict[str, str]]) -> set[str]:
    """元問ごとに最小枝番のみ index（例: 2024-05-5 / 2704b-01-1 / 令和…_問38_選択肢1）。"""
    mins: dict[str, int] = {}
    for row in rows:
        gb = ichimon_group_branch(norm(row.get("id")))
        if gb is None:
            continue
        key, branch = gb
        mins[key] = min(branch, mins.get(key, branch))
    primary: set[str] = set()
    for row in rows:
        rid = norm(row.get("id"))
        gb = ichimon_group_branch(rid)
        if gb is None:
            primary.add(rid)
            continue
        key, branch = gb
        if mins.get(key) == branch:
            primary.add(rid)
    return primary


def set_ichimon_primary_ids(primary: set[str]) -> None:
    global _ichimon_primary_cache
    _ichimon_primary_cache = primary


def ichimon_is_primary_seo_row(row_id: str) -> bool:
    rid = norm(row_id)
    if _ichimon_primary_cache is not None:
        return rid in _ichimon_primary_cache
    parts = ichimon_id_parts(rid)
    if parts is None:
        return True
    _y, _q, c = parts
    return c == 1


def ichimon_robots_meta(row_id: str) -> str:
    return INDEX_ROBOTS_META if ichimon_is_primary_seo_row(row_id) else NOINDEX_ROBOTS_META


def ichimon_body_already_states_truth(body: str, *, is_true: bool) -> bool:
    b = norm(body)
    if not b:
        return False
    if is_true:
        return bool(re.search(r"正しい内容|正当である|適切である|○\s*が正答|答えは\s*○", b))
    return bool(re.search(r"誤り|誤った|不適切|×\s*が正答|答えは\s*×|正しくない", b))


def clean_ichimon_correct_body(
    correct_body: str,
    *,
    summary: str,
    is_true: bool,
) -> str:
    body = dedupe_prose(correct_body)
    sm = dedupe_prose(summary)
    if sm and body.startswith(sm):
        body = body[len(sm) :].lstrip("。、 \n")
    body = re.sub(
        r"^この記述は正しい内容です[。.]?\s*",
        "",
        body,
    )
    body = re.sub(
        r"^この記述は誤りです[。.]?\s*",
        "",
        body,
    )
    if ichimon_body_already_states_truth(body, is_true=is_true):
        body = re.sub(r"^[。.]\s*", "", body)
    return body.strip()


def strip_four_choice_leak(text: str) -> str:
    """一問一答用: 4択過去問インポート由来の「選択肢N」表現を除去・言い換え。"""
    t = norm(text)
    if not t:
        return t

    t = re.sub(
        r"^正解は\s*(?:選択肢\s*)?[（(]?\d+[）)]?\s*です[。.]?\s*",
        "",
        t,
    )
    t = re.sub(
        r"^正答は\s*(?:選択肢\s*)?[（(]?\d+[）)]?\s*です[。.]?\s*",
        "",
        t,
    )
    t = re.sub(
        r"正解は\s*(?:選択肢\s*)?[（(]?\d+[）)]?\s*です[。.]?",
        "",
        t,
    )
    t = re.sub(
        r"正答は\s*(?:選択肢\s*)?[（(]?\d+[）)]?\s*です[。.]?",
        "",
        t,
    )

    def _choice_quote_repl(m: re.Match[str]) -> str:
        quote = m.group(1).strip()
        if quote.endswith("..."):
            quote = quote[:-3].rstrip()
        return f"問題文は「{quote}」の趣旨どおりであり、制度の整理と一致します。"

    t = re.sub(
        r"選択肢\s*[（(]?\d+[）)]?\s*の[「「]([^」]+)[」」]という内容が結論に合います[。.]?",
        _choice_quote_repl,
        t,
    )
    t = re.sub(r"選択肢\s*[（(]?\d+[）)]?\s*の", "問題文の", t)
    t = re.sub(
        r"その他の記述は、主体・手続・期間・効果などの点でずれています[。.]?\s*",
        "",
        t,
    )
    return dedupe_prose(t.strip())
