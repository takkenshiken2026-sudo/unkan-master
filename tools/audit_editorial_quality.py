#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験ガイド・用語詳細の編集品質監査（専門家・プロライター水準）."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_glossary_pages import make_term_lookup  # noqa: E402
from tools.glossary_term_rules import check_glossary_row  # noqa: E402
from tools.guide_article_rules import check_guide_row  # noqa: E402
from tools.editorial_quality import EditorialIssue  # noqa: E402

GUIDE_CSV = ROOT / "data" / "guide_articles.csv"
GLOSSARY_CSV = ROOT / "data" / "glossary_terms.csv"


def audit_guide_cross_duplicates(rows: list[dict[str, str]]) -> list[EditorialIssue]:
    """複数記事で同一 section 本文が使い回されていないか（published のみ）。"""
    from tools.editorial_quality import is_published_guide, norm

    body_to_slugs: dict[str, list[str]] = {}
    for row in rows:
        if not is_published_guide(row):
            continue
        slug = norm(row.get("slug"))
        if not slug:
            continue
        for n in range(1, 8):
            body = norm(row.get(f"section_{n}_body"))
            if len(body) < 120:
                continue
            body_to_slugs.setdefault(body, []).append(slug)
    issues: list[EditorialIssue] = []
    for body, slugs in body_to_slugs.items():
        if len(slugs) < 2:
            continue
        issues.append(
            EditorialIssue(
                "ERROR",
                "section_*_body",
                f"同一本文が {len(slugs)} 記事で使い回されています（{', '.join(slugs[:4])}{'…' if len(slugs) > 4 else ''}）。各記事オリジナルに書き直してください",
            )
        )
    return issues


def audit_guides(*, strict: bool) -> tuple[int, int]:
    errors = warns = 0
    if not GUIDE_CSV.is_file():
        print(f"missing: {GUIDE_CSV}", file=sys.stderr)
        return 1, 0
    rows = list(csv.DictReader(GUIDE_CSV.open(encoding="utf-8-sig")))
    slugs = {r.get("slug", "").strip() for r in rows if r.get("slug", "").strip()}
    for idx, row in enumerate(rows, start=2):
        slug = row.get("slug", "").strip()
        if not slug:
            continue
        for issue in check_guide_row(row, slug_set=slugs, line=idx):
            msg = f"guide_articles.csv:{idx} ({slug}) [{issue.column}] {issue.message}"
            if issue.level == "ERROR":
                errors += 1
                print(msg, file=sys.stderr)
            else:
                warns += 1
                if strict:
                    print(msg, file=sys.stderr)
                else:
                    print(msg)
    for issue in audit_guide_cross_duplicates(rows):
        msg = f"guide_articles.csv [cross] [{issue.column}] {issue.message}"
        errors += 1
        print(msg, file=sys.stderr)
    return errors, warns


def audit_glossary(*, strict: bool) -> tuple[int, int]:
    errors = warns = 0
    if not GLOSSARY_CSV.is_file():
        print(f"missing: {GLOSSARY_CSV}", file=sys.stderr)
        return 1, 0
    rows = list(csv.DictReader(GLOSSARY_CSV.open(encoding="utf-8-sig")))
    entries = [{"term": r["term"].strip(), "slug_file": "g-dummy.html"} for r in rows if r.get("term", "").strip()]
    term_lookup = make_term_lookup(entries)
    for idx, row in enumerate(rows, start=2):
        term = row.get("term", "").strip()
        if not term:
            continue
        for issue in check_glossary_row(row, term_lookup=term_lookup, line=idx):
            msg = f"glossary_terms.csv:{idx} ({term}) {issue.message}"
            if issue.level == "ERROR":
                errors += 1
                print(msg, file=sys.stderr)
            else:
                warns += 1
                if strict:
                    print(msg, file=sys.stderr)
                else:
                    print(msg)
    return errors, warns


def main() -> int:
    parser = argparse.ArgumentParser(description="編集品質監査（試験ガイド・用語詳細）")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="WARN も含めて失敗扱い（本番公開前のゲート用）",
    )
    args = parser.parse_args()

    ge, gw = audit_guides(strict=args.strict)
    te, tw = audit_glossary(strict=args.strict)
    errors = ge + te
    warns = gw + tw

    print(
        f"\n編集品質: ERROR {errors} / WARN {warns}"
        + (" (--strict: WARN も失敗)" if args.strict else "")
    )
    if errors:
        return 1
    if args.strict and warns:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
