#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験ガイド × 知識ハブの配置判定ルール（audit / fix 共通）."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

# 試験ガイドに残すカタログ slug（定義っぽいタイトルでも配置 OK）
GUIDE_KEEP_SLUGS = frozenset(
    {
        "exam-overview",
        "compare-similar-qualifications",
        "numbers-and-deadlines",
        "glossary-how-to",
        "glossary-study-method",
        "confusing-terms",
        "exam-purpose-and-career",
        "first-time-exam-guide",
        "official-info-sources",
    }
)

GUIDE_ACTION_TITLE = re.compile(
    r"勉強法|学習計画|学習法|独学|申込|申し込み|受験資格|合格戦略|再受験|"
    r"直前|当日|模試|過去問.*(?:活用法|進め方|解き方)|教材|通信講座|予備校|"
    r"転職|副業|就活|スケジュール|何から|始め方|進め方|対策法|苦手克服|"
    r"復習.*(?:法|サイクル)|使い方|活用法|ノートの作り方|併願"
)

GUIDE_TERM_TITLE = re.compile(
    r"(?:^|[｜\|])[^｜\|]{1,60}とは[？?]?|の意味[？?]?|の定義[？?]?"
)

GLOSSARY_GUIDE_TERM = re.compile(
    r"^(?:"
    r"直前対策|再受験|勉強法|学習計画|独学|申込|模試|過去問の進め方|教材選び|"
    r"学習スケジュール|受験スケジュール|何から始める"
    r")$|"
    r"(?:勉強法|学習計画|独学対策|再受験戦略|直前対策)$"
)

COMPARE_TITLE = re.compile(
    r"(?:と|・|／|/)[^、。]{1,30}(?:の)?違い|(?:の)?比較[｜\|]|vs\.?"
)

NUMBERS_LIST_TITLE = re.compile(r"数値.*一覧|数字.*一覧|期限.*一覧|早見表.*(?:まとめ|一覧)")

MIN_GLOSSARY_BODY = 80


@dataclass
class RuleFinding:
    level: str
    kind: str
    slug: str
    title: str
    message: str
    target: str = ""
    glossary_term: str = ""
    glossary_slug: str = ""
    confidence: str = ""  # high | medium | review


def norm(value: str | None) -> str:
    return (value or "").strip()


def is_published_guide(row: dict[str, str]) -> bool:
    return norm(row.get("content_status")) == "published" and bool(norm(row.get("slug")))


def title_term_hint(title: str) -> str:
    t = re.sub(r"^【[^】]+】", "", title)
    t = re.sub(r"^[^｜\|]+[｜\|]", "", t)
    t = re.split(r"とは[？?]?", t)[0].strip()
    t = re.sub(r"（[^）]+）", "", t)
    t = re.sub(r"\([^)]+\)", "", t).strip()
    return t


def glossary_index(rows: list[dict[str, str]]) -> tuple[dict[str, dict], dict[str, dict]]:
    by_slug: dict[str, dict] = {}
    by_term: dict[str, dict] = {}
    for row in rows:
        body = norm(row.get("term_detail_body"))
        if len(body) < MIN_GLOSSARY_BODY:
            continue
        slug = norm(row.get("url_slug")) or norm(row.get("slug"))
        if slug:
            by_slug[slug] = row
        term = norm(row.get("term"))
        if term:
            by_term[term] = row
    return by_slug, by_term


def match_glossary(
    guide: dict[str, str],
    by_slug: dict[str, dict],
    by_term: dict[str, dict],
) -> tuple[str, dict[str, str]] | None:
    """ガイドと用語解説の重複候補。slug 一致か、用語定義タイトル（〜とは）のみ判定。"""
    slug = norm(guide.get("slug"))
    if slug in GUIDE_KEEP_SLUGS:
        return None
    if slug in by_slug:
        return "slug", by_slug[slug]

    title = norm(guide.get("title"))
    if not GUIDE_TERM_TITLE.search(title):
        return None
    if GUIDE_ACTION_TITLE.search(title):
        return None
    if re.search(r"仕事内容|就活|転職|副業|キャリア|難易度|メリット|取得後", title):
        return None

    hint = title_term_hint(title)
    if not hint or len(hint) < 2:
        return None

    if hint in by_term:
        return "term_exact", by_term[hint]

    # 用語名の前方一致（「合理的配慮」↔「合理的配慮の提供」）
    prefix_hits: list[tuple[int, dict[str, str]]] = []
    for term, row in by_term.items():
        if term.startswith(hint) or hint.startswith(term):
            if min(len(hint), len(term)) < 2:
                continue
            prefix_hits.append((min(len(hint), len(term)), row))
    if prefix_hits:
        prefix_hits.sort(key=lambda x: -x[0])
        return "term_prefix", prefix_hits[0][1]

    # 複合ヒント（「傾聴・アクティブリスニング」↔「アクティブリスニング」）
    contain_hits: list[tuple[int, dict[str, str]]] = []
    for term, row in by_term.items():
        if len(term) < 2:
            continue
        if term in hint or hint in term:
            contain_hits.append((len(term), row))
    if contain_hits:
        contain_hits.sort(key=lambda x: -x[0])
        return "term_contains", contain_hits[0][1]

    # guide slug ↔ url_slug（eap-guide → eap）
    guide_slug = norm(guide.get("slug"))
    if guide_slug in by_slug:
        return "slug", by_slug[guide_slug]
    for url_slug, row in by_slug.items():
        if guide_slug == url_slug or guide_slug.startswith(url_slug + "-") or url_slug.startswith(guide_slug):
            if min(len(guide_slug), len(url_slug)) >= 3:
                return "slug_related", row

    return None


