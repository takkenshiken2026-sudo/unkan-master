#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build sitemap.xml with lastmod for all public HTML pages."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.site_config import clean_origin  # noqa: E402
from tools.sitemap_utils import SitemapEntry, iso_date, iso_from_mtime, write_sitemap  # noqa: E402

GUIDE_CSV = ROOT / "data" / "guide_articles.csv"


def guide_lastmod_by_slug() -> dict[str, str]:
    out: dict[str, str] = {}
    if not GUIDE_CSV.is_file():
        return out
    text = GUIDE_CSV.read_text(encoding="utf-8-sig")
    for row in csv.DictReader(text.splitlines()):
        slug = (row.get("slug") or "").strip()
        if not slug:
            continue
        for col in ("fact_checked_at", "last_reviewed_at", "source_checked_at"):
            d = iso_date(row.get(col))
            if d:
                out[slug] = d
                break
    return out


def add_file(entries: list[SitemapEntry], base: str, rel: str, lastmod: str | None = None) -> None:
    path = ROOT / rel
    if not path.is_file():
        return
    mod = lastmod or iso_from_mtime(path)
    entries.append(SitemapEntry(loc=f"{base}/{rel.replace(chr(92), '/')}", lastmod=mod))


def collect_entries(base: str) -> list[SitemapEntry]:
    entries: list[SitemapEntry] = []
    guide_dates = guide_lastmod_by_slug()

    static_pages = ["index.html", "about.html", "privacy.html", "related-sites.html"]
    for rel in static_pages:
        add_file(entries, base, rel)

    articles_root = ROOT / "articles"
    if articles_root.is_dir():
        add_file(entries, base, "articles/index.html")
        for article_dir in sorted(articles_root.iterdir()):
            if not article_dir.is_dir():
                continue
            rel = article_dir.relative_to(ROOT).as_posix() + "/index.html"
            slug = article_dir.name
            add_file(entries, base, rel, guide_dates.get(slug))

    qroot = ROOT / "q"
    if qroot.is_dir():
        add_file(entries, base, "q/index.html")
        for path in sorted(qroot.rglob("index.html")):
            if path == qroot / "index.html":
                continue
            add_file(entries, base, path.relative_to(ROOT).as_posix())

    terms_root = ROOT / "terms"
    if terms_root.is_dir():
        add_file(entries, base, "terms/index.html")
        for path in sorted(terms_root.glob("*/index.html")):
            add_file(entries, base, path.relative_to(ROOT).as_posix())
        for path in sorted(terms_root.glob("g-*.html")):
            add_file(entries, base, path.relative_to(ROOT).as_posix())

    return entries


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=clean_origin())
    args = ap.parse_args()
    base = args.base_url.rstrip("/")
    entries = collect_entries(base)
    out = ROOT / "sitemap.xml"
    write_sitemap(entries, out)
    with_lastmod = sum(1 for e in entries if e.lastmod)
    print(f"Wrote {out} ({len(entries)} URLs, {with_lastmod} with lastmod)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
