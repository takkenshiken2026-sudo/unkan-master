# -*- coding: utf-8 -*-
"""過去問・実践演習・一問一答の「類似の問題」ブロック（関連ページの直上）。"""

from __future__ import annotations

import csv
import html
import re
from pathlib import Path

from tools.ichimon_paths import ichimon_rel_path

MODE_LABEL: dict[str, str] = {
    "past": "過去問",
    "practice": "実践演習",
    "ichimon": "一問一答",
}

_PREVIEW_LIMIT = 56
_SIMILAR_LIMIT = 4
_MIN_SCORE = 18


def norm(value: object) -> str:
    return (value or "").strip() if value is not None else ""


def parse_tags(raw: str) -> list[str]:
    return [t.strip() for t in (raw or "").split(";") if t.strip()]


def stem_preview(text: str, limit: int = _PREVIEW_LIMIT) -> str:
    one = re.sub(r"\s+", " ", text).strip()
    if not one:
        return ""
    if len(one) <= limit:
        return one
    return one[: limit - 1] + "…"


def _text_tokens(text: str) -> set[str]:
    s = re.sub(r"\s+", "", norm(text))
    if not s:
        return set()
    words = re.findall(r"[\u3040-\u30ff\u4e00-\u9fff]{2,}", s)
    tokens: set[str] = set(words)
    for w in words:
        if len(w) >= 4:
            for i in range(len(w) - 1):
                tokens.add(w[i : i + 2])
    return tokens


def _past_key(year: int, qno: int) -> tuple[str, int, int]:
    return ("past", year, qno)


def _practice_key(qno: int) -> tuple[str, int]:
    return ("practice", qno)


def _ichimon_key(rid: str) -> tuple[str, str]:
    return ("ichimon", rid)


def load_question_catalog(root: Path) -> list[dict]:
    """3 CSV から類似判定用の参照一覧を構築。"""
    refs: list[dict] = []

    past_csv = root / "data" / "past_questions.csv"
    if past_csv.is_file():
        for i, row in enumerate(
            csv.DictReader(past_csv.read_text(encoding="utf-8-sig").splitlines()),
            start=2,
        ):
            if norm(row.get("is_invalidated", "")).upper() == "TRUE":
                continue
            year = int(row["exam_year"])
            qno = int(row["question_no"])
            cat = norm(row.get("category"))
            stem = norm(row.get("stem"))
            refs.append(
                {
                    "mode": "past",
                    "key": _past_key(year, qno),
                    "rel_path": f"q/past/y{year}/q{qno:02d}/index.html",
                    "category": cat,
                    "tags": parse_tags(norm(row.get("tags"))),
                    "text": stem,
                    "title": f"{year}年 第{qno}問",
                    "preview": stem_preview(stem),
                }
            )

    practice_csv = root / "data" / "practice_questions.csv"
    if practice_csv.is_file():
        for row in csv.DictReader(
            practice_csv.read_text(encoding="utf-8-sig").splitlines()
        ):
            if norm(row.get("is_invalidated", "")).upper() == "TRUE":
                continue
            qno = int(row["question_no"])
            stem = norm(row.get("stem"))
            refs.append(
                {
                    "mode": "practice",
                    "key": _practice_key(qno),
                    "rel_path": f"q/practice/p{qno:03d}/index.html",
                    "category": norm(row.get("category")),
                    "tags": parse_tags(norm(row.get("tags"))),
                    "text": stem,
                    "title": f"第{qno}問",
                    "preview": stem_preview(stem),
                }
            )

    ichimon_csv = root / "data" / "ichimon_questions.csv"
    if ichimon_csv.is_file():
        for row in csv.DictReader(
            ichimon_csv.read_text(encoding="utf-8-sig").splitlines()
        ):
            rid = norm(row.get("id"))
            if not rid:
                continue
            stmt = norm(row.get("question"))
            refs.append(
                {
                    "mode": "ichimon",
                    "key": _ichimon_key(rid),
                    "rel_path": _ichimon_rel_path(rid),
                    "category": norm(row.get("category")),
                    "tags": parse_tags(norm(row.get("tags"))),
                    "text": stmt,
                    "title": rid,
                    "preview": stem_preview(stmt),
                }
            )

    return refs


def _ichimon_rel_path(rid: str) -> str:
    try:
        return ichimon_rel_path(rid)
    except ValueError:
        return "q/ichimon/index.html"


