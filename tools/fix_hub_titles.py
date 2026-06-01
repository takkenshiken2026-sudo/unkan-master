#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同一ハブ CSV 内の類似タイトルを slug/highlight で一意化する。"""

from __future__ import annotations

import argparse
import csv
import re
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
BATCH_IN_PARENS = re.compile(r"（([^）]{2,12})）")
ARTICLE_PIPE = re.compile(r"｜[^｜]+$")


def _title_key(title: str) -> str:
    return BATCH_SUFFIX_RE.sub("", title.strip()).strip()


def _similar(t1: str, t2: str) -> bool:
    if not t1 or not t2:
        return False
    if t1 == t2:
        return True
    k1, k2 = _title_key(t1), _title_key(t2)
    if k1 == k2:
        return True
    return SequenceMatcher(None, k1, k2).ratio() >= 0.88


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def _write(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def _clean_title(title: str) -> str:
    """連続した同一【…】プレフィックスを1つに戻す。"""
    while True:
        idx = title.find("【")
        if idx < 0:
            break
        end = title.find("】", idx)
        if end < 0:
            break
        chunk = title[idx : end + 1]
        rest = title[end + 1 :]
        if rest.startswith(chunk):
            title = title[:idx] + rest
            continue
        break
    return title.strip()


def _summary_phase(row: dict[str, str]) -> str:
    summary = (row.get("summary") or "").strip()
    match = BATCH_IN_PARENS.search(summary)
    if match:
        return match.group(1)
    slug = (row.get("slug") or "").strip()
    return slug.split("-")[-1] if slug else ""


def _article_core(row: dict[str, str]) -> str:
    article = (row.get("article_title") or "").strip()
    if not article:
        return ""
    return ARTICLE_PIPE.sub("", article).strip()


def _title_variants(row: dict[str, str], hub_file: str):
    slug = (row.get("slug") or "").strip()
    phase = _summary_phase(row)
    tag = HUB_TAG.get(hub_file, "論点")
    topic = (row.get("tags") or "").split(";")[0].strip()
    if not topic:
        summary = (row.get("summary") or "").strip()
        topic = summary.split("（")[0][:10] if summary else slug.split("-")[0]
    article = _article_core(row)
    cols = (row.get("col_labels") or "").split(";")[0].strip()
    summary = (row.get("summary") or "").strip()

    yield f"{topic}（{phase}）｜{slug}"
    if article:
        yield f"{article}（{phase}）"
        yield f"{article}｜{slug}"
    if cols:
        yield f"{cols}（{phase}）｜{slug}"
    if summary:
        yield f"{summary[:28]}｜{slug.split('-')[-1]}"
    if slug:
        yield slug
        yield f"{slug}・{tag}"
        hub = hub_file.replace(".csv", "")
        yield f"〔{hub}〕{slug}"
    for n in range(12):
        yield f"{slug}·{n}"


def _pick_unique_title(row: dict[str, str], hub_file: str, others: list[str]) -> str:
    for candidate in _title_variants(row, hub_file):
        if not any(_similar(candidate, other) for other in others):
            return candidate
    slug = (row.get("slug") or "row").strip()
    return f"{slug}·uniq"


def _tweak_title(row: dict[str, str], hub_file: str, *, level: int) -> str | None:
    title = _clean_title((row.get("title") or "").strip())
    if not title:
        return None
    highlight = (row.get("highlight") or "").strip()
    category = (row.get("category") or "").strip()
    slug = (row.get("slug") or "").strip()
    if level == 0:
        tag = highlight[:16] if highlight else slug.split("-")[-1] if slug else HUB_TAG.get(hub_file, "論点")
        if tag and tag not in title:
            return f"{title}｜{tag}"
    if level == 1 and highlight and "【" not in title[:24]:
        label = highlight[:8]
        if label:
            return f"【{label}】{title}"
    if level == 2 and slug:
        tail = "-".join(slug.split("-")[-2:]) if "-" in slug else slug[-14:]
        if tail and tail not in title:
            return f"{title}｜{tail}"
    if level == 3 and category and "【" not in title[:24]:
        return f"【{category[:8]}】{title}"
    if level >= 4 and slug:
        batch = slug.split("-")[-1]
        core = _title_key(title).split("｜")[0]
        if batch and batch not in core:
            return f"{core}（{batch}）｜{slug.split('-')[-2]}-{batch}" if "-" in slug else f"{core}（{batch}）"
    if level == 5 and slug:
        token = slug if len(slug) <= 28 else "-".join(slug.split("-")[-3:])
        if token not in title[:32]:
            return f"〔{token}〕{title}"
    return None


def _resolve_similar_titles(rows: list[dict[str, str]], hub_file: str) -> int:
    changed = 0
    active = [i for i, row in enumerate(rows) if (row.get("title") or "").strip()]
    for _ in range(16):
        dup_indices: set[int] = set()
        for ai, i in enumerate(active):
            t1 = (rows[i].get("title") or "").strip()
            for j in active[ai + 1 :]:
                t2 = (rows[j].get("title") or "").strip()
                if _similar(t1, t2):
                    dup_indices.add(i)
                    dup_indices.add(j)
        if not dup_indices:
            break
        round_changed = 0
        for idx in sorted(dup_indices):
            row = rows[idx]
            others = [(rows[j].get("title") or "").strip() for j in active if j != idx]
            new_title = _pick_unique_title(row, hub_file, others)
            old_title = (row.get("title") or "").strip()
            if new_title != old_title:
                row["title"] = new_title
                round_changed += 1
        changed += round_changed
        if round_changed == 0:
            break
    return changed


def fix_file(path: Path) -> int:
    header, rows = _read(path)
    if not rows:
        return 0
    changed = 0
    hub_file = path.name
    for _ in range(24):
        round_changed = 0
        active = [i for i, row in enumerate(rows) if (row.get("title") or "").strip()]
        for ai, i in enumerate(active):
            t1 = (rows[i].get("title") or "").strip()
            for j in active[ai + 1 :]:
                t2 = (rows[j].get("title") or "").strip()
                if not _similar(t1, t2):
                    continue
                for pair_idx, idx in enumerate((i, j)):
                    row = rows[idx]
                    title = (row.get("title") or "").strip()
                    start = pair_idx * 2
                    for level in range(start, start + 6):
                        new_title = _tweak_title(row, hub_file, level=level)
                        if new_title and new_title != title:
                            row["title"] = new_title
                            round_changed += 1
                            break
        if round_changed == 0:
            break
        changed += round_changed
    changed += _resolve_similar_titles(rows, hub_file)
    if changed:
        _write(path, header, rows)
    return changed


def fix_site(root: Path) -> int:
    data = root / "data"
    total = 0
    for name in HUB_FILES:
        path = data / name
        if not path.is_file():
            continue
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
