#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験ガイド退役候補の選定ルール（テンプレ共通）。"""

from __future__ import annotations

import re
from typing import Callable

from tools.editorial_quality import is_published_guide, norm

# 退役しないコア骨格
KEEP_CORE: frozenset[str] = frozenset(
    {
        "exam-overview",
        "exam-schedule",
        "exam-eligibility",
        "exam-fees",
        "exam-application-flow",
        "pass-score",
        "pass-rate",
        "exam-format-overview",
        "exam-scope-overview",
        "subject-breakdown",
        "study-plan",
        "past-question-strategy",
        "past-questions-by-field",
        "textbook-selection",
        "problem-book-selection",
        "final-day-checklist",
        "exam-day-flow",
        "exam-day-items",
        "after-pass-procedure",
        "retake-strategy",
        "official-info-sources",
        "syllabus-how-to-read",
        "weight-by-topic",
        "time-limit-strategy",
        "application-deadline-checklist",
        "exam-venue-and-region",
        "registration-after-pass",
        "pass-announcement-guide",
        "glossary-how-to",
        "common-misconceptions",
    }
)

STUDY_PLAN_SLUGS = frozenset(
    {
        "study-plan-3months",
        "study-plan-6months",
        "study-plan-1year",
        "study-plan-working",
        "study-plan-beginner",
        "first-30-days-plan",
        "self-study-roadmap",
        "self-study-schedule",
    }
)

SELF_STUDY_META = frozenset(
    {
        "self-study-motivation",
        "self-study-environment",
        "self-study-mistakes",
        "self-study-without-school",
        "self-study-start",
        "plateau-breakthrough",
        "balance-work-study",
        "time-management",
    }
)

PASTQ_MICRO = frozenset(
    {
        "past-questions-by-year",
        "past-questions-latest-year",
        "past-questions-review-cycle",
        "past-questions-score-analysis",
        "past-questions-wrong-reasons",
        "past-questions-first-attempt",
        "bookmark-review-method",
        "almost-correct-review",
        "pass-only-past-questions-myth",
    }
)

PRACTICE_MICRO = frozenset(
    {
        "calculation-drill",
        "drill-volume-guide",
        "ichimon-practice",
        "mock-exam-how-to",
        "simulation-exam-schedule",
        "timed-practice",
    }
)

SCOPE_UPDATE = frozenset(
    {
        "scope-revision-history",
        "scope-vs-past-questions",
        "new-topics-trend",
        "syllabus-update-tracker",
        "material-update-cycle",
        "legal-revision-impact",
        "exam-changes",
        "official-info-update-habits",
    }
)

EXAM_DAY_MICRO = frozenset(
    {
        "exam-day-time-allocation",
        "exam-day-troubleshooting",
        "mental-prep-exam-day",
        "final-sleep-and-health",
        "final-mock-last-run",
        "final-scope-narrowing",
        "final-week-prep",
    }
)

PASS_MYTH = frozenset(
    {
        "pass-rate-how-to-read",
        "difficulty-myths",
        "common-misconceptions",
        "eligibility-myths",
        "study-hours-myth",
        "difficulty-for-beginners",
    }
)

TERMS_META = frozenset(
    {
        "glossary-how-to",
        "glossary-study-method",
        "important-terms-list",
        "terms-importance-levels",
        "terms-with-past-questions",
        "related-terms-navigation",
        "numbers-and-deadlines",
        "rate-and-percentage",
        "numeric-trap-choices",
        "confusing-terms",
    }
)

SOFT_CAREER = frozenset(
    {
        "compare-similar-qualifications",
        "career-after-qualification",
        "exam-purpose-and-career",
        "correspondence-course-guide",
        "free-materials-online",
        "learning-app-guide",
        "textbook-vs-past-questions",
    }
)

REVIEW_META = frozenset(
    {
        "note-taking-method",
        "mistake-notebook",
        "formula-memorization",
        "review-cycle-spaced",
        "score-gap-analysis",
        "fail-retry-plan",
        "retake-schedule-adjustment",
    }
)

NOT_APPLICABLE = frozenset(
    {
        "cbt-computer-exam",
        "written-essay-section",
        "essay-practice-method",
    }
)

FIELD_SUB_SUFFIXES = ("frequent-topics", "calculation", "case-study", "past-question-focus")

