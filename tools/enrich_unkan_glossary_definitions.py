#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""断片型 short_def / definition を試験向けの丁寧な定義文に拡張する。"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.knowledge_hub_seo import glossary_definition_body_text  # noqa: E402

CSV_PATH = ROOT / "data" / "glossary_terms.csv"

_TAIL_RE = re.compile(
    r"[^。]*は「[^」]+」の重要論点として、条文・告示・実務のいずれかで位置づけられる。?"
)
_FRAGMENT_SHORT_RE = re.compile(r"^[^。]{2,40}は、[^。]{1,40}。?$")


def _split_semicolon(value: str) -> list[str]:
    return [x.strip() for x in (value or "").split(";") if x.strip()]


def _def_fragments(defn: str, term: str) -> list[str]:
    text = (defn or "").strip()
    text = re.sub(rf"^まず「{re.escape(term)}」(?:は|とは)?[、,]?\s*", "", text)
    text = _TAIL_RE.sub("", text)
    parts: list[str] = []
    for chunk in re.split(r"(?<=[。．])", text):
        chunk = chunk.strip().rstrip("。")
        if not chunk or len(chunk) < 2:
            continue
        if chunk == term:
            continue
        parts.append(chunk)
    return parts


def _needs_enrich(row: dict[str, str]) -> bool:
    short = (row.get("short_def") or "").replace("\n", " ").strip()
    defn = (row.get("definition") or "").strip()
    if "頻出となる基礎用語" in short:
        return True
    if short.startswith("まず「"):
        return False
    if "試験では、" in short and len(short) >= 120:
        return False
    if len(short) < 80:
        return True
    if _FRAGMENT_SHORT_RE.match(short):
        return True
    if len(defn) < 80:
        return True
    return False


def _compose_core_sentence(
    term: str,
    category: str,
    fragments: list[str],
    legal: str,
    exam_points: list[str],
) -> str:
    legal_first = legal or "関連法令"
    if fragments and all(len(f) <= 18 for f in fragments[:4]):
        detail = "、".join(fragments[:4])
        return (
            f"{term}は、{detail}などが{category}で整理される重要概念である。"
            f"根拠は主に{legal_first}である。"
        )
    if fragments:
        body = "。".join(fragments[:2])
        if not body.startswith(term):
            return f"{term}は、{body}。"
        return body if body.endswith("。") else f"{body}。"
    hint = exam_points[0] if exam_points else category
    return (
        f"{term}は、{category}分野で重要な用語であり、"
        f"{legal_first}上の位置づけと{hint}をセットで押さえる必要がある。"
    )


def _build_rich_short_def(row: dict[str, str]) -> str:
    term = (row.get("term") or "").strip()
    category = (row.get("category") or "").strip()
    legal = _split_semicolon(row.get("legal_basis") or "")
    legal_first = legal[0] if legal else ""
    exam_points = _split_semicolon(row.get("exam_points") or "")
    exam_clean: list[str] = []
    for p in exam_points:
        p = re.sub(r"（[^）]*）", "", p).strip()
        p = re.sub(r"[。．]+$", "", p).strip()
        if p and p not in exam_clean:
            exam_clean.append(p)
    fragments = _def_fragments(row.get("definition") or "", term)
    if not fragments:
        fragments = _def_fragments(row.get("short_def") or "", term)

    core = _compose_core_sentence(term, category, fragments, legal_first, exam_clean)
    if exam_clean:
        example = (
            f"たとえば、{exam_clean[0]}が正誤の分かれ目になりやすい。"
            if len(exam_clean[0]) >= 4
            else f"たとえば、{legal_first or category}との対応を確認する場面で問われます。"
        )
        exam_bits = "・".join(exam_clean[:3])
        exam_line = f"試験では、{exam_bits}を条文とセットで押さえると得点源になります。"
    else:
        example = f"たとえば、{legal_first or category}の条文・告示と照合しながら整理すると定着しやすい。"
        exam_line = f"試験では、{term}の定義と適用場面を説明できる点を押さえると得点源になります。"

    return f"{core}\n\n{example}\n\n{exam_line}"


def _build_definition(term: str, category: str, core: str, legal: str) -> str:
    core_one = core.replace("\n", " ").strip()
    core_one = re.sub(rf"^まず「{re.escape(term)}」(?:は|とは)?[、,]?\s*", "", core_one)
    body = core_one.rstrip("。")
    if not body.startswith(term):
        body = f"{term}は、{body}"
    tail = f"{category}では「{legal or category}」の文脈で繰り返し問われます。"
    return f"まず「{term}」は、{body}。 {tail}"


def enrich_row(row: dict[str, str]) -> tuple[dict[str, str], bool]:
    if not _needs_enrich(row):
        return row, False

    term = (row.get("term") or "").strip()
    category = (row.get("category") or "").strip()
    legal_first = _split_semicolon(row.get("legal_basis") or "")
    legal = legal_first[0] if legal_first else ""

    short_def = _build_rich_short_def(row)
    core_line = short_def.split("\n\n")[0]
    definition = _build_definition(term, category, core_line, legal)

    new_row = dict(row)
    new_row["short_def"] = short_def
    new_row["definition"] = definition
    new_row["term_detail_body"] = ""

    body = glossary_definition_body_text(new_row)
    if len(body) < 180:
        extra = (
            f"{term}は{category}の重要論点として、"
            f"{legal or '関連法令'}を根拠に主体・期限・手続の正誤を見極める。"
        )
        body = f"{body}\n\n{extra}"
    new_row["term_detail_body"] = body

    return new_row, True


def main() -> int:
    if not CSV_PATH.is_file():
        raise SystemExit(f"missing: {CSV_PATH}")

    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        header = list(reader.fieldnames or [])
        rows = list(reader)

    changed = 0
    out_rows: list[dict[str, str]] = []
    for row in rows:
        fixed, did = enrich_row(row)
        if did:
            changed += 1
        out_rows.append(fixed)

    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"enriched {changed}/{len(out_rows)} rows in {CSV_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
