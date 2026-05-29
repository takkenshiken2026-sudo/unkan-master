#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知識ハブ一覧（用語・比較・数値・誤答）向けの定義・概要文を生成する。"""

from __future__ import annotations

import re
from typing import Callable

# CSV enrich / ビルド時の汎用パディング（一覧に出さない）
_GENERIC_SNIPPET_SUFFIXES = (
    "に関わる用語です。",
    "を整理する際に使われます。",
    "と関係します。",
    "を確認します。",
    "を確認するために使われます。",
    "を考える場面で出てきます。",
    "につながる経営課題として捉えます。",
    "を説明する際に使われます。",
    "を検討します。",
)

_GENERIC_DEFINITION_TAIL = re.compile(
    r"[。]?"
    r"[^。]{0,80}は[「][^」]+[」]の重要論点として、"
    r"条文・告示・実務のいずれかで位置づけられる。?$"
)

_GENERIC_SHORT_RE = re.compile(r"運行管理者試験（貨物）で押さえる")

_HUB_DISCLAIMER_RE = re.compile(
    r"数値・日程・合格基準は公益財団法人運行管理者試験センター[^。]*試験要項で必ずご確認ください。"
)

_HUB_LEAD_BOILERPLATE_RE = re.compile(
    r"^[^。]{1,60}は、運行管理者試験[^。]+。"
    r"(?:このページでは、[^。]+。)?"
)

_HUB_LEAD_CTA_RE = re.compile(
    r"過去問・実践演習・一問一答と組み合わせて[^。]+。"
)

_INDEX_SUMMARY_ENDINGS = (
    "を整理します。",
    "を整理した索引です。",
    "を横並びに整理します。",
)


def norm(s: str | None) -> str:
    return (s or "").strip()


def split_semicolon(s: str) -> list[str]:
    return [x.strip() for x in (s or "").split(";") if x.strip()]


MIN_GLOSSARY_INDEX_LEN = 12


def clamp_prose(text: str, max_len: int = 160) -> str:
    one = re.sub(r"\s+", " ", text).strip()
    if not one:
        return ""
    if not one.endswith("。"):
        one += "。"
    if len(one) <= max_len:
        return one
    cut = one[: max_len - 1]
    if "。" in cut:
        cut = cut[: cut.rfind("。") + 1]
    else:
        cut += "…"
    return cut


def _is_generic_index_snippet(text: str, term: str = "") -> bool:
    t = text.strip()
    if not t:
        return True
    if _GENERIC_SHORT_RE.search(t):
        return True
    if term and t.startswith(term) and any(t.endswith(suffix) for suffix in _GENERIC_SNIPPET_SUFFIXES):
        return True
    if _GENERIC_DEFINITION_TAIL.search(t):
        return True
    return False


def _clean_definition_text(definition: str, term: str = "") -> str:
    d = norm(definition)
    if not d:
        return ""
    d = _GENERIC_DEFINITION_TAIL.sub("", d).strip()
    d = re.sub(r"\s+", "", d) if "\n" not in d else re.sub(r"[ \t]+", " ", d)
    if _is_generic_index_snippet(d, term):
        return ""
    return d


def _definition_from_detail_body(body: str) -> str:
    if not body:
        return ""
    m = re.search(
        r"定義\s*\n(.+?)(?=\n\s*条文上の根拠|\n\s*試験で問われやすい)",
        body,
        re.DOTALL,
    )
    if not m:
        return ""
    return re.sub(r"\s+", " ", m.group(1).strip())


def _is_vague_definition(text: str) -> bool:
    t = norm(text)
    if not t or len(t) < 30:
        return True
    if t.endswith("等。") and len(t) < 50:
        return True
    return False


def _clean_exam_point(point: str) -> str:
    p = norm(point)
    p = re.sub(r"（[^）]*の試験論点）", "", p).strip()
    return p.rstrip("。")


def _compose_from_exam_points(term: str, exam_points: str) -> str:
    pts = [_clean_exam_point(p) for p in split_semicolon(exam_points)]
    pts = [p for p in pts if len(p) >= 4]
    if not pts:
        return ""
    p0 = pts[0]
    if len(pts) >= 2:
        p1 = pts[1]
        return f"{term}は、{p0}。試験では{p1}も押さえます。"
    return f"{term}は、{p0}。"


def _finalize_glossary_index(text: str, term: str, entry: dict) -> str:
    out = clamp_prose(text, 160) if text else ""
    if len(out) >= MIN_GLOSSARY_INDEX_LEN:
        return out

    composed = _compose_from_exam_points(term, entry.get("exam_points") or "")
    if composed and len(composed) >= MIN_GLOSSARY_INDEX_LEN:
        return composed

    defn = _clean_definition_text(entry.get("definition") or "", term)
    if defn and not _is_vague_definition(defn) and len(defn) >= MIN_GLOSSARY_INDEX_LEN:
        return clamp_prose(defn, 160)

    pts = [_clean_exam_point(p) for p in split_semicolon(entry.get("exam_points") or "")]
    pts = [p for p in pts if len(p) >= 2]
    if term and pts:
        p0 = pts[0]
        if len(pts) >= 2:
            two = f"{term}は、{p0}。試験では{pts[1]}も押さえます。"
            if len(two) >= MIN_GLOSSARY_INDEX_LEN:
                return two
        one = f"{term}は、{p0}。運行管理者試験で頻出の用語です。"
        if len(one) >= MIN_GLOSSARY_INDEX_LEN:
            return one

    if out:
        padded = f"{term}は、{out.rstrip('。')}。"
        if len(padded) >= MIN_GLOSSARY_INDEX_LEN:
            return padded

    if defn:
        return clamp_prose(defn, 160)

    return f"{term}の意味と試験での押さえ方を整理した用語です。"


