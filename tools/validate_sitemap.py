#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate sitemap.xml against noindex pages and excluded sample paths."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.seo_utils import is_noindex_html, is_sitemap_excluded_rel  # noqa: E402

LOC_RE = re.compile(r"<loc>(.*?)</loc>")


@dataclass
class Issue:
    level: str
    message: str

    def format(self) -> str:
        return f"[{self.level}] sitemap.xml - {self.message}"


def sitemap_rel_paths(sitemap_path: Path) -> list[str]:
    text = sitemap_path.read_text(encoding="utf-8")
    rels: list[str] = []
    for match in LOC_RE.finditer(text):
        parsed = urlparse(match.group(1).strip())
        path = parsed.path.lstrip("/")
        if path:
            rels.append(path)
    return rels


def main() -> int:
    sitemap_path = ROOT / "sitemap.xml"
    issues: list[Issue] = []

    if not sitemap_path.is_file():
        issues.append(Issue("ERROR", "sitemap.xml がありません"))
    else:
        for rel in sitemap_rel_paths(sitemap_path):
            if is_sitemap_excluded_rel(rel):
                issues.append(Issue("ERROR", f"除外対象の URL が含まれています: {rel}"))
                continue
            html_path = ROOT / rel
            if html_path.is_file() and is_noindex_html(html_path):
                issues.append(Issue("ERROR", f"noindex ページが含まれています: {rel}"))

    for issue in issues:
        print(issue.format(), file=sys.stderr if issue.level == "ERROR" else sys.stdout)

    errors = [i for i in issues if i.level == "ERROR"]
    if errors:
        print(f"Sitemap validation failed: {len(errors)} error(s)", file=sys.stderr)
        return 1
    count = len(sitemap_rel_paths(sitemap_path)) if sitemap_path.is_file() else 0
    print(f"Sitemap validation passed: {count} URL(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
