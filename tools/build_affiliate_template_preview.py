#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a local HTML preview for an affiliate article template (design review only)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_article_pages import build_article_html, load_articles  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", default="affiliate-textbooks-recommend")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output HTML path (default: articles/{slug}/index.html)",
    )
    args = parser.parse_args()
    if args.out is None:
        args.out = ROOT / "articles" / args.slug / "index.html"

    articles = load_articles()
    row = next((a for a in articles if a.get("slug") == args.slug), None)
    if not row:
        print(f"slug not found: {args.slug}", file=sys.stderr)
        return 1

    by_slug = {a["slug"]: a for a in articles}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(build_article_html(row, by_slug), encoding="utf-8")
    print(f"Wrote preview → {args.out}")
    print("Open: python3 -m http.server 8765 → /articles/{slug}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
