#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Replace generic S35–S44 hub templates with topic- and batch-specific copy."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from typing import Any

from tools.hub_strip_batch_suffix import BATCH_SUFFIX_RE

BATCH_SUFFIX_RE_SLUG = re.compile(r"-s(\d+)$")
BATCH_PREFIX_RE_SLUG = re.compile(r"^s(\d+)-")
GENERIC_NUMBER_HIGHLIGHTS = frozenset(
    {
        "代表値は要項・法令で確認",
        "要項・法令で確認",
    }
)
GENERIC_NUMBER_VALUE_MARKERS = ("要項", "規則", "法令で確認", "試験要点", "対象・手順")
GENERIC_EXAM_POINTS = frozenset(
    {
        "数値と条件をセット",
        "単位を確認",
        "最新法令で照合",
    }
)
HUB_TEMPLATE_ITEM_LABELS = frozenset(
    {
        "義務主体",
        "実施・頻度",
        "記録・保存",
        "試験の確認点",
        "関連制度",
    }
)
TRAILING_BATCH_TITLE_RE = re.compile(r"\s+S\d+$")
GENERIC_COMPARE_LABELS = frozenset({"観点A", "観点B", "整理", "確認", "用語A", "用語B"})
GENERIC_FAQ = "試験論点・条文・数値の対応を比較表に整理し、過去問で正誤の型を分類してください。"
GENERIC_CONFUSION = frozenset(
    {
        "手順と主体の混同。",
        "手順と主体の混同",
        "再発防止計画・休復職支援は名称が似るため、主語と時点の読み飛ばしが起きやすい。",
    }
)
GENERIC_MISTAKE_PATTERNS = (
    ("手順", "誤った対応", "典型誤答"),
    ("主体", "誤った対応", "典型誤答"),
    ("記録", "誤った対応", "典型誤答"),
    ("報告", "誤った対応", "典型誤答"),
)
GENERIC_CMP_AXES = (
    ("定義", ["主語・目的の確認", "手順・対象の確認"]),
    ("頻出", ["類似語の入替", "数値・条件付き出題"]),
)

ANGLE_BY_BATCH: dict[int, str] = {
    35: "基礎整理",
    36: "実務連動",
    37: "試験頻出",
    38: "判例・ガイド",
    39: "横断総合",
    40: "基礎整理",
    41: "実務連動",
    42: "試験頻出",
    43: "判例・ガイド",
    44: "横断総合",
}

CONFUSION_BY_ANGLE: dict[str, str] = {
    "基礎整理": "{topic}の目的・対象・主体の定義を取り違えやすい。",
    "実務連動": "{topic}の実施主体と手続順序（誰が・いつ・何を）を混同しやすい。",
    "試験頻出": "{topic}の過去問で主語・数値・条件文が入れ替わる肢に注意。",
    "判例・ガイド": "{topic}のガイドライン・通知と法令条文の関係を誤解しやすい。",
    "横断総合": "{topic}と類似制度の境界が曖昧になり、総合問題で誤答しやすい。",
}

LEAD_BY_ANGLE: dict[str, str] = {
    "基礎整理": "{topic}は用語の定義と義務主体を先に固定し、比較表で整理してください。",
    "実務連動": "{topic}は職場フロー（事前確認→実施→記録→報告）に沿って復習すると定着します。",
    "試験頻出": "{topic}は過去問の逆転肢・数値混同を型別に分類し、条件文を最後まで読んでください。",
    "判例・ガイド": "{topic}は法令条文とガイドライン・通知の対応表を作成し、優先関係を確認してください。",
    "横断総合": "{topic}は関連制度との違いを横断マップにまとめ、直前総仕上げに使ってください。",
}

TITLE_SUFFIXES = (
    "の典型誤答",
    "の混同",
    "の誤認",
    "の逆転",
    "の省略",
    "の盲信",
    "の過剰",
    "の未確認",
    "の未使用",
    "の放置",
    "のゼロ",
    "の比較",
    "の違い",
    "の整理",
    "の要点",
    "の対比",
    "の区分",
    "の手順",
    "の制度",
    "の運用",
    "の判定",
    "の数値",
    "の周期",
    "の目安",
    "の頻度",
    "の時間",
    "の回数",
    "の基準",
    "の比率",
    "の配分",
    "の確認",
    "の数値整理",
    "の比較整理",
)


def _batch_num(slug: str) -> int | None:
    s = slug or ""
    m = BATCH_SUFFIX_RE_SLUG.search(s)
    if m:
        return int(m.group(1))
    m = BATCH_PREFIX_RE_SLUG.search(s)
    return int(m.group(1)) if m else None


def _clean_public_title(title: str) -> str:
    t = TRAILING_BATCH_TITLE_RE.sub("", BATCH_SUFFIX_RE.sub(title or "", "")).strip()
    return re.sub(r"\s{2,}", " ", t).strip() or (title or "").strip()


def _items_are_hub_template(row: dict[str, str]) -> bool:
    try:
        items = json.loads(row.get("item_rows") or "[]")
    except json.JSONDecodeError:
        return True
    if not items:
        return True
    labels = {str(i.get("item") or "").strip() for i in items}
    return labels.issubset(HUB_TEMPLATE_ITEM_LABELS) and bool(labels & HUB_TEMPLATE_ITEM_LABELS)


def _enrich_numbers_highlight(row: dict[str, str]) -> None:
    hl = (row.get("highlight") or "").strip()
    if hl not in GENERIC_NUMBER_HIGHLIGHTS:
        return
    topic = _clean_public_title(row.get("title", ""))
    parts: list[str] = []
    try:
        items = json.loads(row.get("item_rows") or "[]")
    except json.JSONDecodeError:
        items = []
    for item in items:
        val = (item.get("value") or "").strip()
        label = (item.get("item") or "").strip()
        if not val or any(marker in val for marker in GENERIC_NUMBER_VALUE_MARKERS):
            continue
        parts.append(f"{label}：{val}" if label else val)
        if len(parts) >= 2:
            break
    if parts:
        row["highlight"] = f"{topic} — {' / '.join(parts[:2])}"
        return
    exam_points = [
        p.strip()
        for p in (row.get("exam_points") or "").split(";")
        if p.strip() and p.strip() not in GENERIC_EXAM_POINTS
    ]
    if exam_points:
        row["highlight"] = f"{topic}（{' / '.join(exam_points[:2])}）"
        return
    memory_tip = (row.get("memory_tip") or "").strip()
    if memory_tip:
        short = memory_tip[:40] + ("…" if len(memory_tip) > 40 else "")
        row["highlight"] = f"{topic} — {short}"
        return
    row["highlight"] = f"{topic}（試験要項・省令で数値確認）"


