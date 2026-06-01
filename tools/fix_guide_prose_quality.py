#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ガイド CSV の抽象・不自然 prose を機械修復する。"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.editorial_quality import is_published_guide, norm  # noqa: E402
from tools.fix_guide_duplicate_bodies import load_site_lib  # noqa: E402
from tools.guide_content_shared import (  # noqa: E402
    action_items_prose,
    faq_official_verify_answer,
    section_body_min_filler,
    user_intent_prose,
)
from tools.guide_prose_patterns import (  # noqa: E402
    BROKEN_FALLBACK_RE,
    FAQ_ARROW_RE,
    GENERIC_ACTION_RE,
    SUBJECT_BOILER_RE,
    TAIL_SECTION_REF_RE,
    VAGUE_USER_INTENT_RE,
    scan_prose_text,
)

TAIL_SENTENCE_RE = re.compile(
    r"\n?\s*「[^」]+」の詳細は[^。]+(?:最新要項|演習解説)[^。]*(?:確認|照合)[^。]*。\s*"
)
BROKEN_POINTS_RE = re.compile(r"の要点を。\s*")
FAQ_ARROW_FIX_RE = re.compile(r"「([^」]+)」→\s*")

GENERIC_STUDY_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("リンクか。ら混同語", "リンクから混同しやすい語"),
    ("混同語を1周", "混同しやすい語を比較表で整理"),
    ("分野タグ付き問題を10問", "関連する設問を10問"),
    ("分野タグ付きの演習問題", "関連する演習問題"),
    ("分野タグ付き演習", "関連する演習"),
    ("似た論点を1周", "似た論点を比較表で整理"),
)


def repair_split_artifacts(text: str) -> str:
    if not text:
        return text
    out = text
    out = re.sub(r"を開き。\s*主体", "を開き、主体", out)
    out = re.sub(r"メモし。\s*用語", "メモし、用語", out)
    out = re.sub(r"確認\s*②", "確認 ②", out)
    return out


def repair_generic_study_phrases(text: str) -> str:
    if not text:
        return text
    out = repair_split_artifacts(repair_broken_fallback(text))
    for old, new in GENERIC_STUDY_REPLACEMENTS:
        out = out.replace(old, new)
    return out


def repair_broken_fallback(text: str) -> str:
    if not text:
        return text
    out = BROKEN_POINTS_RE.sub("の要点は、", text)
    out = re.sub(r"要点を。\s*", "要点は、", out)
    return out


def strip_meta_section_tails(text: str) -> str:
    if not text:
        return text
    prev = None
    out = text
    while prev != out:
        prev = out
        out = TAIL_SENTENCE_RE.sub("\n\n", out)
    return out.rstrip()


def repair_faq_answer(text: str, *, question: str, topic: str, lib) -> str:
    out = norm(text)
    if not out:
        return out
    out = FAQ_ARROW_FIX_RE.sub(r"「\1」については、", out)
    out = re.sub(r"FAQ\d+「」→\s*", "", out)
    if SUBJECT_BOILER_RE.search(out):
        out = faq_official_verify_answer(
            question,
            topic,
            getattr(lib, "EXAM", ""),
            getattr(lib, "EXAM_SHORT", ""),
            getattr(lib, "OFFICIAL", "試験実施団体（公式）"),
        )
    return repair_broken_fallback(out)


def repair_section_body(text: str, *, heading: str, topic: str, official: str) -> str:
    out = strip_meta_section_tails(repair_generic_study_phrases(norm(text)))
    if TAIL_SECTION_REF_RE.search(out):
        out = strip_meta_section_tails(out)
    visible = out
    if len(visible) < 180:
        filler = section_body_min_filler(heading, topic, official)
        if filler not in visible:
            out = f"{visible}\n\n{filler}".strip()
    return out


def repair_user_intent(text: str, *, topic: str, genre: str, lib) -> str:
    raw = norm(text)
    if not raw or not VAGUE_USER_INTENT_RE.search(raw):
        return raw
    return user_intent_prose(
        topic,
        getattr(lib, "EXAM", ""),
        getattr(lib, "EXAM_SHORT", ""),
        getattr(lib, "OFFICIAL", "試験実施団体（公式）"),
        genre,
    )