def load_hub_rows(site_root: Path) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = {}
    for name in ("comparisons.csv", "numbers.csv", "mistakes.csv"):
        path = site_root / "data" / name
        if path.is_file():
            out[name] = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    return out


def audit_guide_rows(
    guides: list[dict[str, str]],
    glossary: list[dict[str, str]],
    hub: dict[str, list[dict[str, str]]],
) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    by_slug, by_term = glossary_index(glossary)
    _ = by_term

    for row in guides:
        if not is_published_guide(row):
            continue
        slug = norm(row.get("slug"))
        title = norm(row.get("title"))
        genre = norm(row.get("genre"))

        if slug in GUIDE_KEEP_SLUGS:
            continue
        if genre == "用語ハブ活用法":
            continue

        matched = match_glossary(row, by_slug, by_term)
        if matched:
            kind, gloss = matched
            conf = "high" if kind in {"slug", "term_exact", "term_prefix", "term_contains", "slug_related"} else "medium"
            gslug = norm(gloss.get("url_slug")) or norm(gloss.get("slug"))
            findings.append(
                RuleFinding(
                    "WARN",
                    "guide_duplicate_glossary",
                    slug,
                    title,
                    "試験ガイドと用語解説に同一論点。用語解説を正とし、ガイドは橋渡しまたは draft 化",
                    target="glossary",
                    glossary_term=norm(gloss.get("term")),
                    glossary_slug=gslug,
                    confidence=conf,
                )
            )
            continue

        if GUIDE_TERM_TITLE.search(title) and not GUIDE_ACTION_TITLE.search(title):
            if re.search(r"仕事内容|キャリア|取得後|就活|転職", title):
                continue
            findings.append(
                RuleFinding(
                    "WARN",
                    "guide_should_be_glossary",
                    slug,
                    title,
                    "用語定義系タイトル。用語解説（glossary_terms.csv）へ移す",
                    target="glossary",
                    confidence="review",
                )
            )
            continue

        if COMPARE_TITLE.search(title) and "併願" not in title and "講座" not in title:
            if re.search(r"ノート|作り方", title):
                continue
            findings.append(
                RuleFinding(
                    "INFO",
                    "guide_should_be_compare",
                    slug,
                    title,
                    "比較・整理表（comparisons.csv）候補。併願・学習戦略が主題ならガイド維持",
                    target="comparisons",
                    confidence="review",
                )
            )
            continue

        if NUMBERS_LIST_TITLE.search(title) and slug != "numbers-and-deadlines":
            findings.append(
                RuleFinding(
                    "WARN",
                    "guide_should_be_numbers",
                    slug,
                    title,
                    "数値一覧系。numbers.csv へ移す（numbers-and-deadlines は活用法ガイドとして維持）",
                    target="numbers",
                    confidence="review",
                )
            )

    return findings


def audit_glossary_rows(
    glossary: list[dict[str, str]],
    guides: list[dict[str, str]],
) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    guide_slugs = {norm(r.get("slug")) for r in guides if norm(r.get("slug"))}

    for row in glossary:
        term = norm(row.get("term"))
        body = norm(row.get("term_detail_body"))
        if len(body) < MIN_GLOSSARY_BODY:
            continue
        slug = norm(row.get("url_slug")) or norm(row.get("slug"))
        title = norm(row.get("article_title")) or term

        if GLOSSARY_GUIDE_TERM.search(term):
            if norm(row.get("term_detail_body")).startswith("【配置整理】"):
                continue
            findings.append(
                RuleFinding(
                    "WARN",
                    "glossary_should_be_guide",
                    slug or term,
                    title,
                    f"用語名が学習行動系（{term}）。試験ガイドへ移す",
                    target="guide",
                    glossary_term=term,
                    glossary_slug=slug,
                    confidence="high",
                )
            )
            continue

        if slug and slug in guide_slugs:
            pub = next(
                (g for g in guides if norm(g.get("slug")) == slug and is_published_guide(g)),
                None,
            )
            if pub and norm(pub.get("genre")) == "用語ハブ活用法" and "配置整理" in norm(pub.get("revision_note")):
                continue
            if pub:
                findings.append(
                    RuleFinding(
                        "WARN",
                        "slug_collision",
                        slug,
                        title,
                        "url_slug が試験ガイド slug と同名。ガイド側を整理",
                        target="guide",
                        glossary_term=term,
                        glossary_slug=slug,
                        confidence="high",
                    )
                )

    return findings


def glossary_href(row: dict[str, str]) -> str:
    slug = norm(row.get("url_slug")) or norm(row.get("slug"))
    if slug:
        return f"/terms/{slug}.html"
    term = norm(row.get("term"))
    return f"/terms/index.html?q={term}" if term else "/terms/index.html"
