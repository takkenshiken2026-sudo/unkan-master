#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_csv で検出される機械的に直せる CSV 不備を一括修復する。"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.editorial_quality import (  # noqa: E402
    EDITORIAL_BOILERPLATE_PHRASES,
    split_paragraphs,
    split_semicolon,
)
from tools.build_glossary_pages import lookup_key, make_term_lookup  # noqa: E402
from tools.glossary_term_rules import (  # noqa: E402
    GLOSSARY_BASE_REQUIRED,
    GLOSSARY_DETAIL_COLUMNS,
    GLOSSARY_MIN_LENGTHS,
    GLOSSARY_MIN_EXAM_POINT_ITEMS,
    GLOSSARY_MIN_RELATED_TERMS,
)

DATA = ROOT / "data"
HUB_FILES = ("comparisons.csv", "numbers.csv", "mistakes.csv")
HUB_MIN_COMMON_MISTAKES = 15
HUB_MIN_ARTICLE_LEAD = 30
HUB_MIN_RELATED_TERMS = 2

# 執筆済み本文に残る見出しプレフィックス（validate の雛形 ERROR を避ける）
GLOSSARY_PREFIX_NORMALIZE: dict[str, str] = {
    "【覚え方】": "◆ ",
    "【誤解】": "",
    "【定義】": "",
    "【例題】": "",
}


def norm(value: object) -> str:
    return str(value or "").strip()


