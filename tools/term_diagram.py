#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用語解説記事向け HTML 図解（data/term_diagrams/*.json）の読み込みと描画。"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIAGRAMS_DIR = ROOT / "data" / "term_diagrams"
DIAGRAM_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# 他サイト fork 由来の eyebrow（ビルド時に site-config へ差し替え）
_LEGACY_SITE_EYEBROWS = frozenset(
    {
        "宅建 図解",
        "マン管 図解",
        "運管 図解",
        "賃貸 図解",
        "衛生 図解",
        "精神 図解",
        "危険物 図解",
        "ボイラー 図解",
    }
)


def _site_diagram_eyebrow() -> str:
    try:
        from tools.site_config import brand_mark, brand_name, exam_grade

        grade = exam_grade()
        if grade:
            return f"{grade} 図解"
        mark = brand_mark()
        if mark:
            return f"{mark} 図解"
        name = brand_name()
        if name and name != "Sampleマスター":
            return f"{name} 図解"
    except Exception:
        pass
    return "図解"


def resolve_diagram_eyebrow(data: dict) -> str:
    raw = str(data.get("eyebrow") or "").strip()
    if not raw or raw in _LEGACY_SITE_EYEBROWS:
        return _site_diagram_eyebrow()
    return raw


def load_diagram(diagram_id: str) -> dict | None:
    if not diagram_id or not DIAGRAM_ID_RE.fullmatch(diagram_id):
        return None
    path = DIAGRAMS_DIR / f"{diagram_id}.json"
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        return None
    return data


def _land_diagram_html() -> str:
    return (
        '<div class="term-diagram-visual term-diagram-visual--land" aria-hidden="true">'
        '<div class="term-diagram-land">'
        '<span class="term-diagram-land-site">敷地</span>'
        '<div class="term-diagram-land-plot"></div>'
        '<span class="term-diagram-land-label">建築面積</span>'
        "</div></div>"
    )


def _floors_diagram_html(floors: list[str]) -> str:
    rows = "".join(
        f'<div class="term-diagram-floor-row">{html.escape(label)}</div>' for label in floors
    )
    return (
        '<div class="term-diagram-visual term-diagram-visual--floors" aria-hidden="true">'
        '<div class="term-diagram-floors">'
        f"{rows}"
        '<div class="term-diagram-floors-base"></div>'
        "</div></div>"
    )


def _visual_html(item: dict) -> str:
    visual = item.get("visual") or ""
    if visual == "land":
        return _land_diagram_html()
    if visual == "floors":
        floors = item.get("floors") or ["3階 80㎡", "2階 80㎡", "1階 80㎡"]
        if not isinstance(floors, list):
            floors = ["3階 80㎡", "2階 80㎡", "1階 80㎡"]
        return _floors_diagram_html([str(x) for x in floors if str(x).strip()])
    return ""


def _compare_card_html(item: dict) -> str:
    label = html.escape(str(item.get("label") or ""))
    catch = html.escape(str(item.get("catch") or ""))
    formula = html.escape(str(item.get("formula") or ""))
    example = html.escape(str(item.get("example") or ""))
    memo = html.escape(str(item.get("memo") or ""))
    visual = _visual_html(item)
    return (
        '<section class="term-diagram-card">'
        f'<div class="term-diagram-card-label">{label}</div>'
        f'<p class="term-diagram-card-catch">{catch}</p>'
        f"{visual}"
        '<div class="term-diagram-card-box term-diagram-card-box--formula">'
        '<p class="term-diagram-card-box-kicker">計算式</p>'
        f'<p class="term-diagram-card-box-body">{formula}</p>'
        "</div>"
        '<div class="term-diagram-card-box term-diagram-card-box--example">'
        '<p class="term-diagram-card-box-kicker">例</p>'
        f'<p class="term-diagram-card-box-body">{example}</p>'
        "</div>"
        f'<p class="term-diagram-card-memo">{memo}</p>'
        "</section>"
    )


def render_compare_dual(data: dict) -> str:
    left = data.get("left") if isinstance(data.get("left"), dict) else {}
    right = data.get("right") if isinstance(data.get("right"), dict) else {}
    eyebrow = html.escape(resolve_diagram_eyebrow(data))
    title = html.escape(str(data.get("title") or ""))
    subtitle = html.escape(str(data.get("subtitle") or ""))
    exam_point = html.escape(str(data.get("exam_point") or ""))

    quiz_html = ""
    quiz = data.get("quiz") if isinstance(data.get("quiz"), dict) else {}
    quiz_q = str(quiz.get("question") or "").strip()
    answers = quiz.get("answers") if isinstance(quiz.get("answers"), list) else []
    if quiz_q and answers:
        answer_cells = []
        for ans in answers:
            if not isinstance(ans, dict):
                continue
            text = html.escape(str(ans.get("text") or ""))
            cls = "term-diagram-quiz-answer"
            if ans.get("highlight"):
                cls += " term-diagram-quiz-answer--highlight"
            answer_cells.append(f'<div class="{cls}">{text}</div>')
        if answer_cells:
            quiz_html = (
                '<section class="term-diagram-quiz">'
                '<h3 class="term-diagram-quiz-title">一問一答</h3>'
                f'<p class="term-diagram-quiz-question">{html.escape(quiz_q)}</p>'
                f'<div class="term-diagram-quiz-answers">{"".join(answer_cells)}</div>'
                "</section>"
            )

    exam_html = ""
    if exam_point:
        exam_html = (
            '<section class="term-diagram-exam-point">'
            '<h3 class="term-diagram-exam-point-title">試験での覚え方</h3>'
            f'<p class="term-diagram-exam-point-body">{exam_point}</p>'
            "</section>"
        )

    header_html = ""
    if title:
        header_html = (
            '<header class="term-diagram-header">'
            f'<p class="term-diagram-eyebrow">{eyebrow}</p>'
            f'<h3 class="term-diagram-title">{title}</h3>'
        )
        if subtitle:
            header_html += f'<p class="term-diagram-subtitle">{subtitle}</p>'
        header_html += "</header>"

    return (
        '<figure class="term-diagram term-diagram--compare-dual" role="group">'
        f"{header_html}"
        '<div class="term-diagram-grid">'
        f"{_compare_card_html(left)}"
        f"{_compare_card_html(right)}"
        "</div>"
        f"{exam_html}"
        f"{quiz_html}"
        "</figure>"
    )


def render_diagram(data: dict) -> str:
    diagram_type = str(data.get("type") or "").strip()
    if diagram_type == "compare_dual":
        return render_compare_dual(data)
    return ""


def diagram_body_html(diagram_id: str) -> str:
    data = load_diagram(diagram_id)
    if not data:
        return ""
    return render_diagram(data)


def list_diagram_ids() -> list[str]:
    if not DIAGRAMS_DIR.is_dir():
        return []
    return sorted(
        p.stem
        for p in DIAGRAMS_DIR.glob("*.json")
        if p.is_file() and DIAGRAM_ID_RE.fullmatch(p.stem)
    )


def diagram_id_exists(diagram_id: str) -> bool:
    if load_diagram(diagram_id) is not None:
        return True
    # FP 等: 過去問・実践用図解は data/question_diagrams/ に置く場合がある
    qpath = ROOT / "data" / "question_diagrams" / f"{diagram_id}.json"
    return bool(diagram_id and DIAGRAM_ID_RE.fullmatch(diagram_id) and qpath.is_file())
