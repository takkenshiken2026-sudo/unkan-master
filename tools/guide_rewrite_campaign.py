#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全サイト試験ガイド手書きリライトキャンペーン進捗。"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_guide_rewrite_inventory import DEFAULT_SITES, PROSE_COLS, reader_text  # noqa: E402
from tools.editorial_quality import is_published_guide, norm  # noqa: E402
from tools.guide_rewrite_quality import prose_quality_status  # noqa: E402
from tools.guide_rewrite_rules import tier_priority  # noqa: E402


def audit_site(root: Path) -> list[dict[str, str]]:
    csv_path = root / "data" / "guide_articles.csv"
    if not csv_path.is_file():
        return []
    site = root.name
    out: list[dict[str, str]] = []
    for row in csv.DictReader(csv_path.open(encoding="utf-8-sig")):
        if not is_published_guide(row):
            continue
        slug = norm(row.get("slug"))
        parts = [reader_text(row, c, slug) for c in PROSE_COLS]
        combined = "\n".join(p for p in parts if p)
        status = prose_quality_status(row, combined)
        out.append(
            {
                "site": site,
                "slug": slug,
                "genre": norm(row.get("genre")),
                "title": norm(row.get("title"))[:70],
                "priority": tier_priority(row),
                "status": status,
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="手書きリライトキャンペーン進捗")
    ap.add_argument("--root", type=Path, help="単一サイト")
    ap.add_argument("--sites-root", type=Path, default=Path.home() / "Projects")
    ap.add_argument("--all-sites", action="store_true")
    ap.add_argument("--next", type=int, default=0, help="次に手書きする slug を N 件表示")
    ap.add_argument("--priority", choices=("A", "B", "C"), default="A")
    ap.add_argument("-o", "--output", type=Path, help="CSV 出力")
    args = ap.parse_args()

    targets: list[Path] = []
    if args.root:
        targets = [args.root.resolve()]
    elif args.all_sites:
        targets = [args.sites_root / n for n in DEFAULT_SITES if n != "takken-master"]
    else:
        targets = [ROOT]

    rows: list[dict[str, str]] = []
    for t in targets:
        if t.is_dir():
            rows.extend(audit_site(t))

    by_status = Counter(r["status"] for r in rows)
    by_site: dict[str, Counter] = {}
    for r in rows:
        by_site.setdefault(r["site"], Counter())[r["status"]] += 1

    print(
        f"summary: published={len(rows)} "
        f"hand_done={by_status.get('hand_done', 0)} "
        f"auto_pending={by_status.get('auto_pending', 0)} "
        f"needs_rewrite={by_status.get('needs_rewrite', 0)} "
        f"affiliate_pending={by_status.get('affiliate_pending', 0)}"
    )
    for site in sorted(by_site):
        c = by_site[site]
        total = sum(c.values())
        done = c.get("hand_done", 0)
        pct = (100 * done // total) if total else 0
        print(
            f"  {site}: {done}/{total} hand_done ({pct}%) "
            f"auto={c.get('auto_pending', 0)} forbid={c.get('needs_rewrite', 0)}"
        )

    if args.next > 0:
        pending = [
            r
            for r in rows
            if r["status"] in {"auto_pending", "needs_rewrite", "ok"}
            and r["priority"] == args.priority
        ]
        pending.sort(key=lambda r: (r["site"], r["slug"]))
        print(f"\nnext {args.priority}-priority slugs ({min(args.next, len(pending))}):")
        for r in pending[: args.next]:
            print(f"  [{r['site']}] {r['slug']} — {r['title']}")

    if args.output:
        fields = ["site", "slug", "genre", "title", "priority", "status"]
        with args.output.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {args.output}")

    pending_total = by_status.get("auto_pending", 0) + by_status.get("needs_rewrite", 0) + by_status.get("ok", 0)
    return 1 if pending_total and args.all_sites else 0


if __name__ == "__main__":
    raise SystemExit(main())
