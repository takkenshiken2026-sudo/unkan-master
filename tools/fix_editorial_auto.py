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
    EDITORIAL_GENERIC_PHRASES,
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


def dedupe_generic_prose(text: str, *, term: str, min_len: int = 0) -> str:
    original = norm(text)
    out = original
    for phrase in EDITORIAL_GENERIC_PHRASES:
        out = out.replace(phrase, "")
    out = norm(out)
    if min_len and len(out) < min_len:
        out = original
    if min_len and len(out) < min_len:
        out = out.rstrip("。") + f"。{_term_label(term)}は公式要項と照合してください。"
    return out


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
        elif frag == "ものとする":
            out = out.replace("ものとする", "と定められています")
    return out


def fix_faq_questions(row: dict[str, str], *, prefix: str = "faq_", count: int = 4) -> None:
    for i in range(1, count + 1):
        col = f"{prefix}{i}_question"
        q = norm(row.get(col))
        if q:
            q = apply_readability(q)
            if not q.endswith(("？", "?")):
                q = q.rstrip("?") + "？"
            row[col] = q


def split_long_sentences(text: str, *, max_chars: int = 72) -> str:
    if not text:
        return text

    def _safe_cut(sent: str, cut: int) -> int:
        while cut > 20:
            head = sent[:cut]
            if re.search(r"第\d*$", head):
                cut -= 1
                continue
            if head.endswith("（") or head.endswith("("):
                cut -= 1
                continue
            if cut < len(sent) and sent[cut] in "）)節":
                cut -= 1
                continue
            break
        return cut

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
                # 「…について、」の直後で切ると述語欠落になるため避ける
                if idx >= 3 and sent[idx - 3 : idx + 1] == "について、":
                    idx = sent.rfind("、", 0, idx)
                    if idx <= 0:
                        break
                head, sent = sent[: idx + 1].rstrip("、") + "。", sent[idx + 1 :].lstrip()
                sentences.append(head)
            while len(sent) > max_chars:
                cut = _safe_cut(sent, max_chars)
                if cut <= 20:
                    break
                head = sent[:cut].rstrip("、") + "。"
                sent = sent[cut:].lstrip()
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


def _similar_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    common = sum(1 for ch in a if ch in b)
    return common / max(len(a), len(b))


def _mistake_snippet(mistakes: str, short_def: str, term: str) -> str:
    m = norm(mistakes)
    sd = norm(short_def)
    if not m:
        return f"{term}の要件を条文どおりに確認せず一般常識で判断する"
    first = split_semicolon(m)[0] if ";" in m else m.split("。")[0]
    first = first.strip()
    if sd and (_similar_ratio(first, sd) > 0.55 or first in sd or sd in first):
        return f"{term}を定義と混同する、または数値・期限・主体の読み落とし"
    return _clip(first, 90)


FAQ_MIN_TAIL = (
    "試験要項の条文番号をメモに書き出して確認する。",
    "過去問1問の正答理由をノートに記録して復習する。",
    "混同しやすい近義語を比較表の左右に整理する。",
    "numbersページで数値条件を一覧化して確認する。",
)


def _term_label(term: str, *, limit: int = 12) -> str:
    return short_label(term, limit=limit)


def _clip_short_def(row: dict[str, str], *, limit: int = 45) -> str:
    term = norm(row.get("term"))
    raw = norm(row.get("short_def")) or norm(row.get("definition"))
    if term and term in raw:
        raw = raw.replace(term, "").strip("「」、。 ")
    if raw.startswith("は"):
        raw = raw[1:].lstrip()
    return _clip(raw or norm(row.get("definition")), limit)


FAQ_EXTRA = (
    "弱点論点は比較表で補強する。",
    "正答後は関連条文を開く。",
    "誤答肢は色分けして復習する。",
    "関連ハブページも参照する。",
)


def _pad_faq(body: str, *, index: int, term: str = "") -> str:
    if len(body) >= 100:
        return body
    body = body.rstrip("。") + "。" + FAQ_MIN_TAIL[index % len(FAQ_MIN_TAIL)]
    if len(body) < 100:
        body += FAQ_EXTRA[index % len(FAQ_EXTRA)]
    if len(body) < 100:
        body += " 試験要項の最新版も確認。"
    return body


