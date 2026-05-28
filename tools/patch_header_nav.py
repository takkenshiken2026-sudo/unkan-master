#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerate topnav/site-footer in static HTML using html_footer (fast header-only patch)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.html_footer import site_page_footer, site_page_header

HEADER_RE = re.compile(
    r'<header class="topnav site-shell-header[^"]*">.*?</header>',
    re.S,
)
FOOTER_RE = re.compile(
    r'<footer class="site-footer" role="contentinfo">.*?</footer>\s*'
    r"(?:<!-- GA4:.*?-->\s*)?"
    r'(?:<script>window\.__GA4_MEASUREMENT_ID__="[^"]*";</script>\s*)?'
    r'(?:<script defer src="[^"]*site-analytics\.js"></script>\s*)?',
    re.S,
)

CURRENT_BY_PREFIX = {
    "terms/": "terms",
    "q/practice/": "practice",
    "q/ichimon/": "ichimon",
    "q/": "q",
    "articles/": "articles",
}


def current_for(rel: Path) -> str | None:
    s = rel.as_posix()
    if s in {"about.html", "privacy.html", "related-sites.html"}:
        return {"about.html": "about", "privacy.html": "privacy", "related-sites.html": "related"}[s]
    for prefix, key in CURRENT_BY_PREFIX.items():
        if s.startswith(prefix):
            return key
    return None


def patch_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if 'class="topnav site-shell-header' not in text:
        return False
    rel = path.relative_to(ROOT)
    current = current_for(rel)
    new_header = site_page_header(rel, current=current)
    new_footer = site_page_footer(rel, current=current)
    new_text, n1 = HEADER_RE.subn(new_header, text, count=1)
    new_text, n2 = FOOTER_RE.subn(new_footer + "\n", new_text, count=1)
    if n1 and n2 and new_text != text:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def main() -> int:
    changed = 0
    for path in sorted(ROOT.rglob("*.html")):
        if path.name.startswith("."):
            continue
        if patch_file(path):
            changed += 1
    print(f"Patched {changed} HTML files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
