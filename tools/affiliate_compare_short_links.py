#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""比較記事本文の bare affiliate slug を短ラベル Markdown リンクへ置換する。"""

from __future__ import annotations

import re

_DEFAULT_LABELS: dict[str, str] = {
    "affiliate-textbooks-recommend": "おすすめテキスト3選",
    "affiliate-problem-books": "おすすめ問題集3選",
    "affiliate-mock-exam-materials": "おすすめ一問一答・速習",
    "affiliate-free-vs-paid-study": "無料と有料教材の使い分け",
    "affiliate-correspondence-course": "おすすめ通信講座",
    "affiliate-online-course-compare": "オンライン講座比較",
    "affiliate-cram-school": "通学講座の選び方",
    "affiliate-beginner-material-set": "初学者向け教材セット",
    "affiliate-retake-short-course": "再受験者向け短期講座",
    "affiliate-qualification-support-service": "受験支援サービス",
}

_GUIDE_LABELS: dict[str, str] = {
    "study-plan": "学習計画の立て方",
    "study-plan-beginner": "初学者向け学習計画",
    "textbook-selection": "テキストの選び方",
    "self-study-start": "独学の始め方",
    "free-materials-online": "無料教材の活用",
    "past-questions-by-field": "分野別過去問",
    "past-question-strategy": "過去問の使い方",
    "final-week-prep": "直前1週間の対策",
}

_MD_LINK = re.compile(r"\[[^\]]+\]\([^)]+\)")
_URL = re.compile(r"https?://\S+")


def md_link(slug: str, label: str) -> str:
    return f"[{label}](../{slug}/)"


def labels_for_site(site_id: str) -> dict[str, str]:
    labels = dict(_DEFAULT_LABELS)
    labels.update(_GUIDE_LABELS)
    if site_id == "takken-master":
        labels["affiliate-correspondence-course"] = "おすすめ通信講座4選"
    return labels


def replace_bare_slugs(text: str, labels: dict[str, str]) -> str:
    if not text:
        return text

    slots: list[str] = []

    def stash(match: re.Match[str]) -> str:
        slots.append(match.group(0))
        return f"\ue000{len(slots)-1}\ue001"

    protected = _MD_LINK.sub(stash, text)
    protected = _URL.sub(stash, protected)

    ordered = sorted(labels, key=len, reverse=True)
    alts = "|".join(re.escape(s) for s in ordered)
    token_re = re.compile(rf"(?<![a-z0-9-/\[])(?:{alts})(?![a-z0-9-/\]])")

    def repl(match: re.Match[str]) -> str:
        slug = match.group(0)
        return md_link(slug, labels[slug])

    out = token_re.sub(repl, protected)
    for i, raw in enumerate(slots):
        out = out.replace(f"\ue000{i}\ue001", raw)
    return out


def bare_affiliate_slugs(text: str) -> list[str]:
    hits: list[str] = []
    for m in re.finditer(r"affiliate-[a-z0-9-]+", text):
        i = m.start()
        if i >= 3 and text[i - 3 : i] == "../":
            continue
        if i >= 1 and text[i - 1] == "[":
            continue
        token = m.group(0)
        if token not in hits:
            hits.append(token)
    return hits
