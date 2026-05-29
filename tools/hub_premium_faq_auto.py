# -*- coding: utf-8 -*-
"""手書き PREMIUM_FAQS 未登録 slug 向け FAQ 自動生成（行データから組み立て・新規事実は付けない）."""

from __future__ import annotations

import ast
import re

from tools.hub_faq_expand import MIN_FAQ_ANSWER, _FALLBACK
from tools.editorial_quality import EDITORIAL_GENERIC_PHRASES, split_semicolon

_GENERIC_MARKERS = (
    "本ページは学習整理用",
    "関連用語ページと条文を並べて読むと",
    "試験実施団体の公式情報もあわせて確認",
)


def _norm(value: object) -> str:
    return str(value or "").strip()


def _clip(text: str, limit: int) -> str:
    text = _norm(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip("、。 ") + "…"


def _first_clause(raw: str) -> str:
    text = _norm(raw)
    if not text:
        return ""
    part = text.split(";")[0].strip()
    for prefix in ("× ", "○ ", "×", "○"):
        if part.startswith(prefix):
            part = part[len(prefix) :].strip()
    if " → " in part:
        part = part.split(" → ", 1)[1].strip()
    return part


def _has_generic_phrase(text: str) -> bool:
    return any(p in text for p in EDITORIAL_GENERIC_PHRASES)


def _strip_generic(text: str) -> str:
    out = _norm(text)
    for phrase in EDITORIAL_GENERIC_PHRASES:
        out = out.replace(phrase, "")
    return _norm(out)


FAQ_BOILERPLATE = (
    "試験論点・条文・数値の対応を比較表に整理し、過去問で正誤の型を分類してください。"
)


def _needs_auto(row: dict[str, str]) -> bool:
    answers = [_norm(row.get(f"faq_{i}_answer")) for i in range(1, 5)]
    if not all(answers):
        return True
    if any(FAQ_BOILERPLATE in a for a in answers):
        return True
    if any(len(a) < MIN_FAQ_ANSWER for a in answers):
        return True
    joined = " ".join(answers)
    if any(m in joined for m in _GENERIC_MARKERS) or _FALLBACK in joined:
        return True
    return _has_generic_phrase(joined)


def _pad_answer(text: str, *, extra: str = "") -> str:
    combined = _norm(text)
    if extra and extra not in combined:
        combined = f"{combined} {extra}".strip()
    if len(combined) < MIN_FAQ_ANSWER:
        combined = f"{combined} 過去問で正誤の型を分類し、試験要項で数値・期限を照合してください。".strip()
    return _strip_generic(combined) or combined


def _safe_answer(text: str, *, extra: str = "", row: dict[str, str] | None = None) -> str:
    answer = _pad_answer(text, extra=extra)
    if _has_generic_phrase(answer):
        answer = _strip_generic(answer)
    if len(answer) >= MIN_FAQ_ANSWER and not _has_generic_phrase(answer):
        return answer
    row = row or {}
    title = _norm(row.get("title") or row.get("article_title"))
    exam = _first_clause(_norm(row.get("exam_points"))) or "出題論点と条文"
    mistake = _clip(_norm(row.get("common_mistakes") or row.get("confusion_point")), 80)
    fallback = (
        f"「{title}」では{exam}を軸に、条文・数値・主体の取り違えを比較表で整理してください。"
        f"{(' 典型誤答は' + mistake + '。') if mistake else ''}"
        " 過去問では条件文の主語入れ替え肢に注意してください。"
    )
    return _pad_answer(fallback, extra=extra)


def faqs_from_row(row: dict[str, str], *, official_suffix: str = "") -> list[tuple[str, str]]:
    title = _norm(row.get("title") or row.get("article_title") or row.get("slug"))
    lead = _clip(_strip_generic(_norm(row.get("article_lead") or row.get("summary"))), 120)
    exam_points = [
        _strip_generic(_first_clause(p))
        for p in split_semicolon(_norm(row.get("exam_points")))
        if p
    ][:3]
    mistake = _clip(_strip_generic(_norm(row.get("common_mistakes") or row.get("confusion_point"))), 100)
    tip = _clip(_strip_generic(_norm(row.get("memory_tip"))), 80)
    highlight = _clip(_strip_generic(_norm(row.get("highlight"))), 60)
    suffix = _strip_generic(official_suffix.strip())

    exam1 = exam_points[0] if exam_points else "出題論点と条文の対応"
    exam2 = exam_points[1] if len(exam_points) > 1 else exam1

    pairs: list[tuple[str, str]] = [
        (
            f"「{title}」の試験での位置づけは？",
            _safe_answer(
                f"{lead or title + 'の論点整理ページです。'} "
                f"試験では{exam1}を軸に、関連条文・数値・主体の取り違えを照合してください。",
                extra=suffix,
                row=row,
            ),
        ),
        (
            f"「{title}」でよくある誤答パターンは？",
            _safe_answer(
                f"{mistake or '似た用語・数値・手続の混同が典型です。'} "
                f"誤答肢では{exam2}の主語や条件が入れ替わることが多いので、比較表で整理してください。",
                extra=suffix,
                row=row,
            ),
        ),
        (
            f"「{title}」の覚え方・確認手順は？",
            _safe_answer(
                f"{('覚え方：' + tip + ' ') if tip else ''}"
                f"{('早見の要点：' + highlight + ' ') if highlight else ''}"
                "用語集→本ページ→過去問の順で往復し、正誤理由をメモに残してください。",
                extra=suffix,
                row=row,
            ),
        ),
        (
            f"「{title}」の公式情報はどこで確認しますか？",
            _safe_answer(
                "数値・期限・合格基準・制度改正は年度で変わります。"
                "学習中も試験要項・施行規則・実施団体の公式サイトで最新情報を照合してください。"
                + (f" {suffix}" if suffix else ""),
                row=row,
            ),
        ),
    ]
    return pairs


def apply_premium_faq(row: dict[str, str], *, official_suffix: str = "") -> dict[str, str]:
    if not _needs_auto(row):
        return row
    out = dict(row)
    for i, (q, a) in enumerate(faqs_from_row(out, official_suffix=official_suffix), start=1):
        out[f"faq_{i}_question"] = q
        out[f"faq_{i}_answer"] = a
    return out


def apply_all(rows: list[dict[str, str]], *, official_suffix: str = "") -> list[dict[str, str]]:
    return [apply_premium_faq(r, official_suffix=official_suffix) for r in rows]


def discover_official_suffix(site_root) -> str:
    """write_*_hub_s30.py の _OFFICIAL 定数を探す."""
    from pathlib import Path

    root = Path(site_root)
    for fp in sorted(root.glob("tools/write_*_hub_s30.py")):
        text = fp.read_text(encoding="utf-8")
        m = re.search(r'_OFFICIAL\s*=\s*("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'])*\')', text)
        if m:
            try:
                return ast.literal_eval(m.group(1))
            except (SyntaxError, ValueError):
                continue
    return ""