# slug -> 統合先（明示）
EXPLICIT_REDIRECT: dict[str, str] = {
    **{s: "study-plan" for s in STUDY_PLAN_SLUGS},
    **{s: "study-plan" for s in SELF_STUDY_META},
    **{s: "past-question-strategy" for s in PASTQ_MICRO},
    **{s: "past-question-strategy" for s in PRACTICE_MICRO},
    **{s: "syllabus-how-to-read" for s in SCOPE_UPDATE},
    **{s: "final-day-checklist" for s in EXAM_DAY_MICRO},
    **{s: "exam-overview" for s in PASS_MYTH},
    **{s: "glossary-how-to" for s in TERMS_META if s != "glossary-how-to"},
    **{s: "exam-overview" for s in SOFT_CAREER},
    **{s: "study-plan" for s in REVIEW_META},
    **{s: "exam-format-overview" for s in NOT_APPLICABLE},
}


def is_v2_complete(note: str) -> bool:
    n = norm(note).replace("・", "·")
    return "手書きリライト" in n and "具体例" in n and "v2" in n


def retire_reason(slug: str, *, site_field_ids: list[str], template_slugs: frozenset[str]) -> str | None:
    if slug in KEEP_CORE:
        return None
    if slug in EXPLICIT_REDIRECT or slug in NOT_APPLICABLE:
        return "template_cluster"
    m = re.match(r"field-([^-]+)-(.+)$", slug)
    if m:
        fid, sub = m.group(1), m.group(2)
        if sub in FIELD_SUB_SUFFIXES:
            if not site_field_ids or fid in site_field_ids:
                return "field_sub"
        return None
    if slug not in template_slugs and not slug.startswith("field-"):
        return None
    return None


def redirect_target(
    slug: str,
    *,
    published_slugs: set[str],
    retiring: set[str] | None = None,
) -> str:
    retiring = retiring or set()
    if slug in EXPLICIT_REDIRECT:
        target = EXPLICIT_REDIRECT[slug]
    else:
        m = re.match(r"field-([^-]+)-(.+)$", slug)
        if m:
            target = f"field-{m.group(1)}-basics"
        else:
            target = "exam-overview"
    if target == slug or target in retiring:
        for fallback in (
            target,
            "study-plan",
            "past-question-strategy",
            "exam-overview",
        ):
            if fallback not in retiring and fallback in published_slugs:
                return fallback
        for fallback in KEEP_CORE:
            if fallback not in retiring and fallback in published_slugs:
                return fallback
        return "exam-overview"
    if target in published_slugs:
        return target
    for fallback in ("study-plan", "exam-overview"):
        if fallback in published_slugs and fallback not in retiring:
            return fallback
    return "exam-overview"


def select_retire_candidates(
    rows: list[dict[str, str]],
    *,
    site_field_ids: list[str],
    template_slugs: frozenset[str],
    ratio: float = 0.4,
    only_non_v2: bool = True,
) -> list[tuple[str, str, str]]:
    """Returns list of (slug, reason, redirect_to)."""
    eligible: list[tuple[str, str, str, int]] = []
    published_slugs = {norm(r.get("slug")) for r in rows if is_published_guide(r) and norm(r.get("slug"))}
    for row in rows:
        if not is_published_guide(row):
            continue
        if "アフィリエイト" in norm(row.get("tags")):
            continue
        slug = norm(row.get("slug"))
        if not slug or slug in KEEP_CORE:
            continue
        if only_non_v2 and is_v2_complete(row.get("revision_note", "")):
            continue
        reason = retire_reason(slug, site_field_ids=site_field_ids, template_slugs=template_slugs)
        if not reason:
            continue
        target = redirect_target(slug, published_slugs=published_slugs)
        priority = 0
        if reason == "field_sub":
            priority = 3
        elif reason == "template_cluster":
            priority = 2
        eligible.append((slug, reason, target, priority))
    eligible.sort(key=lambda x: (-x[3], x[0]))
    non_aff_published = sum(
        1
        for r in rows
        if is_published_guide(r)
        and "アフィリエイト" not in norm(r.get("tags"))
        and (not only_non_v2 or not is_v2_complete(r.get("revision_note", "")))
    )
    limit = max(1, round(non_aff_published * ratio))
    picked = eligible[:limit]
    retiring = {s for s, _, _, _ in picked}
    return [
        (s, r, redirect_target(s, published_slugs=published_slugs, retiring=retiring))
        for s, r, _, _ in picked
    ]


def load_template_slugs(catalog_path) -> frozenset[str]:
    import re as _re
    from pathlib import Path

    text = Path(catalog_path).read_text(encoding="utf-8")
    slugs: set[str] = set()
    for m in _re.finditer(r"\|\s*([a-z0-9-]+)\s*\|", text):
        s = m.group(1)
        if s not in ("slug", "genre") and "field" not in s:
            slugs.add(s)
    return frozenset(slugs)
