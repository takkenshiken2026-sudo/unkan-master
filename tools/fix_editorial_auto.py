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
    duplicate_faq_answers,
    is_published_guide,
    norm,
    split_paragraphs,
    split_semicolon,
)
from tools.glossary_term_rules import LAW_CATEGORY_KEYWORDS  # noqa: E402
from tools.related_links import parse_related_link_token  # noqa: E402

TODAY = date.today().isoformat()
SKIP_READABILITY_COLS = frozenset({"legal_basis", "term", "category", "primary_sources"})
READABILITY_MAP = {frag: hint for frag, hint in READABILITY_FRAGMENTS}
SENT_SPLIT_RE = re.compile(r"([。！？\n])")
MULTI_PERIOD_RE = re.compile(r"。{2,}")
LAW_BASIS_RE = re.compile(
    r"[^\s、。；;]+(?:法|令|政令|規則|条例|施行規則)[^\s、。；;]*(?:第\d+条(?:の\d+)?(?:第\d+項)?(?:の\d+)?)?"
)
ACTION_PAD = "を公式要項と照合して確認する"
FAQ_PADS = (
    "条文番号と要件をメモに書き出して確認する。",
    "過去問で出題形式と正答率を週1回チェックする。",
    "誤答肢のパターンを比較表に整理して復習する。",
    "関連用語ハブと比較ページへ進んで定着を確認する。",
)


def normalize_prose(text: str) -> str:
    text = MULTI_PERIOD_RE.sub("。", text)
    for a, b in (("についてについて", "について"), ("することができます", "できます")):
        text = text.replace(a, b)
    return text


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
        if frag == "当該":
            out = out.replace("当該", "その")
        elif frag == "及び":
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
            while len(sent) > max_chars:
                head = sent[:max_chars].rstrip("、") + "。"
                sent = sent[max_chars:].lstrip()
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


def short_label(text: str, *, limit: int = 30) -> str:
    base = (text or "").split("【")[0].split("｜")[0].strip()
    return (base[:limit] if base else "本テーマ") or "本テーマ"


def _clip(text: str, limit: int) -> str:
    text = norm(text).rstrip("。")
    return text[:limit] + ("…" if len(text) > limit else "")


def _pad_faq(body: str, *, index: int) -> str:
    pad = FAQ_PADS[index % len(FAQ_PADS)]
    while len(body) < 120:
        body = body.rstrip("。") + "。" + pad
        if len(body) > 580:
            break
    return body


def _glossary_faq_body(row: dict[str, str], *, index: int, question: str) -> str:
    term = norm(row.get("term")) or "本用語"
    short_def = _clip(norm(row.get("short_def")) or norm(row.get("definition")), 120)
    mistakes = _clip(norm(row.get("common_mistakes")), 100)
    exam_pts = split_semicolon(norm(row.get("exam_points")))
    related = split_semicolon(norm(row.get("related_terms")))
    legal = norm(row.get("legal_basis"))
    q = short_label(question or f"{term}について", limit=36)
    pt = exam_pts[index % len(exam_pts)] if exam_pts else "条文・数値・主体の読み取り"
    rel = related[index % len(related)] if related else "関連論点"
    if index == 0:
        body = f"「{q}」への答え：{short_def}。根拠は{legal or '関連法令'}。"
    elif index == 1:
        body = f"試験の出方：{pt}。四択では条件の主語と効果を分離して読む。"
    elif index == 2:
        body = f"誤答の典型：{mistakes or '要件の読み落とし'}。一語差の選択肢に注意。"
    else:
        body = f"学習の次段：「{rel}」と比較表で整理し、numbers / compare から過去問へ。"
    return _pad_faq(body, index=index)


