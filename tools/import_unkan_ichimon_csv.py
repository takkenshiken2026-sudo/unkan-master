#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
~/Desktop/運行管理者試験_一問一答500問.csv → data/ichimon_questions.csv 変換。

ソース CSV のスキーマ:
  one_answer_id, source_question_id, source_choice_no, exam_type,
  license_type, section_no, section_name, topic, question_text,
  answer (○/×), explanation, source_exam_id, source_question_file,
  conversion_type, quality_status, conversion_note

ターゲット CSV (data/ichimon_questions.csv):
  id, question, answer, explanation,
  explanation_summary, explanation_correct, explanation_opposite,
  explanation_point, category, tags, source, note

ID 戦略:
  サイトオリジナル一問一答として 2026-01-001 〜 2026-01-500 を割り当て。
  これは tools/ichimon_paths.py の _ID_PATH (YYYY-M-N) に整合し、
  q/ichimon/y2026/i01-001/index.html 等に展開される。
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path("/Users/otedaiki/Desktop/運行管理者試験_一問一答500問.csv")
DST = ROOT / "data" / "ichimon_questions.csv"
SRC_COPY = ROOT / "data" / "source_unkan_freight_ichimon.csv"

TARGET_FIELDS = [
    "id",
    "question",
    "answer",
    "explanation",
    "explanation_summary",
    "explanation_correct",
    "explanation_opposite",
    "explanation_point",
    "category",
    "tags",
    "source",
    "note",
]

# section_name → site-config.json fields[].name と一致するか確認用
ALLOWED_CATEGORIES = {
    "貨物自動車運送事業法関係",
    "道路運送車両法関係",
    "道路交通法関係",
    "労働基準法関係",
    "実務上の知識及び能力",
}


def norm(s: str | None) -> str:
    return (s or "").strip()


def normalize_answer(a: str) -> str:
    a = norm(a)
    if a in ("○", "〇", "○"):
        return "○"
    if a in ("×", "✕", "x", "X"):
        return "×"
    raise ValueError(f"未知の answer: {a!r}")


def build_explanation_variants(explanation: str, answer: str, topic: str, category: str) -> dict:
    """4 種類の解説バリアントを explanation から派生生成する。

    元データには 1 種類の解説しかないので、テンプレ側のレイアウト破綻を防ぐため
    意味のあるバリアントを最小限に作る。
    """
    base = norm(explanation)
    is_correct = answer == "○"
    if is_correct:
        correct = f"記述は正しい。{base}"
        opposite = (
            "× を選んだ場合は、要件・期限・主体・例外規定のいずれかを取り違えている可能性があります。"
            f"このテーマ（{topic or category}）では、原則と例外、誰が・いつ・どこまで行うかの条件を整理してください。"
        )
    else:
        correct = f"記述は誤り。{base}"
        opposite = (
            "○ を選んだ場合は、原文をそのまま受け入れてしまった可能性があります。"
            f"このテーマ（{topic or category}）では、「あらかじめ／遅滞なく」「届出／許可」「期限の数値」など、"
            "判断の決め手となるキーワードを意識して再確認してください。"
        )
    summary = base if base else f"{category}の基本論点。条文・通達の原則を正確に押さえることが要点。"
    point = (
        f"類題は分野「{category}」の過去問・実践演習で繰り返し出題されます。"
        f"用語解説で関連語をたどり、数値・期限・主体を比較表で整理すると定着しやすくなります。"
    )
    return {
        "explanation_summary": summary,
        "explanation_correct": correct,
        "explanation_opposite": opposite,
        "explanation_point": point,
    }


def main() -> int:
    if not SRC.exists():
        print(f"source not found: {SRC}", flush=True)
        return 1

    src_rows: list[dict] = []
    with SRC.open(encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            src_rows.append(r)

    # データ品質バリデート
    skipped: list[str] = []
    accepted: list[dict] = []
    for i, r in enumerate(src_rows, start=1):
        qtext = norm(r.get("question_text"))
        ans = norm(r.get("answer"))
        cat = norm(r.get("section_name"))
        if not qtext:
            skipped.append(f"line {i}: question_text 空")
            continue
        if cat not in ALLOWED_CATEGORIES:
            skipped.append(f"line {i}: 未知の section_name: {cat!r}")
            continue
        try:
            ans = normalize_answer(ans)
        except ValueError as e:
            skipped.append(f"line {i}: {e}")
            continue
        accepted.append({**r, "_answer": ans, "_question": qtext, "_category": cat})

    # ターゲット行を生成（年=2026, 回=01, 番号=001..NNN の連番）
    SRC_COPY.parent.mkdir(parents=True, exist_ok=True)
    rows_out: list[dict] = []
    for idx, r in enumerate(accepted, start=1):
        rid = f"2026-01-{idx:03d}"
        topic = norm(r.get("topic"))
        explanation = norm(r.get("explanation"))
        variants = build_explanation_variants(explanation, r["_answer"], topic, r["_category"])
        src_qid = norm(r.get("source_question_id"))
        oa_id = norm(r.get("one_answer_id"))
        rows_out.append(
            {
                "id": rid,
                "question": r["_question"],
                "answer": r["_answer"],
                "explanation": explanation,
                "explanation_summary": variants["explanation_summary"],
                "explanation_correct": variants["explanation_correct"],
                "explanation_opposite": variants["explanation_opposite"],
                "explanation_point": variants["explanation_point"],
                "category": r["_category"],
                "tags": topic,
                "source": f"{src_qid} / {oa_id}".strip(" /"),
                "note": "",
            }
        )

    # 書き出し
    with DST.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TARGET_FIELDS)
        w.writeheader()
        for row in rows_out:
            w.writerow(row)

    # ソース CSV のコピー（テンプレ同期で参照できるように）
    with SRC.open(encoding="utf-8-sig", newline="") as fin, SRC_COPY.open(
        "w", encoding="utf-8", newline=""
    ) as fout:
        fout.write(fin.read())

    print(f"imported: {len(rows_out)} / {len(src_rows)} (skipped: {len(skipped)})", flush=True)
    if skipped:
        for s in skipped[:20]:
            print(f"  - {s}", flush=True)
    print(f"wrote: {DST}", flush=True)
    print(f"wrote: {SRC_COPY}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
