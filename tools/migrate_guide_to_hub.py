#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験ガイドから知識ハブ（比較・数値）への本文移管と橋渡しガイド化."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from tools.content_placement_rules import norm

# 監査 false positive — 試験ガイドに残す
SKIP_MIGRATE_SLUGS = frozenset(
    {
        "mistake-notebook",  # 間違い「ノート」≠ 比較
        "cbt-computer-exam",  # カタログ: 出題・形式
        "compare-similar-qualifications",  # 併願戦略付きガイド
    }
)

COMPARE_SUBJECTS: dict[str, tuple[str, str, str]] = {
    # slug: (subject_a, subject_b, category)
    "takken-hikaku": ("宅建", "FP・マンション管理士等", "試験制度"),
    "operator-vs-engineer": ("ボイラー取扱作業主任者", "2級ボイラー技士", "試験制度"),
    "steam-properties-guide": ("飽和蒸気", "過熱蒸気・湿り蒸気", "ボイラーの構造"),
    "forced-circulation-boiler": ("強制循環", "自然循環", "ボイラーの構造"),
    "teiki-shakka-guide": ("定期借家", "普通借家", "借地借家法"),
    "sangyoui-senmon-eisei": ("産業医", "衛生管理者", "労働安全衛生法"),
    "1shu-2shu-chigai": ("第一種衛生管理者", "第二種衛生管理者", "試験制度"),
    "hogo-gu-mask-sentei": ("防じんマスク", "防毒マスク", "労働安全衛生法"),
    "hoshano-kakutei-kakuritsu": ("確定的影響", "確率的影響", "放射線"),
    "hoshu-bunseki-vs-chokusetsu": ("捕集分析法", "直接読み取り式", "作業環境測定"),
    "tokubetsu-kyoiku-chigai": ("特別教育", "職長教育", "労働安全衛生法"),
    "tokubetsu-kyoiku-jugyomae": ("特別教育", "雇入れ時教育", "労働安全衛生法"),
}

NUMBERS_MIGRATE_SLUGS = frozenset({"takken-tokkuten", "kankei-horei-matome"})

HUB_BRIDGE_GENRE = "用語ハブ活用法"
HUB_BRIDGE_NOTE = "配置整理: 比較・数値の正本は知識ハブ。本記事は導線用"