def repair_action_items(text: str, *, topic: str, slug: str, genre: str, lib) -> str:
    raw = norm(text)
    if not raw:
        return raw
    cleaned = repair_generic_study_phrases(raw)
    if GENERIC_ACTION_RE.search(cleaned) or cleaned != raw:
        return action_items_prose(
            topic,
            getattr(lib, "EXAM", ""),
            getattr(lib, "EXAM_SHORT", ""),
            getattr(lib, "OFFICIAL", "試験実施団体（公式）"),
            slug,
            genre,
        )
    return cleaned


def fix_guide_row(row: dict[str, str], *, lib, official: str) -> bool:
    from tools.guide_coherence_rules import short_topic_from_title  # noqa: E402
    from tools.guide_topic_normalize import scrub_exam_duplication, strip_exam_prefix  # noqa: E402

    if not is_published_guide(row):
        return False
    slug = norm(row.get("slug"))
    title = norm(row.get("title"))
    genre = norm(row.get("genre"))
    topic = getattr(lib, "topic_from_row", lambda r: short_topic_from_title(title))(row)
    if not topic:
        topic = short_topic_from_title(title)
    topic = strip_exam_prefix(topic, getattr(lib, "EXAM", ""), getattr(lib, "EXAM_SHORT", ""))
    before = {k: row.get(k, "") for k in row}

    ui = repair_user_intent(norm(row.get("user_intent")), topic=topic, genre=genre, lib=lib)
    if ui != norm(row.get("user_intent")):
        row["user_intent"] = ui

    ai = repair_action_items(
        norm(row.get("action_items")),
        topic=topic,
        slug=slug,
        genre=genre,
        lib=lib,
    )
    if ai != norm(row.get("action_items")):
        row["action_items"] = ai

    for idx in range(1, 8):
        hcol = f"section_{idx}_heading"
        bcol = f"section_{idx}_body"
        heading = norm(row.get(hcol))
        body = norm(row.get(bcol))
        if not heading or not body:
            continue
        fixed = repair_section_body(body, heading=heading, topic=topic, official=official)
        if fixed != body:
            row[bcol] = fixed

    for idx in range(1, 5):
        qcol = f"faq_{idx}_question"
        acol = f"faq_{idx}_answer"
        question = norm(row.get(qcol))
        answer = norm(row.get(acol))
        if not answer:
            continue
        fixed = repair_faq_answer(answer, question=question, topic=topic, lib=lib)
        if fixed != answer:
            row[acol] = fixed

    exam = getattr(lib, "EXAM", "")
    exam_short = getattr(lib, "EXAM_SHORT", "")
    prose_cols = ["lead", "user_intent", "meta_description", "action_items"]
    prose_cols.extend(f"section_{n}_body" for n in range(1, 8))
    prose_cols.extend(f"faq_{n}_answer" for n in range(1, 5))
    for col in prose_cols:
        text = norm(row.get(col))
        if not text:
            continue
        fixed = repair_generic_study_phrases(text)
        if col.startswith("faq"):
            fixed = repair_faq_answer(fixed, question=norm(row.get(col.replace("answer", "question"))), topic=topic, lib=lib)
        cleaned = scrub_exam_duplication(fixed, exam, exam_short)
        if cleaned != text:
            row[col] = cleaned

    return any(before.get(k) != row.get(k, "") for k in row)


def fix_site(root: Path, *, dry_run: bool = False) -> dict:
    guide_csv = root / "data" / "guide_articles.csv"
    if not guide_csv.is_file():
        return {"changed": 0, "error": "missing guide_articles.csv"}
    lib = load_site_lib(root)
    official = getattr(lib, "OFFICIAL", "試験実施団体（公式）")
    with guide_csv.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    changed = sum(1 for row in rows if fix_guide_row(row, lib=lib, official=official))
    if not dry_run and changed:
        with guide_csv.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    return {"changed": changed, "rows": len(rows)}


def main() -> int:
    parser = argparse.ArgumentParser(description="ガイド prose 品質の CSV 修復")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    stats = fix_site(args.root.resolve(), dry_run=args.dry_run)
    print(f"prose quality fix: {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
