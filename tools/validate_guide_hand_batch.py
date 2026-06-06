#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""手書き batch（REWRITES）の apply 前チェック。"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.apply_guide_rewrite_batch import load_rewrites_module  # noqa: E402
from tools.build_article_pages import sanitize_guide_text  # noqa: E402
from tools.editorial_quality import norm  # noqa: E402
from tools.guide_article_rules import GUIDE_MIN_FAQ_ANSWER, GUIDE_MIN_SECTION_BODY  # noqa: E402
from tools.guide_prose_patterns import scan_prose_text  # noqa: E402
from tools.guide_rewrite_rules import is_affiliate_row, rewrite_forbidden_hits  # noqa: E402
from tools.guide_concrete_rewrite_rules import validate_concrete_rewrite  # noqa: E402
from tools.guide_rewrite_quality import is_auto_prose_text, revision_is_hand  # noqa: E402
from tools.strip_generic_guide_padding import strip_padding_from_text  # noqa: E402

REQUIRED_KEYS = (
    "title",
    "lead",
    "meta_description",
    "user_intent",
    "action_items",
)
SECTION_HEADING_KEYS = tuple(f"section_{n}_heading" for n in range(1, 6))
SECTION_BODY_KEYS = tuple(f"section_{n}_body" for n in range(1, 6))
FAQ_Q_KEYS = tuple(f"faq_{n}_question" for n in range(1, 4))
FAQ_A_KEYS = tuple(f"faq_{n}_answer" for n in range(1, 4))
TITLE_DUP_EXAM_RE = re.compile(r"試験の試験[のと]|試験試験")


def _visible_body(slug: str, text: str) -> str:
    return sanitize_guide_text(strip_padding_from_text(norm(text)), slug)


def _batch_duplicate_heading_errors(rewrites: dict[str, dict[str, str]]) -> list[str]:
    """5本 batch で同一見出しが4回以上 → テンプレ使い回し疑い。"""
    errors: list[str] = []
    if len(rewrites) < 5:
        return errors
    for n in range(1, 6):
        hcol = f"section_{n}_heading"
        headings = [norm(p.get(hcol)) for p in rewrites.values() if norm(p.get(hcol))]
        for heading, count in Counter(headings).items():
            if count >= 4:
                errors.append(
                    f"batch: {hcol} duplicated {count}x across slugs ({heading[:36]}…)"
                )
    return errors


def validate_rewrites(rewrites: dict[str, dict[str, str]], *, root: Path) -> list[str]:
    errors: list[str] = []
    errors.extend(_batch_duplicate_heading_errors(rewrites))
    try:
        from tools.fix_guide_duplicate_bodies import load_site_lib

        lib = load_site_lib(root)
        exam = getattr(lib, "EXAM", "")
        exam_short = getattr(lib, "EXAM_SHORT", "")
    except Exception:
        exam, exam_short = "", ""

    for slug, patch in rewrites.items():
        prefix = f"{slug}:"
        if slug.startswith("affiliate-") or is_affiliate_row({"tags": patch.get("tags", ""), "slug": slug}):
            errors.append(
                f"{prefix} アフィリエイト slug — 手書き batch 対象外。"
                f" docs/affiliate/affiliate-article-rules.md を参照"
            )
            continue
        for key in REQUIRED_KEYS:
            if not norm(patch.get(key)):
                errors.append(f"{prefix} missing {key}")
        for key in SECTION_BODY_KEYS + FAQ_A_KEYS:
            val = patch.get(key)
            if isinstance(val, (tuple, list)):
                errors.append(
                    f"{prefix} {key} is tuple/list — use implicit string concat, not comma-separated ()"
                )

        title = norm(patch.get("title"))
        if title and TITLE_DUP_EXAM_RE.search(title):
            errors.append(f"{prefix} title has duplicated 試験 wording: {title[:40]}")

        lead = norm(patch.get("lead"))
        if lead and len(lead) < 80:
            errors.append(f"{prefix} lead too short ({len(lead)} chars, need 80+)")

        questions = [norm(patch.get(k)) for k in FAQ_Q_KEYS if norm(patch.get(k))]
        if len(questions) != len(set(questions)):
            errors.append(f"{prefix} duplicate faq_*_question")

        for n in range(1, 6):
            hcol = f"section_{n}_heading"
            bcol = f"section_{n}_body"
            heading = norm(patch.get(hcol))
            body = norm(patch.get(bcol))
            if body and not heading:
                errors.append(f"{prefix} {bcol} set but {hcol} missing")
            if heading and not body:
                errors.append(f"{prefix} {hcol} set but {bcol} missing")
            if body:
                visible = _visible_body(slug, body)
                if len(visible) < GUIDE_MIN_SECTION_BODY:
                    errors.append(
                        f"{prefix} {bcol} too short after sanitize ({len(visible)} chars, need {GUIDE_MIN_SECTION_BODY}+)"
                    )
                for phrase in rewrite_forbidden_hits(visible):
                    errors.append(f"{prefix} {bcol} forbidden phrase: {phrase[:32]}…")
                for hit in scan_prose_text(visible, column=bcol, exam=exam, exam_short=exam_short):
                    errors.append(f"{prefix} {bcol} prose hit: {hit.pattern}")

        for acol in FAQ_A_KEYS:
            answer = norm(patch.get(acol))
            if not answer:
                continue
            visible = _visible_body(slug, answer)
            if len(visible) < GUIDE_MIN_FAQ_ANSWER:
                errors.append(
                    f"{prefix} {acol} too short ({len(visible)} chars, need {GUIDE_MIN_FAQ_ANSWER}+)"
                )

        prose_cols = list(REQUIRED_KEYS) + list(SECTION_BODY_KEYS) + list(FAQ_A_KEYS)
        for col in prose_cols:
            text = norm(patch.get(col))
            if not text:
                continue
            visible = _visible_body(slug, text)
            for phrase in rewrite_forbidden_hits(visible):
                errors.append(f"{prefix} {col} forbidden: {phrase[:32]}…")

        if revision_is_hand(patch):
            combined_bodies = " ".join(norm(patch.get(k)) for k in SECTION_BODY_KEYS if norm(patch.get(k)))
            if is_auto_prose_text(combined_bodies):
                errors.append(f"{prefix} section bodies contain auto-prose signatures (not hand quality)")

        errors.extend(validate_concrete_rewrite(slug, patch))

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="手書き batch REWRITES の apply 前検証")
    ap.add_argument("--batch", type=Path, required=True)
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args()
    mod = load_rewrites_module(args.batch.resolve())
    rewrites = getattr(mod, "REWRITES")
    errors = validate_rewrites(rewrites, root=args.root.resolve())
    print(f"validate_guide_hand_batch: {args.batch.name} slugs={len(rewrites)} errors={len(errors)}")
    for msg in errors[:40]:
        print(f"  ERROR {msg}")
    if len(errors) > 40:
        print(f"  ... and {len(errors) - 40} more")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