def glossary_index_definition(
    entry: dict,
    *,
    seed: dict | None = None,
) -> str:
    """用語一覧の「定義」列。詳細記事の定義・出題ポイントから一意の要約文を作る。"""
    term = norm(entry.get("term"))
    if not term:
        return ""

    work_entry = dict(entry)
    if seed:
        work_entry = {**entry, **{k: v for k, v in seed.items() if v}}

    if seed:
        defn = _clean_definition_text(seed.get("definition") or "", term)
        short = norm(seed.get("short_def"))
        if defn and not _is_vague_definition(defn):
            return _finalize_glossary_index(defn, term, work_entry)
        if short and not _is_generic_index_snippet(short, term):
            return _finalize_glossary_index(short, term, work_entry)

    defn = _clean_definition_text(entry.get("definition") or "", term)
    short = norm(entry.get("short_def"))
    if defn and not _is_vague_definition(defn) and not _is_generic_index_snippet(defn, term):
        return _finalize_glossary_index(defn, term, work_entry)
    if short and not _is_generic_index_snippet(short, term) and not _is_vague_definition(short):
        return _finalize_glossary_index(short, term, work_entry)
    body_def = _definition_from_detail_body(entry.get("term_detail_body") or "")
    if body_def and not _is_generic_index_snippet(body_def, term):
        return _finalize_glossary_index(body_def, term, work_entry)

    composed = _compose_from_exam_points(term, entry.get("exam_points") or "")
    if composed:
        return _finalize_glossary_index(composed, term, work_entry)

    legal = norm(entry.get("legal_basis"))
    if legal:
        first = legal.split("、")[0].split(";")[0].strip()
        return _finalize_glossary_index(
            f"{term}は、{first}などに基づく制度・手続に関する用語です。",
            term,
            work_entry,
        )

    return ""


def _strip_hub_boilerplate(lead: str) -> str:
    text = norm(lead)
    if not text:
        return ""
    text = _HUB_DISCLAIMER_RE.sub("", text).strip()
    text = _HUB_LEAD_BOILERPLATE_RE.sub("", text).strip()
    text = _HUB_LEAD_CTA_RE.sub("", text).strip()
    return re.sub(r"\s+", " ", text).strip()


def _is_template_summary(summary: str) -> bool:
    s = norm(summary)
    if not s:
        return True
    if any(s.endswith(end) for end in _INDEX_SUMMARY_ENDINGS):
        return True
    if s.count("整理") >= 2:
        return True
    return False


def hub_index_summary(entry: dict) -> str:
    """比較・数値・誤答一覧の「概要」列。article_lead と出題ポイントから記事要約を作る。"""
    title = norm(entry.get("title"))
    lead = _strip_hub_boilerplate(entry.get("article_lead") or "")
    if len(lead) >= 36:
        return clamp_prose(lead, 180)

    pts = split_semicolon(entry.get("exam_points") or "")
    if title and pts:
        p0 = pts[0].rstrip("。")
        if len(pts) >= 2:
            p1 = pts[1].rstrip("。")
            return clamp_prose(f"{title}では、{p0}。試験では{p1}が問われやすい。", 180)
        return clamp_prose(f"{title}では、{p0}。", 180)

    confusion = norm(entry.get("confusion_point"))
    if title and confusion:
        return clamp_prose(f"{title}では、{confusion.rstrip('。')}。", 180)

    highlight = norm(entry.get("highlight"))
    if title and highlight:
        return clamp_prose(f"{title}の早見ポイントは、{highlight.rstrip('。')}。", 180)

    summary = norm(entry.get("summary"))
    if summary and not _is_template_summary(summary):
        return clamp_prose(summary, 180)

    return clamp_prose(summary, 180) if summary else ""


def load_glossary_seed_map() -> dict[str, dict]:
    """generate_glossary_step1 と同じシードから用語→最小フィールドの辞書。"""
    from tools.generate_glossary_step1 import (  # noqa: WPS433
        deduped_raw_terms,
        raw_to_seed,
    )

    return {s["term"]: s for s in (raw_to_seed(r) for r in deduped_raw_terms())}


def refresh_glossary_index_fields(
    row: dict,
    *,
    seed_map: dict[str, dict],
) -> str:
    seed = seed_map.get(norm(row.get("term")))
    return glossary_index_definition(row, seed=seed)
