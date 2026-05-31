#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成済み試験ガイド HTML の意味整合チェック（build 後ゲート）。"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.editorial_quality import is_published_guide, norm  # noqa: E402
from tools.guide_coherence_rules import audit_article_html, is_tier_a_slug  # noqa: E402

GUIDE_CSV = ROOT / "data" / "guide_articles.csv"
ARTICLES_DIR = ROOT / "articles"
GEN_MARKER = ".generated-by-exam-site"


def main() -> int:
    parser = argparse.ArgumentParser(description="試験ガイド HTML の意味整合チェック")
    parser.add_argument(
        "--all",
        action="store_true",
        help="全 published 記事を対象（既定は A級 slug のみ）",
    )
    args = parser.parse_args()

    if not GUIDE_CSV.is_file():
        print(f"missing: {GUIDE_CSV}", file=sys.stderr)
        return 0
    rows = list(csv.DictReader(GUIDE_CSV.open(encoding="utf-8-sig")))
    errors = 0
    checked = 0
    for row in rows:
        slug = norm(row.get("slug"))
        if not slug or not is_published_guide(row):
            continue
        if not args.all and not is_tier_a_slug(slug):
            continue
        html_path = ARTICLES_DIR / slug / "index.html"
        if not html_path.is_file():
            print(f"ERROR {slug}: HTML missing ({html_path.relative_to(ROOT)})", file=sys.stderr)
            errors += 1
            continue
        if not (ARTICLES_DIR / slug / GEN_MARKER).is_file():
            continue
        checked += 1
        html = html_path.read_text(encoding="utf-8")
        for msg in audit_article_html(slug, html):
            print(f"ERROR {slug}: {msg}", file=sys.stderr)
            errors += 1
    print(f"validate_guide_html_coherence: checked {checked} articles, errors {errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
