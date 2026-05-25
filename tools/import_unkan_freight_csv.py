#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""運行管理者試験（貨物）過去問 CSV → data/past_questions.csv に取り込む。

入力 (運行管理者試験センター形式・25 列):
  exam_id, exam_type, license_type, year_label, exam_round, exam_date_label,
  question_id, question_no, section_no, section_name, question_type, prompt,
  choice_1..choice_8, full_question_text, correct_answer, explanation,
  source_question_file, source_answer_file

出力 (本番拡張形式・30 列):
  data/past_questions.csv

採用ポリシー（全形式取り込み）:
- ``question_type`` を以下に正規化:
    single_select       -> "single"        correct="3"
    multiple_select     -> "multi"         correct="1,3"
    combination         -> "A-2;B-3;C-5"   そのまま正規化
    true_false_group    -> "適-2,3;不適-1,4" など label-番号 形式
- choice_1..choice_8 まで保持。テンプレ既定の choice_1..4 を超える列は
  本番側のスキーマ拡張として扱う（template_site_only.paths で同期除外）。
- ``exam_year`` は ``西暦 * 10 + exam_round`` に圧縮し、(exam_year, question_no)
  を一意化する。``exam_wareki`` は "平成21年度 第1回" のように人間可読のまま。
- ``category`` は section_name をそのまま入れる（site-config.json の fields に
  登録済みであることが前提）。

既定の入力パスは ``~/Desktop/運行管理者試験_過去問.csv``。--source で上書き可。
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DEFAULT_SOURCE = Path.home() / "Desktop" / "運行管理者試験_過去問.csv"

OUT_CSV = DATA_DIR / "past_questions.csv"
SOURCE_COPY = DATA_DIR / "source_unkan_freight_questions.csv"

OUT_HEADERS = [
    "exam_year", "exam_wareki", "question_no", "type", "category", "tags",
    "stem", "preamble",
    "statement_a", "statement_b", "statement_c", "statement_d",
    "choice_1", "choice_2", "choice_3", "choice_4",
    "choice_5", "choice_6", "choice_7", "choice_8",
    "correct", "is_exempt", "is_invalidated", "note",
    "explanation", "explanation_summary", "explanation_correct",
    "explanation_choices", "explanation_point", "related_links",
]

WAREKI_MAP = {
    "平成20年度": 2008, "平成21年度": 2009, "平成22年度": 2010,
    "平成23年度": 2011, "平成24年度": 2012, "平成25年度": 2013,
    "平成26年度": 2014, "平成27年度": 2015, "平成28年度": 2016,
    "平成29年度": 2017, "平成30年度": 2018,
    "令和元年度": 2019, "令和2年度": 2020, "令和3年度": 2021,
    "令和4年度": 2022, "令和5年度": 2023, "令和6年度": 2024,
    "令和7年度": 2025, "令和8年度": 2026,
}

QTYPE_MAP = {
    "single_select": "single",
    "multiple_select": "multi",
    "combination": "combination",
    "true_false_group": "truefalse_group",
}


def norm(value: str | None) -> str:
    return (value or "").strip()


def round_no(exam_round: str) -> int:
    m = re.search(r"第(\d+)回", exam_round)
    return int(m.group(1)) if m else 0


def to_exam_year(year_label: str, exam_round: str) -> int:
    base = WAREKI_MAP.get(year_label.strip())
    if base is None:
        raise ValueError(f"未知の year_label: {year_label!r}")
    return base * 10 + round_no(exam_round)


_NUM_DELIM = re.compile(r"\s*[\d０-９][\.．]\s*")


def split_combined_cell(value: str) -> list[str]:
    """1セルに「健全 ２．総合的 ３．自主的 ４．輸送の安全」のように複数候補が結合
    されているソースデータを分割する。先頭は番号なしで始まり、以降「数字．」が区切り。"""
    if not value:
        return []
    parts = _NUM_DELIM.split(value)
    return [p.strip() for p in parts if p.strip()]


