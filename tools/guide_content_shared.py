#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全試験サイト guide content lib 共通の prose 生成ヘルパー。"""

from __future__ import annotations

from typing import Callable

from tools.guide_topic_normalize import exam_topic_clause, topic_label


def normalize_topic_from_title(
    title: str,
    *,
    exam: str,
    exam_short: str,
    skip_prefixes: tuple[str, ...] = (),
) -> str:
    from tools.guide_topic_normalize import strip_exam_prefix

    t = (title or "").strip()
    t = __import__("re").sub(r"^(.+?)【[^】]+】$", r"\1", t).strip()
    t = strip_exam_prefix(t, exam, exam_short)
    for prefix in (f"{exam}の", f"{exam}｜", f"{exam_short}の", *skip_prefixes):
        if t.startswith(prefix):
            t = t[len(prefix) :].strip()
    return t


def official_note_single(official: str) -> str:
    return (
        f"数値・日程・合格基準は年度で更新されるため、学習前と申込前には{official}の最新案内を確認してください。"
    )


def keyword_fallback_default(
    heading: str,
    topic: str,
    *,
    exam: str,
    exam_short: str,
    official: str,
    official_note_fn: Callable[[], str],
    practice_note_fn: Callable[[str], str],
    two_paragraphs_fn: Callable[[str, str], str],
) -> str:
    label = topic_label(topic, exam, exam_short)
    if exam and exam not in label:
        subject = f"{exam}の{label}"
    else:
        subject = label
    return two_paragraphs_fn(
        f"「{heading}」に関する{subject}の要点を、{official}の受験要項と受験票で整理します。"
        f"公式テキストの該当章を開きながら読むと、演習問題の解説とも対応づけやすくなります。",
        f"{official_note_fn()} {practice_note_fn(label)}",
    )


def section_body_tail(heading: str, official: str) -> str:
    return f"「{heading}」の詳細は{official}の最新要項と演習解説で照合してください。"


EXAM_DAY_KEYWORD_CHECKS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("持参", "必ず持"), "_heading_試験当日持ち物"),
    (("禁止", "持込", "持ち込み"), "_heading_持込禁止"),
    (("タイムライン",), "_heading_当日タイムライン"),
    (("アクセス", "センター"), "_heading_試験会場アクセス"),
    (("チェックリスト", "忘れ物"), "_heading_最終確認リスト"),
)
