#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ガイド記事のトピック名から試験名の重複プレフィックスを除去する。"""

from __future__ import annotations

import re


def strip_exam_prefix(text: str, *aliases: str) -> str:
    out = (text or "").strip()
    if not out:
        return out
    for alias in sorted({a.strip() for a in aliases if a and a.strip()}, key=len, reverse=True):
        for prefix in (f"{alias}の", f"{alias}｜", f"{alias}|", f"{alias} "):
            if out.startswith(prefix):
                out = out[len(prefix) :].strip()
        if out.startswith(alias):
            rest = out[len(alias) :].lstrip(" の｜|")
            if len(rest) >= 4:
                out = rest
    return out


def topic_label(topic: str, exam: str, exam_short: str = "") -> str:
    """本文に埋め込む短いトピック名（試験名の二重化を避ける）。"""
    cleaned = strip_exam_prefix(topic, exam, exam_short)
    if cleaned and cleaned != topic:
        return cleaned
    if exam and exam in topic:
        return cleaned or "本テーマ"
    return topic or "本テーマ"


def exam_topic_clause(exam: str, topic: str, exam_short: str = "") -> str:
    """「{試験}の{トピック}について」形式（重複を避ける）。"""
    label = strip_exam_prefix(topic, exam, exam_short) or topic or "本テーマ"
    if exam and (exam in label or (exam_short and exam_short in label and exam not in label)):
        return f"{label}について"
    if exam:
        return f"{exam}の{label}について"
    return f"{label}について"


def scrub_exam_duplication(text: str, exam: str, exam_short: str = "") -> str:
    """CSV 既存文の「試験名＋短称」二重化を除去する。"""
    if not text or not exam:
        return text
    out = text
    aliases = [a for a in (exam_short, exam) if a]
    for alias in sorted(set(aliases), key=len, reverse=True):
        out = re.sub(rf"{re.escape(exam)}の{re.escape(alias)}\s+", f"{exam}の", out)
        out = re.sub(rf"{re.escape(exam)}の{re.escape(alias)}の", f"{exam}の", out)
        if alias != exam:
            out = re.sub(rf"{re.escape(exam)}の{re.escape(exam)}", exam, out)
    out = re.sub(rf"({re.escape(exam)}の)\1+", r"\1", out)
    return re.sub(r"[ \t]{2,}", " ", out).strip()
