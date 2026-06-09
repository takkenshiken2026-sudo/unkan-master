#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""量産テンプレ（週次逆算・正本乱用・長大見出し連結）を読者向け prose へ整える。

  python3 tools/fix_guide_week_template_prose.py --root ~/Projects/mentalhealth-master
  python3 tools/fix_guide_week_template_prose.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.editorial_quality import is_published_guide, norm  # noqa: E402
from tools.guide_article_rules import GUIDE_MIN_SECTION_BODY  # noqa: E402
from tools.guide_content_shared import official_note_single  # noqa: E402
from tools.guide_field_prose import resolve_reader_slug_prose  # noqa: E402
from tools.guide_slug_prose import slug_link_label  # noqa: E402
from tools.strip_generic_guide_padding import strip_padding_from_text  # noqa: E402

USER_FACING_COLS = (
    "title",
    "meta_description",
    "lead",
    "user_intent",
    "action_items",
    "key_points",
    *(f"section_{n}_heading" for n in range(1, 8)),
    *(f"section_{n}_body" for n in range(1, 8)),
    *(f"faq_{n}_question" for n in range(1, 5)),
    *(f"faq_{n}_answer" for n in range(1, 5)),
)

# 6月第2週…定番 / 6月6日·残り18週… など週次逆算テンプレ文
WEEK_SENTENCE_RE = re.compile(
    r"[^。！？\n;；]*?"
    r"(?:"
    r"(?:6|7|8|9|10|11|12)月第?\d+週"
    r"|(?:6|7|8|9|10)月\d+日(?:開始|時点)?[^。;；]*?残り\d+週"
    r"|6月6日[^。;；]*?10月\d+日試験"
    r"|試験日\d+月\d+日[^。;；]*?残り\d+週"
    r"|残り\d+週を計算"
    r")"
    r"[^。！？\n;；]*?[。;；]?",
    re.I,
)
WEEK_CELL_RE = re.compile(r"(?:6|7|8|9|10|11|12)月第?\d+週")
WEEK_NEUTRAL_LABELS = ("初期", "中期", "後期", "直前", "第1回", "第2回", "第3回")

TEIBAN_SENTENCE_RE = re.compile(
    r"[^。！？\n]*?(?:定番です|のが定番|流れが定番|確認するのが定番|判断するのが定番|修正するのが定番)[^。！？\n]*?[。]",
    re.I,
)
WEEK_ONLY_SENTENCE_RE = re.compile(
    r"[^。！？\n]*?第\d+週[^。！？\n]*?(?:定番|逆算|演習|修正)[^。！？\n]*?[。]",
)

TITLE_SEIBON_SUFFIX_RE = re.compile(r"｜[^｜]*正本[^｜]*$")
TITLE_EDITOR_SUFFIX_RE = re.compile(r"｜[^｜]*(?:入口|連携|役割分担)[^｜]*$")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((\.\./[^)]+)\)")
SLUG_FROM_MD_RE = re.compile(r"\.\./([^/)]+)/?")


def _load_exam(root: Path) -> str:
    cfg = root / "site-config.json"
    if not cfg.is_file():
        return ""
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
        return norm(data.get("examName") or "")
    except json.JSONDecodeError:
        return ""


def _load_official(root: Path) -> str:
    cfg = root / "site-config.json"
    if not cfg.is_file():
        return "公式情報"
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
        return norm(data.get("officialOrganization") or "公式情報")
    except json.JSONDecodeError:
        return "公式情報"


def neutralize_week_markers(text: str) -> str:
    if not text or not WEEK_CELL_RE.search(text):
        return text
    idx = 0

    def repl(_: re.Match[str]) -> str:
        nonlocal idx
        label = WEEK_NEUTRAL_LABELS[min(idx, len(WEEK_NEUTRAL_LABELS) - 1)]
        idx += 1
        return label

    return WEEK_CELL_RE.sub(repl, text)


