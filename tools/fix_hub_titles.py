#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同一ハブ CSV 内の類似タイトルを slug/highlight で一意化する。"""

from __future__ import annotations

import argparse
import csv
import sys
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.hub_strip_batch_suffix import BATCH_SUFFIX_RE  # noqa: E402

HUB_FILES = ("comparisons.csv", "numbers.csv", "mistakes.csv")
HUB_TAG = {
    "comparisons.csv": "比較",
    "numbers.csv": "数値",
    "mistakes.csv": "誤答",
}


def _title_key(title: str) -> str:
    return BATCH_SUFFIX_RE.sub("", title.strip()).strip()


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def _write(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def _disambiguator(row: dict[str, str], hub_file: str) -> str:
    highlight = (row.get("highlight") or "").strip()
    if highlight and len(highlight) <= 18:
        return highlight
    slug = (row.get("slug") or "").strip()
    tail = slug.split("-")[-1] if slug else ""
    if tail:
        return tail
    return HUB_TAG.get(hub_file, "論点")


def fix_file(path: Path) -> int:
    header, rows = _read(path)
    if not rows:
        return 0
    changed = 0
    titles = [(i, (row.get("title") or "").strip()) for i, row in enumerate(rows)]
    for i, t1 in titles:
        if not t1:
            continue
        for j, t2 in titles[i + 1 :]:
            if not t2:
                continue
            if t1 == t2 or SequenceMatcher(None, _title_key(t1), _title_key(t2)).ratio() >= 0.88:
                for idx in (i, j):
                    row = rows[idx]
                    title = (row.get("title") or "").strip()
                    tag = _disambiguator(row, path.name)
                    if tag and tag not in title:
                        new_title = f"{title}｜{tag}"
                        if new_title != title:
                            row["title"] = new_title
                            changed += 1
    if changed:
        _write(path, header, rows)
    return changed


def fix_site(root: Path) -> int:
    total = 0
    data = root / "data"
    for name in HUB_FILES:
        path = data / name
        if path.is_file():
            n = fix_file(path)
            if n:
                print(f"  {name}: {n} title tweaks")
            total += n
    return total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    n = fix_site(args.root.resolve())
    print(f"done: {n} title tweaks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
