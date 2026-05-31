#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用語と過去問のマッチング・HTML生成。"""

from __future__ import annotations

import csv
import html
import re
from functools import lru_cache
from pathlib import Path

from tools.glossary_term_search import term_matches_text, term_search_keys  # noqa: E402
from tools.site_config import resolve_site_root  # noqa: E402


def _site_root() -> Path:
    return resolve_site_root()


def _past_csv() -> Path:
    return _site_root() / "data" / "past_questions.csv"


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _preview(text: str, limit: int = 72) -> str:
    plain = _strip_html(text).replace("\n", " ")
    if len(plain) <= limit:
        return plain
    return plain[: limit - 1] + "…"


@lru_cache(maxsize=8)
def load_past_question_index(root_key: str = "") -> list[dict]:
    root = Path(root_key) if root_key else _site_root()
    past_csv = root / "data" / "past_questions.csv"
    if not past_csv.is_file():
        return []
    rows = list(csv.DictReader(past_csv.read_text(encoding="utf-8-sig").splitlines()))
    index: list[dict] = []
    for row in rows:
        year_raw = (row.get("exam_year") or "").strip()
        try:
            qno = int(row.get("question_no") or 0)
        except ValueError:
            continue
        if not year_raw or qno < 1:
            continue
        try:
            year = int(year_raw)
        except ValueError:
            continue
        href_rel = f"q/past/y{year}/q{qno:02d}/index.html"
        if not (root / href_rel).is_file():
            continue
        parts = [row.get("stem") or "", row.get("explanation") or ""]
        for i in range(1, 5):
            parts.append(row.get(f"choice_{i}") or "")
        hay = " ".join(parts)
        index.append(
            {
                "year": year,
                "qno": qno,
                "category": (row.get("category") or "").strip(),
                "hay": hay,
                "stem": row.get("stem") or "",
                "correct": (row.get("correct") or "").strip(),
                "href_rel": href_rel,
            }
        )
    return index


def find_past_questions_for_term(
    term: str,
    *,
    limit: int = 3,
    related_terms: str = "",
    legal_basis: str = "",
) -> list[dict]:
    term = (term or "").strip()
    if not term or len(term) < 2:
        return []
    hits: list[dict] = []
    seen_pages: set[tuple[int, int]] = set()
    root_key = str(_site_root())
    for page in load_past_question_index(root_key):
        key = (page["year"], page["qno"])
        if key in seen_pages:
            continue
        if not term_matches_text(term, page["hay"], related_terms, legal_basis):
            continue
        seen_pages.add(key)
        hits.append(page)
    hits.sort(key=lambda p: (p["year"], p["qno"]), reverse=True)
    return hits[:limit]


def example_from_past_hit(hit: dict, term: str) -> tuple[str, str]:
    q = f"（{hit['year']}年 第{hit['qno']}問）{_preview(hit['stem'], 100)}"
    cor = hit.get("correct") or ""
    if cor.isdigit():
        ans = f"正答は選択肢{cor}です。用語「{term}」が問われた過去問のため、解説と条文の対応を確認してください。"
    else:
        ans = f"本問は無効・免除等のため正答なし。用語「{term}」の文脈確認用として参照してください。"
    return q, ans


def past_questions_section_html(hits: list[dict], rel_path: Path, *, section_num: int | None = None) -> str:
    if not hits:
        return ""
    depth = len(rel_path.parent.parts)
    prefix = "../" * depth if depth else ""
    links = []
    for h in hits:
        href = html.escape(f"{prefix}{h['href_rel']}")
        label = html.escape(f"{h['year']}年 第{h['qno']}問（{h['category']}）")
        links.append(f'<a class="related-link" href="{href}">{label}</a>')
    num_html = (
        f'<span class="section-heading-num">{section_num}</span>' if section_num is not None else ""
    )
    return (
        '<section class="seo-article-section" aria-labelledby="term-past-title">'
        f'<h2 id="term-past-title">{num_html}関連する過去問</h2>'
        "<p>この用語が本文・解説に登場する過去問です。リンクから問題と解説を確認できます。</p>"
        f'<div class="related-links term-past-list">{"".join(links)}</div>'
        "</section>"
    )
