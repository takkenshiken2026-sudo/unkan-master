#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全サイト試験ガイドのリライトインベントリ（要/済/除外の一覧）。"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_article_pages import resolve_guide_section_body, sanitize_guide_text  # noqa: E402
from tools.editorial_quality import is_published_guide, norm  # noqa: E402
from tools.guide_rewrite_rules import (  # noqa: E402
    is_affiliate_row,
    is_hand_rewritten,
    rewrite_forbidden_hits,
    rewrite_status,
    slug_leaks_in_text,
    tier_priority,
)

PROSE_COLS = (
    "lead",
    "user_intent",
    "meta_description",
    *(f"section_{n}_body" for n in range(1, 8)),
    *(f"faq_{n}_answer" for n in range(1, 5)),
)

DEFAULT_SITES = (
    "takken-master",
    "mentalhealth-master",
    "kikenbutsu-master",
    "eisei1shu-master",
    "chintaikanrishi-master",
    "eisei2shu-master",
    "kangyou-master",
    "mankan-master",
    "unkan-master",
    "boiler-master.jp",
)


def reader_text(row: dict[str, str], col: str, slug: str) -> str:
    raw = norm(row.get(col))
    if not raw:
        return ""
    if col.startswith("section_") and col.endswith("_body"):
        return sanitize_guide_text(resolve_guide_section_body(row, raw), slug)
    return sanitize_guide_text(raw, slug)


def audit_site(site_root: Path) -> list[dict[str, str]]:
    csv_path = site_root / "data" / "guide_articles.csv"
    if not csv_path.is_file():
        return []
    site_name = site_root.name
    rows: list[dict[str, str]] = []
    for row in csv.DictReader(csv_path.open(encoding="utf-8-sig")):
        if not is_published_guide(row):
            continue
        slug = norm(row.get("slug"))
        parts = [reader_text(row, c, slug) for c in PROSE_COLS]
        combined = "\n".join(p for p in parts if p)
        forbidden = rewrite_forbidden_hits(combined)
        leaks = slug_leaks_in_text(combined, slug)
        status = rewrite_status(row, combined_text=combined)
        if is_affiliate_row(row) and not is_hand_rewritten(row):
            status = "affiliate_pending"
        rows.append(
            {
                "site": site_name,
                "slug": slug,
                "genre": norm(row.get("genre")),
                "title": norm(row.get("title")),
                "priority": tier_priority(row),
                "status": status,
                "hand_rewritten": "yes" if is_hand_rewritten(row) else "no",
                "affiliate": "yes" if is_affiliate_row(row) else "no",
                "forbidden_count": str(len(forbidden)),
                "forbidden_sample": forbidden[0][:40] if forbidden else "",
                "slug_leak": leaks[0] if leaks else "",
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="試験ガイドリライトインベントリ")
    ap.add_argument("--root", type=Path, help="単一サイトルート")
    ap.add_argument(
        "--sites-root",
        type=Path,
        default=Path.home() / "Projects",
        help="全サイト親ディレクトリ（既定: ~/Projects）",
    )
    ap.add_argument("--all-sites", action="store_true", help="DEFAULT_SITES を一括監査")
    ap.add_argument("-o", "--output", type=Path, help="CSV 出力先")
    ap.add_argument("--json", action="store_true", help="JSON で標準出力")
    args = ap.parse_args()

    targets: list[Path] = []
    if args.root:
        targets = [args.root.resolve()]
    elif args.all_sites:
        targets = [args.sites_root / name for name in DEFAULT_SITES]
    else:
        targets = [ROOT]

    all_rows: list[dict[str, str]] = []
    for t in targets:
        if t.is_dir():
            all_rows.extend(audit_site(t))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        fields = list(all_rows[0].keys()) if all_rows else []
        with args.output.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            w.writeheader()
            w.writerows(all_rows)
        print(f"wrote {len(all_rows)} rows -> {args.output}")

    needs = sum(1 for r in all_rows if r["status"] == "needs_rewrite")
    done = sum(1 for r in all_rows if r["status"] == "done")
    summary = {"total": len(all_rows), "needs_rewrite": needs, "done": done}
    if args.json:
        print(json.dumps({"summary": summary, "rows": all_rows}, ensure_ascii=False, indent=2))
    else:
        print(f"summary: total={summary['total']} needs_rewrite={needs} done={done}")
        by_site: dict[str, int] = {}
        for r in all_rows:
            if r["status"] == "needs_rewrite":
                by_site[r["site"]] = by_site.get(r["site"], 0) + 1
        for site, n in sorted(by_site.items(), key=lambda x: -x[1]):
            print(f"  {site}: {n}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
