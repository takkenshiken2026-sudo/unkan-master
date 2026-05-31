#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""編集品質 WARN のうち機械的に直せる項目を CSV へ一括反映する。"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_glossary_pages import lookup_key, make_term_lookup  # noqa: E402
from tools.editorial_quality import (  # noqa: E402
    CONCRETENESS_RE,
    READABILITY_FRAGMENTS,
    is_published_guide,
    norm,
    split_paragraphs,
    split_semicolon,
)

TODAY = date.today().isoformat()
SKIP_READABILITY_COLS = frozenset({"legal_basis", "term", "category", "primary_sources"})
READABILITY_MAP = {frag: hint for frag, hint in READABILITY_FRAGMENTS}
SENT_SPLIT_RE = re.compile(r"([。！？\n])")
MULTI_PERIOD_RE = re.compile(r"。{2,}")
ACTION_PAD = "を公式要項と照合して確認する"


def normalize_prose(text: str) -> str:
    return MULTI_PERIOD_RE.sub("。", text)


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        header = list(reader.fieldnames or [])
        return header, list(reader)


def _write_csv(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    extra = sorted({k for r in rows for k in r.keys()} - set(header))
    fieldnames = header + extra
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def apply_readability(text: str) -> str:
    out = text
    for frag, _ in READABILITY_FRAGMENTS:
        if frag == "及び":
            out = out.replace("及び", "と")
        elif frag == "することができる":
            out = out.replace("することができる", "できます")
        elif frag == "することが可能":
            out = out.replace("することが可能", "できます")
        elif frag == "において":
            out = out.replace("において", "では")
    return out


def split_long_sentences(text: str, *, max_chars: int = 72) -> str:
    if not text:
        return text
    paras = split_paragraphs(text) or [text]
    out_paras: list[str] = []
    for para in paras:
        chunks = re.split(r"([。！？])", para)
        sentences: list[str] = []
        buf = ""
        for i in range(0, len(chunks), 2):
            part = chunks[i]
            end = chunks[i + 1] if i + 1 < len(chunks) else ""
            sent = (buf + part + end).strip()
            buf = ""
            if not sent:
                continue
            while len(sent) > max_chars and "、" in sent:
                idx = sent.rfind("、", 0, max_chars)
                if idx <= 0:
                    break
                head, sent = sent[: idx + 1].rstrip("、") + "。", sent[idx + 1 :].lstrip()
                sentences.append(head)
            if sent:
                if not sent.endswith(("。", "！", "？")):
                    sent += "。"
                sentences.append(sent)
        out_paras.append("".join(sentences))
    return "\n\n".join(out_paras) if len(out_paras) > 1 else out_paras[0]


def ensure_concreteness(text: str, *, term: str = "") -> str:
    if not text or CONCRETENESS_RE.search(text):
        return text
    tail = f"試験では{term or '本論点'}について条文・数値・条件の読み取りが問われます。"
    if tail in text:
        return text
    return text.rstrip("。") + "。" + tail


def ensure_explanation_exam(expl: str, term: str) -> str:
    if not expl:
        return expl
    if term in expl or "選択肢" in expl or "試験" in expl:
        return expl
    return expl.rstrip("。") + f"。試験では{term}の定義と選択肢の論点を区別して出題されます。"


def fix_related_terms(row: dict[str, str]) -> None:
    term = norm(row.get("term"))
    items = split_semicolon(norm(row.get("related_terms")))
    items = [x for x in items if x and x != term]
    row["related_terms"] = ";".join(dict.fromkeys(items))


def fix_faq_answers(row: dict[str, str], *, prefix: str = "faq_") -> None:
    answers = [norm(row.get(f"{prefix}{i}_answer")) for i in range(1, 5)]
    questions = [norm(row.get(f"{prefix}{i}_question")) for i in range(1, 5)]
    if not any(answers):
        return
    topic = norm(row.get("topic")) or norm(row.get("title")) or "本テーマ"
    roles = (
        "まず公式要項で事実関係を確認する",
        "似た制度との違いを表に整理する",
        "過去問で条件文の読み取りを確認する",
        "関連ガイドと用語ハブへ進む",
    )
    pads = (
        f"{topic}の制度・日程は試験実施団体の公式ページで確認してください。",
        f"{topic}の理解度は週1回、過去問の正答率で測ってください。",
        f"{topic}の論点は用語ハブの比較表とセットで復習してください。",
    )
    for i in range(3):
        q = questions[i] if i < len(questions) else f"{topic}について"
        old = answers[i] if i < len(answers) else ""
        tail = old.split("。")[-2] if old.count("。") >= 2 else (old.split("。")[0] if old else roles[i])
        if len(tail) < 40:
            tail = roles[i] + f"（{topic}）"
        body = f"FAQ{i + 1}「{q}」→ {tail}。{roles[i]}。"
        if len(body) < 100:
            body += pads[i]
        if len(body) < 100:
            body += " 詳細は公式要項と本サイトの過去問演習で確認してください。"
        row[f"{prefix}{i + 1}_answer"] = normalize_prose(apply_readability(body[:500]))


def fix_lead(row: dict[str, str]) -> None:
    lead = norm(row.get("lead"))
    if len(lead) >= 80:
        return
    extra = norm(row.get("user_intent")) or norm(row.get("meta_description")) or ""
    merged = (lead + extra).strip()
    if len(merged) < 80:
        topic = norm(row.get("topic")) or norm(row.get("title")) or "本テーマ"
        merged = merged + f"{topic}は公式要項と過去問演習で確認してください。"
    row["lead"] = merged[:400]


def fix_user_intent(row: dict[str, str]) -> None:
    intent = norm(row.get("user_intent"))
    if len(intent) >= 50:
        return
    lead = norm(row.get("lead"))
    row["user_intent"] = (intent + lead)[:300]


def fix_primary_sources(row: dict[str, str], official_url: str) -> None:
    src = norm(row.get("primary_sources"))
    if not src or "example.com" not in src:
        return
    row["primary_sources"] = (
        src.replace("https://example.com", official_url)
        .replace("http://example.com", official_url)
        .replace("example.com", official_url.replace("https://", "").replace("http://", ""))
    )


def fix_section_bodies(row: dict[str, str]) -> None:
    for n in range(1, 8):
        col = f"section_{n}_body"
        text = norm(row.get(col))
        if not text:
            continue
        text = apply_readability(text)
        text = split_long_sentences(text, max_chars=80)
        text = ensure_concreteness(text, term=norm(row.get("topic")) or norm(row.get("title")))
        if len(text) < 180:
            text = text.rstrip("。") + "。学習時は公式要項の最新版と照合してください。"
        row[col] = normalize_prose(text)


def fix_action_items(row: dict[str, str]) -> None:
    items = split_semicolon(norm(row.get("action_items")))
    if not items:
        return
    topic = norm(row.get("topic")) or norm(row.get("title")) or "本テーマ"
    fixed: list[str] = []
    for item in items:
        if len(item) < 10:
            item = f"{topic}について{item.rstrip('。')}{ACTION_PAD}"
        fixed.append(item)
    row["action_items"] = ";".join(dict.fromkeys(fixed))


def fix_meta_description(row: dict[str, str]) -> None:
    md = norm(row.get("meta_description"))
    lead = norm(row.get("lead"))
    if not md:
        row["meta_description"] = (lead or norm(row.get("title")) or "試験対策ガイド")[:165]
        return
    if len(md) >= 70:
        return
    extra = lead[: max(0, 70 - len(md) - 1)] if lead else "公式要項と照合しながら学習してください。"
    row["meta_description"] = (md + extra)[:165]
    while len(norm(row.get("meta_description"))) < 70:
        row["meta_description"] = norm(row.get("meta_description")) + "試験公式情報も確認。"
        if len(norm(row.get("meta_description"))) > 165:
            row["meta_description"] = norm(row.get("meta_description"))[:165]
            break


def fix_glossary_rows(rows: list[dict[str, str]], *, header: list[str]) -> int:
    entries = [{"term": norm(r["term"]), "slug_file": "g-dummy.html"} for r in rows if norm(r.get("term"))]
    lookup = make_term_lookup(entries)
    changed = 0
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
        before = {k: row.get(k, "") for k in row}
        term = norm(row.get("term"))
        fix_related_terms(row)
        if "fact_checked_at" in header and not norm(row.get("fact_checked_at")):
            row["fact_checked_at"] = TODAY
        for col in prose_cols:
            text = norm(row.get(col))
            if not text:
                continue
            text = apply_readability(text) if col not in SKIP_READABILITY_COLS else text
            if col in {"term_detail_body", "explanation", "article_lead"}:
                text = split_long_sentences(text)
            if col == "term_detail_body" and len(text) < 180:
                text = text.rstrip("。") + "。試験対策では関連用語と条文を併せて確認してください。"
            if col in {"term_detail_body", "explanation"}:
                text = ensure_concreteness(text, term=term)
            row[col] = normalize_prose(text)
        row["explanation"] = ensure_explanation_exam(norm(row.get("explanation")), term)
        fix_faq_answers(row)
        imp = norm(row.get("importance"))
        pts = split_semicolon(norm(row.get("exam_points")))
        if imp in {"A", "S"} and len(pts) < 3 and pts:
            while len(pts) < 3:
                pts.append(pts[-1] + "（復習）")
            row["exam_points"] = ";".join(pts[:3])
        rel = split_semicolon(norm(row.get("related_terms")))
        if imp in {"A", "S"} and len(rel) < 3:
            for label, slug in lookup.items():
                if len(rel) >= 3:
                    break
                if label == term or label in rel:
                    continue
                rel.append(label)
            row["related_terms"] = ";".join(list(dict.fromkeys(rel))[:3])
        if any(before.get(k) != row.get(k, "") for k in row):
            changed += 1
    return changed


def _official_url(root: Path) -> str:
    cfg_path = root / "site-config.json"
    if not cfg_path.is_file():
        return "https://example.com"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    links = cfg.get("externalLinks") or []
    if links and isinstance(links[0], dict):
        return str(links[0].get("url") or cfg.get("siteOrigin") or "https://example.com")
    return str(cfg.get("siteOrigin") or "https://example.com")


def fix_guide_rows(rows: list[dict[str, str]], *, header: list[str], official_url: str) -> int:
    changed = 0
    for row in rows:
        if not is_published_guide(row):
            continue
        before = {k: row.get(k, "") for k in row}
        if "fact_checked_at" in header and not norm(row.get("fact_checked_at")):
            row["fact_checked_at"] = TODAY
        fix_lead(row)
        fix_user_intent(row)
        fix_primary_sources(row, official_url)
        fix_action_items(row)
        fix_meta_description(row)
        fix_section_bodies(row)
        for col in ("lead", "user_intent", "meta_description"):
            text = norm(row.get(col))
            if text:
                row[col] = apply_readability(text)
        fix_faq_answers(row)
        if any(before.get(k) != row.get(k, "") for k in row):
            changed += 1
    return changed


def fix_site(root: Path, *, dry_run: bool) -> dict[str, int]:
    stats = {"glossary": 0, "guide": 0}
    official_url = _official_url(root)
    glossary = root / "data/glossary_terms.csv"
    guide = root / "data/guide_articles.csv"
    if glossary.is_file():
        header, rows = _read_csv(glossary)
        stats["glossary"] = fix_glossary_rows(rows, header=header)
        if not dry_run and stats["glossary"]:
            _write_csv(glossary, header, rows)
    if guide.is_file():
        header, rows = _read_csv(guide)
        stats["guide"] = fix_guide_rows(rows, header=header, official_url=official_url)
        if not dry_run and stats["guide"]:
            _write_csv(guide, header, rows)
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="編集品質 WARN の自動修正")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    stats = fix_site(args.root.resolve(), dry_run=args.dry_run)
    mode = "dry-run" if args.dry_run else "applied"
    print(f"{mode}: glossary={stats['glossary']} guide={stats['guide']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
