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

from tools.seo_utils import (  # noqa: E402
    content_date_from_row,
    is_noindex_html,
    is_sitemap_excluded_rel,
)
from tools.site_config import clean_origin  # noqa: E402
from tools.sitemap_utils import SitemapEntry, iso_date, iso_from_mtime, write_sitemap  # noqa: E402

GUIDE_CSV = ROOT / "data" / "guide_articles.csv"
GLOSSARY_CSV = ROOT / "data" / "glossary_terms.csv"
COMPARE_CSV = ROOT / "data" / "comparisons.csv"
NUMBERS_CSV = ROOT / "data" / "numbers.csv"
MISTAKES_CSV = ROOT / "data" / "mistakes.csv"


def norm(value: str | None) -> str:
    return (value or "").strip()


def guide_lastmod_by_slug() -> dict[str, str]:
    out: dict[str, str] = {}
    if not GUIDE_CSV.is_file():
        return out
    text = GUIDE_CSV.read_text(encoding="utf-8-sig")
    for row in csv.DictReader(text.splitlines()):
        slug = norm(row.get("slug"))
        if not slug:
            continue
        d = content_date_from_row(row)
        if d:
            out[slug] = d
    return out


def _glossary_slug_file(row: dict[str, str], used: dict[str, str]) -> str:
    from tools.build_glossary_pages import term_slug

    term = norm(row.get("term"))
    legacy_slug = norm(row.get("slug")) or norm(row.get("url_slug"))
    if legacy_slug:
        slug_file = f"{legacy_slug}.html"
        used[slug_file] = term
        return slug_file
    slug_file = term_slug(term, used) + ".html"
    return slug_file


def glossary_lastmod_by_rel() -> dict[str, str]:
    out: dict[str, str] = {}
    if not GLOSSARY_CSV.is_file():
        return out
    text = GLOSSARY_CSV.read_text(encoding="utf-8-sig")
    used: dict[str, str] = {}
    for row in csv.DictReader(text.splitlines()):
        if not norm(row.get("term")):
            continue
        slug_file = _glossary_slug_file(row, used)
        d = content_date_from_row(row)
        if d:
            out[f"terms/{slug_file}"] = d
    return out


def _compare_slug_file(row: dict[str, str], used: dict[str, str], line: int) -> str:
    from tools.build_compare_pages import compare_slug

    title = norm(row.get("title"))
    legacy_slug = norm(row.get("slug"))
    if legacy_slug:
        slug_file = f"{legacy_slug}.html"
        used[slug_file] = title
        return slug_file
    return compare_slug(title, used) + ".html"


def compare_lastmod_by_rel() -> dict[str, str]:
    out: dict[str, str] = {}
    if not COMPARE_CSV.is_file():
        return out
    text = COMPARE_CSV.read_text(encoding="utf-8-sig")
    used: dict[str, str] = {}
    for i, row in enumerate(csv.DictReader(text.splitlines()), start=2):
        if not norm(row.get("title")):
            continue
        slug_file = _compare_slug_file(row, used, i)
        d = content_date_from_row(row)
        if d:
            out[f"terms/compare/{slug_file}"] = d
    return out


def hub_lastmod_by_rel(csv_path: Path, rel_prefix: str, slug_prefix: str) -> dict[str, str]:
    from tools.build_numbers_mistakes_pages import hub_slug

    out: dict[str, str] = {}
    if not csv_path.is_file():
        return out
    text = csv_path.read_text(encoding="utf-8-sig")
    used: dict[str, str] = {}
    for row in csv.DictReader(text.splitlines()):
        title = norm(row.get("title"))
        if not title:
            continue
        legacy_slug = norm(row.get("slug"))
        if legacy_slug:
            slug_file = f"{legacy_slug}.html"
            used[slug_file] = title
        else:
            slug_file = hub_slug(title, used, prefix=slug_prefix) + ".html"
        d = content_date_from_row(row)
        if d:
            out[f"{rel_prefix}/{slug_file}"] = d
    return out


def should_include_rel(rel: str) -> bool:
    if is_sitemap_excluded_rel(rel):
        return False
    path = ROOT / rel
    if path.is_file() and is_noindex_html(path):
        return False
    return True


def add_file(
    entries: list[SitemapEntry],
    base: str,
    rel: str,
    lastmod: str | None = None,
    *,
    csv_dates: dict[str, str],
) -> None:
    if not should_include_rel(rel):
        return
    path = ROOT / rel
    if not path.is_file():
        return
    mod = csv_dates.get(rel) or lastmod or iso_from_mtime(path)
    entries.append(SitemapEntry(loc=f"{base}/{rel.replace(chr(92), '/')}", lastmod=mod))


def collect_entries(base: str) -> list[SitemapEntry]:
    entries: list[SitemapEntry] = []
    guide_dates = guide_lastmod_by_slug()
    csv_dates = {
        **glossary_lastmod_by_rel(),
    }

    static_pages = ["index.html", "about.html", "privacy.html", "related-sites.html"]
    for rel in static_pages:
        add_file(entries, base, rel, csv_dates=csv_dates)

    articles_root = ROOT / "articles"
    if articles_root.is_dir():
        add_file(entries, base, "articles/index.html", csv_dates=csv_dates)
        for article_dir in sorted(articles_root.iterdir()):
            if not article_dir.is_dir():
                continue
            rel = article_dir.relative_to(ROOT).as_posix() + "/index.html"
            slug = article_dir.name
            add_file(entries, base, rel, guide_dates.get(slug), csv_dates=csv_dates)

    qroot = ROOT / "q"
    if qroot.is_dir():
        add_file(entries, base, "q/index.html", csv_dates=csv_dates)
        for path in sorted(qroot.rglob("index.html")):
            if path == qroot / "index.html":
                continue
            add_file(entries, base, path.relative_to(ROOT).as_posix(), csv_dates=csv_dates)

    terms_root = ROOT / "terms"
    if terms_root.is_dir():
        add_file(entries, base, "terms/index.html", csv_dates=csv_dates)
        for path in sorted(terms_root.glob("*/index.html")):
            add_file(entries, base, path.relative_to(ROOT).as_posix(), csv_dates=csv_dates)
        for path in sorted(terms_root.glob("g-*.html")):
            add_file(entries, base, path.relative_to(ROOT).as_posix(), csv_dates=csv_dates)

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
