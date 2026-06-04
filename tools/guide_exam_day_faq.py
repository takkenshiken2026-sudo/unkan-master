#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験当日系 FAQ の整合性向け共通回答。"""

from __future__ import annotations


def belongings_faq_answer(*, official: str) -> str:
    return (
        f"受験票・筆記用具（HB程度の鉛筆またはシャープペン、消しゴム）は基本の持ち物です。"
        f"電子機器・辞書・参考書類は原則持込不可のため、{official}の受験要項で禁止物と持参物を確認してください。"
        f"時計や身分証の要否も会場案内に従い、前日に持ち物リストへチェックを入れておくと安心です。"
    )


def access_faq_answer(*, official: str) -> str:
    return (
        f"会場の正式名称・住所・最寄り駅は受験票と{official}の会場案内が正本です。"
        f"前日に地図アプリで自宅から会場までの所要時間を確認し、開始30分前到着＋余裕30分を目安に出発時刻を決めてください。"
        f"交通遅延時の予備ルートと問い合わせ先も控えておくと安心です。"
    )


def faq_answer_for_belongings_question(question: str, *, official: str) -> str | None:
    q = (question or "").strip()
    if not q:
        return None
    if "持ち物" in q or "持参" in q:
        return belongings_faq_answer(official=official)
    return None


def faq_answer_for_access_question(question: str, *, official: str) -> str | None:
    q = (question or "").strip()
    if not q:
        return None
    if "アクセス" in q or "住所" in q or "会場" in q:
        return access_faq_answer(official=official)
    return None


def faq_answer_for_coherence(question: str, *, official: str) -> str | None:
    return faq_answer_for_belongings_question(question, official=official) or faq_answer_for_access_question(
        question, official=official
    )
