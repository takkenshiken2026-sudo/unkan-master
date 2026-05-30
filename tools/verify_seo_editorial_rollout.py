#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEO 記事デザイン展開後のエンジン・生成 HTML を機械確認する。

  python3 tools/verify_seo_editorial_rollout.py --target /path/to/site
  python3 tools/verify_seo_editorial_rollout.py --target .   # テンプレ自身
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_ENGINE_FILES = (
    "seo-editorial.css",
    "tools/seo_editorial_chrome.py",
    "tools/knowledge_hub_seo.py",
    "tools/internal_links.py",
    "tools/seo_body_markup.py",
    "tools/glossary_past_questions.py",
    "tools/build_article_pages.py",
    "tools/build_glossary_pages.py",
    "tools/build_compare_pages.py",
    "tools/build_numbers_mistakes_pages.py",
    "tools/build_seo_editorial_preview.py",
)

HTML_MARKERS = (
    ("css_link", "seo-editorial.css?v="),
    ("faq_details", 'class="term-faq-item"'),
    ("key_points", "seo-key-points-box"),
    ("related_link", 'class="related-link"'),
)


def read_css_ver(root: Path) -> str | None:
    path = root / "tools" / "seo_editorial_chrome.py"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    m = re.search(r'SEO_EDITORIAL_CSS_VER\s*=\s*"([^"]+)"', text)
    return m.group(1) if m else None


def first_existing(root: Path, patterns: tuple[str, ...]) -> Path | None:
    for pat in patterns:
        hits = sorted(root.glob(pat))
        if hits:
            return hits[0]
    return None


def check_html_markers(path: Path, css_ver: str | None) -> list[str]:
    issues: list[str] = []
    if not path.is_file():
        return [f"missing sample file"]
    text = path.read_text(encoding="utf-8", errors="replace")
    for label, marker in HTML_MARKERS:
        if marker not in text:
            issues.append(f"{path.name}: marker missing ({label})")
    if css_ver and f"seo-editorial.css?v={css_ver}" not in text:
        issues.append(f"{path.name}: css ver mismatch (expected ?v={css_ver})")
    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description="SEO editorial rollout verification")
    ap.add_argument("--target", required=True, type=Path, help="サイト root")
    ap.add_argument(
        "--template",
        type=Path,
        default=ROOT,
        help="比較用テンプレ root（default: exam-site-shell）",
    )
    args = ap.parse_args()
    target = args.target.resolve()
    template = args.template.resolve()

    if not target.is_dir():
        print(f"error: not a directory: {target}", file=sys.stderr)
        return 1

    errors = 0
    warns = 0

    for rel in REQUIRED_ENGINE_FILES:
        p = target / rel
        if not p.is_file():
            print(f"ERROR missing engine file: {rel}", file=sys.stderr)
            errors += 1
        else:
            print(f"ok engine: {rel}")

    tpl_ver = read_css_ver(template)
    tgt_ver = read_css_ver(target)
    if not tpl_ver:
        print("ERROR template SEO_EDITORIAL_CSS_VER not found", file=sys.stderr)
        errors += 1
    elif not tgt_ver:
        print("ERROR target SEO_EDITORIAL_CSS_VER not found", file=sys.stderr)
        errors += 1
    elif tpl_ver != tgt_ver:
        print(
            f"ERROR CSS version mismatch: template={tpl_ver} target={tgt_ver}",
            file=sys.stderr,
        )
        errors += 1
    else:
        print(f"ok CSS version: {tgt_ver}")

    samples: list[tuple[str, Path | None]] = [
        (
            "guide",
            first_existing(target, ("articles/*/index.html",)),
        ),
        ("term", first_existing(target, ("terms/g-*.html",))),
        (
            "compare",
            first_existing(target, ("terms/compare/c-*.html",)),
        ),
        (
            "preview",
            target / "terms" / "samples" / "seo-editorial-preview.html",
        ),
    ]
    for label, path in samples:
        if path is None:
            print(f"WARN no {label} HTML to scan (build not run yet?)", file=sys.stderr)
            warns += 1
            continue
        marker_issues = check_html_markers(path, tpl_ver)
        if marker_issues:
            for msg in marker_issues:
                print(f"ERROR {label}: {msg}", file=sys.stderr)
            errors += len(marker_issues)
        else:
            print(f"ok html markers: {label} ({path.relative_to(target)})")

    print(f"\nverify_seo_editorial_rollout: ERROR={errors} WARN={warns}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
