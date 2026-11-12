#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""問題データ（過去問・実践演習・一問一答）の破損を検出してビルドを止める。

図表抽出の潰れ込み／選択肢の分割断片／正答の形式・範囲／一問一答の○×矛盾など、
本セッションで実際に見つかった破損パターンの再発を防ぐための防衛ライン。
ERROR が 1 件でもあれば非 0 で終了し、build_all.py / CI のデプロイを止める。

使い方: python3 tools/validate_question_integrity.py
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

csv.field_size_limit(10**7)
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# 図表がテキストに潰れ込んだときにだけ現れる連結ヘッダ（正常な設問文には出ない）
_CONCAT_HEADERS = (
    "始業時刻出庫時刻",
    "出庫時刻到着時刻",
    "到着時刻終業時刻",
    "乗務前点呼等運転",
    "乗務後点呼等（",
    "運転運転休憩運転",
    "休憩運転休憩運転",
    "荷下ろし荷積み運転",
    "営業所乗務前点呼",
)
# 選択肢が測定値の境界で分割された断片（既知パターン）
_CHOICE_FRAGMENTS = {
    "積載物の高さは、原則として",
    "8メートル以上",
    "9メートル以上",
    "5メートル、高さ",
    "6メートル、高さ",
    "積載物の高さは、",
    "時速5",
    "5キロメートル",
}
_LONG_DIGITS = re.compile(r"\d{5,}")  # 設問文中の5桁以上連続数字＝図版数値の潰れ込み
_errors: list[str] = []
_warns: list[str] = []


def _e(msg: str) -> None:
    _errors.append(msg)


def _w(msg: str) -> None:
    _warns.append(msg)


def _norm(v) -> str:
    return (v or "").strip()


def _choices(row: dict) -> dict:
    return {i: _norm(row.get(f"choice_{i}")) for i in range(1, 9) if _norm(row.get(f"choice_{i}"))}


def _nums(correct: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", correct)]


def check_mcq(label: str, row: dict) -> None:
    """過去問・実践演習（選択式）の破損を検査。"""
    stem = _norm(row.get("stem")) + " " + _norm(row.get("preamble"))
    typ = _norm(row.get("type"))
    correct = _norm(row.get("correct"))
    ch = _choices(row)
    n = len(ch)

    # 1) 設問文に図版の潰れ込み
    for h in _CONCAT_HEADERS:
        if h in stem:
            _e(f"{label}: 設問文に図表の潰れ込み（連結ヘッダ『{h}』）")
            break
    m = _LONG_DIGITS.search(stem)
    if m:
        _e(f"{label}: 設問文に5桁以上の連続数字『{m.group()[:12]}』（図版数値の潰れ込みの疑い）")

    # 2) 選択肢の分割断片
    for i, v in ch.items():
        if v in _CHOICE_FRAGMENTS:
            _e(f"{label}: 選択肢{i}が分割断片『{v}』")

    # 3) 空の必須項目
    if not stem.strip():
        _e(f"{label}: 設問文が空")
    if not correct:
        _e(f"{label}: 正答が空")
    if n < 2:
        _e(f"{label}: 選択肢が{n}個しかない")

    # 4) 正答の形式・範囲
    if typ in ("single", "multi"):
        nums = _nums(correct)
        if not nums:
            _e(f"{label}: 正答『{correct}』に番号が無い")
        if typ == "single" and len(nums) != 1:
            _e(f"{label}: single だが正答が複数/不正『{correct}』")
        for x in nums:
            if not (1 <= x <= n):
                _e(f"{label}: 正答番号{x}が選択肢数{n}の範囲外")
    elif typ == "combination":
        pairs = re.findall(r"[A-EＡ-Ｅア-オ]\s*-\s*(\d+)", correct)
        if not pairs:
            _e(f"{label}: combination の正答形式が不正『{correct}』")
        for x in pairs:
            if int(x) > n:
                _e(f"{label}: combination 正答{x}が選択肢数{n}超")
    elif typ == "truefalse_group":
        if not re.search(r"(適|正|否|不適|誤)\s*-", correct):
            _e(f"{label}: truefalse の正答形式が不正『{correct}』")


def audit_mcq_csv(fname: str, is_practice: bool) -> None:
    path = DATA / fname
    if not path.is_file():
        return
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for i, row in enumerate(rows, start=2):
        if is_practice:
            label = f"{fname}:{i} 実践{_norm(row.get('question_no'))}"
        else:
            label = f"{fname}:{i} {_norm(row.get('exam_wareki'))} 問{_norm(row.get('question_no'))}"
        check_mcq(label, row)


def audit_ichimon() -> None:
    path = DATA / "ichimon_questions.csv"
    if not path.is_file():
        return
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for i, row in enumerate(rows, start=2):
        label = f"ichimon_questions.csv:{i} {_norm(row.get('id'))}"
        ans = _norm(row.get("answer"))
        ec = _norm(row.get("explanation_correct"))
        q = _norm(row.get("question"))
        if ans not in ("○", "×"):
            _e(f"{label}: answer が ○/× 以外『{ans}』")
        if not q:
            _e(f"{label}: 設問が空")
        # ○× と解説の矛盾
        head = ec[:8]
        if ans == "○" and "記述は誤り" in head:
            _e(f"{label}: ○なのに解説が『記述は誤り』")
        if ans == "×" and "記述は正しい" in head:
            _e(f"{label}: ×なのに解説が『記述は正しい』")


def main() -> int:
    audit_mcq_csv("past_questions.csv", is_practice=False)
    audit_mcq_csv("practice_questions.csv", is_practice=True)
    audit_ichimon()
    for w in _warns:
        print(f"[WARN] {w}")
    for e in _errors:
        print(f"[ERROR] {e}")
    if _errors:
        print(f"\n問題データ整合性チェック: {len(_errors)} 件のエラー（ビルドを中止）")
        return 1
    print(f"問題データ整合性チェック: 異常なし（警告 {len(_warns)} 件）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
