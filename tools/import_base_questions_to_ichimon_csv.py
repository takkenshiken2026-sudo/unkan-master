#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4択問題（過去問 CSV + 実践演習 CSV）から一問一答 CSV を生成する。

SPA の buildIchiSourcePool と同様、個数・組合せ問題などは除外。
各4択から「正解肢を ○ とする」一問一答を1件ずつ書き出す（静的ページ用の決定的変換）。

  python3 tools/import_base_questions_to_ichimon_csv.py
  python3 tools/import_base_questions_to_ichimon_csv.py --keep-manual
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.csv_to_exam_site_past_js import (  # noqa: E402
    build_plain_text,
    norm,
    practice_row_to_obj,
    row_to_obj,
)
from tools.site_config import field_labels  # noqa: E402

PRACTICE_CSV = ROOT / "data" / "practice_questions.csv"
PAST_CSV = ROOT / "data" / "past_questions.csv"
ICHIMON_CSV = ROOT / "data" / "ichimon_questions.csv"

CSV_COLUMNS = [
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

STEM_STRIPS = [
    r"次の記述のうち[、,　\s]*誤りがあるものはどれか[。．]?",
    r"次の記述のうち[、,　\s]*誤っているものはどれか[。．]?",
    r"次の記述のうち[、,　\s]*正しいものはどれか[。．]?",
    r"次の記述について[、,　\s]*誤っているものはどれか[。．]?",
    r"次の記述について[、,　\s]*正しいものはどれか[。．]?",
    r"次の各記述のうち[、,　\s]*誤っているものはどれか[。．]?",
    r"次の各記述のうち[、,　\s]*正しいものはどれか[。．]?",
    r"次の各記述について[、,　\s]*正しいものはどれか[。．]?",
    r"次のうち[、,　\s]*誤っているものはどれか[。．]?",
    r"次のうち[、,　\s]*正しいものはどれか[。．]?",
    r"次の記述について[、,　\s]*適切なものはどれか[。．]?",
    r"誤っている記述はどれか[。．]?",
    r"誤りがあるものはどれか[。．]?",
    r"正しい記述はどれか[。．]?",
    r"誤っているものはどれか[。．]?",
    r"誤りのあるものはどれか[。．]?",
    r"適切なものはどれか[。．]?",
    r"妥当なものはどれか[。．]?",
    r"正しくないものはどれか[。．]?",
    r"正しいものはどれか[。．]?",
]

FIELD_TO_CATEGORY = {fid: name for fid, name in field_labels().items()}


def adapt_stem_for_ichimon(text: str) -> str:
    s = norm(text)
    for pat in STEM_STRIPS:
        s = re.sub(pat, "", s)
    s = re.sub(
        r"以下の(?:1から4までの|１から４までの)?記述のうち[、,　\s]*[^。．]*(?:を選びなさい|はどれか|どれか)[。．]?",
        "",
        s,
    )
    s = re.sub(
        r"次の(?:1から4までの|１から４までの)?記述のうち[、,　\s]*[^。．]*(?:を選びなさい|はどれか|どれか)[。．]?",
        "",
        s,
    )
    s = re.sub(r"[、，]\s*$", "", s, flags=re.MULTILINE)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def normalize_option_sentence(opt: str) -> str:
    s = norm(opt)
    if not s:
        return s
    if s[-1] not in "。．!?！？":
        s += "。"
    return s


def compose_ichi_statement(stem_raw: str, opt: str) -> str:
    stem = adapt_stem_for_ichimon(stem_raw)
    opt = norm(opt)
    if not stem:
        return normalize_option_sentence(opt)
    if not opt:
        return stem
    stem_flat = re.sub(r"[\s　\r\n]+", "", stem)
    opt_flat = re.sub(r"[\s　\r\n]+", "", opt)
    if len(opt_flat) > 12 and opt_flat in stem_flat:
        return normalize_option_sentence(stem)
    if stem.endswith(("について", "に関する", "として", "において")):
        return normalize_option_sentence(stem + opt)
    if stem[-1] in "。．":
        return normalize_option_sentence(stem + opt)
    return normalize_option_sentence(stem + "。" + opt)


def is_ichi_convertible(stem: str, opts: list[str]) -> bool:
    if re.search(r"いくつあるか|何個|個数|組合せ|組み合わせ", stem):
        return False
    if opts and all(
        re.match(
            r"^(?:正しい|誤っている|誤りのある|適切な|不適切な)?記述は(?:一|二|三|四|ない|[0-9０-９]+)つ",
            o,
        )
        for o in opts
    ):
        return False
    if opts and all(re.match(r"^[アイウエオ](?:と[アイウエオ])*$", o) for o in opts):
        return False
    return True


def ichi_answer_truth(stem: str) -> bool:
    if re.search(r"組合せ|組み合わせ|いくつ|何個|個数", stem):
        return True
    if re.search(r"誤っている|誤りがある|誤りのある|正しくない|不適切|妥当でない", stem):
        return False
    return True


def field_to_category(field_id: str) -> str:
    return FIELD_TO_CATEGORY.get(field_id, field_id)


def adapt_explanation_for_ichimon(text: str) -> str:
    s = norm(text)
    if not s:
        return "（解説は未入力です。）"
    for old, new in (
        (r"正解の選択肢", "論点として正しいこと"),
        (r"不正解の選択肢", "誤りとされる記述"),
        (r"他の選択肢", "その他の記述"),
    ):
        s = re.sub(old, new, s)
    return s


def base_to_ichimon_row(
    *,
    row_id: str,
    stem: str,
    opts: list[str],
    ans_idx: int,
    exp: str,
    field: str,
    tags: str,
    source: str,
) -> dict[str, str] | None:
    if not is_ichi_convertible(stem, opts):
        return None
    if ans_idx < 0 or ans_idx >= len(opts):
        return None
    truth = ichi_answer_truth(stem)
    statement = compose_ichi_statement(stem, opts[ans_idx])
    answer = "○" if truth else "×"
    explanation = adapt_explanation_for_ichimon(exp)
    summary = explanation[:120] + ("…" if len(explanation) > 120 else "")
    return {
        "id": row_id,
        "question": statement,
        "answer": answer,
        "explanation": explanation,
        "explanation_summary": summary,
        "explanation_correct": explanation,
        "explanation_opposite": "",
        "explanation_point": "",
        "category": field_to_category(field),
        "tags": tags,
        "source": source,
        "note": "",
    }


def read_manual_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8-sig")
    rows = list(csv.DictReader(text.splitlines()))
    manual: list[dict[str, str]] = []
    for row in rows:
        src = norm(row.get("source"))
        if src and "auto-import" not in src.lower():
            manual.append({col: norm(row.get(col)) for col in CSV_COLUMNS})
    return manual


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="4択プール → ichimon_questions.csv")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--keep-manual", action="store_true", help="手動行（source に auto-import を含まない）を先頭に残す")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    practice_csv = root / "data" / "practice_questions.csv"
    past_csv = root / "data" / "past_questions.csv"
    output = (args.output or root / "data" / "ichimon_questions.csv").resolve()

    manual = read_manual_rows(output) if args.keep_manual else []
    seen_ids = {r["id"] for r in manual if r.get("id")}

    generated: list[dict[str, str]] = []
    skipped = 0

    if not past_csv.is_file():
        past_items: list[dict] = []
    else:
        text = past_csv.read_text(encoding="utf-8-sig")
        past_items = []
        for i, row in enumerate(csv.DictReader(text.splitlines()), start=2):
            obj = row_to_obj(row, i)
            if obj is not None:
                past_items.append({"row": row, "obj": obj})

    if not practice_csv.is_file():
        practice_items: list[dict] = []
    else:
        text = practice_csv.read_text(encoding="utf-8-sig")
        practice_items = []
        for i, row in enumerate(csv.DictReader(text.splitlines()), start=2):
            obj = practice_row_to_obj(row, i)
            if obj is not None:
                practice_items.append({"row": row, "obj": obj})

    for item in past_items:
        row, obj = item["row"], item["obj"]
        year = int(row["exam_year"])
        qno = int(row["question_no"])
        rid = f"{year}-{qno}-1"
        if rid in seen_ids:
            continue
        stem = build_plain_text(row)
        opts = obj["opts"]
        ich = base_to_ichimon_row(
            row_id=rid,
            stem=stem,
            opts=opts,
            ans_idx=int(obj["ans"]),
            exp=str(obj["exp"]),
            field=str(obj["field"]),
            tags=norm(row.get("tags")) or "過去問",
            source="auto-import/past",
        )
        if ich is None:
            skipped += 1
            continue
        generated.append(ich)
        seen_ids.add(rid)

    for item in practice_items:
        row, obj = item["row"], item["obj"]
        qno = int(row["question_no"])
        rid = f"9000-{qno}-1"
        if rid in seen_ids:
            continue
        stem = build_plain_text(row)
        opts = obj["opts"]
        ich = base_to_ichimon_row(
            row_id=rid,
            stem=stem,
            opts=opts,
            ans_idx=int(obj["ans"]),
            exp=str(obj["exp"]),
            field=str(obj["field"]),
            tags=norm(row.get("tags")) or "実践演習",
            source="auto-import/practice",
        )
        if ich is None:
            skipped += 1
            continue
        generated.append(ich)
        seen_ids.add(rid)

    all_rows = manual + generated
    print(
        f"一問一答 CSV: 手動 {len(manual)} + 自動 {len(generated)} = {len(all_rows)} 行"
        f"（除外 {skipped}）"
    )
    print(f"  出力: {output}")

    if args.dry_run:
        return 0

    if output.is_file() and not args.no_backup:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = output.with_suffix(f".csv.bak-{stamp}")
        shutil.copy2(output, backup)
        print(f"  バックアップ: {backup.name}")

    write_csv(output, all_rows)
    print("書き出し完了。続けて python3 tools/build_all.py を実行してください。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
