#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
takken-data-original.js の ORIG_QUESTIONS を data/practice_questions.csv に書き出す。

宅建本番など、SPA 用 JS に実践演習バンクがあるが CSV がサンプルのみのサイト向け。
書き出し後は python3 tools/build_all.py で q/practice/ と exam-site-data-practice.js を再生成する。

  python3 tools/import_orig_questions_to_practice_csv.py
  python3 tools/import_orig_questions_to_practice_csv.py --source takken-data-original.js --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.site_config import category_to_field_map, field_labels  # noqa: E402

CSV_COLUMNS = [
    "question_no",
    "type",
    "category",
    "tags",
    "stem",
    "preamble",
    "statement_a",
    "statement_b",
    "statement_c",
    "statement_d",
    "choice_1",
    "choice_2",
    "choice_3",
    "choice_4",
    "correct",
    "explanation",
    "explanation_summary",
    "explanation_correct",
    "explanation_choices",
    "explanation_point",
]

NODE_LOADER = r"""
const fs = require('fs');
const src = fs.readFileSync(process.argv[1], 'utf8');
const fn = new Function(src + '\nreturn ORIG_QUESTIONS;');
process.stdout.write(JSON.stringify(fn()));
"""


def load_orig_questions(source: Path) -> dict:
    if not source.is_file():
        raise FileNotFoundError(f"ORIG ソースがありません: {source}")
    proc = subprocess.run(
        ["node", "-e", NODE_LOADER, str(source)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"node で ORIG_QUESTIONS を読めませんでした:\n{proc.stderr}")
    data = json.loads(proc.stdout)
    normalized: dict[int, list] = {}
    for lv in (1, 2, 3):
        bucket = data.get(lv) or data.get(str(lv)) or []
        if not isinstance(bucket, list):
            raise ValueError(f"ORIG_QUESTIONS[{lv}] が配列ではありません")
        normalized[lv] = bucket
    return normalized


def field_id_to_category(field_id: str) -> str:
    labels = field_labels()
    if field_id in labels:
        return labels[field_id]
    rev = {v: k for k, v in category_to_field_map().items()}
    if field_id in rev:
        return rev[field_id]
    raise ValueError(f"未対応の field: {field_id!r}")


def format_kaisetsu_choices(kaisetsu: dict, opts: list[str], correct_idx: int) -> str:
    choices = kaisetsu.get("choices") if isinstance(kaisetsu, dict) else None
    if not isinstance(choices, list):
        return ""
    parts: list[str] = []
    for item in choices:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        reason = str(item.get("reason") or "").strip()
        if not reason:
            continue
        idx = None
        for i, opt in enumerate(opts, start=1):
            if label and label in opt:
                idx = i
                break
        if idx is None:
            for i, opt in enumerate(opts, start=1):
                if i != correct_idx + 1:
                    idx = i
                    break
        if idx is not None:
            parts.append(f"{idx}:{reason}")
    return ";".join(parts)


def question_to_row(qno: int, q: dict) -> dict[str, str]:
    field = str(q.get("field") or "").strip()
    category = field_id_to_category(field)
    level = int(q.get("level") or 1)
    opts = [str(o).strip() for o in (q.get("opts") or [])[:4]]
    while len(opts) < 4:
        opts.append("")
    ans = int(q.get("ans", 0))
    if ans < 0 or ans > 3:
        raise ValueError(f"question_no={qno}: ans={ans} が範囲外")
    exp = str(q.get("exp") or "").strip() or "（解説は未入力です。）"
    kaisetsu = q.get("kaisetsu") if isinstance(q.get("kaisetsu"), dict) else {}
    summary = str(kaisetsu.get("topic") or "").strip()
    if not summary and len(exp) > 120:
        summary = exp[:117] + "…"
    elif not summary:
        summary = exp
    basis = kaisetsu.get("basis") if isinstance(kaisetsu.get("basis"), dict) else {}
    reason = kaisetsu.get("reason") if isinstance(kaisetsu.get("reason"), dict) else {}
    return {
        "question_no": str(qno),
        "type": "single",
        "category": category,
        "tags": f"level{level}",
        "stem": str(q.get("text") or "").strip(),
        "preamble": "",
        "statement_a": "",
        "statement_b": "",
        "statement_c": "",
        "statement_d": "",
        "choice_1": opts[0],
        "choice_2": opts[1],
        "choice_3": opts[2],
        "choice_4": opts[3],
        "correct": str(ans + 1),
        "explanation": exp,
        "explanation_summary": summary,
        "explanation_correct": str(basis.get("text") or "").strip(),
        "explanation_choices": format_kaisetsu_choices(kaisetsu, opts, ans),
        "explanation_point": str(reason.get("text") or "").strip(),
    }


def flatten_orig(orig: dict[int, list]) -> list[dict]:
    out: list[dict] = []
    for lv in (1, 2, 3):
        for q in orig.get(lv, []):
            if not isinstance(q, dict):
                continue
            item = dict(q)
            item.setdefault("level", lv)
            out.append(item)
    return out


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="ORIG_QUESTIONS → practice_questions.csv")
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="サイトルート（既定: スクリプトの親の親）",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="takken-data-original.js（既定: <root>/takken-data-original.js）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="出力 CSV（既定: <root>/data/practice_questions.csv）",
    )
    parser.add_argument("--dry-run", action="store_true", help="件数のみ表示し書き込まない")
    parser.add_argument("--no-backup", action="store_true", help="既存 CSV のバックアップを取らない")
    args = parser.parse_args()

    root = args.root.resolve()
    source = (args.source or root / "takken-data-original.js").resolve()
    output = (args.output or root / "data" / "practice_questions.csv").resolve()

    try:
        orig = load_orig_questions(source)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ORIG 読み込み失敗: {exc}", file=sys.stderr)
        return 1

    flat = flatten_orig(orig)
    if not flat:
        print("ORIG_QUESTIONS が空です。", file=sys.stderr)
        return 1

    rows: list[dict[str, str]] = []
    for i, q in enumerate(flat, start=1):
        try:
            rows.append(question_to_row(i, q))
        except ValueError as exc:
            print(f"行変換エラー: {exc}", file=sys.stderr)
            return 1

    by_level = {1: 0, 2: 0, 3: 0}
    for r in rows:
        m = re.match(r"level(\d)", r.get("tags", ""))
        if m:
            by_level[int(m.group(1))] = by_level.get(int(m.group(1)), 0) + 1

    print(f"ORIG → practice CSV: {len(rows)} 問（L1={by_level[1]} L2={by_level[2]} L3={by_level[3]}）")
    print(f"  ソース: {source}")
    print(f"  出力:   {output}")

    if args.dry_run:
        return 0

    if output.is_file() and not args.no_backup:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = output.with_suffix(f".csv.bak-{stamp}")
        shutil.copy2(output, backup)
        print(f"  バックアップ: {backup.name}")

    write_csv(output, rows)
    print("書き出し完了。続けて python3 tools/build_all.py を実行してください。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
