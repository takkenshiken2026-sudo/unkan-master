#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mentalhealth guide_articles.csv の related_links をテンプレ検証向けに修正。"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

TARGET_REMAP = {
    "terms/index.html": "glossary-how-to",
    "terms/utsu-byo/index.html": "depression-workplace",
    "terms/36-kyotei/index.html": "overwork-prevention",
    "articles/chapters/index.html": "subjects",
    "q/index.html": "past-questions-study",
}


def fix_token(token: str, slugs: set[str]) -> str:
    token = token.strip()
    if not token:
        return token
    if token.startswith(("http://", "https://")):
        return token
    if "|" in token and ":" not in token:
        parts = token.split("|", 1)
        token = f"{parts[0].strip()}:{parts[1].strip()}"
    if ":" in token:
        target, label = token.split(":", 1)
        target = target.strip()
        label = label.strip()
    else:
        target, label = token, ""
    target = TARGET_REMAP.get(target, target)
    if not SLUG_RE.match(target):
        return ""
    if target not in slugs:
        return ""
    return f"{target}:{label}" if label else target


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, type=Path)
    args = ap.parse_args()
    path = args.target.resolve() / "data" / "guide_articles.csv"
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    slugs = {(r.get("slug") or "").strip() for r in rows if (r.get("slug") or "").strip()}

    for row in rows:
        raw = (row.get("related_links") or "").strip()
        if not raw:
            continue
        out: list[str] = []
        for token in raw.split(";"):
            fixed = fix_token(token, slugs)
            if fixed:
                out.append(fixed)
        row["related_links"] = ";".join(out)

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"updated {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