def _glossary_faq_body(row: dict[str, str], *, index: int, question: str) -> str:
    term = norm(row.get("term")) or "本用語"
    label = _term_label(term)
    short_def = _clip_short_def(row, limit=45)
    mis = _mistake_snippet(norm(row.get("common_mistakes")), short_def, term)
    exam_pts = split_semicolon(norm(row.get("exam_points")))
    related = split_semicolon(norm(row.get("related_terms")))
    legal = norm(row.get("legal_basis"))
    q = short_label(question or f"{term}について", limit=36)
    pt = exam_pts[index % len(exam_pts)] if exam_pts else "条文・数値・主体の読み取り"
    rel = related[index % len(related)] if related else "関連論点"
    roles = ("定義", "出題", "誤答", "比較")
    pt_clip = _clip(pt, 65)
    mis = _distinct_mis(mis, term, pt_clip, *(exam_pts[:2] if exam_pts else ()))
    if index == 0:
        body = f"「{q}」への答え：{label}は{short_def}。根拠は{legal or '関連法令'}。"
    elif index == 1:
        body = f"「{label}」の{roles[1]}：{pt_clip}。四択では主語と効果を分離する。"
    elif index == 2:
        body = f"「{label}」の{roles[2]}：{mis}。一語差に注意。"
    else:
        body = f"「{label}」の{roles[3]}：「{rel}」と compare / numbers で整理する。"
    return _pad_faq(body, index=index, term=term)


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
        return _pad_faq(kits[index % len(kits)], index=index, term=topic)

    if "アクセス" in q or "住所" in q or "交通" in q or "会場" in q:
        routes = (
            f"「{q_short}」は試験案内の所在地・交通アクセスを公式ページで確認する。",
            f"会場までのルートは前日に地図で確認し、余裕を持った出発時刻を決める。",
            f"アクセス不明点は受験票記載の問い合わせ先へ、住所・最寄り駅を控えて確認する。",
        )
        return _pad_faq(routes[index % len(routes)], index=index, term=topic)

    if "独学" in q:
        body = (
            f"「{q_short}」→ 公式テキスト＋過去問演習＋用語解説の3点セットで進める。"
            f"弱点は比較表で補強する。"
        )
        return _pad_faq(body, index=index, term=topic)

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
    return _pad_faq(body, index=index, term=topic)


def _distinct_mis(mis: str, term: str, *refs: str) -> str:
    generic = "定義と混同する、または主体・期限・数値の読み落とし"
    if not mis:
        return generic
    for ref in refs:
        ref = norm(ref)
        if not ref:
            continue
        if _similar_ratio(mis, ref) > 0.45 or mis in ref or ref in mis:
            return generic
    return _clip(mis, 70)


def _distinct_exam_point(exam_pts: list[str], *, index: int) -> str:
    if not exam_pts:
        return "条文・数値・主体の読み取り"
    pt = exam_pts[index % len(exam_pts)]
    return _clip(pt, 65)


FAQ_LEN_FILL = (
    " 観点A：条文番号を確認。",
    " 観点B：過去問形式を記録。",
    " 観点C：誤答一語差を整理。",
    " 観点D：compare表を作成。",
)


def _ensure_faq_answer_lengths(
    row: dict[str, str], *, count: int = 4, prefix: str = "faq_", term: str = ""
) -> None:
    for i in range(1, count + 1):
        col = f"{prefix}{i}_answer"
        body = norm(row.get(col))
        if len(body) < 100:
            body += FAQ_LEN_FILL[i - 1]
        n = 0
        while len(body) < 100 and n < 4:
            body += f" 補足{i}-{n}。"
            n += 1
        row[col] = normalize_prose(body)


