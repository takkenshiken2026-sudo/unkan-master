#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知識ハブ CSV 統合出力の共通ヘルパー（S30 + S31、プレミアムFAQ適用）."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable

from tools.hub_faq_expand import expand_all as expand_short_faqs  # noqa: E402
from tools.hub_premium_faq_auto import apply_all as apply_auto_premium  # noqa: E402
from tools.hub_premium_faq_auto import discover_official_suffix  # noqa: E402
from tools.hub_strip_batch_suffix import strip_hub_rows  # noqa: E402
from tools.hub_collapse_angles import collapse_finalized_hubs, write_hub_redirects  # noqa: E402
from tools.hub_diversify_content import diversify_hub_rows  # noqa: E402


def apply_hub_collapse(
    data_dir: Path,
    comparisons: list[dict],
    numbers: list[dict],
    mistakes: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    comparisons, numbers, mistakes, redirects = collapse_finalized_hubs(
        comparisons, numbers, mistakes
    )
    write_hub_redirects(data_dir, redirects)
    return comparisons, numbers, mistakes


def finalize_hub_rows(
    rows: list[dict],
    *,
    apply_premium: Callable[[list[dict]], list[dict]] | None = None,
    official_suffix: str | None = None,
) -> list[dict]:
    if apply_premium:
        rows = apply_premium(rows)
    rows = strip_hub_rows(rows)
    suffix = official_suffix if official_suffix is not None else discover_official_suffix(
        Path(__file__).resolve().parents[2]
    )
    rows = apply_auto_premium(rows, official_suffix=suffix)
    rows = diversify_hub_rows(rows)
    return expand_short_faqs(rows)


def merge_rows(*groups: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for group in groups:
        for row in group:
            slug = row["slug"]
            if slug in seen:
                raise ValueError(f"duplicate slug: {slug}")
            seen.add(slug)
            out.append(row)
    return out


merge = merge_rows  # backward compat for write_*_hub_data.py


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def write_hub_csvs(
    data_dir: Path,
    *,
    header_compare: list[str],
    header_numbers: list[str],
    header_mistakes: list[str],
    comparisons: list[dict],
    numbers: list[dict],
    mistakes: list[dict],
    apply_premium: Callable[[list[dict]], list[dict]] | None = None,
) -> None:
    if apply_premium:
        comparisons = apply_premium(comparisons)
        numbers = apply_premium(numbers)
        mistakes = apply_premium(mistakes)
    comparisons = strip_hub_rows(comparisons)
    numbers = strip_hub_rows(numbers)
    mistakes = strip_hub_rows(mistakes)
    suffix = discover_official_suffix(data_dir.parent)
    comparisons = apply_auto_premium(comparisons, official_suffix=suffix)
    numbers = apply_auto_premium(numbers, official_suffix=suffix)
    mistakes = apply_auto_premium(mistakes, official_suffix=suffix)
    comparisons = diversify_hub_rows(comparisons)
    numbers = diversify_hub_rows(numbers)
    mistakes = diversify_hub_rows(mistakes)
    comparisons = expand_short_faqs(comparisons)
    numbers = expand_short_faqs(numbers)
    mistakes = expand_short_faqs(mistakes)
    comparisons, numbers, mistakes, redirects = collapse_finalized_hubs(
        comparisons, numbers, mistakes
    )
    write_hub_redirects(data_dir, redirects)
    write_csv(data_dir / "comparisons.csv", header_compare, comparisons)
    write_csv(data_dir / "numbers.csv", header_numbers, numbers)
    write_csv(data_dir / "mistakes.csv", header_mistakes, mistakes)
    print(
        f"wrote compare={len(comparisons)} numbers={len(numbers)} mistakes={len(mistakes)}"
    )