def collect_choices(row: dict) -> list[str]:
    """choice_1..choice_8 を採用。空セル間に値があるパターン（choice_1, choice_5 のみ
    埋まり間が空）と、1 セル内結合パターンの両方に対応して順序維持で 1..8 に再配置。"""
    raw_cells: list[str] = []
    for i in range(1, 9):
        raw_cells.append(norm(row.get(f"choice_{i}")))

    expanded: list[str] = []
    for cell in raw_cells:
        if not cell:
            expanded.append("")
            continue
        # 1 セル内に「数字．」区切りで複数候補が結合されている場合は分割
        parts = split_combined_cell(cell)
        if len(parts) >= 2:
            expanded.extend(parts)
        else:
            expanded.append(cell)

    # 空セルを除去して非空のみ順序維持で集める（行全体で見て選択肢を 1..N に詰める）
    non_empty = [c for c in expanded if c]
    return non_empty[:8]


def detect_type_from_correct(raw: str) -> str:
    """correct 文字列のフォーマットから出題型を推定（ソースデータの型ミス救済用）。"""
    raw = (raw or "").strip()
    if not raw:
        return ""
    # combination: 「A-2;B-3;C-5」(各組が単一数字)
    if re.fullmatch(r"[A-Za-zア-オ甲乙①-⑫]-\d+(;[A-Za-zア-オ甲乙①-⑫]-\d+)*", raw):
        return "combination"
    # truefalse_group: 「適-2,3;不適-1,4」(ラベルが日本語/英字、各組が複数数字許容)
    if ";" in raw and re.fullmatch(r"[^,\d;]+-\d+(,\d+)*(;[^,\d;]+-\d+(,\d+)*)+", raw):
        return "truefalse_group"
    # multi: 数字のカンマ区切り
    if re.fullmatch(r"\d+(,\d+)+", raw):
        return "multi"
    # single: 単一数字
    if re.fullmatch(r"\d+", raw):
        return "single"
    return ""


def normalize_correct(qtype: str, raw: str, max_choice: int) -> str | None:
    """型別に正答フォーマットを検証・正規化する。"""
    raw = norm(raw)
    if not raw:
        return None
    if qtype == "single":
        try:
            n = int(raw)
        except ValueError:
            return None
        if 1 <= n <= max_choice:
            return str(n)
        return None
    if qtype == "multi":
        nums = [s.strip() for s in raw.split(",") if s.strip()]
        try:
            ints = sorted({int(n) for n in nums})
        except ValueError:
            return None
        if not ints:
            return None
        if any(n < 1 or n > max_choice for n in ints):
            return None
        return ",".join(str(n) for n in ints)
    if qtype == "combination":
        # "A-2;B-3;C-5" 形式（並び順は元データ尊重）
        pairs = [p.strip() for p in raw.split(";") if p.strip()]
        out_pairs: list[str] = []
        for p in pairs:
            m = re.match(r"^([A-Za-z①-⑫ア-オ甲乙])-(\d+)$", p)
            if not m:
                return None
            label, num = m.group(1), int(m.group(2))
            if not 1 <= num <= max_choice:
                return None
            out_pairs.append(f"{label}-{num}")
        if not out_pairs:
            return None
        return ";".join(out_pairs)
    if qtype == "truefalse_group":
        # "適-2,3;不適-1,4" / "正-3,4;誤-1,2" 等
        groups = [g.strip() for g in raw.split(";") if g.strip()]
        out_groups: list[str] = []
        used: set[int] = set()
        for g in groups:
            m = re.match(r"^([^-]+)-(.+)$", g)
            if not m:
                return None
            label = m.group(1).strip()
            nums_raw = m.group(2)
            try:
                nums = sorted({int(s.strip()) for s in nums_raw.split(",") if s.strip()})
            except ValueError:
                return None
            if not nums or any(n < 1 or n > max_choice for n in nums):
                return None
            if any(n in used for n in nums):
                return None
            used.update(nums)
            out_groups.append(f"{label}-{','.join(str(n) for n in nums)}")
        if not out_groups:
            return None
        return ";".join(out_groups)
    return None