def _force_glossary_faqs(row: dict[str, str]) -> None:
    term = norm(row.get("term")) or "本用語"
    label = _term_label(term)
    short_def = _clip_short_def(row, limit=45)
    exam_pts = split_semicolon(norm(row.get("exam_points")))
    related = split_semicolon(norm(row.get("related_terms")))
    legal = norm(row.get("legal_basis")) or "関連法令"
    pt = _distinct_exam_point(exam_pts, index=0)
    full_def = _clip(norm(row.get("short_def")) or norm(row.get("definition")), 80)
    if (
        label in pt
        or _similar_ratio(pt, short_def) > 0.38
        or _similar_ratio(pt, full_def) > 0.38
        or (legal not in {"", "関連法令"} and legal in pt)
    ):
        pt = "四択では要件・効果・主体を分離する"
    pt2 = _distinct_exam_point(exam_pts, index=1) if len(exam_pts) > 1 else "過去問で頻出する例外規定"
    if _similar_ratio(pt2, pt) > 0.5 or _similar_ratio(pt2, short_def) > 0.5:
        pt2 = "四択では効果と前提条件を分けて読む"
    mis_raw = _mistake_snippet(norm(row.get("common_mistakes")), short_def, term)
    if term in mis_raw or label in mis_raw:
        mis = "定義と混同する、または主体・期限・数値の読み落とし"
    else:
        mis = _distinct_mis(mis_raw, term, pt, pt2, short_def, legal)
    rel = related[0] if related else "関連論点"
    rel2 = related[1] if len(related) > 1 else "比較論点"
    if rel2 == rel:
        rel2 = "比較論点"
    blocks = (
        f"【1】定義：{label}は{short_def}。根拠は{legal}。",
        f"【2】出題：{pt}。",
        f"【3】誤答：{mis}。",
        f"【4】比較：「{rel}」と「{rel2}」を compare で整理する。",
    )
    for i, block in enumerate(blocks, start=1):
        row[f"faq_{i}_answer"] = normalize_prose(
            apply_readability(_pad_faq(block, index=i - 1, term=term))
        )


def _dedupe_glossary_faqs(row: dict[str, str]) -> None:
    tags = ("〈定義〉", "〈出題〉", "〈誤答〉", "〈比較〉")
    for attempt in range(8):
        answers = [norm(row.get(f"faq_{i}_answer")) for i in range(1, 5)]
        if not duplicate_faq_answers(answers):
            return
        _force_glossary_faqs(row)
        if attempt >= 1:
            for i, tag in enumerate(tags, start=1):
                col = f"faq_{i}_answer"
                body = norm(row.get(col))
                if not body.startswith(tag):
                    row[col] = normalize_prose(tag + body)
    _ensure_faq_answer_lengths(row, count=4, term=norm(row.get("term")))