def _core_topic(title: str) -> str:
    t = (title or "").strip()
    for suffix in TITLE_SUFFIXES:
        if t.endswith(suffix):
            t = t[: -len(suffix)]
            break
    return t.strip() or title.strip()


def _topic_terms(row: dict[str, str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    def add(term: str) -> None:
        t = _strip_paren_suffix(term.strip())
        if not t or t in seen:
            return
        seen.add(t)
        out.append(t)

    for part in (row.get("col_labels") or "").split(";"):
        add(part)
    for part in (row.get("related_terms") or "").split(";"):
        add(part)
    tags = [x.strip() for x in (row.get("tags") or "").split(";") if x.strip()]
    generic = {
        "比較",
        "数値",
        "誤答",
        "整理",
        "メンタルヘルスII種",
        "宅建",
        "第一種",
        "第二種",
        "2級ボイラー技士",
        "試験対策",
        "賃貸住宅管理業",
        "管理業務主任者",
        "衛生管理者",
        "危険物取扱者",
        "環境計量士",
    }
    for t in tags:
        if t not in generic and not re.fullmatch(r"S\d+", t):
            add(t)
    if not out:
        add(_core_topic(row.get("title", "")))
    return out[:6]


def _title_nuance(row: dict[str, str]) -> str:
    title = _clean_public_title(_strip_angle_suffix(row.get("title", "")))
    for suffix in TITLE_SUFFIXES:
        if title.endswith(suffix):
            return suffix.lstrip("の")
    return ""


def _compare_pair_terms(row: dict[str, str]) -> tuple[str, str]:
    parts = [_strip_paren_suffix(p.strip()) for p in (row.get("col_labels") or "").split(";") if p.strip()]
    if (
        len(parts) >= 2
        and parts[0] != parts[1]
        and parts[0] not in GENERIC_COMPARE_LABELS
        and parts[1] not in GENERIC_COMPARE_LABELS
    ):
        return parts[0], parts[1]

    related = [x.strip() for x in (row.get("related_terms") or "").split(";") if x.strip()]
    title = _clean_public_title(_strip_angle_suffix(row.get("title", "")))
    topic = _core_topic(title)

    if "：" in title:
        head, tail = title.split("：", 1)
        head, tail = head.strip(), tail.strip()
        for sfx in ("の比較", "の整理", "の違い", "の対比"):
            tail = tail.replace(sfx, "").strip()
        if head and tail and head != tail:
            return head, tail

    if related:
        slug = row.get("slug", "")
        start = _variant_index(slug, len(related))
        for off in range(len(related)):
            alt = related[(start + off) % len(related)]
            if alt != topic:
                return topic, alt

    tags = _topic_terms(row)
    if len(tags) >= 2:
        return tags[0], tags[1]

    nuance = _title_nuance(row)
    if nuance and nuance not in topic:
        return topic, f"{topic}（{nuance}）"

    disambig = _reader_disambig(row, row.get("slug", ""))
    if disambig and disambig != topic:
        return topic, disambig

    return topic, f"{topic}の関連制度"


def _has_generic_item_values(row: dict[str, str]) -> bool:
    try:
        items = json.loads(row.get("item_rows") or "[]")
    except json.JSONDecodeError:
        return False
    if len(items) < 2:
        return False
    bad = sum(
        1
        for item in items
        if any(marker in (item.get("value") or "") for marker in GENERIC_NUMBER_VALUE_MARKERS)
    )
    return bad >= 2


def _faqs_need_rewrite(row: dict[str, str]) -> bool:
    answers = [(row.get(f"faq_{i}_answer") or "").strip() for i in range(1, 5)]
    if not all(answers):
        return True
    if any(GENERIC_FAQ in a for a in answers):
        return True
    if all(len(a) >= 72 for a in answers):
        title = _clean_public_title(row.get("title", ""))
        if title and sum(1 for a in answers if title[: min(8, len(title))] in a) >= 2:
            return False
    return True


def _variant_index(slug: str, n: int) -> int:
    if n <= 0:
        return 0
    h = int(hashlib.md5(slug.encode()).hexdigest(), 16)
    return h % n


CONFUSION_TEMPLATE_MARKERS = (
    "の目的・対象・主体の定義を取り違えやすい",
    "の実施主体と手続順序（誰が・いつ・何を）を混同しやすい",
    "の過去問で主語・数値・条件文が入れ替わる肢に注意",
    "のガイドライン・通知と法令条文の関係を誤解しやすい",
    "と類似制度の境界が曖昧になり、総合問題で誤答しやすい",
)
PATTERN_TEMPLATE_MARKERS = (
    "義務主体の取り違え",
    "実施順序の逆転",
    "数値・条件の単独暗記",
    "記録・報告の省略",
    "定義確認）",
    "フロー確認）",
    "逆転肢対策）",
)


def _mistake_pair_terms(row: dict[str, str]) -> tuple[str, str]:
    title = _strip_angle_suffix(row.get("title", ""))
    terms = _topic_terms(row)
    if "：" in title:
        _, tail = title.split("：", 1)
        for suffix in ("の混同誤り", "の典型誤答", "の混同", "の誤り", "の誤認"):
            tail = tail.replace(suffix, "")
        tail = tail.strip()
        if "と" in tail:
            left, right = tail.split("と", 1)
            left, right = left.strip(), right.strip()
            if left and right and left != right:
                return left, right
    if len(terms) >= 2 and terms[0] != terms[1]:
        return terms[0], terms[1]
    core = _core_topic(title)
    alt = terms[0] if terms and terms[0] != core else f"{core}の関連制度"
    return core, alt


def _is_template_confusion(cp: str) -> bool:
    text = (cp or "").strip()
    if not text:
        return True
    if text in GENERIC_CONFUSION:
        return True
    return any(marker in text for marker in CONFUSION_TEMPLATE_MARKERS)


def _is_template_mistake_patterns(row: dict[str, str]) -> bool:
    try:
        patterns = json.loads(row.get("pattern_rows") or "[]")
    except json.JSONDecodeError:
        return True
    if not patterns:
        return True
    blob = json.dumps(patterns, ensure_ascii=False)
    if any(marker in blob for marker in PATTERN_TEMPLATE_MARKERS):
        return True
    wrongs = [(p.get("wrong") or "").strip() for p in patterns]
    if wrongs and all(len(w) > 36 for w in wrongs):
        return True
    if wrongs and all(w.startswith("「") for w in wrongs):
        return True
    return False


def _has_handcrafted_mistake_patterns(row: dict[str, str]) -> bool:
    try:
        patterns = json.loads(row.get("pattern_rows") or "[]")
    except json.JSONDecodeError:
        return False
    if len(patterns) != 4:
        return False
    for pattern in patterns:
        wrong = (pattern.get("wrong") or "").strip()
        correct = (pattern.get("correct") or "").strip()
        if not wrong or not correct or len(wrong) > 42 or len(correct) > 42:
            return False
        if wrong.startswith("「") or correct.startswith("「"):
            return False
    return True


def _is_generic_mistake(row: dict[str, str]) -> bool:
    cp = (row.get("confusion_point") or "").strip()
    if cp in GENERIC_CONFUSION or "手順と主体" in cp or "主語と時点" in cp:
        return True
    if _is_template_mistake_patterns(row):
        return True
    try:
        patterns = json.loads(row.get("pattern_rows") or "[]")
    except json.JSONDecodeError:
        return False
    if len(patterns) != 4:
        return False
    traps = [p.get("trap") for p in patterns]
    wrongs = [p.get("wrong") for p in patterns]
    if traps == ["主体誤", "手続誤", "数値誤", "効果誤"] and wrongs == [
        "逆転",
        "省略",
        "固定誤",
        "同一",
    ]:
        return True
    if any(p.get("wrong") == "名称だけで判断" for p in patterns):
        return True
    for p, (axis, wrong, trap) in zip(patterns, GENERIC_MISTAKE_PATTERNS):
        if p.get("topic") != axis or p.get("wrong") != wrong or p.get("trap") != trap:
            break
    else:
        return True
    return traps.count("典型誤答") >= 3


def _mistake_patterns(row: dict[str, str], topic: str, terms: list[str], angle: str, slug: str) -> list[dict[str, str]]:
    t1, t2 = _mistake_pair_terms(row)
    pools: dict[str, list[tuple[str, str, str, str]]] = {
        "基礎整理": [
            ("混同", f"{t1}＝{t2}", f"{t1}と{t2}は別", "名称類似"),
            ("主体", "管業が決定", "管理組合が決定", "主体誤"),
            ("機関", "理事会のみ", "総会決議", "機関誤"),
            ("決議", "過半数", "5分の4", "決議誤"),
        ],
        "実務連動": [
            ("手続", f"{t1}の手続を省略", f"{t1}→{t2}の順で確認", "手続誤"),
            ("記録", "記録不要", "記録・保存まで追跡", "記録誤"),
            ("費用", f"{t1}と{t2}を同一費目", "費目・会計を分離", "費用誤"),
            ("主体", "管理会社が単独決定", "組合の意思決定", "主体誤"),
        ],
        "試験頻出": [
            ("逆転", f"{t2}の主語を{t1}に", "主語・条件を下線", "主語入替"),
            ("数値", "数値だけ暗記", "数値+条件をセット", "数値誤"),
            ("決議", "普通決議で足りる", "特別決議・5分の4", "決議誤"),
            ("混同", f"{t1}の条文を{t2}に適用", "根拠法ごとに整理", "条文混同"),
        ],
        "判例・ガイド": [
            ("根拠", "通知だけで判断", "法令→通知の順で確認", "根拠誤"),
            ("規約", "規約が法令より優先", "法令優先・規約は補完", "優先誤"),
            ("判例", "典型例で一律判断", "事案ごとに条文・判例", "判例誤"),
            ("主体", f"{t1}と{t2}の権限同一", "権限・責任を表で分離", "権限誤"),
        ],
        "横断総合": [
            ("横断", f"{t1}と{t2}を同列処理", "制度ごとに軸を分ける", "横断誤"),
            ("費用", "修繕費と管理費を混同", "会計区分を固定", "会計誤"),
            ("時点", "手続完了前に効力発生", "決議→実行の順序固定", "時点誤"),
            ("選任", "管理会社社員で代替", "法定選任要件を確認", "選任誤"),
        ],
    }
    specs = pools.get(angle, pools["試験頻出"])
    shift = _variant_index(slug, len(specs))
    rotated = specs[shift:] + specs[:shift]
    out: list[dict[str, str]] = []
    for axis, wrong, correct, trap in rotated:
        out.append({"topic": axis, "wrong": wrong, "correct": correct, "trap": trap})
    return out


def _mistake_exam_points(topic: str, angle: str, slug: str) -> str:
    pools = {
        "基礎整理": [
            f"{topic}の定義と主体を固定",
            "用語の境界を表で整理",
            "類似語の入替肢に注意",
        ],
        "実務連動": [
            f"{topic}の実施フローを順序固定",
            "記録・報告まで一体確認",
            "担当者分担を明確化",
        ],
        "試験頻出": [
            f"{topic}の逆転肢パターンを分類",
            "条件文の主語を下線",
            "数値+条件のセット暗記",
        ],
        "判例・ガイド": [
            f"{topic}のガイドと条文の対応",
            "通知・通達の位置づけ確認",
            "優先順位を表で整理",
        ],
        "横断総合": [
            f"{topic}と関連制度の違い",
            "横断マップで弱点可視化",
            "直前は誤答型の反復",
        ],
    }
    pts = pools.get(angle, pools["試験頻出"])
    start = _variant_index(slug, len(pts))
    return ";".join(pts[start:] + pts[:start])


def _mistake_common(topic: str, terms: list[str], slug: str) -> str:
    opts = [
        f"{topic}の主体を固定せずに暗記",
        f"{terms[0] if terms else topic}と類似制度を混同",
        "手順を省略したまま正解と判断",
        "記録・報告義務を見落とす",
        "旧要項・旧数値をそのまま適用",
    ]
    i = _variant_index(slug, len(opts))
    return ";".join([opts[i], opts[(i + 1) % len(opts)], opts[(i + 2) % len(opts)]])


def _memory_tip(topic: str, angle: str) -> str:
    tips = {
        "基礎整理": f"「{topic}＝定義→主体→対象」",
        "実務連動": f"「{topic}＝確認→実施→記録」",
        "試験頻出": f"「{topic}＝主語→条件→数値」",
        "判例・ガイド": f"「{topic}＝条文→ガイド→事例」",
        "横断総合": f"「{topic}＝関連制度と境界線」",
    }
    return tips.get(angle, f"「{topic}を表で整理」")


def _faq_mistake(row: dict[str, str], topic: str, angle: str) -> None:
    terms = _topic_terms(row)
    t0 = terms[0] if terms else topic
    row["faq_1_question"] = f"「{row.get('title', topic)}」で最初に確認すべき点は？"
    row["faq_1_answer"] = (
        f"{topic}では{t0}の義務主体と実施タイミングを先に固定してください。"
        f"{angle}の観点では、比較表の1行目に「誰が・いつ・何を」を書くと誤答が減ります。"
    )
    row["faq_2_question"] = f"「{topic}」の典型誤答パターンは？"
    row["faq_2_answer"] = (
        f"{row.get('confusion_point', '')} "
        f"過去問では{t0}に関する逆転肢や、類似制度の数値流用に注意してください。"
    )
    row["faq_3_question"] = f"「{topic}」の復習の進め方（{angle}）は？"
    row["faq_3_answer"] = (
        LEAD_BY_ANGLE.get(angle, LEAD_BY_ANGLE["試験頻出"]).format(topic=topic)
        + " 誤答した設問は原因（主体・手順・数値・記録）をタグ付けして再演習してください。"
    )
    row["faq_4_question"] = f"「{topic}」の関連条文・資料は？"
    row["faq_4_answer"] = (
        f"用語集の「{t0}」と関連法令・試験要項を照合してください。"
        " 直前は誤答ノートと本ページを往復し、同型の引っかけを連続で解いてください。"
    )


def _confusion_for_row(row: dict[str, str], topic: str, angle: str) -> str:
    t1, t2 = _mistake_pair_terms(row)
    by_angle = {
        "基礎整理": f"「{t1}」と「{t2}」の定義・目的を取り違え、同一制度と短絡しやすい。",
        "実務連動": f"「{t1}」と「{t2}」の実施主体・手続順序（誰が・いつ・何を）を混同しやすい。",
        "試験頻出": f"「{t1}」と「{t2}」の過去問で、主語・数値・条件文が入れ替わる肢に注意。",
        "判例・ガイド": f"「{t1}」と「{t2}」について、法令条文と通知・ガイドラインの関係を誤解しやすい。",
        "横断総合": f"「{t1}」と「{t2}」の境界が曖昧になり、総合問題で誤答しやすい。",
    }
    base = by_angle.get(angle, by_angle["試験頻出"])
    related = [x.strip() for x in (row.get("related_terms") or "").split(";") if x.strip()]
    if related and related[0] not in base and related[0] not in (t1, t2):
        base = base.rstrip("。") + f"。関連する「{related[0]}」との違いもセットで確認してください。"
    return base


def _summary_mistake(row: dict[str, str], topic: str, angle: str) -> str:
    label = _clean_public_title(_strip_angle_suffix(row.get("title", "")))
    return (
        f"「{label}」（{angle}）で出やすい誤答を、"
        "主体の取り違え・手順の前後逆・数値の単独暗記・記録省略の4型に分けて整理します。"
    )


def _summary_compare(t1: str, t2: str, topic: str, angle: str) -> str:
    return (
        f"「{t1}」と「{t2}」（{angle}）について、"
        "目的・主体・手続・数値・試験論点の5軸で違いを比較します。"
    )


def _summary_numbers(row: dict[str, str], topic: str, angle: str) -> str:
    label = _clean_public_title(_strip_angle_suffix(row.get("title", "")))
    nuance = _title_nuance(row)
    focus = f"{nuance}の" if nuance else ""
    return (
        f"「{label}」で押さえる{focus}代表数値・条件・記録要件を、"
        f"{angle}の観点で表に整理します。"
    )


def _personalize_confusion_point(row: dict[str, str]) -> None:
    batch = _batch_num(row.get("slug", ""))
    if batch is None or batch < 35 or "confusion_point" not in row:
        return
    cp = (row.get("confusion_point") or "").strip()
    if cp and not _is_template_confusion(cp):
        return
    topic = _core_topic(_clean_public_title(_strip_angle_suffix(row.get("title", ""))))
    angle = ANGLE_BY_BATCH.get(batch, "試験頻出")
    row["confusion_point"] = _confusion_for_row(row, topic, angle)


def _patterns_need_refresh(row: dict[str, str]) -> bool:
    if _is_generic_mistake(row):
        return True
    if _has_handcrafted_mistake_patterns(row):
        return False
    return _is_template_mistake_patterns(row)


def _diversify_mistake(row: dict[str, str]) -> None:
    batch = _batch_num(row.get("slug", ""))
    if batch is None or batch < 35:
        return
    topic = _core_topic(_clean_public_title(_strip_angle_suffix(row.get("title", ""))))
    angle = ANGLE_BY_BATCH.get(batch, "試験頻出")
    terms = _topic_terms(row)
    slug = row.get("slug", "")
    if _is_generic_mistake(row):
        row["confusion_point"] = _confusion_for_row(row, topic, angle)
        row["summary"] = _summary_mistake(row, topic, angle)
        row["pattern_rows"] = json.dumps(_mistake_patterns(row, topic, terms, angle, slug), ensure_ascii=False)
        row["article_lead"] = LEAD_BY_ANGLE[angle].format(topic=topic)
        row["exam_points"] = _mistake_exam_points(topic, angle, slug)
        row["common_mistakes"] = _mistake_common(topic, terms, slug)
        row["memory_tip"] = _memory_tip(topic, angle)
        if not row.get("article_title"):
            row["article_title"] = f"{row.get('title', topic)}｜誤答パターン"
        if _faqs_need_rewrite(row):
            _faq_mistake(row, topic, angle)
    elif _patterns_need_refresh(row):
        _refresh_mistake_patterns(row)
    _personalize_confusion_point(row)
    _apply_batch_angle_title(row, batch)


def _refresh_mistake_patterns(row: dict[str, str]) -> None:
    batch = _batch_num(row.get("slug", ""))
    if batch is None or batch < 35 or "confusion_point" not in row:
        return
    topic = _core_topic(_clean_public_title(_strip_angle_suffix(row.get("title", ""))))
    angle = ANGLE_BY_BATCH.get(batch, "試験頻出")
    terms = _topic_terms(row)
    row["pattern_rows"] = json.dumps(
        _mistake_patterns(row, topic, terms, angle, row.get("slug", "")),
        ensure_ascii=False,
    )


def _apply_batch_angle_title(row: dict[str, str], batch: int | None) -> None:
    if batch is None or batch < 35:
        return
    angle = ANGLE_BY_BATCH.get(batch, "試験頻出")
    base = _strip_angle_suffix(row.get("title", ""))
    if base and f"（{angle}）" not in base:
        row["title"] = f"{base}（{angle}）"


def _is_generic_compare(row: dict[str, str]) -> bool:
    lead = (row.get("article_lead") or "").strip()
    if "義務主体・実施手順・記録保存" in lead:
        return True
    if lead.startswith("比較表で") and "整理" in lead and len(lead) < 80:
        return True
    try:
        axes = json.loads(row.get("compare_rows") or "[]")
    except json.JSONDecodeError:
        return False
    if len(axes) < 2:
        return False
    labels = {(a.get("axis"), tuple(a.get("cols") or [])) for a in axes}
    for generic in GENERIC_CMP_AXES:
        if (generic[0], tuple(generic[1])) in labels:
            return True
    return "観点A" in (row.get("col_labels") or "")


def _faq_compare(row: dict[str, str], topic: str, angle: str) -> None:
    t1, t2 = _compare_pair_terms(row)
    row["faq_1_question"] = f"「{t1}」と「{t2}」の違いは何ですか？"
    row["faq_1_answer"] = (
        f"{topic}（{angle}）では、比較表の5軸（目的・主体・手続・数値・試験論点）で"
        f"{t1}と{t2}を並べ、主語と条件文の差を確認してください。"
    )
    row["faq_2_question"] = f"「{topic}」の比較表の使い方は？"
    row["faq_2_answer"] = (
        LEAD_BY_ANGLE.get(angle, LEAD_BY_ANGLE["試験頻出"]).format(topic=topic)
        + " 過去問で入れ替わった肢は、表のどの行が逆転したかをメモしてください。"
    )
    row["faq_3_question"] = f"「{topic}」で試験に出やすい混同は？"
    row["faq_3_answer"] = (
        f"{row.get('common_mistakes', '')} "
        f"名称だけで判断せず、{t1}と{t2}それぞれの義務主体を条文で確認してください。"
    )
    row["faq_4_question"] = f"「{topic}」の直前復習（{angle}）は？"
    row["faq_4_answer"] = (
        f"比較表を見ずに{t1}と{t2}の違いを口述し、"
        " 誤答した設問は逆転した軸（主体・手順・数値）をタグ付けして再演習してください。"
    )


def _compare_rows(row: dict[str, str], topic: str, terms: list[str], angle: str) -> list[dict[str, Any]]:
    t1, t2 = _compare_pair_terms(row)
    if t1 == t2:
        t2 = f"{t1}の関連制度"
    pools: dict[str, list[tuple[str, list[str]]]] = {
        "基礎整理": [
            ("目的", [f"{t1}の目的", f"{t2}の目的"]),
            ("主体", [f"{t1}の義務者", f"{t2}の義務者"]),
            ("対象", [f"{t1}の適用範囲", f"{t2}の適用範囲"]),
            ("手続", [f"{t1}の手続", f"{t2}の手続"]),
            ("試験", [f"{t1}の頻出論点", f"{t2}との混同点"]),
        ],
        "実務連動": [
            ("フロー", [f"{t1}の実施順", f"{t2}の実施順"]),
            ("記録", [f"{t1}の記録", f"{t2}の記録"]),
            ("連携", [f"{t1}の関係者", f"{t2}の関係者"]),
            ("異常時", [f"{t1}の対応", f"{t2}の対応"]),
            ("試験", [f"実務→試験の変換", f"手順省略肢"]),
        ],
        "試験頻出": [
            ("論点", [f"{t1}の条文", f"{t2}の条文"]),
            ("数値", [f"{t1}の数値", f"{t2}の数値"]),
            ("条件", [f"{t1}の要件", f"{t2}の要件"]),
            ("逆転", [f"{t1}の正答型", f"逆転肢の例"]),
            ("混同", [f"{t1}と{t2}の境界", "名称だけの判断"]),
        ],
        "判例・ガイド": [
            ("根拠", [f"{t1}の法令", f"{t2}の法令"]),
            ("ガイド", [f"{t1}の指針", f"{t2}の指針"]),
            ("運用", [f"{t1}の実務解釈", f"{t2}の実務解釈"]),
            ("更新", [f"{t1}の改定点", f"{t2}の改定点"]),
            ("試験", [f"条文×ガイド", "旧通知の流用"]),
        ],
        "横断総合": [
            ("制度", [f"{t1}の位置づけ", f"{t2}の位置づけ"]),
            ("関係", [f"{t1}との連携", f"{t2}との連携"]),
            ("リスク", [f"{t1}の違反リスク", f"{t2}の違反リスク"]),
            ("総合", [f"横断マップ上の{t1}", f"横断マップ上の{t2}"]),
            ("直前", [f"弱点チェック", "同型誤答の再確認"]),
        ],
    }
    return [{"axis": a, "cols": c} for a, c in pools.get(angle, pools["試験頻出"])]


ANGLE_COL_FOCUS: dict[str, tuple[str, str]] = {
    "基礎整理": ("定義・目的", "主体・対象"),
    "実務連動": ("実施手順", "記録・報告"),
    "試験頻出": ("頻出論点", "逆転肢"),
    "判例・ガイド": ("法令根拠", "ガイド・通知"),
    "横断総合": ("制度位置づけ", "類似制度との違い"),
}


def _strip_angle_suffix(title: str) -> str:
    t = BATCH_SUFFIX_RE.sub("", title or "").strip()
    t = TRAILING_BATCH_TITLE_RE.sub("", t).strip()
    for angle in ANGLE_BY_BATCH.values():
        suffix = f"（{angle}）"
        if t.endswith(suffix):
            t = t[: -len(suffix)].strip()
    return t


def _strip_paren_suffix(text: str) -> str:
    return re.sub(r"（[^）]*）$", "", (text or "").strip()).strip() or text


def _reader_disambig(row: dict[str, str], slug: str) -> str:
    """読者向けの短い差別化ラベル（slug英字は使わない）."""
    if "mgmt-compare" in slug or re.search(r"-mgmt(?:-|$)", slug):
        return "管理措置"
    terms = _topic_terms(row)
    if terms:
        return terms[0]
    base = _strip_angle_suffix(row.get("title", ""))
    if "：" in base:
        return base.split("：", 1)[0].strip()
    return "整理"


def _ensure_compare_content(row: dict[str, str]) -> None:
    batch = _batch_num(row.get("slug", ""))
    if batch is None or batch < 35:
        return
    base_title = _strip_angle_suffix(row.get("title", ""))
    topic = _core_topic(base_title)
    angle = ANGLE_BY_BATCH.get(batch, "試験頻出")
    terms = _topic_terms(row)
    t1, t2 = _compare_pair_terms(row)
    if t1 == t2:
        t2 = terms[1] if len(terms) > 1 and terms[1] != t1 else f"{t1}の関連手続"

    row["col_labels"] = f"{t1};{t2}"
    row["compare_rows"] = json.dumps(_compare_rows(row, topic, terms, angle), ensure_ascii=False)
    row["summary"] = _summary_compare(t1, t2, topic, angle)
    if not row.get("article_lead") or len((row.get("article_lead") or "")) < 40:
        row["article_lead"] = LEAD_BY_ANGLE[angle].format(topic=topic or t1)
    row["exam_points"] = _mistake_exam_points(topic or t1, angle, row.get("slug", ""))
    row["common_mistakes"] = _mistake_common(topic or t1, terms, row.get("slug", ""))
    row["memory_tip"] = _memory_tip(topic or t1, angle)


def _apply_compare_batch_angle(row: dict[str, str]) -> None:
    batch = _batch_num(row.get("slug", ""))
    if batch is None or batch < 35:
        return
    angle = ANGLE_BY_BATCH.get(batch, "試験頻出")
    base_title = _strip_angle_suffix(row.get("title", ""))
    if base_title and f"（{angle}）" not in base_title:
        row["title"] = f"{base_title}（{angle}）"

    parts = [p.strip() for p in (row.get("col_labels") or "").split(";") if p.strip()]
    if len(parts) >= 2:
        f1, f2 = ANGLE_COL_FOCUS.get(angle, ("観点A", "観点B"))
        c1 = _strip_paren_suffix(parts[0])
        c2 = _strip_paren_suffix(parts[1])
        if c1 == c2:
            t1, t2 = _compare_pair_terms(row)
            c1, c2 = t1, t2
        row["col_labels"] = f"{c1}（{f1}）;{c2}（{f2}）"

    try:
        axes = json.loads(row.get("compare_rows") or "[]")
    except json.JSONDecodeError:
        axes = []
    if axes:
        focus = ANGLE_COL_FOCUS.get(angle, ("整理", "確認"))[0]
        for axis_row in axes:
            axis_name = _strip_paren_suffix(axis_row.get("axis") or "")
            if focus not in axis_name:
                axis_row["axis"] = f"{axis_name}（{focus}）"
            cols = axis_row.get("cols") or []
            axis_row["cols"] = [_strip_paren_suffix(c) for c in cols]
        row["compare_rows"] = json.dumps(axes, ensure_ascii=False)

    topic = _core_topic(base_title)
    if topic and not row.get("summary"):
        row["summary"] = f"{topic}（{angle}）について、比較表で違いを整理します。"


def _compare_needs_refresh(row: dict[str, str]) -> bool:
    if _is_generic_compare(row):
        return True
    parts = [_strip_paren_suffix(p.strip()) for p in (row.get("col_labels") or "").split(";") if p.strip()]
    if any(p in GENERIC_COMPARE_LABELS for p in parts):
        return True
    try:
        axes = json.loads(row.get("compare_rows") or "[]")
    except json.JSONDecodeError:
        return False
    for axis_row in axes:
        cols = axis_row.get("cols") or []
        if len(cols) >= 2 and cols[0] == cols[1]:
            return True
    return False


def _diversify_compare(row: dict[str, str]) -> None:
    batch = _batch_num(row.get("slug", ""))
    if batch is None or batch < 35:
        return
    if _compare_needs_refresh(row):
        base_title = _strip_angle_suffix(row.get("title", ""))
        topic = _core_topic(base_title)
        angle = ANGLE_BY_BATCH.get(batch, "試験頻出")
        terms = _topic_terms(row)
        t1, t2 = _compare_pair_terms(row)
        row["title"] = f"{base_title or topic}（{angle}）"
        row["col_labels"] = f"{t1};{t2}"
        row["compare_rows"] = json.dumps(_compare_rows(row, topic, terms, angle), ensure_ascii=False)
        row["summary"] = _summary_compare(t1, t2, topic, angle)
        row["article_lead"] = LEAD_BY_ANGLE[angle].format(topic=topic)
        row["exam_points"] = _mistake_exam_points(topic, angle, row.get("slug", ""))
        row["common_mistakes"] = _mistake_common(topic, terms, row.get("slug", ""))
        row["memory_tip"] = _memory_tip(topic, angle)
        if _faqs_need_rewrite(row):
            _faq_compare(row, topic, angle)
    _apply_compare_batch_angle(row)


def _is_generic_numbers(row: dict[str, str]) -> bool:
    hl = (row.get("highlight") or "").strip()
    if hl in ("代表値は要項・法令で確認", "要項・法令で確認"):
        return True
    cm = (row.get("common_mistakes") or "").strip()
    if cm == "数値だけ暗記;手順省略;主体混同":
        return True
    try:
        items = json.loads(row.get("item_rows") or "[]")
    except json.JSONDecodeError:
        return False
    if not items:
        return False
    notes = [i.get("note", "") for i in items]
    if notes.count("試験要点を確認") >= 3:
        return True
    if notes.count("試験頻出") >= 3 and len(set(i.get("item") for i in items)) <= 2:
        return True
    return False


def _faq_numbers(row: dict[str, str], topic: str, angle: str) -> None:
    terms = _topic_terms(row)
    t0 = terms[0] if terms else topic
    row["faq_1_question"] = f"「{topic}」で確認すべき数値・条件は？"
    row["faq_1_answer"] = (
        f"{topic}（{angle}）では{t0}に関する数値だけでなく、"
        "義務主体・実施条件・記録保存までセットで確認してください。"
    )
    row["faq_2_question"] = f"「{topic}」の数値暗記のコツは？"
    row["faq_2_answer"] = (
        f"{row.get('memory_tip', '')} "
        "数値は条文・試験要項の表と照合し、旧要項との差分は更新日付で管理してください。"
    )
    row["faq_3_question"] = f"「{topic}」の典型誤答は？"
    row["faq_3_answer"] = (
        f"{row.get('common_mistakes', '')} "
        f"{angle}では条件文の主語と数値が入れ替わる肢に注意してください。"
    )
    row["faq_4_question"] = f"「{topic}」の関連資料は？"
    row["faq_4_answer"] = (
        f"用語集の「{t0}」、関連法令・試験要項、直近の通知・ガイドラインを照合してください。"
        " 直前は本ページの確認表と過去問を往復してください。"
    )


def _rich_number_items(row: dict[str, str], topic: str, terms: list[str], angle: str) -> list[dict[str, str]]:
    label = _clean_public_title(_strip_angle_suffix(row.get("title", "")))
    nuance = _title_nuance(row)
    related = [x.strip() for x in (row.get("related_terms") or "").split(";") if x.strip()]
    ref = related[0] if related else (terms[0] if terms else topic)
    slug = row.get("slug", "")
    shift = _variant_index(slug, 4)

    rows_spec = [
        (
            "確認テーマ",
            label or topic,
            {
                "基礎整理": "定義と主体を条文で確認",
                "実務連動": "現場フロー上の位置づけ",
                "試験頻出": "条件文の主語を下線",
                "判例・ガイド": "通知・ガイドとの対応",
                "横断総合": "関連制度との境界",
            }.get(angle, "試験要点"),
        ),
        (
            "数値・条件",
            f"{nuance or '基準値'}は試験要項・省令で確認",
            {
                "基礎整理": "単位と適用条件をセット",
                "実務連動": "記録様式と照合",
                "試験頻出": "逆転肢の数値混同に注意",
                "判例・ガイド": "改正差分を更新日で管理",
                "横断総合": "類似制度の数値流用に注意",
            }.get(angle, "数値+条件で暗記"),
        ),
        (
            "関連制度",
            ref,
            "横串の比較表と併読",
        ),
        (
            "記録・保存",
            {
                "基礎整理": "定義確認のメモ",
                "実務連動": "運転日誌・報告書",
                "試験頻出": "過去問の条件メモ",
                "判例・ガイド": "条文×通知の対応表",
                "横断総合": "弱点タグ付きノート",
            }.get(angle, "学習記録"),
            "異常時は原因を併記",
        ),
        (
            "試験の確認点",
            {
                "基礎整理": "主語→目的→対象",
                "実務連動": "誰が・いつ・何を",
                "試験頻出": "逆転肢の型分類",
                "判例・ガイド": "優先関係の整理",
                "横断総合": "同型誤答の再演習",
            }.get(angle, "過去問で型確認"),
            f"{angle}の観点で口述",
        ),
    ]
    rotated = rows_spec[shift:] + rows_spec[:shift]
    return [{"item": a, "value": b, "note": c} for a, b, c in rotated]


def _number_items(topic: str, terms: list[str], angle: str) -> list[dict[str, str]]:
    labels = ["義務主体", "実施・頻度", "記録・保存", "試験の確認点", "関連制度"]
    out: list[dict[str, str]] = []
    for i, label in enumerate(labels):
        term = terms[i % len(terms)] if terms else topic
        note_by_angle = {
            "基礎整理": "定義・主体を確認",
            "実務連動": "フロー上の位置づけ",
            "試験頻出": "数値・条件のセット",
            "判例・ガイド": "条文・通知を照合",
            "横断総合": "関連制度とセット",
        }
        out.append(
            {
                "item": label,
                "value": term,
                "note": note_by_angle.get(angle, "試験要点を確認"),
            }
        )
    return out


def _refresh_numbers_highlight(row: dict[str, str]) -> None:
    try:
        items = json.loads(row.get("item_rows") or "[]")
    except json.JSONDecodeError:
        items = []
    label = _clean_public_title(_strip_angle_suffix(row.get("title", "")))
    parts: list[str] = []
    for item in items[:3]:
        val = (item.get("value") or "").strip()
        name = (item.get("item") or "").strip()
        if val:
            parts.append(f"{name}：{val}" if name else val)
    if parts:
        row["highlight"] = f"{label} — {' / '.join(parts[:2])}"
    elif label:
        row["highlight"] = f"{label}（試験要項・省令で数値確認）"


def _diversify_numbers(row: dict[str, str]) -> None:
    batch = _batch_num(row.get("slug", ""))
    if batch is None or batch < 35:
        if (row.get("highlight") or "").strip() in GENERIC_NUMBER_HIGHLIGHTS:
            _enrich_numbers_highlight(row)
        return
    topic = _core_topic(_clean_public_title(row.get("title", "")))
    angle = ANGLE_BY_BATCH.get(batch, "試験頻出")
    terms = _topic_terms(row)
    row["item_rows"] = json.dumps(_rich_number_items(row, topic, terms, angle), ensure_ascii=False)
    _refresh_numbers_highlight(row)
    row["summary"] = _summary_numbers(row, topic, angle)
    row["article_lead"] = (
        f"「{_clean_public_title(_strip_angle_suffix(row.get('title', '')))}」では、"
        "数値だけでなく義務主体・実施条件・記録保存まで一体で確認してください。"
        + LEAD_BY_ANGLE[angle].format(topic=topic)
    )
    row["exam_points"] = _mistake_exam_points(topic, angle, row.get("slug", ""))
    row["common_mistakes"] = _mistake_common(topic, terms, row.get("slug", ""))
    row["memory_tip"] = _memory_tip(topic, angle)
    if _faqs_need_rewrite(row):
        _faq_numbers(row, topic, angle)
    _apply_batch_angle_title(row, batch)


def _slug_series_label(slug: str) -> str:
    """タイトル衝突時のみ。読者向け日本語ラベル."""
    if "mgmt-compare" in slug or re.search(r"-mgmt(?:-|$)", slug):
        return "管理措置"
    return ""


def _dedupe_compare_titles(rows: list[dict[str, str]]) -> None:
    compare_rows = [
        r
        for r in rows
        if "compare_rows" in r and (_batch_num(r.get("slug", "")) or 0) >= 35
    ]
    by_title: dict[str, list[dict[str, str]]] = {}
    for row in compare_rows:
        by_title.setdefault(row.get("title", ""), []).append(row)
    for group in by_title.values():
        if len(group) < 2:
            continue
        for row in group:
            batch = _batch_num(row.get("slug", ""))
            angle = ANGLE_BY_BATCH.get(batch or 0, "試験頻出")
            slug = row.get("slug", "")
            base = _strip_angle_suffix(row.get("title", ""))
            label = _reader_disambig(row, slug)
            if "：" in base:
                head, tail = base.split("：", 1)
                tail = tail.replace("の比較", "").strip()
                if label and label not in tail and label != head:
                    new_base = f"{head}：{label}と{tail}の比較"
                else:
                    new_base = base if base.endswith("比較") else f"{base}の比較"
            else:
                topic = base.replace("の比較", "").strip() or base
                new_base = f"{topic}：{label}の比較"
            row["title"] = f"{new_base}（{angle}）"
            _apply_compare_batch_angle(row)


def _dedupe_mistake_titles(rows: list[dict[str, str]]) -> None:
    mistake_rows = [
        r
        for r in rows
        if "confusion_point" in r and (_batch_num(r.get("slug", "")) or 0) >= 35
    ]
    by_title: dict[str, list[dict[str, str]]] = {}
    for row in mistake_rows:
        by_title.setdefault(row.get("title", ""), []).append(row)
    for group in by_title.values():
        if len(group) < 2:
            continue
        for row in group:
            batch = _batch_num(row.get("slug", ""))
            angle = ANGLE_BY_BATCH.get(batch or 0, "試験頻出")
            slug = row.get("slug", "")
            base = _strip_angle_suffix(row.get("title", ""))
            label = _reader_disambig(row, slug)
            core = base.replace("の典型誤答", "").strip()
            if "：" in core:
                head, tail = core.split("：", 1)
                if label and label not in tail and label != head:
                    new_base = f"{head}：{label}・{tail}"
                else:
                    new_base = core
            else:
                new_base = f"{core}：{label}"
            row["title"] = f"{new_base}（{angle}）"


def _dedupe_numbers_titles(rows: list[dict[str, str]]) -> None:
    num_rows = [
        r
        for r in rows
        if "item_rows" in r and "highlight" in r and (_batch_num(r.get("slug", "")) or 0) >= 35
    ]
    by_title: dict[str, list[dict[str, str]]] = {}
    for row in num_rows:
        by_title.setdefault(row.get("title", ""), []).append(row)
    for group in by_title.values():
        if len(group) < 2:
            continue
        for row in group:
            batch = _batch_num(row.get("slug", ""))
            angle = ANGLE_BY_BATCH.get(batch or 0, "試験頻出")
            slug = row.get("slug", "")
            base = _strip_angle_suffix(row.get("title", ""))
            label = _reader_disambig(row, slug)
            if "：" in base:
                head, tail = base.split("：", 1)
                if label and label not in tail and label != head:
                    row["title"] = f"{head}：{label}・{tail}（{angle}）"
                else:
                    row["title"] = f"{base}（{angle}）"
            else:
                row["title"] = f"{base}：{label}（{angle}）"


def _dedupe_compare_col_labels(rows: list[dict[str, str]]) -> None:
    by_batch: dict[int, dict[str, list[dict[str, str]]]] = {}
    for row in rows:
        if "compare_rows" not in row:
            continue
        batch = _batch_num(row.get("slug", ""))
        if batch is None or batch < 35:
            continue
        key = row.get("col_labels", "")
        by_batch.setdefault(batch, {}).setdefault(key, []).append(row)
    for batch_rows in by_batch.values():
        for group in batch_rows.values():
            if len(group) < 2:
                continue
            for row in group:
                batch = _batch_num(row.get("slug", ""))
                angle = ANGLE_BY_BATCH.get(batch or 0, "試験頻出")
                topic = _core_topic(_strip_angle_suffix(row.get("title", "")))
                terms = _topic_terms(row)
                label = _clean_public_title(_strip_angle_suffix(row.get("title", "")))
                t1, t2 = _compare_pair_terms(row)
                if label and label not in (t1, t2):
                    t1 = label
                row["col_labels"] = f"{t1};{t2}"
                row["compare_rows"] = json.dumps(
                    _compare_rows(row, topic, terms, angle), ensure_ascii=False
                )
                row["summary"] = _summary_compare(t1, t2, topic, angle)
                _apply_compare_batch_angle(row)


def _apply_row_faqs(row: dict[str, str]) -> None:
    batch = _batch_num(row.get("slug", ""))
    if batch is None or batch < 35:
        return
    if not _faqs_need_rewrite(row):
        return
    base = _strip_angle_suffix(row.get("title", ""))
    topic = _core_topic(base)
    angle = ANGLE_BY_BATCH.get(batch, "試験頻出")
    if "confusion_point" in row:
        _faq_mistake(row, topic, angle)
    elif "compare_rows" in row:
        _faq_compare(row, topic, angle)
    elif "highlight" in row and "item_rows" in row:
        _faq_numbers(row, topic, angle)


def diversify_hub_row(row: dict[str, str]) -> dict[str, str]:
    batch = _batch_num(row.get("slug", ""))
    if batch is not None and batch >= 35:
        if "confusion_point" in row:
            _diversify_mistake(row)
        elif "compare_rows" in row:
            _diversify_compare(row)
        elif "highlight" in row and "item_rows" in row:
            _diversify_numbers(row)
        _apply_row_faqs(row)
    elif "highlight" in row and "item_rows" in row:
        if (row.get("highlight") or "").strip() in GENERIC_NUMBER_HIGHLIGHTS:
            _enrich_numbers_highlight(row)
    return row


def _differentiate_duplicate_patterns(row: dict[str, str]) -> None:
    try:
        patterns = json.loads(row.get("pattern_rows") or "[]")
    except json.JSONDecodeError:
        return
    if not patterns:
        return
    title = (row.get("title") or "").strip()
    topic = _core_topic(title)
    label = title.split("：")[0].strip() if "：" in title else topic
    terms = _topic_terms(row)
    shift = _variant_index(row.get("slug", ""), max(len(patterns), 1))
    for j, p in enumerate(patterns):
        term = terms[(j + shift) % len(terms)] if terms else topic
        anchor = label if label not in (term, topic) else term
        wrong = (p.get("wrong") or "").strip()
        correct = (p.get("correct") or "").strip()
        if anchor not in wrong:
            p["wrong"] = f"【{anchor}】{wrong}" if wrong else anchor
        if anchor not in correct:
            p["correct"] = f"【{anchor}】→{correct}" if correct else anchor
    row["pattern_rows"] = json.dumps(patterns, ensure_ascii=False)


def _dedupe_mistake_patterns(rows: list[dict[str, str]]) -> None:
    by_batch: dict[int, dict[str, list[dict[str, str]]]] = {}
    for row in rows:
        if "confusion_point" not in row:
            continue
        batch = _batch_num(row.get("slug", ""))
        if batch is None or batch < 35:
            continue
        pat = row.get("pattern_rows", "")
        by_batch.setdefault(batch, {}).setdefault(pat, []).append(row)
    for batch_rows in by_batch.values():
        for group in batch_rows.values():
            if len(group) < 2:
                continue
            for row in group:
                batch = _batch_num(row.get("slug", "")) or 0
                angle = ANGLE_BY_BATCH.get(batch, "試験頻出")
                topic = _core_topic(_strip_angle_suffix(row.get("title", "")))
                terms = _topic_terms(row)
                row["pattern_rows"] = json.dumps(
                    _mistake_patterns(row, topic, terms, angle, row.get("slug", "")),
                    ensure_ascii=False,
                )


BATCH_EARLY_LABEL: dict[int, str] = {
    30: "基礎",
    31: "整理",
    32: "構造・取扱い",
    33: "取扱い深掘り",
    34: "試験頻出",
}


def _resolve_title_collisions(rows: list[dict[str, str]]) -> None:
    by_title: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        batch = _batch_num(row.get("slug", ""))
        if batch is not None and batch >= 35:
            continue
        by_title[(row.get("title") or "").strip()].append(row)
    for title, group in by_title.items():
        if len(group) < 2 or not title:
            continue
        for row in group:
            batch = _batch_num(row.get("slug", ""))
            label = BATCH_EARLY_LABEL.get(batch or 0) or _reader_disambig(row, row.get("slug", ""))
            if label and f"（{label}）" not in title:
                row["title"] = f"{title}（{label}）"


def diversify_hub_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    _resolve_title_collisions(rows)
    for row in rows:
        diversify_hub_row(row)
    _dedupe_mistake_patterns(rows)
    _dedupe_compare_col_labels(rows)
    _dedupe_compare_titles(rows)
    _dedupe_mistake_titles(rows)
    _dedupe_numbers_titles(rows)
    return rows
