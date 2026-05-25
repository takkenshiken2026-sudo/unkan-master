#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared sitemap helpers with lastmod support."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape


@dataclass(frozen=True)
class SitemapEntry:
    loc: str
    lastmod: str | None = None
    changefreq: str = "monthly"

    def sort_key(self) -> tuple[str, str]:
        return (self.loc, self.lastmod or "")


def iso_date(value: str | None) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    return None


def iso_from_mtime(path: Path) -> str | None:
    if not path.is_file():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()


def iso_today() -> str:
    return date.today().isoformat()


def write_sitemap(entries: list[SitemapEntry], out: Path) -> None:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for entry in sorted({e.loc: e for e in entries}.values(), key=lambda e: e.loc):
        lines.append("  <url>")
        lines.append(f"    <loc>{xml_escape(entry.loc)}</loc>")
        if entry.lastmod:
            lines.append(f"    <lastmod>{xml_escape(entry.lastmod)}</lastmod>")
        lines.append(f"    <changefreq>{xml_escape(entry.changefreq)}</changefreq>")
        lines.append("  </url>")
    lines.append("</urlset>")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