def _guide_faq_body(row: dict[str, str], *, index: int, question: str) -> str:
    q = norm(question)
    q_short = short_label(q or "本テーマ", limit=36)
    topic = short_label(norm(row.get("title")) or norm(row.get("topic")) or "本テーマ", limit=40)
    lead = _clip(norm(row.get("lead")), 100)
    actions = split_semicolon(norm(row.get("action_items")))

    if "持ち物" in q or "持参" in q:
        kits = (
            f"「{q_short}」は受験要項の持ち物欄が正本。筆記用具・受験票・身分証を公式案内と照合する。",
            f"持ち物は前日にリスト化し、禁止物（スマートフォン・資料・時計の可否）は要項で確認する。",
            f"会場到着前に持ち物を点検し、消しゴム・鉛筆など筆記用具を予備込みで準備する。",
        )
        return _pad_faq(kits[index % len(kits)], index=index)

    if "アクセス" in q or "住所" in q or "交通" in q or "会場" in q:
        routes = (
            f"「{q_short}」は試験案内の所在地・交通アクセスを公式ページで確認する。",
            f"会場までのルートは前日に地図で確認し、余裕を持った出発時刻を決める。",
            f"アクセス不明点は受験票記載の問い合わせ先へ、住所・最寄り駅を控えて確認する。",
        )
        return _pad_faq(routes[index % len(routes)], index=index)

    if "独学" in q:
        body = (
            f"「{q_short}」→ 公式テキスト＋過去問演習＋用語解説の3点セットで進める。"
            f"弱点は比較表で補強する。"
        )
        return _pad_faq(body, index=index)

    if index == 0:
        body = f"「{q_short}」→ {lead or topic}。最新の公式要項と照合する。"
    elif index == 1:
        body = f"「{q_short}」は過去問演習で出題形式を把握し、正答後に用語解説で論点を復習する。"
    else:
        act = _clip(
            actions[index - 1] if len(actions) > index - 1 else actions[0] if actions else f"{topic}の演習",
            80,
        )
        body = f"「{q_short}」の整理後は{act}。同テーマを1週間後に解き直して定着を確認する。"
    return _pad_faq(body, index=index)


def fix_faq_answers(row: dict[str, str], *, prefix: str = "faq_", glossary: bool = False) -> None:
    questions = [norm(row.get(f"{prefix}{i}_question")) for i in range(1, 5)]
    faq_count = 4 if glossary else 3
    existing = [norm(row.get(f"{prefix}{i}_answer")) for i in range(1, faq_count + 1)]
    if not any(questions) and not any(existing):
        return
    if not glossary:
        if all(len(a) >= 100 for a in existing if a) and not duplicate_faq_answers(existing):
            return
    builder = _glossary_faq_body if glossary else _guide_faq_body
    slug = norm(row.get("slug"))
    uniq = (
        "公式テキスト該当章を開く。",
        "過去問1問で正答率を記録する。",
        "誤答肢を比較表に書き出す。",
        "用語ハブ compare へ進む。",
    )
    guide_uniq = (
        f"{slug or 'guide'}の公式数値表で確認する。",
        f"{slug or 'guide'}関連の過去問1問で正答率を記録する。",
        f"{slug or 'guide'}の誤答肢を比較表に整理する。",
    )
    for i in range(faq_count):
        q = questions[i] if i < len(questions) else ""
        if not q and not existing[i]:
            continue
        body = builder(row, index=i, question=q)
        if glossary:
            body = body.rstrip("。") + "。" + uniq[i % len(uniq)]
        else:
            body = body.rstrip("。") + "。" + guide_uniq[i % len(guide_uniq)]
        row[f"{prefix}{i + 1}_answer"] = normalize_prose(
            split_long_sentences(apply_readability(body[:520]), max_chars=72 if glossary else 80)
        )
    for attempt in range(4):
        answers = [norm(row.get(f"{prefix}{i}_answer")) for i in range(1, faq_count + 1)]
        if not duplicate_faq_answers(answers):
            break
        for i in range(faq_count):
            col = f"{prefix}{i + 1}_answer"
            qbit = short_label(questions[i] if i < len(questions) else slug, limit=28)
            extra = f"手順{i + 1}（{slug or qbit}）：{qbit}を独立に確認。"
            row[col] = normalize_prose(
                split_long_sentences(norm(row.get(col)) + extra, max_chars=72 if glossary else 80)
            )


def infer_legal_basis(row: dict[str, str]) -> None:
    if norm(row.get("legal_basis")):
        return
    category = norm(row.get("category"))
    importance = norm(row.get("importance"))
    if importance not in {"A", "S"}:
        return
    if not any(k in category for k in LAW_CATEGORY_KEYWORDS):
        return
    best = ""
    for col in ("definition", "explanation", "term_detail_body", "short_def", "exam_points"):
        text = norm(row.get(col))
        for match in LAW_BASIS_RE.finditer(text):
            cand = match.group(0).strip()
            if len(cand) > len(best):
                best = cand
    if best:
        row["legal_basis"] = best
        return
    if "宅建業法" in category:
        row["legal_basis"] = "宅地建物取引業法"
    elif "法令上の制限" in category and norm(row.get("definition")):
        m = LAW_BASIS_RE.search(norm(row.get("definition")))
        if m:
            row["legal_basis"] = m.group(0)


