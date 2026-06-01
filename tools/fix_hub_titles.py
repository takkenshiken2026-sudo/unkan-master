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

from tools.hub_strip_batch_suffix import strip_batch_suffix  # noqa: E402

HUB_FILES = ("comparisons.csv", "numbers.csv", "mistakes.csv")
HUB_TAG = {
    "comparisons.csv": "比較",
    "numbers.csv": "数値",
    "mistakes.csv": "誤答",
}


def _title_key(title: str) -> str:
    return strip_batch_suffix(title.strip())


def _similar(t1: str, t2: str) -> bool:
    if not t1 or not t2:
        return False
    if t1 == t2:
        return True
    if _title_key(t1) == _title_key(t2):
        return True
    return SequenceMatcher(None, _title_key(t1), _title_key(t2)).ratio() >= 0.88


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def _write(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def _disambiguator(row: dict[str, str], hub_file: str, *, level: int) -> str:
    highlight = (row.get("highlight") or "").strip()
    category = (row.get("category") or "").strip()
    slug = (row.get("slug") or "").strip()
    if level >= 3 and slug:
        parts = slug.split("-")
        return "-".join(parts[-2:]) if len(parts) >= 2 else slug[-16:]
    if level >= 2 and highlight:
        return highlight[:16]
    if level >= 1 and category:
        return category[:14]
    if highlight and len(highlight) <= 18:
        return highlight
    tail = slug.split("-")[-1] if slug else ""
    if tail:
        return tail
    return HUB_TAG.get(hub_file, "論点")


def _tweak_title(row: dict[str, str], hub_file: str, *, level: int) -> str | None:
    title = (row.get("title") or "").strip()
    if not title:
        return None
    highlight = (row.get("highlight") or row.get("category") or "").strip()
    if level >= 4:
        label = highlight[:8] or _disambiguator(row, hub_file, level=3)[:8]
        if label and not title.startswith(f"【{label}】"):
            return f"【{label}】{title}"
        return None
    tag = _disambiguator(row, hub_file, level=level)
    if tag and tag not in title:
        return f"{title}｜{tag}"
    return None


def fix_file(path: Path) -> int:
    header, rows = _read(path)
    if not rows:
        return 0
    changed = 0
    for _ in range(12):
        round_changed = 0
        indices = [i for i, row in enumerate(rows) if (row.get("title") or "").strip()]
        for ai, i in enumerate(indices):
            t1 = (rows[i].get("title") or "").strip()
            for j in indices[ai + 1 :]:
                t2 = (rows[j].get("title") or "").strip()
                if not _similar(t1, t2):
                    continue
                for idx in (i, j):
                    row = rows[idx]
                    title = (row.get("title") or "").strip()
                    for level in range(5):
                        new_title = _tweak_title(row, path.name, level=level)
                        if new_title and new_title != title:
                            row["title"] = new_title
                            round_changed += 1
                            break
        if round_changed == 0:
            break
        changed += round_changed
    if changed:
        _write(path, header, rows)
    return changed


def fix_site(root: Path) -> int:
    data = root / "data"
    rows_by: dict[str, tuple[list[str], list[dict[str, str]]]] = {}
    for name in HUB_FILES:
        path = data / name
        if path.is_file():
            rows_by[name] = _read(path)
    total = 0
    for name in HUB_FILES:
        path = data / name
        if not path.is_file():
            continue
        n = fix_file(path)
        if n:
            print(f"  {name}: {n} title tweaks")
        total += n
        rows_by[name] = _read(path)

    entries: list[tuple[str, int, dict[str, str]]] = []
    for name in HUB_FILES:
        if name not in rows_by:
            continue
        _, rows = rows_by[name]
        for i, row in enumerate(rows):
            if (row.get("title") or "").strip():
                entries.append((name, i, row))
    cross = 0
    for round_no in range(8):
        round_cross = 0
        for a in range(len(entries)):
            f1, _, r1 = entries[a]
            t1 = (r1.get("title") or "").strip()
            for b in range(a + 1, len(entries)):
                f2, _, r2 = entries[b]
                t2 = (r2.get("title") or "").strip()
                if not _similar(t1, t2):
                    continue
                for fname, row in ((f1, r1), (f2, r2)):
                    for level in range(5):
                        new_title = _tweak_title(row, fname, level=level + round_no)
                        if new_title and new_title != (row.get("title") or "").strip():
                            row["title"] = new_title
                            round_cross += 1
                            break
        cross += round_cross
        if round_cross == 0:
            break
    if cross:
        for name in HUB_FILES:
            if name in rows_by:
                header, rows = rows_by[name]
                _write(data / name, header, rows)
        print(f"  cross-hub: {cross} title tweaks")
    total += cross
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
