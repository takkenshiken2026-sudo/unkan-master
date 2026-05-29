# -*- coding: utf-8 -*-
"""知識ハブ：短い FAQ 回答を試験文脈付きで100字前後まで拡張（事実の創作なし）."""

from __future__ import annotations

MIN_FAQ_ANSWER = 100

_FALLBACK = (
    "本ページは学習整理用です。数値・制度変更は必ず公式情報（試験要項・法令）で確認し、"
    "過去問で正誤の型を分類してください。"
)


def _first_clause(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    part = text.split(";")[0].strip()
    for prefix in ("× ", "○ ", "×", "○"):
        if part.startswith(prefix):
            part = part[len(prefix) :].strip()
    if " → " in part:
        part = part.split(" → ", 1)[1].strip()
    return part


def expand_faq_answer(answer: str, row: dict[str, str]) -> str:
    text = (answer or "").strip()
    if len(text) >= MIN_FAQ_ANSWER:
        return text

    exam = _first_clause(row.get("exam_points", ""))
    tip = _first_clause(row.get("memory_tip", ""))
    mistake = _first_clause(row.get("common_mistakes", ""))
    lead = (row.get("article_lead") or row.get("summary") or "").strip()

    suffix_parts: list[str] = []
    if exam and exam not in text:
        suffix_parts.append(f"試験では{exam}をセットで確認してください。")
    if mistake and mistake not in text:
        suffix_parts.append(f"誤答では{mistake}に注意してください。")
    if tip and tip not in text:
        suffix_parts.append(f"覚え方：{tip}")
    if lead and len(lead) > 20:
        snippet = lead[:60].rstrip("。、 ") + "。"
        if snippet not in text:
            suffix_parts.append(snippet)

    combined = text
    for part in suffix_parts:
        if len(combined) >= MIN_FAQ_ANSWER:
            break
        combined = f"{combined} {part}".strip()

    if len(combined) < MIN_FAQ_ANSWER:
        combined = f"{combined} {_FALLBACK}".strip()

    if len(combined) < MIN_FAQ_ANSWER:
        combined = combined + " 関連用語ページと条文を並べて読むと、主語と数値の取り違えを防げます。"

    return combined


def expand_row_faqs(row: dict[str, str]) -> dict[str, str]:
    out = dict(row)
    for i in range(1, 5):
        key = f"faq_{i}_answer"
        if out.get(key):
            out[key] = expand_faq_answer(out[key], out)
    return out


def expand_all(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [expand_row_faqs(r) for r in rows]