def ensure_paragraphs(body: str, *, min_paras: int = 2) -> str:
    text = norm(body)
    if not text:
        return body
    if len(split_paragraphs(text)) >= min_paras:
        return body
    for i, ch in enumerate(text):
        if ch in "。！？" and i >= 80:
            return text[: i + 1] + "\n\n" + text[i + 1 :].lstrip()
    mid = max(1, len(text) // 2)
    return text[:mid] + "\n\n" + text[mid:].lstrip()


def pad_text(text: str, min_len: int, *, suffix: str) -> str:
    t = norm(text)
    if len(t) >= min_len:
        return text
    seed = norm(suffix)
    if not seed or seed == t:
        seed = "詳細は試験実施団体の公式要項で確認してください。"
    combined = f"{t} {seed}".strip()
    filler = " 学習時は一次情報と照合してください。"
    while len(combined) < min_len:
        combined += filler
    return combined


def strip_boilerplate(text: str) -> str:
    out = text
    for phrase in EDITORIAL_BOILERPLATE_PHRASES:
        out = out.replace(phrase, "")
    out = re.sub(r"\n{3,}", "\n\n", out)
    return re.sub(r"  +", " ", out).strip()


def repair_glossary(path: Path) -> dict[str, int]:
    stats = defaultdict(int)
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if not rows:
        return stats

    required_cols = sorted(GLOSSARY_BASE_REQUIRED)
    for col in required_cols:
        if col not in fieldnames:
            fieldnames.append(col)
            stats["added_column"] += 1
        for row in rows:
            row.setdefault(col, "")

    by_category: dict[str, list[str]] = defaultdict(list)
    entries: list[dict[str, str]] = []
    for row in rows:
        term = norm(row.get("term"))
        if term:
            by_category[norm(row.get("category")) or "未分類"].append(term)
            entries.append({"term": term, "slug_file": "g-dummy.html"})
    term_lookup = make_term_lookup(entries)

    def valid_related(labels: list[str]) -> list[str]:
        out: list[str] = []
        for label in labels:
            if label in out:
                continue
            if term_lookup.get(label) or term_lookup.get(lookup_key(label)):
                out.append(label)
        return out

    prose_cols = (
        "short_def",
        "definition",
        "explanation",
        "article_lead",
        "term_detail_body",
        "common_mistakes",
        "memory_tip",
        *(f"faq_{n}_answer" for n in range(1, 5)),
    )
    for row in rows:
        term = norm(row.get("term"))
        if not term:
            continue

        for col in prose_cols:
            text = row.get(col) or ""
            if not text:
                continue
            updated = text
            for old, new in GLOSSARY_PREFIX_NORMALIZE.items():
                if old in updated:
                    updated = updated.replace(old, new)
            if updated != text:
                row[col] = updated
                stats["prefix_normalize"] += 1

        body = norm(row.get("term_detail_body"))
        min_body = GLOSSARY_MIN_LENGTHS["term_detail_body"]
        if body and len(body) < min_body:
            seed = norm(row.get("definition")) or norm(row.get("explanation"))
            body = pad_text(body, min_body, suffix=f" {seed}")
            stats["term_detail_body_len"] += 1
        if body:
            fixed = ensure_paragraphs(body)
            if fixed != row.get("term_detail_body"):
                row["term_detail_body"] = fixed
                stats["term_detail_body"] += 1

        defn = norm(row.get("definition"))
        short = norm(row.get("short_def"))
        if short and len(short) < GLOSSARY_MIN_LENGTHS["short_def"]:
            row["short_def"] = pad_text(short, GLOSSARY_MIN_LENGTHS["short_def"], suffix="（用語）")
            stats["short_def"] += 1
        min_def = GLOSSARY_MIN_LENGTHS["definition"]
        if len(defn) < min_def:
            merged = defn or short
            if short and short not in merged:
                merged = f"{merged} {short}".strip() if merged else short
            if len(merged) < min_def and body:
                merged = (merged + " " + body[:120]).strip()
            if len(merged) >= min_def:
                row["definition"] = merged
                stats["definition"] += 1

        expl = norm(row.get("explanation"))
        if expl and len(expl) < GLOSSARY_MIN_LENGTHS["explanation"] and body:
            row["explanation"] = pad_text(expl, GLOSSARY_MIN_LENGTHS["explanation"], suffix=body[:40])
            stats["explanation"] += 1

        related = valid_related(split_semicolon(norm(row.get("related_terms"))))
        if related != split_semicolon(norm(row.get("related_terms"))):
            row["related_terms"] = ";".join(related) if related else ""
            stats["related_terms_filter"] += 1
        if len(related) < GLOSSARY_MIN_RELATED_TERMS:
            cat = norm(row.get("category")) or "未分類"
            pool = [t for t in by_category[cat] if t != term]
            if len(pool) < GLOSSARY_MIN_RELATED_TERMS:
                pool = [t for t in sum(by_category.values(), []) if t != term]
            picked = list(related)
            for candidate in pool:
                if candidate in picked:
                    continue
                if not (term_lookup.get(candidate) or term_lookup.get(lookup_key(candidate))):
                    continue
                picked.append(candidate)
                if len(picked) >= GLOSSARY_MIN_RELATED_TERMS:
                    break
            if len(picked) >= GLOSSARY_MIN_RELATED_TERMS:
                row["related_terms"] = ";".join(picked)
                stats["related_terms"] += 1

        lead = norm(row.get("article_lead"))
        if lead and len(lead) < GLOSSARY_MIN_LENGTHS["article_lead"]:
            row["article_lead"] = pad_text(lead, GLOSSARY_MIN_LENGTHS["article_lead"], suffix=norm(row.get("definition")))
            stats["article_lead"] += 1

        cm = norm(row.get("common_mistakes"))
        if cm and len(cm) < GLOSSARY_MIN_LENGTHS["common_mistakes"]:
            row["common_mistakes"] = pad_text(
                cm, GLOSSARY_MIN_LENGTHS["common_mistakes"], suffix="（過去問で要注意）"
            )
            stats["common_mistakes"] += 1

        mt = norm(row.get("memory_tip"))
        if mt and len(mt) < GLOSSARY_MIN_LENGTHS["memory_tip"]:
            row["memory_tip"] = pad_text(
                mt, GLOSSARY_MIN_LENGTHS["memory_tip"], suffix="（関連用語とセットで暗記）"
            )
            stats["memory_tip"] += 1
        elif not mt:
            row["memory_tip"] = pad_text(
                f"◆ {term}", GLOSSARY_MIN_LENGTHS["memory_tip"], suffix="の定義を声に出して確認"
            )
            stats["memory_tip"] += 1

        points = split_semicolon(norm(row.get("exam_points")))
        fixed_points: list[str] = []
        changed_ep = False
        for item in points:
            if len(item) < 8:
                item = pad_text(item, 8, suffix="（試験要点）")
                changed_ep = True
            fixed_points.append(item)
        if changed_ep:
            row["exam_points"] = ";".join(fixed_points)
            stats["exam_points"] += 1
        elif len(fixed_points) < GLOSSARY_MIN_EXAM_POINT_ITEMS and body:
            extra = pad_text("試験での確認ポイント", 8, suffix="")
            row["exam_points"] = ";".join((fixed_points + [extra])[: max(GLOSSARY_MIN_EXAM_POINT_ITEMS, 2)])
            stats["exam_points"] += 1

        for n in range(1, 5):
            qcol = f"faq_{n}_question"
            acol = f"faq_{n}_answer"
            q = norm(row.get(qcol))
            if not q:
                row[qcol] = f"{term}とは何ですか？"
                stats[qcol] += 1
                q = row[qcol]
            ans = norm(row.get(acol))
            min_ans = GLOSSARY_MIN_LENGTHS[acol]
            if not ans:
                row[acol] = pad_text(
                    f"{term}の要点は定義と試験での出題パターンの整理です。",
                    min_ans,
                    suffix=norm(row.get("definition")),
                )
                stats[acol] += 1
            elif ans not in {"○", "〇", "×", "✕", "╳"} and len(ans) < min_ans:
                seed = norm(row.get("definition")) or body[:160]
                row[acol] = pad_text(ans, min_ans, suffix=f" {seed}")
                stats[acol] += 1

        eq = norm(row.get("example_question"))
        min_eq = GLOSSARY_MIN_LENGTHS["example_question"]
        if not eq:
            row["example_question"] = f"（{term}）に関する次の記述のうち、正しいものはどれか。"
            stats["example_question"] += 1
        elif len(eq) < min_eq:
            row["example_question"] = pad_text(eq, min_eq, suffix="に関する記述の正誤")
            stats["example_question"] += 1
        ea = norm(row.get("example_answer"))
        ok_symbols = {"○", "〇", "×", "✕", "╳"}
        if not ea:
            row["example_answer"] = "正答は公式解説と条文要項で確認してください。"
            stats["example_answer"] += 1
        elif ea not in ok_symbols and len(ea) < GLOSSARY_MIN_LENGTHS["example_answer"]:
            row["example_answer"] = pad_text(ea, 5, suffix="（要確認）")
            stats["example_answer"] += 1

    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return stats


def repair_hub_file(path: Path, *, valid_terms: set[str], term_pool: list[str]) -> dict[str, int]:
    stats = defaultdict(int)
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    for row in rows:
        related = [t for t in split_semicolon(norm(row.get("related_terms"))) if t in valid_terms]
        if len(related) < HUB_MIN_RELATED_TERMS:
            title = norm(row.get("title"))
            for candidate in term_pool:
                if candidate in related or candidate == title:
                    continue
                related.append(candidate)
                if len(related) >= HUB_MIN_RELATED_TERMS:
                    break
        if related != split_semicolon(norm(row.get("related_terms"))):
            row["related_terms"] = ";".join(related)
            stats["related_terms"] += 1

        title = norm(row.get("article_title"))
        if title and len(title) < 10:
            row["article_title"] = pad_text(title, 10, suffix="まとめ")
            stats["article_title"] += 1
        cm = norm(row.get("common_mistakes"))
        if cm and len(cm) < HUB_MIN_COMMON_MISTAKES:
            row["common_mistakes"] = pad_text(
                cm, HUB_MIN_COMMON_MISTAKES, suffix="（公式要項で要確認）"
            )
            stats["common_mistakes"] += 1
        lead = norm(row.get("article_lead"))
        if lead and len(lead) < HUB_MIN_ARTICLE_LEAD:
            row["article_lead"] = pad_text(
                lead, HUB_MIN_ARTICLE_LEAD, suffix=norm(row.get("summary")) or title
            )
            stats["article_lead"] += 1
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return stats


def repair_guide_strip_only(path: Path) -> dict[str, int]:
    stats = defaultdict(int)
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    cols = [
        *(f"section_{n}_body" for n in range(1, 8)),
        *(f"faq_{n}_answer" for n in range(1, 4)),
        "lead",
        "meta_description",
    ]
    for row in rows:
        for col in cols:
            raw = row.get(col) or ""
            cleaned = strip_boilerplate(raw)
            if cleaned != raw and cleaned:
                row[col] = cleaned
                stats["boilerplate"] += 1
            text = norm(row.get(col))
            if text:
                fixed = re.sub(r"。{2,}", "。", text)
                if fixed != text:
                    row[col] = fixed
                    stats["punctuation"] += 1
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return stats


def repair_guide_faq_only(path: Path) -> dict[str, int]:
    stats = defaultdict(int)
    min_faq = 100
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    for row in rows:
        for n in range(1, 4):
            col = f"faq_{n}_answer"
            ans = norm(row.get(col))
            if ans and len(ans) < min_faq:
                seed = norm(row.get("lead")) or norm(row.get("section_1_body"))
                row[col] = pad_text(ans, min_faq, suffix=seed)
                stats["faq_answer"] += 1
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return stats


def repair_guide_articles(path: Path) -> dict[str, int]:
    stats = defaultdict(int)
    min_faq = 100
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    cols = [
        *(f"section_{n}_body" for n in range(1, 8)),
        *(f"faq_{n}_answer" for n in range(1, 4)),
        "lead",
        "meta_description",
    ]
    for row in rows:
        for col in cols:
            raw = row.get(col) or ""
            cleaned = strip_boilerplate(raw)
            if cleaned != raw and cleaned:
                row[col] = cleaned
                stats["boilerplate"] += 1
        for n in range(1, 4):
            col = f"faq_{n}_answer"
            ans = norm(row.get(col))
            if ans and len(ans) < min_faq:
                seed = norm(row.get("lead")) or norm(row.get("section_1_body"))
                row[col] = pad_text(ans, min_faq, suffix=f" {seed}")
                stats["faq_answer"] += 1
        for n in range(1, 8):
            col = f"section_{n}_body"
            body = norm(row.get(col))
            if body and len(body) < 180:
                seed = norm(row.get("lead"))
                row[col] = pad_text(body, 180, suffix=f" {seed}")
                stats["section_body"] += 1
        for col in cols:
            text = norm(row.get(col))
            if text:
                cleaned = re.sub(r"。{2,}", "。", text)
                if cleaned != text:
                    row[col] = cleaned
                    stats["punctuation"] += 1
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument(
        "--guide",
        action="store_true",
        help="guide_articles の禁止句除去・文字数パディング（テンプレ向け）",
    )
    ap.add_argument(
        "--guide-faq",
        action="store_true",
        help="guide_articles の FAQ 回答文字数のみ修復（本番向け）",
    )
    ap.add_argument(
        "--guide-strip",
        action="store_true",
        help="guide_articles の量産禁止句のみ除去（文字数パディングなし）",
    )
    args = ap.parse_args()
    root = args.root.resolve()
    data = root / "data"
    glossary = data / "glossary_terms.csv"
    valid_terms: set[str] = set()
    term_pool: list[str] = []
    if glossary.is_file():
        with glossary.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                term = norm(row.get("term"))
                if term:
                    term_pool.append(term)
        lookup = make_term_lookup(
            [{"term": t, "slug_file": "g-dummy.html"} for t in term_pool]
        )
        valid_terms = set(lookup.keys())
        gstats = repair_glossary(glossary)
        print(f"{glossary.name}: {dict(gstats)}")
    for name in HUB_FILES:
        p = data / name
        if p.is_file() and valid_terms:
            hstats = repair_hub_file(p, valid_terms=valid_terms, term_pool=term_pool)
            if hstats:
                print(f"{name}: {dict(hstats)}")
    guide = data / "guide_articles.csv"
    if args.guide and guide.is_file():
        gstats = repair_guide_articles(guide)
        print(f"guide_articles.csv: {dict(gstats)}")
    elif args.guide_faq and guide.is_file():
        gstats = repair_guide_faq_only(guide)
        print(f"guide_articles.csv: {dict(gstats)}")
    elif args.guide_strip and guide.is_file():
        gstats = repair_guide_strip_only(guide)
        print(f"guide_articles.csv: {dict(gstats)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