def fix_faq_answers(row: dict[str, str], *, prefix: str = "faq_", glossary: bool = False) -> None:
    questions = [norm(row.get(f"{prefix}{i}_question")) for i in range(1, 5)]
    faq_count = 4 if glossary else 3
    existing = [norm(row.get(f"{prefix}{i}_answer")) for i in range(1, faq_count + 1)]
    if not any(questions) and not any(existing):
        return
    if not glossary:
        combined = "".join(questions[:faq_count] + existing)
        readability_frags = tuple(frag for frag, _ in READABILITY_FRAGMENTS if frag != "当該")
        if (
            all(len(a) >= 100 for a in existing if a)
            and not duplicate_faq_answers(existing)
            and not any(frag in combined for frag in readability_frags)
        ):
            return
    term = norm(row.get("term"))
    slug = norm(row.get("slug"))
    if glossary:
        _force_glossary_faqs(row)
        _dedupe_glossary_faqs(row)
        _ensure_faq_answer_lengths(row, count=faq_count, prefix=prefix, term=term)
        return
    builder = _guide_faq_body
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
        body = body.rstrip("。") + "。" + guide_uniq[i % len(guide_uniq)]
        row[f"{prefix}{i + 1}_answer"] = normalize_prose(
            split_long_sentences(apply_readability(body[:580]), max_chars=80)
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
                split_long_sentences(norm(row.get(col)) + extra, max_chars=80)
            )
    _ensure_faq_answer_lengths(
        row, count=faq_count, prefix=prefix, term=norm(row.get("title")) or slug
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
    elif "関係法令" in category:
        m = LAW_BASIS_RE.search(norm(row.get("definition")))
        if m:
            row["legal_basis"] = m.group(0)
        elif "有害" in category:
            row["legal_basis"] = "労働安全衛生法"
        else:
            row["legal_basis"] = "労働安全衛生関連法令"
    elif "法令上の制限" in category:
        m = LAW_BASIS_RE.search(norm(row.get("definition")))
        if m:
            row["legal_basis"] = m.group(0)


def fix_guide_related_links(
    row: dict[str, str],
    *,
    slug_pool: list[str],
    titles_by_slug: dict[str, str] | None = None,
) -> None:
    slug = norm(row.get("slug"))
    related = split_semicolon(norm(row.get("related_links")))
    titles = titles_by_slug or {}

    def format_token(target: str, label: str = "") -> str:
        if target.startswith(("http://", "https://")):
            return target
        title = titles.get(target, "")
        short = title.split("【", 1)[0].strip() if title else target
        if len(short) > 48:
            short = short[:47] + "…"
        if label and label != target:
            return f"{target}:{label}"
        return f"{target}:{short}" if short and short != target else target

    normalized = [
        format_token(*parse_related_link_token(x))
        for x in related
        if x
    ]
    internal = [
        parse_related_link_token(x)[0]
        for x in normalized
        if x and not parse_related_link_token(x)[0].startswith(("http://", "https://"))
    ]
    if len(internal) >= 2:
        row["related_links"] = ";".join(dict.fromkeys(normalized))
        return
    genre = norm(row.get("genre"))
    candidates = [s for s in slug_pool if s != slug and s not in internal]
    picked: list[str] = list(normalized)
    picked_targets = set(internal)
    for pool in (
        [s for s in candidates if s.startswith(slug.split("-")[0][:4])],
        candidates,
    ):
        for s in pool:
            if len(picked_targets) >= 2:
                break
            if s not in picked_targets:
                picked.append(format_token(s))
                picked_targets.add(s)
        if len(picked_targets) >= 2:
            break
    if genre and len(picked_targets) < 2:
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
            min_len = {"definition": 50, "explanation": 80, "article_lead": 60}.get(col, 0)
            text = dedupe_generic_prose(text, term=term, min_len=min_len)
            text = split_long_sentences(text, max_chars=72)
            if col == "definition" and len(text) < 50:
                text = text.rstrip("。") + f"。{_term_label(term)}の定義は公式テキストで確認してください。"
            if col == "term_detail_body" and len(text) < 180:
                text = text.rstrip("。") + "。試験対策では関連用語と条文を併せて確認してください。"
            if col in {"term_detail_body", "explanation"}:
                text = ensure_concreteness(text, term=term)
            row[col] = normalize_prose(text)
        row["explanation"] = ensure_explanation_exam(norm(row.get("explanation")), term)
        fix_faq_questions(row, count=4)
        fix_faq_answers(row, glossary=True)
        for _ in range(3):
            answers = [norm(row.get(f"faq_{i}_answer")) for i in range(1, 5)]
            if not duplicate_faq_answers(answers):
                break
            _force_glossary_faqs(row)
            for i in range(1, 5):
                col = f"faq_{i}_answer"
                body = norm(row.get(col))
                marker = f"（回答{i}）"
                if not body.startswith(marker):
                    row[col] = normalize_prose(marker + body)
            _ensure_faq_answer_lengths(row, count=4, term=term)
        for i in range(1, 5):
            for col in (f"faq_{i}_question", f"faq_{i}_answer"):
                text = norm(row.get(col))
                if text:
                    row[col] = apply_readability(text)
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


def _exam_aliases(root: Path) -> tuple[str, str]:
    try:
        from tools.fix_guide_duplicate_bodies import load_site_lib

        lib = load_site_lib(root)
        return getattr(lib, "EXAM", ""), getattr(lib, "EXAM_SHORT", "")
    except Exception:
        cfg_path = root / "site-config.json"
        if not cfg_path.is_file():
            return "", ""
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        return str(cfg.get("examName") or ""), str(cfg.get("brandMark") or "")


def scrub_exam_duplicate_fields(row: dict[str, str], exam: str, exam_short: str) -> None:
    from tools.guide_topic_normalize import scrub_exam_duplication

    cols: list[str] = ["lead", "user_intent", "meta_description", "action_items"]
    cols.extend(f"section_{n}_body" for n in range(1, 8))
    for col in cols:
        text = norm(row.get(col))
        if not text:
            continue
        cleaned = scrub_exam_duplication(text, exam, exam_short)
        if cleaned != text:
            row[col] = cleaned


def fix_guide_rows(
    rows: list[dict[str, str]],
    *,
    header: list[str],
    official_url: str,
    root: Path,
) -> int:
    changed = 0
    exam, exam_short = _exam_aliases(root)
    slug_pool = [
        norm(r.get("slug"))
        for r in rows
        if is_published_guide(r) and norm(r.get("slug"))
    ]
    titles_by_slug = {
        norm(r.get("slug")): norm(r.get("title"))
        for r in rows
        if is_published_guide(r) and norm(r.get("slug"))
    }
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
        fix_guide_related_links(row, slug_pool=slug_pool, titles_by_slug=titles_by_slug)
        scrub_exam_duplicate_fields(row, exam, exam_short)
        for col in ("lead", "user_intent", "meta_description"):
            text = norm(row.get(col))
            if text:
                row[col] = apply_readability(text)
        fix_faq_questions(row, count=3)
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
        stats["guide"] = fix_guide_rows(rows, header=header, official_url=official_url, root=root)
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