def guide_sections(guide: dict[str, str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for n in range(1, 8):
        heading = norm(guide.get(f"section_{n}_heading"))
        body = norm(guide.get(f"section_{n}_body"))
        if heading or body:
            out.append((heading or f"論点{n}", body))
    return out


def parse_compare_subjects(guide: dict[str, str]) -> tuple[str, str, str]:
    slug = norm(guide.get("slug"))
    if slug in COMPARE_SUBJECTS:
        a, b, cat = COMPARE_SUBJECTS[slug]
        return a, b, cat
    title = norm(guide.get("title"))
    m = re.search(r"(.+?)と(.+?)の違い", title)
    if m:
        return m.group(1).strip(), m.group(2).strip(), norm(guide.get("genre")) or "法令・制度"
    m = re.search(r"(.+?)【.+】(.+?)を比較", title)
    if m:
        return m.group(1).strip(), m.group(2).strip(), "試験制度"
    return "項目A", "項目B", norm(guide.get("genre")) or "法令・制度"


def guide_to_compare_row(guide: dict[str, str]) -> dict[str, str]:
    slug = norm(guide.get("slug"))
    title = norm(guide.get("title"))
    subject_a, subject_b, category = parse_compare_subjects(guide)
    sections = guide_sections(guide)
    compare_rows: list[dict] = [
        {
            "axis": "概要",
            "cols": [norm(guide.get("lead"))[:600] or f"{subject_a}と{subject_b}の違い", ""],
        }
    ]
    for heading, body in sections[:6]:
        compare_rows.append(
            {
                "axis": heading[:40],
                "cols": [body[:900], ""],
            }
        )
    if len(compare_rows) < 3:
        compare_rows.append(
            {"axis": "試験での見方", "cols": [norm(guide.get("user_intent"))[:500], ""]}
        )

    tags = norm(guide.get("tags")) or "整理;用語"
    related = f"{subject_a};{subject_b}"
    return {
        "slug": slug,
        "title": title,
        "category": category,
        "tags": tags,
        "summary": norm(guide.get("lead"))[:120] or f"{subject_a}と{subject_b}の違いを表で整理します。",
        "col_labels": f"{subject_a};{subject_b}",
        "compare_rows": json.dumps(compare_rows, ensure_ascii=False),
        "article_title": title,
        "article_lead": norm(guide.get("lead"))[:500],
        "exam_points": "選択肢の言い換えに注意する;数値・期限・主体をセットで確認する",
        "common_mistakes": norm(guide.get("section_1_body"))[:200]
        or f"{subject_a}と{subject_b}を混同すると誤答になりやすいです。",
        "memory_tip": f"{subject_a}と{subject_b}の役割差を短いフレーズで対比してください。",
        "related_terms": related,
        "faq_1_question": norm(guide.get("faq_1_question")) or f"{subject_a}と{subject_b}の違いは？",
        "faq_1_answer": norm(guide.get("faq_1_answer")) or norm(guide.get("lead"))[:300],
        "faq_2_question": norm(guide.get("faq_2_question")) or "どちらから覚えるべき？",
        "faq_2_answer": norm(guide.get("faq_2_answer"))
        or "用語解説で各項目の定義を確認してから、この比較表で差分を整理してください。",
        "faq_3_question": norm(guide.get("faq_3_question")) or "試験でどう問われますか？",
        "faq_3_answer": norm(guide.get("faq_3_answer"))
        or "定義の言い換え、数値・期限、主体の取り違えが四択で出やすいです。",
        "faq_4_question": norm(guide.get("faq_4_question")) or "関連用語はどこで確認？",
        "faq_4_answer": norm(guide.get("faq_4_answer"))
        or "各項目の用語解説とあわせて読むと定着しやすくなります。",
        "fact_checked_at": norm(guide.get("fact_checked_at")),
    }


def guide_to_numbers_row(guide: dict[str, str]) -> dict[str, str]:
    slug = norm(guide.get("slug"))
    title = norm(guide.get("title"))
    sections = guide_sections(guide)
    item_rows: list[dict] = []
    for heading, body in sections[:8]:
        item_rows.append(
            {
                "item": heading[:60],
                "value": body[:400],
                "note": "",
            }
        )
    if not item_rows:
        item_rows = [{"item": title, "value": norm(guide.get("lead"))[:400], "note": ""}]

    return {
        "slug": slug,
        "title": title,
        "category": norm(guide.get("genre")) or "法令・制度",
        "tags": norm(guide.get("tags")) or "数字;期限",
        "summary": norm(guide.get("lead"))[:120] or f"{title}の数値・期限を早見表に整理します。",
        "highlight": title[:80],
        "item_rows": json.dumps(item_rows, ensure_ascii=False),
        "article_title": title,
        "article_lead": norm(guide.get("lead"))[:500],
        "exam_points": "数字と条件（誰が・いつ）をセットで覚える;公式テキストで最新値を確認する",
        "common_mistakes": "似た数字を入れ替えて覚えると一問失点しやすいです。",
        "memory_tip": "分野ごとに短いフレーズで順序付きに覚えます。",
        "related_terms": "用語解説;過去問",
        "faq_1_question": norm(guide.get("faq_1_question")) or f"{title}の代表的な数字は？",
        "faq_1_answer": norm(guide.get("faq_1_answer")) or "早見表の数値・期限列を参照してください。",
        "faq_2_question": norm(guide.get("faq_2_question")) or "一覧表の使い方は？",
        "faq_2_answer": norm(guide.get("faq_2_answer"))
        or "学習中の確認と直前の総復習向けです。用語解説で根拠条文まで深掘りしてください。",
        "faq_3_question": norm(guide.get("faq_3_question")) or "試験でどう問われますか？",
        "faq_3_answer": norm(guide.get("faq_3_answer"))
        or "数値そのものの暗記、条件の追加、近い数字との選択が典型です。",
        "faq_4_question": norm(guide.get("faq_4_question")) or "数字は暗記だけで足りる？",
        "faq_4_answer": norm(guide.get("faq_4_answer"))
        or "演習で肢を確認し、公式テキストで裏取りしてください。",
        "fact_checked_at": norm(guide.get("fact_checked_at")),
    }


def hub_href(hub_type: str, slug: str) -> str:
    if hub_type == "compare":
        return f"/terms/compare/{slug}.html"
    if hub_type == "numbers":
        return f"/terms/numbers/{slug}.html"
    return "/terms/index.html"


def bridge_guide_to_hub(
    guide: dict[str, str],
    *,
    hub_type: str,
    hub_slug: str,
    hub_title: str,
    exam_label: str,
) -> dict[str, str]:
    href = hub_href(hub_type, hub_slug)
    hub_label = "比較・整理表" if hub_type == "compare" else "数値・期限早見表"
    row = dict(guide)
    row["genre"] = HUB_BRIDGE_GENRE
    row["revision_note"] = HUB_BRIDGE_NOTE
    row["lead"] = (
        f"「{hub_title}」の表・数値一覧は **知識ハブ（{hub_label}）** に集約しています。"
        f"本ページでは、確認後に試験ガイドと演習へ進む導線だけを案内します。"
    )
    row["user_intent"] = (
        f"{hub_title}を試験対策用に整理した表を確認し、関連する過去問・学習計画へつなげたい読者向け。"
    )
    row["action_items"] = (
        f"知識ハブの{hub_label}で{hub_title}を確認する;"
        f"関連用語を用語解説で2件以上たどる;"
        f"過去問演習で該当分野を解く;"
        f"学習計画・分野別対策ガイドで次の行動を決める"
    )
    row["section_1_heading"] = f"{hub_label}で確認する内容"
    row["section_1_body"] = (
        f"{exam_label}では、{hub_title}は表形式で整理した方が復習効率が上がります。"
        f"詳細は <a href=\"{href}\">{hub_label}「{hub_title}」</a> を正本として参照してください。"
    )
    row["section_2_heading"] = "試験ガイドとの使い分け"
    row["section_2_body"] = (
        f"知識ハブは「What（何が違うか／数字はいくつか）」、試験ガイドは「How/When（どう学ぶか）」です。"
        f"表を読んだら <a href=\"/articles/index.html\">試験ガイド</a> または過去問演習へ進んでください。"
    )
    row["section_3_heading"] = "おすすめの学習順"
    row["section_3_body"] = (
        f"① <a href=\"{href}\">{hub_label}</a> で表を確認。"
        f"② 用語解説で関連語を確認。"
        f"③ 過去問で該当分野を解き、間違えた選択肢を表と照合。"
    )
    for n in range(4, 8):
        row[f"section_{n}_heading"] = ""
        row[f"section_{n}_body"] = ""
    row["faq_1_question"] = f"{hub_title}はどこで詳しく見られますか？"
    row["faq_1_answer"] = (
        f"<a href=\"{href}\">{hub_label}「{hub_title}」</a> が正本です。"
        f"試験ガイド側に同じ表を載せないのが配置ルールです。"
    )
    row["faq_2_question"] = "表を確認したあと何をすればよいですか？"
    row["faq_2_answer"] = (
        "関連用語と過去問演習に進んでください。学習全体の設計は試験ガイドの学習計画・分野別対策を参照します。"
    )
    row["faq_3_question"] = "用語解説との違いは？"
    row["faq_3_answer"] = (
        f"用語解説は1語の定義、{hub_label}は2項目の差分や数値の一覧です。役割が異なるため使い分けてください。"
    )
    row["faq_4_question"] = "直前対策でどう使う？"
    row["faq_4_answer"] = (
        f"直前は{hub_label}を総復習のチェックリストとして使い、弱い行の用語解説と過去問に戻るのが効率的です。"
    )
    return row


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        return fields, list(reader)


def save_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    all_keys = list(fields)
    for row in rows:
        for k in row:
            if k not in all_keys:
                all_keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def upsert_hub_row(
    path: Path,
    new_row: dict[str, str],
) -> bool:
    if not path.is_file():
        return False
    fields, rows = load_csv(path)
    slug = norm(new_row.get("slug"))
    replaced = False
    for i, row in enumerate(rows):
        if norm(row.get("slug")) == slug:
            merged = dict(row)
            merged.update(new_row)
            rows[i] = merged
            replaced = True
            break
    if not replaced:
        rows.append(new_row)
    save_csv(path, fields, rows)
    return True


def migrate_compare_guides(
    guide_rows: list[dict[str, str]],
    compare_csv: Path,
    *,
    exam_label: str,
) -> tuple[list[dict[str, str]], int]:
    changed = 0
    for i, guide in enumerate(guide_rows):
        if norm(guide.get("content_status")) != "published":
            continue
        slug = norm(guide.get("slug"))
        if slug in SKIP_MIGRATE_SLUGS:
            continue
        if slug not in COMPARE_SUBJECTS:
            continue
        if not compare_csv.is_file():
            continue
        fields, existing = load_csv(compare_csv)
        _ = fields
        if any(norm(r.get("slug")) == slug for r in existing):
            # 既に移管済み — 橋渡しだけ
            guide_rows[i] = bridge_guide_to_hub(
                guide,
                hub_type="compare",
                hub_slug=slug,
                hub_title=norm(guide.get("title")),
                exam_label=exam_label,
            )
            changed += 1
            continue
        new_row = guide_to_compare_row(guide)
        upsert_hub_row(compare_csv, new_row)
        guide_rows[i] = bridge_guide_to_hub(
            guide,
            hub_type="compare",
            hub_slug=slug,
            hub_title=new_row["title"],
            exam_label=exam_label,
        )
        changed += 1
    return guide_rows, changed


def migrate_numbers_guides(
    guide_rows: list[dict[str, str]],
    numbers_csv: Path,
    *,
    exam_label: str,
) -> tuple[list[dict[str, str]], int]:
    changed = 0
    for i, guide in enumerate(guide_rows):
        if norm(guide.get("content_status")) != "published":
            continue
        slug = norm(guide.get("slug"))
        if slug not in NUMBERS_MIGRATE_SLUGS:
            continue
        if not numbers_csv.is_file():
            continue
        fields, existing = load_csv(numbers_csv)
        _ = fields
        if any(norm(r.get("slug")) == slug for r in existing):
            guide_rows[i] = bridge_guide_to_hub(
                guide,
                hub_type="numbers",
                hub_slug=slug,
                hub_title=norm(guide.get("title")),
                exam_label=exam_label,
            )
            changed += 1
            continue
        new_row = guide_to_numbers_row(guide)
        upsert_hub_row(numbers_csv, new_row)
        guide_rows[i] = bridge_guide_to_hub(
            guide,
            hub_type="numbers",
            hub_slug=slug,
            hub_title=new_row["title"],
            exam_label=exam_label,
        )
        changed += 1
    return guide_rows, changed
