#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ガイド CSV から 180字確保用の汎用パディングを除去する。"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.editorial_quality import is_published_guide, norm  # noqa: E402
from tools.guide_prose_patterns import PROSE_COLUMNS  # noqa: E402

# section_body_min_filler / ensure_visible_min が付与する末尾文
GENERIC_SECTION_PAD_RE = re.compile(
    r"(?:\s|\n)*"
    r"「[^」]+」では、[^。]*?"
    r"公式テキストの該当章を開き、主体・期限・数値をメモしながら演習問題で定着を確認します。"
    r"数値・日程は[^。]+(?:の)?最新要項で必ず照合してください。"
    r"[。]?",
    re.MULTILINE,
)

# 切れたタイトル + 同パターン（アフィリエイト等）
BROKEN_TITLE_PAD_RE = re.compile(
    r"(?:\s|\n)*"
    r"「[^」]+」では、[^。]{0,80}について公式テキストの該当章を開き、"
    r"主体・期限・数値をメモしながら演習問題で定着を確認します。"
    r"数値・日程は[^。]+(?:の)?最新要項で必ず照合してください。"
    r"[。]?",
    re.MULTILINE,
)

# 節末尾の「「見出し」で。」だけ
INCOMPLETE_HEADING_TAIL_RE = re.compile(
    r"(?:\s|\n)*「[^」]+」(?:で|では)[。、]?\s*$",
    re.MULTILINE,
)

ENRICH_SECTION_PAD_RE = re.compile(
    r"(?:\s|\n)*"
    r"(?:「[^」]+」は[^。]+の論点として、公式テキスト該当章[^。]*演習→用語解説→1週間後[^。]*。"
    r"|[^。]*演習→用語解説→1週間後の解き直しで定着を確認[^。]*。"
    r"|「[^」]+」は[^。]+の論点として、公式テキスト該当章と[^。]+の案内を照合し、"
    r"演習→用語解説→1週間後の解き直しで定着を確認してください。"
    r"(?:数値・日程・合格基準は[^。]+確認してください。?)?"
    r")"
    r"[。]?",
    re.MULTILINE,
)

ENRICH_FAQ_PAD_RE = re.compile(
    r"(?:\s|\n)*"
    r"「[^」]+」は[^。]+(?:の要項と公式テキストで最新情報を確認してください|について[^。]+確認してください)"
    r"[^。]*条文の主体・期限・数値を演習問題とセットで押さえる[^。]*。"
    r"[。]?",
    re.MULTILINE,
)

AUTO_LEAD_PAD_RE = re.compile(
    r"^マンション管理士試験の試験の[^。]+について、マ管受験者が現場で迷いやすい[^。]+。"
    r"3分野の全体像[^。]*。$",
    re.MULTILINE,
)

FAQ_GENERIC_PAD_RE = re.compile(
    r"\s*"
    r"(?:合格までの学習を続けるには、出題範囲を分けて、演習と復習を定期的に回す計画が重要です。"
    r"公式情報を先に確認し、このサイトの演習と用語解説で弱点を補強する流れを推奨します。|"
    r"マンション管理士試験の[^。]+について、マ管受験者が現場で迷いやすい論点と試験での出題パターンを整理する記事です。"
    r"公式テキストと[^。]+を参照しながら、演習・用語解説で弱点を補強する進め方をまとめます。|"
    r"独学で合格を目指す場合は、教材を増やす前に出題範囲と復習の仕組みを決めておくことが大切です。"
    r"公式情報を先に確認し、このサイトの演習と用語解説で弱点を補強する流れを推奨します。|"
    r"用語解説は、過去問で出た語句の意味、根拠、似た用語との違いを確認するための入口です。"
    r"公式情報を先に確認し、このサイトの演習と用語解説で弱点を補強する流れを推奨します。"
    r")",
)

BROKEN_TOPIC_DE_RE = re.compile(r"では、を")
BROKEN_TOPIC_FIX = "では、"


def strip_padding_from_text(text: str) -> str:
    if not text:
        return text
    out = text
    prev = None
    while prev != out:
        prev = out
        out = GENERIC_SECTION_PAD_RE.sub("", out)
        out = BROKEN_TITLE_PAD_RE.sub("", out)
        out = ENRICH_SECTION_PAD_RE.sub("", out)
        out = ENRICH_FAQ_PAD_RE.sub("", out)
        out = AUTO_LEAD_PAD_RE.sub("", out)
        out = FAQ_GENERIC_PAD_RE.sub("", out)
        out = INCOMPLETE_HEADING_TAIL_RE.sub("", out)
    out = BROKEN_TOPIC_DE_RE.sub(BROKEN_TOPIC_FIX, out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    return out.strip()


def strip_row(row: dict[str, str]) -> bool:
    before = {k: row.get(k, "") for k in row}
    for col in PROSE_COLUMNS:
        raw = norm(row.get(col))
        if not raw:
            continue
        cleaned = strip_padding_from_text(raw)
        if cleaned != raw:
            row[col] = cleaned
    return any(before.get(k) != row.get(k, "") for k in row)


def strip_site(root: Path, *, dry_run: bool = False, all_rows: bool = False) -> dict:
    guide_csv = root / "data" / "guide_articles.csv"
    if not guide_csv.is_file():
        return {"changed": 0, "error": "missing guide_articles.csv"}
    with guide_csv.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    changed = 0
    for row in rows:
        if not all_rows and not is_published_guide(row):
            continue
        if strip_row(row):
            changed += 1
    if changed and not dry_run:
        with guide_csv.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    return {"changed": changed, "rows": len(rows)}


def main() -> int:
    parser = argparse.ArgumentParser(description="ガイド CSV 汎用パディング除去")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--all-rows", action="store_true", help="draft 含む全行")
    args = parser.parse_args()
    stats = strip_site(args.root.resolve(), dry_run=args.dry_run, all_rows=args.all_rows)
    print(f"strip generic padding: {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