def current_ref_from_page(page: dict, *, mode: str) -> dict:
    """ビルド中の page dict から current ref を作る。"""
    if mode == "past":
        stem = norm(page.get("stem_plain") or page.get("stem"))
        year, qno = page["year"], page["qno"]
        return {
            "mode": "past",
            "key": _past_key(year, qno),
            "rel_path": page["rel_path"],
            "category": norm(page.get("category")),
            "tags": list(page.get("tags") or []),
            "text": stem,
            "title": f"{year}年 第{qno}問",
            "preview": stem_preview(stem),
        }
    if mode == "practice":
        stem = norm(page.get("stem_plain"))
        qno = page["qno"]
        return {
            "mode": "practice",
            "key": _practice_key(qno),
            "rel_path": page["rel_path"],
            "category": norm(page.get("category")),
            "tags": list(page.get("tags") or []),
            "text": stem,
            "title": f"第{qno}問",
            "preview": stem_preview(stem),
        }
    rid = page["id"]
    stmt = norm(page.get("statement"))
    return {
        "mode": "ichimon",
        "key": _ichimon_key(rid),
        "rel_path": page["rel_path"],
        "category": norm(page.get("category")),
        "tags": list(page.get("tags") or []),
        "text": stmt,
        "title": rid,
        "preview": stem_preview(stmt),
    }


def _ref_page_exists(root: Path | None, ref: dict) -> bool:
    if root is None:
        return True
    rel = norm(ref.get("rel_path"))
    return bool(rel) and (root / rel).is_file()


def similarity_score(current: dict, other: dict) -> int:
    if other["key"] == current["key"] and other["mode"] == current["mode"]:
        return -1
    score = 0
    if norm(other["category"]) and other["category"] == current["category"]:
        score += 50
    tag_overlap = set(other["tags"]) & set(current["tags"])
    score += 15 * len(tag_overlap)
    if other["mode"] != current["mode"] and other["category"] == current["category"]:
        score += 12
    ta = _text_tokens(current["text"])
    tb = _text_tokens(other["text"])
    if ta and tb:
        score += min(len(ta & tb) * 8, 36)
    return score


def pick_similar_questions(
    current: dict,
    catalog: list[dict],
    *,
    limit: int = _SIMILAR_LIMIT,
    publish_root: Path | None = None,
) -> list[dict]:
    scored: list[tuple[int, dict]] = []
    for ref in catalog:
        if not _ref_page_exists(publish_root, ref):
            continue
        s = similarity_score(current, ref)
        if s >= _MIN_SCORE:
            scored.append((s, ref))
    scored.sort(key=lambda x: (-x[0], x[1]["mode"], x[1]["title"]))
    picked = [ref for _, ref in scored[:limit]]
    if len(picked) >= 2:
        return picked

    # フォールバック: 同分野のみ（スコア閾値なし）
    if norm(current["category"]):
        fallback: list[dict] = []
        for ref in catalog:
            if ref["key"] == current["key"] and ref["mode"] == current["mode"]:
                continue
            if ref["category"] != current["category"]:
                continue
            if not _ref_page_exists(publish_root, ref):
                continue
            fallback.append(ref)
        fallback.sort(key=lambda r: (r["mode"] != current["mode"], r["title"]))
        return fallback[:limit]
    return picked


def build_similar_questions_html(
    page: dict,
    rel_path: Path,
    catalog: list[dict],
    *,
    mode: str,
    rel_href,
    limit: int = _SIMILAR_LIMIT,
    publish_root: Path | None = None,
) -> str:
    """類似の問題セクション HTML。rel_href は build_* の rel_href 関数。"""
    current = current_ref_from_page(page, mode=mode)
    similar = pick_similar_questions(
        current, catalog, limit=limit, publish_root=publish_root
    )
    if not similar:
        return ""

    items: list[str] = []
    for ref in similar:
        href = rel_href(rel_path, ref["rel_path"])
        mode_label = MODE_LABEL.get(ref["mode"], ref["mode"])
        cat = html.escape(ref["category"] or "")
        title = html.escape(ref["title"])
        preview = html.escape(ref["preview"] or ref["text"][:_PREVIEW_LIMIT])
        items.append(
            f'<li class="q-similar-item">'
            f'<a class="q-similar-card" href="{html.escape(href)}">'
            f'<span class="q-similar-card-head">'
            f'<span class="q-similar-mode">{html.escape(mode_label)}</span>'
            f'<span class="q-similar-title">{title}</span>'
            f'</span>'
            f'<span class="q-similar-cat">{cat}</span>'
            f'<p class="q-similar-preview">{preview}</p>'
            f"</a></li>"
        )

    return (
        '<section class="q-block q-similar" aria-labelledby="q-similar-h">'
        '<h2 id="q-similar-h" class="q-h2">類似の問題</h2>'
        '<p class="q-similar-lead">同じ分野・タグや問題文のキーワードが近い問題です。'
        "解き直しや確認に使えます。</p>"
        f'<ul class="q-similar-list">{"".join(items)}</ul>'
        "</section>"
    )
