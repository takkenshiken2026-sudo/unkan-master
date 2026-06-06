#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""手書きリライト batch ファイルの雛形を slug 一覧から生成。"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.editorial_quality import is_published_guide, norm  # noqa: E402
from tools.guide_rewrite_rules import tier_priority  # noqa: E402


def slug_fields(row: dict[str, str]) -> dict[str, str]:
    fields: dict[str, str] = {
        "meta_description": "",
        "user_intent": "",
        "action_items": "",
    }
    for i in range(1, 8):
        h = norm(row.get(f"section_{i}_heading"))
        if h:
            fields[f"section_{i}_body"] = ""
    for i in range(1, 4):
        q = norm(row.get(f"faq_{i}_question"))
        if q:
            fields[f"faq_{i}_question"] = q
            fields[f"faq_{i}_answer"] = ""
    return fields


def render_batch(site: str, batch_num: int, entries: list[tuple[str, dict[str, str], str]]) -> str:
    lines = [
        "#!/usr/bin/env python3",
        "# -*- coding: utf-8",
        f'"""{site} guide 手書きリライト batch {batch_num}。"""',
        "",
        "from __future__ import annotations",
        "",
        "REWRITES: dict[str, dict[str, str]] = {",
    ]
    for slug, _fields, title in entries:
        lines.append(f'    # {title}')
        lines.append(f'    "{slug}": {{')
        for key in sorted(_fields.keys()):
            lines.append(f'        "{key}": "",')
        lines.append("    },")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--batch-num", type=int, default=1)
    ap.add_argument("--priority", choices=("A", "B", "C", "all"), default="A")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("-o", "--output", type=Path, required=True)
    args = ap.parse_args()
    csv_path = args.root.resolve() / "data" / "guide_articles.csv"
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8-sig")))
    site = args.root.resolve().name
    candidates = [r for r in rows if is_published_guide(r)]
    if args.priority != "all":
        candidates = [r for r in candidates if tier_priority(r) == args.priority]
    candidates.sort(key=lambda r: (tier_priority(r), r.get("slug", "")))
    selected = candidates[: args.limit]
    entries = [(norm(r["slug"]), slug_fields(r), norm(r.get("title"))) for r in selected]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_batch(site, args.batch_num, entries), encoding="utf-8")
    print(f"wrote {args.output} ({len(entries)} slugs)")
    for slug, _, title in entries:
        print(f"  - {slug}: {title[:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
