#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知識ハブ品質監査レポート（numbers / FAQ generic / title 類似 / 薄い本文）."""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.editorial_quality import EDITORIAL_GENERIC_PHRASES  # noqa: E402
from tools.hub_faq_expand import MIN_FAQ_ANSWER, _FALLBACK  # noqa: E402
from tools.hub_strip_batch_suffix import BATCH_SUFFIX_RE  # noqa: E402
from tools.knowledge_hub_rules import HUB_MIN_LENGTHS  # noqa: E402

DATA = ROOT / "data"
OUT = ROOT / "reports" / "hub_audit"
REGISTRY = Path("/Users/otedaiki/Projects/exam-site-shell/docs/hub_numbers_verified.json")
if not REGISTRY.is_file():
    REGISTRY = Path("/Users/otedaiki/Projects/docs/hub_numbers_verified.json")
HUB_FILES = ("comparisons.csv", "numbers.csv", "mistakes.csv")
DIGIT_RE = re.compile(r"\d")


def _title_key(title: str) -> str:
    return BATCH_SUFFIX_RE.sub("", title.strip()).strip()


def audit_batch_suffix(rows: list[dict[str, str]], hub_file: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows:
        slug = (row.get("slug") or "").strip()
        title = (row.get("title") or "").strip()
        for key, val in row.items():
            if key == "slug" or not isinstance(val, str):
                continue
            if BATCH_SUFFIX_RE.search(val):
                out.append(
                    {
                        "hub_file": hub_file,
                        "slug": slug,
                        "title": title,
                        "field": key,
                        "snippet": val[:80],
                    }
                )
    return out


def _read_rows(name: str) -> list[dict[str, str]]:
    path = DATA / name
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def _load_verified_registry() -> dict[str, dict[str, str]]:
    if not REGISTRY.is_file():
        return {}
    try:
        raw = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    site_key = ROOT.name
    site = raw.get(site_key) or {}
    out: dict[str, dict[str, str]] = {}
    if isinstance(site, dict):
        for slug, meta in site.items():
            if isinstance(meta, dict):
                out[str(slug)] = meta
    return out


def audit_numbers(
    rows: list[dict[str, str]], hub_file: str, verified_registry: dict[str, dict[str, str]]
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows:
        slug = (row.get("slug") or "").strip()
        title = (row.get("title") or "").strip()
        highlight = (row.get("highlight") or "").strip()
        raw = row.get("item_rows") or "[]"
        try:
            items = json.loads(raw)
        except json.JSONDecodeError:
            items = []
        values: list[str] = []
        flags: list[str] = []
        has_digit_in_values = False
        if not isinstance(items, list) or not items:
            flags.append("empty_item_rows")
        else:
            for item in items:
                if isinstance(item, dict):
                    val = str(item.get("value", "")).strip()
                    values.append(val)
                    if val and DIGIT_RE.search(val):
                        has_digit_in_values = True
                    elif val and any(
                        k in val for k in ("日", "年", "月", "点", "％", "%", "時間", "こう")
                    ):
                        flags.append("maybe_missing_digit")
        if has_digit_in_values:
            flags.append("verify_official")
        elif not DIGIT_RE.search(highlight):
            flags.append("concept_page")
        verified = ""
        meta = verified_registry.get(slug)
        if meta:
            verified = str(meta.get("status") or "OK")
        out.append(
            {
                "hub_file": hub_file,
                "slug": slug,
                "title": title,
                "highlight": highlight,
                "values": " | ".join(values[:6]),
                "flags": ";".join(sorted(set(flags))),
                "verified": verified,
            }
        )
    return out


def audit_faq_generic(rows: list[dict[str, str]], hub_file: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    markers = (_FALLBACK, "本ページは学習整理用", "関連用語ページと条文")
    for row in rows:
        slug = (row.get("slug") or "").strip()
        title = (row.get("title") or "").strip()
        for i in range(1, 5):
            q = (row.get(f"faq_{i}_question") or "").strip()
            a = (row.get(f"faq_{i}_answer") or "").strip()
            if not a:
                continue
            reasons: list[str] = []
            if len(a) < MIN_FAQ_ANSWER:
                reasons.append("short")
            if any(m in a for m in markers):
                reasons.append("generic_fallback")
            for phrase in EDITORIAL_GENERIC_PHRASES:
                if phrase in a:
                    reasons.append("generic_phrase")
                    break
            if reasons:
                out.append(
                    {
                        "hub_file": hub_file,
                        "slug": slug,
                        "title": title,
                        "faq_n": str(i),
                        "question": q,
                        "answer_len": str(len(a)),
                        "reasons": ";".join(sorted(set(reasons))),
                    }
                )
    return out


def audit_thin_body(rows: list[dict[str, str]], hub_file: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    checks = {
        "article_lead": HUB_MIN_LENGTHS["article_lead"] + 10,
        "common_mistakes": HUB_MIN_LENGTHS["common_mistakes"] + 5,
        "memory_tip": HUB_MIN_LENGTHS["memory_tip"] + 5,
        "summary": HUB_MIN_LENGTHS["summary"] + 5,
    }
    for row in rows:
        slug = (row.get("slug") or "").strip()
        title = (row.get("title") or "").strip()
        for col, min_len in checks.items():
            text = (row.get(col) or "").strip()
            if text and len(text) < min_len:
                out.append(
                    {
                        "hub_file": hub_file,
                        "slug": slug,
                        "title": title,
                        "column": col,
                        "length": str(len(text)),
                        "min_recommended": str(min_len),
                    }
                )
    return out


def audit_title_similar(rows_by_file: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    entries: list[tuple[str, str, str]] = []
    for hub_file, rows in rows_by_file.items():
        for row in rows:
            title = (row.get("title") or "").strip()
            slug = (row.get("slug") or "").strip()
            if title:
                entries.append((hub_file, slug, title))

    out: list[dict[str, str]] = []
    for i, (f1, s1, t1) in enumerate(entries):
        for f2, s2, t2 in entries[i + 1 :]:
            if t1 == t2:
                out.append(
                    {
                        "hub_a": f1,
                        "slug_a": s1,
                        "hub_b": f2,
                        "slug_b": s2,
                        "title": t1,
                        "similarity": "1.000",
                        "kind": "exact",
                    }
                )
                continue
            ratio = SequenceMatcher(None, _title_key(t1), _title_key(t2)).ratio()
            if _title_key(t1) == _title_key(t2):
                continue
            if ratio >= 0.88:
                out.append(
                    {
                        "hub_a": f1,
                        "slug_a": s1,
                        "hub_b": f2,
                        "slug_b": s2,
                        "title_a": t1,
                        "title_b": t2,
                        "similarity": f"{ratio:.3f}",
                        "kind": "similar",
                    }
                )
    return out


def main() -> int:
    rows_by_file = {name: _read_rows(name) for name in HUB_FILES}
    verified_registry = _load_verified_registry()
    numbers_rows: list[dict[str, str]] = []
    faq_rows: list[dict[str, str]] = []
    thin_rows: list[dict[str, str]] = []
    batch_rows: list[dict[str, str]] = []

    for name, rows in rows_by_file.items():
        if name == "numbers.csv":
            numbers_rows.extend(audit_numbers(rows, name, verified_registry))
        faq_rows.extend(audit_faq_generic(rows, name))
        thin_rows.extend(audit_thin_body(rows, name))
        batch_rows.extend(audit_batch_suffix(rows, name))

    title_rows = audit_title_similar(rows_by_file)

    _write_csv(
        OUT / "audit_numbers.csv",
        ["hub_file", "slug", "title", "highlight", "values", "flags", "verified"],
        numbers_rows,
    )
    _write_csv(
        OUT / "audit_faq_generic.csv",
        ["hub_file", "slug", "title", "faq_n", "question", "answer_len", "reasons"],
        faq_rows,
    )
    _write_csv(
        OUT / "audit_thin_body.csv",
        ["hub_file", "slug", "title", "column", "length", "min_recommended"],
        thin_rows,
    )
    _write_csv(
        OUT / "audit_batch_suffix.csv",
        ["hub_file", "slug", "title", "field", "snippet"],
        batch_rows,
    )
    title_header = sorted({k for r in title_rows for k in r.keys()})
    _write_csv(OUT / "audit_title_dup.csv", title_header, title_rows)

    summary = {
        "numbers_rows": len(numbers_rows),
        "numbers_flagged": sum(
            1
            for r in numbers_rows
            if r.get("flags")
            and "concept_page" not in r.get("flags", "")
            and r.get("flags") != "concept_page"
        ),
        "numbers_verified_ok": sum(
            1 for r in numbers_rows if r.get("verified", "").startswith("OK")
        ),
        "numbers_verify_pending": sum(
            1
            for r in numbers_rows
            if "verify_official" in (r.get("flags") or "")
            and not r.get("verified", "").startswith("OK")
        ),
        "faq_issues": len(faq_rows),
        "batch_suffix": len(batch_rows),
        "thin_body": len(thin_rows),
        "title_dup_similar": len(title_rows),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote hub audit to {OUT}")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