def convert_row(row: dict, *, line: int, log_skip: list[str]) -> dict | None:
    src_qtype = norm(row.get("question_type"))
    qtype = QTYPE_MAP.get(src_qtype)
    if not qtype:
        log_skip.append(f"line {line}: skip qtype={src_qtype!r}")
        return None

    choices = collect_choices(row)
    if len([c for c in choices if c]) < 2:
        log_skip.append(f"line {line}: skip choices<2 ({len([c for c in choices if c])})")
        return None

    raw_correct = row.get("correct_answer", "")
    correct = normalize_correct(qtype, raw_correct, len(choices))
    if correct is None:
        # ソースデータの type と correct フォーマットが一致しない場合、
        # correct のフォーマットから型を推定してリトライ（PDF 抽出ミス救済）
        guessed = detect_type_from_correct(raw_correct)
        if guessed and guessed != qtype:
            correct = normalize_correct(guessed, raw_correct, len(choices))
            if correct is not None:
                qtype = guessed
        if correct is None:
            log_skip.append(
                f"line {line}: skip type={qtype} correct={raw_correct!r}"
            )
            return None
    # multi で correct が 1 個だけの場合は single にダウングレード（ソースデータの誤分類対応）
    if qtype == "multi" and "," not in correct:
        qtype = "single"

    try:
        exam_year = to_exam_year(row.get("year_label", ""), row.get("exam_round", ""))
    except ValueError as exc:
        log_skip.append(f"line {line}: skip {exc}")
        return None

    qno = int(norm(row.get("question_no")) or 0)
    if qno <= 0:
        log_skip.append(f"line {line}: skip qno={row.get('question_no')!r}")
        return None

    out = {h: "" for h in OUT_HEADERS}
    out["exam_year"] = str(exam_year)
    out["exam_wareki"] = f"{norm(row.get('year_label'))} {norm(row.get('exam_round'))}".strip()
    out["question_no"] = str(qno)
    out["type"] = qtype
    out["category"] = norm(row.get("section_name"))
    out["tags"] = ""
    out["stem"] = norm(row.get("prompt"))
    out["preamble"] = ""
    for idx, value in enumerate(choices, start=1):
        if idx <= 8:
            out[f"choice_{idx}"] = value
    out["correct"] = correct
    out["is_exempt"] = "FALSE"
    out["is_invalidated"] = "FALSE"
    out["note"] = ""
    out["explanation"] = norm(row.get("explanation"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="運管・貨物の過去問 CSV を取り込む")
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                    help=f"入力 CSV (default: {DEFAULT_SOURCE})")
    ap.add_argument("--keep-source-copy", action="store_true",
                    help=f"オリジナル CSV を {SOURCE_COPY} にコピー保存")
    args = ap.parse_args()

    src: Path = args.source
    if not src.is_file():
        print(f"error: source not found: {src}", file=sys.stderr)
        return 1

    text = src.read_text(encoding="utf-8-sig")
    rows = list(csv.DictReader(text.splitlines()))

    converted: list[dict] = []
    skipped: list[str] = []
    qtype_counter = Counter()
    out_qtype_counter = Counter()

    for i, row in enumerate(rows, start=2):
        qtype_counter[norm(row.get("question_type"))] += 1
        out = convert_row(row, line=i, log_skip=skipped)
        if out is None:
            continue
        converted.append(out)
        out_qtype_counter[out["type"]] += 1

    seen: set[tuple[int, int]] = set()
    deduped: list[dict] = []
    for r in converted:
        key = (int(r["exam_year"]), int(r["question_no"]))
        if key in seen:
            skipped.append(f"dup {key}")
            continue
        seen.add(key)
        deduped.append(r)

    deduped.sort(key=lambda r: (int(r["exam_year"]), int(r["question_no"])))

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_HEADERS)
        writer.writeheader()
        writer.writerows(deduped)

    if args.keep_source_copy:
        SOURCE_COPY.write_text(text, encoding="utf-8")

    print(f"source: {src}")
    print(f"output: {OUT_CSV} ({len(deduped)} rows)")
    print("question_type counts in source:")
    for qt, n in qtype_counter.most_common():
        print(f"  {n:>5}  {qt}")
    print("normalized type counts in output:")
    for qt, n in out_qtype_counter.most_common():
        print(f"  {n:>5}  {qt}")
    print(f"skipped: {len(rows) - len(deduped)} (parse error / dup)")
    if skipped:
        print("first 10 skip reasons:")
        for s in skipped[:10]:
            print(f"  {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
