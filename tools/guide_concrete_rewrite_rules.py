#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験ガイド手書きリライト：具体性＋文中例示ルール。"""

from __future__ import annotations

import re

from tools.editorial_quality import norm

# 文中の例示・場面描写
EXAMPLE_MARKERS_RE = re.compile(
    r"例えば|たとえば|たとえ|例として|イメージ(?:として|すると)|好比|想像すると|"
    r"具体(?:例|的)には|一例として|場面として|ケース(?:として|例)|"
    r"「[^」]{6,48}」(?:の|と|なら|では)"
)

# 5節中、中身のある例示が必要な節数（記事全体2～3例示を目安）
MIN_SECTIONS_WITH_SUBSTANTIVE_EXAMPLE = 2

# 例示がない節は表外 prose に必要な具体アンカー数
MIN_ANCHORS_WITHOUT_EXAMPLE = 3

# FAQ 回答のうち具体性を満たす必要がある数
MIN_FAQ_WITH_CONCRETE = 2

# 例示文（マーカー含む文）の最低文字数
MIN_EXAMPLE_SENTENCE_LEN = 24

# 資格非依存の具体アンカー（表の行は _body_without_table で除外）
CONCRETE_ANCHOR_RE = re.compile(
    r"\d+[％%]|"
    r"\d+[問時間分週日]|"
    r"\d+:\d+|"
    r"\d+/\d+|"
    r"令和[0-9０-９]+年度|"
    r"第[0-9０-９]+章|"
    r"P\.[0-9０-９]+|"
    r"Q[0-9０-９]+|"
    r"正答率|"
    r"残り\d+|"
    r"\d+か月|\d+週|"
    r"[0-9,，]+円|"
    r"演習[0-9０-９]+|"
    r"ミス[0-9０-９]+|"
    r"模試|要項|受験票|申込|"
    r"締切|PDF"
)

# マーカー直後が抽象助言だけの浅い例示
SHALLOW_AFTER_MARKER_RE = re.compile(
    r"(?:例えば|たとえば|具体例として|一例として)[、,]?"
    r"[^。！？\n]{0,40}(?:してください|しましょう|が大切|を心がけ|が重要|必要です|おすすめです)"
)

LEAD_TIME_RE = re.compile(r"残り[0-9０-９]+|\d+週|\d+か月")

SENTENCE_SPLIT_RE = re.compile(r"[。！？\n]+")

PIPE_TABLE_ROW_RE = re.compile(r"^\|", re.M)

# 分野別記事に載せない学習運用ジャargon（テンプレ混入防止）
FIELD_GUIDE_FORBIDDEN_RE = re.compile(
    r"5行表|7行表|/terms/|Day3解き直し|Day0→3→7|11/22新規0|9月通し\d+/50|9/\d+通し\d+/\d+"
)

# 分野別記事に最低1つは試験論点語が必要
FIELD_GUIDE_SUBSTANCE_RE = re.compile(
    r"条文|論点|制度|法第|運行管理者|点呼|運行計画|整備|"
    r"事業法|車両法|道路交通|労基法|労働基準|実務|"
    r"貨物|旅客|CBT|正答率|"
    r"判例|横断|分野またぎ|"
    r"届出|許可|記録|運転時間|休息"
)


def validate_field_guide_genre(slug: str, patch: dict[str, str]) -> list[str]:
    """分野別 field-* 記事のジャンル適合（学習計画テンプレ混入を ERROR）。"""
    if not slug.startswith("field-"):
        return []
    errors: list[str] = []
    prefix = f"{slug}:"
    prose_cols = (
        ["lead", "user_intent"]
        + [f"section_{n}_body" for n in range(1, 6)]
        + [f"faq_{n}_answer" for n in range(1, 4)]
    )
    combined = ""
    for col in prose_cols:
        combined += norm(patch.get(col)) + "\n"
    if FIELD_GUIDE_FORBIDDEN_RE.search(combined):
        errors.append(
            f"{prefix} field guide must not use study-schedule jargon "
            f"(7行表, /terms/, Day3, 9/6通し 等). Link to study-plan instead."
        )
    section_bodies = "".join(norm(patch.get(f"section_{n}_body")) for n in range(1, 6))
    if section_bodies and not FIELD_GUIDE_SUBSTANCE_RE.search(section_bodies):
        errors.append(
            f"{prefix} field guide section bodies need exam substance "
            f"(事業法/点呼/運行計画/労基法 等)"
        )
    return errors


def skip_concrete_rules(patch: dict[str, str]) -> bool:
    """編集合格お手本（exam-schedule 等・具体例なし）のみ具体性チェック対象外。"""
    note = norm(patch.get("revision_note", ""))
    return "お手本" in note and "具体例" not in note


def _body_without_table(body: str) -> str:
    lines = [ln for ln in body.split("\n") if ln.strip() and not PIPE_TABLE_ROW_RE.match(ln.strip())]
    return "\n".join(lines)


def _sentences(text: str) -> list[str]:
    parts = SENTENCE_SPLIT_RE.split(norm(text))
    return [p.strip() for p in parts if p.strip()]


def substantive_example_sentences(prose: str) -> list[str]:
    """例示マーカー＋具体アンカー＋最低長を満たす文。"""
    found: list[str] = []
    for sent in _sentences(prose):
        if not EXAMPLE_MARKERS_RE.search(sent):
            continue
        if len(sent) < MIN_EXAMPLE_SENTENCE_LEN:
            continue
        if SHALLOW_AFTER_MARKER_RE.search(sent):
            continue
        if CONCRETE_ANCHOR_RE.search(sent):
            found.append(sent)
    return found


