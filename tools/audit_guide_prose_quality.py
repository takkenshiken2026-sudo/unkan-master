#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ガイド記事 prose 品質監査（sanitize 後の読者向け本文）。"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_article_pages import sanitize_guide_text  # noqa: E402
from tools.editorial_quality import is_published_guide, norm  # noqa: E402
from tools.fix_guide_duplicate_bodies import load_site_lib  # noqa: E402
from tools.guide_prose_patterns import PROSE_COLUMNS, scan_prose_text  # noqa: E402

HTML_BAD_RE = re.compile(
    r"記事\s+[a-z0-9-]+\s*「|"
    r"第\d+。節|"
    r"現場判断と\d+分野|"
    r"「[^」]+」では、[^。]+について。衛生|"
    r"「[^」]+」では、[^。]+について。管業|"
    r"「[^」]+」では、[^。]+について。ボイラー"
)


def _exam_aliases(root: Path) -> tuple[str, str]:
    try:
        lib = load_site_lib(root)
        return getattr(lib, "EXAM", ""), getattr(lib, "EXAM_SHORT", "")
    except Exception:
        cfg = root / "site-config.json"
        if not cfg.is_file():
            return "", ""
        data = json.loads(cfg.read_text(encoding="utf-8"))
        return str(data.get("examName") or ""), str(data.get("brandMark") or "")


def audit_csv(root: Path) -> dict:
    guide_csv = root / "data" / "guide_articles.csv"
    if not guide_csv.is_file():
        return {"ok": False, "error": f"missing {guide_csv}"}
    exam, exam_short = _exam_aliases(root)
    rows = list(csv.DictReader(guide_csv.open(encoding="utf-8-sig")))
    pattern_counts: Counter[str] = Counter()
    slug_hits: dict[str, list[str]] = defaultdict(list)
    total_hits = 0
    pub = 0
    for row in rows:
        if not is_published_guide(row):
            continue
        pub += 1
        slug = norm(row.get("slug"))
        for col in PROSE_COLUMNS:
            raw = norm(row.get(col))
            if not raw:
                continue
            text = sanitize_guide_text(raw, slug)
            for hit in scan_prose_text(text, column=col, exam=exam, exam_short=exam_short):
                pattern_counts[hit.pattern] += 1
                total_hits += 1
                if slug and hit.pattern not in slug_hits[slug]:
                    slug_hits[slug].append(hit.pattern)
    return {
        "ok": total_hits == 0,
        "published": pub,
        "affected_slugs": len(slug_hits),
        "total_hits": total_hits,
        "patterns": dict(pattern_counts),
        "slug_samples": dict(list(slug_hits.items())[:8]),
    }


def audit_html(root: Path) -> dict:
    articles = root / "articles"
    if not articles.is_dir():
        return {"ok": True, "files": 0, "bad": 0}
    bad = 0
    total = 0
    for html in articles.glob("*/index.html"):
        total += 1
        text = html.read_text(encoding="utf-8", errors="ignore")
        if HTML_BAD_RE.search(text):
            bad += 1
    return {"ok": bad == 0, "files": total, "bad": bad}


def main() -> int:
    parser = argparse.ArgumentParser(description="ガイド prose 品質監査")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--strict", action="store_true", help="ERROR 時 exit 1")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--html-only", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()

    report = {"site": root.name, "csv": {}, "html": {}}
    if not args.html_only:
        report["csv"] = audit_csv(root)
    report["html"] = audit_html(root)
    ok = report.get("csv", {}).get("ok", True) and report["html"].get("ok", True)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        c = report.get("csv") or {}
        h = report["html"]
        print(f"site: {root.name}")
        if c:
            print(
                f"  csv: published={c.get('published')} affected_slugs={c.get('affected_slugs')} "
                f"hits={c.get('total_hits')} patterns={c.get('patterns')}"
            )
        print(f"  html: files={h.get('files')} bad={h.get('bad')}")
        print("  status:", "PASS" if ok else "FAIL")

    if args.strict and not ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