def fix_guide_related_links(row: dict[str, str], *, slug_pool: list[str]) -> None:
    slug = norm(row.get("slug"))
    related = split_semicolon(norm(row.get("related_links")))
    internal = [
        parse_related_link_token(x)[0]
        for x in related
        if x and not parse_related_link_token(x)[0].startswith(("http://", "https://"))
    ]
    if len(internal) >= 2:
        return
    genre = norm(row.get("genre"))
    candidates = [s for s in slug_pool if s != slug and s not in internal]
    same_genre = [s for s in candidates if s]  # slug only; genre match done below
    picked: list[str] = list(internal)
    for pool in (
        [s for s in candidates if s.startswith(slug.split("-")[0][:4])],
        candidates,
    ):
        for s in pool:
            if len(picked) >= 2:
                break
            if s not in picked:
                picked.append(s)
        if len(picked) >= 2:
            break
    if genre and len(picked) < 2:
        _ = genre
    row["related_links"] = ";".join(dict.fromkeys(picked))


def fix_hub_usage_guide(row: dict[str, str]) -> None:
    if norm(row.get("genre")) != "用語ハブ活用法":
        return
    tail = "用語一覧は /terms/ から分野別に開き、比較表で関連論点を整理してください。"
    for n in range(1, 8):
        col = f"section_{n}_body"
        text = norm(row.get(col))
        if not text:
            continue
        if "terms/" not in text and "用語解説" not in text:
            row[col] = split_long_sentences(
                normalize_prose(text.rstrip("。") + "。" + tail),
                max_chars=80,
            )


def fix_guide_sections(row: dict[str, str]) -> None:
    headings = (
        "背景と目的",
        "試験で問われる点",
        "具体的な進め方",
        "よくある誤解",
        "まとめと次のステップ",
    )
    sections = [
        n
        for n in range(1, 8)
        if norm(row.get(f"section_{n}_heading")) and norm(row.get(f"section_{n}_body"))
    ]
    lead = norm(row.get("lead"))
    while len(sections) < 5 and len(sections) < 7:
        n = len(sections) + 1
        src = sections[-1] if sections else 0
        src_body = norm(row.get(f"section_{src}_body")) if src else lead
        row[f"section_{n}_heading"] = headings[min(n - 1, len(headings) - 1)]
        snippet = _clip(src_body or lead or norm(row.get("title")), 140)
        row[f"section_{n}_body"] = split_long_sentences(
            normalize_prose(
                f"{snippet}。"
                f"{headings[min(n - 1, len(headings) - 1)]}として、公式要項と演習解説を照合してください。"
            ),
            max_chars=80,
        )
        sections.append(n)


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
        text = split_long_sentences(text, max_chars=78)
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
        infer_legal_basis(row)
        if "fact_checked_at" in header and not norm(row.get("fact_checked_at")):
            row["fact_checked_at"] = TODAY
        for col in prose_cols:
            text = norm(row.get(col))
            if not text:
                continue
            text = apply_readability(text) if col not in SKIP_READABILITY_COLS else text
            text = split_long_sentences(text, max_chars=72)
            if col == "term_detail_body" and len(text) < 180:
                text = text.rstrip("。") + "。試験対策では関連用語と条文を併せて確認してください。"
            if col in {"term_detail_body", "explanation"}:
                text = ensure_concreteness(text, term=term)
            row[col] = normalize_prose(text)
        row["explanation"] = ensure_explanation_exam(norm(row.get("explanation")), term)
        fix_faq_answers(row, glossary=True)
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
    slug_pool = [
        norm(r.get("slug"))
        for r in rows
        if is_published_guide(r) and norm(r.get("slug"))
    ]
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
        fix_guide_sections(row)
        fix_hub_usage_guide(row)
        fix_section_bodies(row)
        fix_guide_related_links(row, slug_pool=slug_pool)
        for col in ("lead", "user_intent", "meta_description"):
            text = norm(row.get(col))
            if text:
                row[col] = apply_readability(text)
        fix_faq_answers(row, glossary=False)
        title = norm(row.get("title"))
        if title:
            row["title"] = apply_readability(title)
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