def section_has_example(body: str) -> bool:
    prose = _body_without_table(norm(body))
    return bool(prose and EXAMPLE_MARKERS_RE.search(prose))


def section_concrete_anchor_count(body: str) -> int:
    prose = _body_without_table(norm(body))
    if not prose:
        return 0
    return len(CONCRETE_ANCHOR_RE.findall(prose))


def section_concrete_status(body: str) -> tuple[bool, str]:
    """(合格, 理由コード: substantive|anchors|shallow|missing)"""
    prose = _body_without_table(norm(body))
    if not prose:
        return False, "missing"
    if substantive_example_sentences(prose):
        return True, "substantive"
    if section_has_example(prose) and not substantive_example_sentences(prose):
        return False, "shallow"
    if section_concrete_anchor_count(body) >= MIN_ANCHORS_WITHOUT_EXAMPLE:
        return True, "anchors"
    return False, "missing"


def faq_answer_is_concrete(answer: str) -> bool:
    text = norm(answer)
    if not text:
        return False
    if substantive_example_sentences(text):
        return True
    return section_concrete_anchor_count(text) >= 2


def _lead_errors(prefix: str, lead: str) -> list[str]:
    errors: list[str] = []
    if not lead:
        return errors
    has_time = bool(LEAD_TIME_RE.search(lead))
    has_numeric_anchor = section_concrete_anchor_count(lead) >= 1
    has_substantive = bool(substantive_example_sentences(lead))
    has_marker_with_anchors = (
        EXAMPLE_MARKERS_RE.search(lead) is not None
        and section_concrete_anchor_count(lead) >= 2
    )
    if not has_time and not has_numeric_anchor:
        errors.append(
            f"{prefix} lead needs numbers/dates anchors (18/30, 6,660円, 締切 等)"
        )
    if not has_substantive and not has_marker_with_anchors and section_concrete_anchor_count(lead) < 2:
        errors.append(
            f"{prefix} lead needs numbers/dates anchors (18/30, 6,660円, 締切 等)"
        )
    if EXAMPLE_MARKERS_RE.search(lead) and not has_substantive:
        if SHALLOW_AFTER_MARKER_RE.search(lead):
            errors.append(f"{prefix} lead example is too abstract (add numbers/field/weekday)")
    return errors


def _user_intent_errors(prefix: str, patch: dict[str, str]) -> list[str]:
    errors: list[str] = []
    ui = norm(patch.get("user_intent"))
    if not ui:
        return errors
    if not substantive_example_sentences(ui) and section_concrete_anchor_count(ui) < 1:
        errors.append(
            f"{prefix} user_intent needs a concrete anchor or 例えば scene (not title repeat)"
        )
    lead = norm(patch.get("lead"))
    if lead and ui:
        # 先頭80字がほぼ同一ならリードの写しとみなす
        a, b = lead[:80], ui[:80]
        if a == b or (len(a) > 40 and a[:40] == b[:40] and len(set(a.split()) & set(b.split())) > 12):
            errors.append(f"{prefix} user_intent must differ from lead opening (reader benefit)")
    return errors


def validate_concrete_rewrite(slug: str, patch: dict[str, str]) -> list[str]:
    """REWRITES 1件分の具体性＋例示チェック。ERROR 文言の list を返す。"""
    if skip_concrete_rules(patch):
        return []

    errors: list[str] = []
    prefix = f"{slug}:"

    lead = norm(patch.get("lead"))
    errors.extend(_lead_errors(prefix, lead))
    errors.extend(_user_intent_errors(prefix, patch))

    substantive_sections = 0
    for n in range(1, 6):
        bcol = f"section_{n}_body"
        body = norm(patch.get(bcol))
        if not body:
            continue
        ok, reason = section_concrete_status(body)
        if reason == "substantive":
            substantive_sections += 1
        elif not ok:
            if reason == "shallow":
                errors.append(
                    f"{prefix} {bcol} has 例えば/たとえば but example lacks "
                    f"numbers/field/weekday (shallow)"
                )
            else:
                errors.append(
                    f"{prefix} {bcol} needs substantive 例えば scene OR "
                    f"{MIN_ANCHORS_WITHOUT_EXAMPLE}+ concrete anchors outside the table"
                )

    if substantive_sections < MIN_SECTIONS_WITH_SUBSTANTIVE_EXAMPLE:
        errors.append(
            f"{prefix} need {MIN_SECTIONS_WITH_SUBSTANTIVE_EXAMPLE}+ sections with "
            f"substantive 例えば/たとえば (got {substantive_sections})"
        )

    faq_answers = [norm(patch.get(f"faq_{n}_answer")) for n in range(1, 4)]
    faq_answers = [a for a in faq_answers if a]
    concrete_faq = sum(1 for a in faq_answers if faq_answer_is_concrete(a))
    if concrete_faq < MIN_FAQ_WITH_CONCRETE:
        errors.append(
            f"{prefix} need {MIN_FAQ_WITH_CONCRETE}+ FAQ answers with example or "
            f"2+ anchors (got {concrete_faq})"
        )

    errors.extend(validate_field_guide_genre(slug, patch))

    return errors