def strip_week_template_sentences(text: str) -> str:
    if not text:
        return text
    out = text
    prev = None
    while prev != out:
        prev = out
        out = WEEK_SENTENCE_RE.sub("", out)
        out = TEIBAN_SENTENCE_RE.sub("", out)
        out = WEEK_ONLY_SENTENCE_RE.sub("", out)
    out = neutralize_week_markers(out)
    out = re.sub(r"[ \t·]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def strip_exam_prefix(label: str, exam: str) -> str:
    t = norm(label)
    if not t or not exam:
        return t
    prefix = f"{exam}の"
    while t.startswith(prefix):
        t = t[len(prefix) :].strip()
    return t or label


def soften_seibon(text: str) -> str:
    if not text:
        return text
    out = text
    out = re.sub(r"が正本です", "を確認してください", out)
    out = re.sub(r"は正本です", "を確認してください", out)
    out = re.sub(r"の正本です", "の公式情報です", out)
    out = re.sub(r"一次情報の正本", "一次情報", out)
    out = re.sub(r"形式·数値正本", "形式·数値の整理", out)
    out = re.sub(r"数値·構造の正本", "数値·構造の整理", out)
    out = re.sub(r"学習の正本", "学習の入口", out)
    out = re.sub(r"正本は", "公式情報は", out)
    out = re.sub(r"概要正本", "概要", out)
    out = re.sub(r"正本表", "一覧表", out)
    out = re.sub(r"正本(?=[。、])", "公式情報", out)
    return out


def fix_title(title: str, exam: str) -> str:
    t = norm(title)
    if not t:
        return t
    t = TITLE_SEIBON_SUFFIX_RE.sub("", t)
    t = TITLE_EDITOR_SUFFIX_RE.sub("", t)
    t = re.sub(r"｜7章と7領域対応$", "", t)
    if exam and t.startswith(f"{exam}の"):
        short = slug_link_label(t)
        if short and len(short) < len(t):
            t = short
    return t.strip()


def shorten_md_links(text: str, slug_titles: dict[str, str], *, exam: str = "") -> str:
    if not text or not slug_titles:
        return text

    def repl(match: re.Match[str]) -> str:
        label = match.group(1)
        url = match.group(2)
        sm = SLUG_FROM_MD_RE.search(url)
        if not sm:
            return match.group(0)
        slug = sm.group(1)
        short = slug_link_label(slug_titles.get(slug, "")) or label
        short = strip_exam_prefix(short, exam)
        label_short = strip_exam_prefix(label, exam)
        best = short if len(short) <= len(label_short) else label_short
        if len(best) < len(label):
            return f"[{best}]({url})"
        return match.group(0)

    return MD_LINK_RE.sub(repl, text)


def scrub_exam_prefixed_labels(text: str, exam: str, slug_titles: dict[str, str]) -> str:
    if not text or not exam:
        return text
    out = text
    prefix = f"{exam}の"
    for slug, title in slug_titles.items():
        full_title = norm(title)
        short = slug_link_label(full_title)
        if not short:
            continue
        for candidate in (full_title, f"{prefix}{short}"):
            if candidate in out and short != candidate and len(short) < len(candidate):
                out = out.replace(candidate, short)
    return out


def fix_section_heading(heading: str, *, section_num: int, exam: str) -> str:
    h = norm(heading)
    if not h:
        return h
    if "との連携" in h and len(h) > 25:
        return "関連ガイドとの使い分け"
    if section_num == 5 and (
        (exam and h.count(exam) >= 2)
        or h.count("·") >= 3
    ):
        return "関連ガイドとの使い分け"
    if exam and h.count(exam) >= 2 and len(h) > 45:
        return slug_link_label(h.split("·")[0]) or h.split("·")[0].strip()
    return h


def fix_action_item(item: str) -> str:
    s = strip_week_template_sentences(soften_seibon(norm(item)))
    if re.search(r"第\d+週", s):
        s = re.sub(r"^[^;]*第\d+週[^;]*;?", "", s).strip("; ")
    return s.strip()


def section_min_pad(*, heading: str, topic: str, official: str) -> str:
    note = official_note_single(official)
    h = heading or topic
    if any(k in h for k in ("連携", "使い分け", "関連")):
        return (
            "関連記事は役割が重ならないよう、概要→形式→学習計画の順で読むと迷いにくくなります。"
            f"{note}"
        )
    if any(k in h for k in ("表", "チェック", "一覧", "対応")):
        return (
            f"表をノートに転記したら、演習10問で理解を確認し、"
            f"誤答は公式テキスト該当章で読み直してください。{note}"
        )
    return (
        f"演習10問を解き、解説で参照条文を公式テキストで開いて読み返してください。"
        f"{note}"
    )


def fix_prose_cell(
    text: str,
    *,
    col: str,
    slug: str,
    slug_titles: dict[str, str],
    exam: str,
    official: str,
    section_num: int = 0,
    heading: str = "",
    topic: str = "",
) -> str:
    raw = norm(text)
    if not raw:
        return raw
    out = strip_week_template_sentences(raw)
    out = soften_seibon(out)
    out = shorten_md_links(out, slug_titles, exam=exam)
    out = scrub_exam_prefixed_labels(out, exam, slug_titles)
    out = resolve_reader_slug_prose(
        out,
        slug_titles=slug_titles,
        current_slug=slug,
        link_internal=col.endswith("_body") or col in {"lead", "faq_1_answer", "faq_2_answer", "faq_3_answer"},
    )
    if col.endswith("_heading"):
        out = fix_section_heading(out, section_num=section_num, exam=exam)
    if col == "action_items":
        parts = [fix_action_item(p) for p in re.split(r"[;；]", out) if p.strip()]
        parts = [
            p
            for p in parts
            if p and not re.search(r"第\d+週", p) and not re.search(r"残り\d+週", p)
        ]
        out = ";".join(parts)
    if col.endswith("_body") and heading and len(out) < GUIDE_MIN_SECTION_BODY:
        out = f"{out.rstrip()}\n\n{section_min_pad(heading=heading, topic=topic, official=official)}".strip()
    out = strip_padding_from_text(out)
    return out.strip()


def slug_titles_from_rows(rows: list[dict[str, str]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in rows:
        slug = norm(row.get("slug"))
        title = norm(row.get("title"))
        if slug and title:
            out[slug] = title
    return out


def fix_site(root: Path, *, dry_run: bool = False) -> dict:
    guide_csv = root / "data" / "guide_articles.csv"
    if not guide_csv.is_file():
        return {"changed": 0, "error": "missing guide_articles.csv"}
    with guide_csv.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    slug_titles = slug_titles_from_rows(rows)
    exam = _load_exam(root)
    official = _load_official(root)
    changed = 0
    for row in rows:
        if not is_published_guide(row):
            continue
        slug = norm(row.get("slug"))
        topic = slug_link_label(row.get("title", "")) or slug
        before = {k: row.get(k, "") for k in row}
        if row.get("title"):
            row["title"] = fix_title(row["title"], exam)
        for col in USER_FACING_COLS:
            if col == "title":
                continue
            val = row.get(col) or ""
            if not val:
                continue
            sec_num = 0
            heading = ""
            if col.startswith("section_") and "_body" in col:
                sec_num = int(col.split("_")[1])
                heading = norm(row.get(f"section_{sec_num}_heading"))
            elif col.startswith("section_") and "_heading" in col:
                sec_num = int(col.split("_")[1])
            row[col] = fix_prose_cell(
                val,
                col=col,
                slug=slug,
                slug_titles=slug_titles,
                exam=exam,
                official=official,
                section_num=sec_num,
                heading=heading,
                topic=topic,
            )
        if any(before.get(k) != row.get(k, "") for k in row):
            changed += 1
    if changed and not dry_run:
        with guide_csv.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    return {"changed": changed, "rows": len(rows)}


def main() -> int:
    parser = argparse.ArgumentParser(description="週次逆算テンプレ prose 修復")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    stats = fix_site(args.root.resolve(), dry_run=args.dry_run)
    print(f"fix week template prose: {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
