#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""不要ガイド記事を archived にし、リダイレクト先を登録する。"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.editorial_quality import is_published_guide, norm  # noqa: E402
from tools.guide_retire_catalog import (  # noqa: E402
    load_template_slugs,
    select_retire_candidates,
)
from tools.related_links import parse_related_link_token  # noqa: E402
from tools.site_config import load_config  # noqa: E402


def site_field_ids(root: Path) -> list[str]:
    cfg = load_config()
    fields = cfg.get("fields") or []
    out: list[str] = []
    for f in fields:
        if isinstance(f, dict):
            out.append(norm(f.get("id")))
        else:
            out.append(norm(str(f)))
    return [x for x in out if x]


def split_semicolon(value: str) -> list[str]:
    return [x.strip() for x in norm(value).split(";") if x.strip()]


def join_semicolon(items: list[str]) -> str:
    return ";".join(x for x in items if x)


def strip_retired_from_related(related: str, retired: set[str]) -> str:
    kept: list[str] = []
    for item in split_semicolon(related):
        target, label = parse_related_link_token(item)
        if target and target in retired:
            continue
        kept.append(item)
    return join_semicolon(kept)


def apply_retire(
    root: Path,
    candidates: list[tuple[str, str, str]],
    *,
    dry_run: bool,
) -> dict[str, int]:
    csv_path = root / "data" / "guide_articles.csv"
    retired_json = root / "data" / "guide_retired.json"
    retired_slugs = {slug for slug, _, _ in candidates}
    redirect_map = {slug: target for slug, _, target in candidates}
    today = date.today().isoformat()

    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    stats = {"archived": 0, "related_patched": 0}
    for row in rows:
        slug = norm(row.get("slug"))
        if slug in retired_slugs:
            if not dry_run:
                row["content_status"] = "archived"
                note = norm(row.get("revision_note"))
                row["revision_note"] = f"{today}: archived（guide retire·{redirect_map[slug]}へ統合）"
                orig = norm(row.get("original_note"))
                tag = f"retire_redirect:{redirect_map[slug]}"
                row["original_note"] = f"{orig};{tag}".strip(";") if orig else tag
            stats["archived"] += 1
            continue
        if not is_published_guide(row):
            continue
        rel = norm(row.get("related_links"))
        if not rel:
            continue
        new_rel = strip_retired_from_related(rel, retired_slugs)
        if new_rel != rel:
            if not dry_run:
                row["related_links"] = new_rel
            stats["related_patched"] += 1

    if dry_run:
        return stats

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    payload = {"updated": today, "redirects": redirect_map}
    if retired_json.is_file():
        existing = json.loads(retired_json.read_text(encoding="utf-8"))
        merged = dict(existing.get("redirects") or {})
        merged.update(redirect_map)
        payload["redirects"] = merged
    retired_json.parent.mkdir(parents=True, exist_ok=True)
    retired_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description="Retire redundant guide articles (~40%)")
    ap.add_argument("--root", type=Path, default=ROOT, help="Site root")
    ap.add_argument("--ratio", type=float, default=0.4, help="Target retire ratio")
    ap.add_argument("--slugs-file", type=Path, help="One slug per line (skip auto select)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--list-only", action="store_true")
    args = ap.parse_args()
    root = args.root.resolve()
    import os

    os.environ["EXAM_SITE_ROOT"] = str(root)
    csv_path = root / "data" / "guide_articles.csv"
    if not csv_path.is_file():
        print(f"Missing {csv_path}", file=sys.stderr)
        return 1

    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    catalog = root.parent / "exam-site-shell" / "docs" / "guide-article-catalog.md"
    if not catalog.is_file():
        catalog = ROOT / "docs" / "guide-article-catalog.md"
    template_slugs = load_template_slugs(catalog)
    fields = site_field_ids(root)
    published_slugs = {norm(r.get("slug")) for r in rows if is_published_guide(r)}

    if args.slugs_file:
        slugs = [ln.strip() for ln in args.slugs_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        from tools.guide_retire_catalog import redirect_target

        candidates = [(s, "manual", redirect_target(s, published_slugs=published_slugs)) for s in slugs]
    else:
        candidates = select_retire_candidates(
            rows,
            site_field_ids=fields,
            template_slugs=template_slugs,
            ratio=args.ratio,
        )

    print(f"site: {root.name}  candidates: {len(candidates)}")
    for slug, reason, target in candidates:
        print(f"  {slug} -> {target}  ({reason})")

    if args.list_only:
        return 0

    stats = apply_retire(root, candidates, dry_run=args.dry_run)
    mode = "dry-run" if args.dry_run else "applied"
    print(f"{mode}: archived={stats['archived']} related_patched={stats['related_patched']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
