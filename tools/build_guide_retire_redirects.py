#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""archived ガイド記事の articles/{slug}/ へ noindex リダイレクト HTML を書く。"""

from __future__ import annotations

import csv
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.editorial_quality import norm  # noqa: E402

RETIRED_JSON = ROOT / "data" / "guide_retired.json"

REDIRECT_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="0;url={url}">
<link rel="canonical" href="{url}">
<meta name="robots" content="noindex, follow">
<title>記事移動中…</title>
<script>location.replace({url_js});</script>
</head>
<body>
<p>新しい記事へ移動します。<a href="{url}">こちら</a></p>
</body>
</html>
"""


def load_retired_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    if RETIRED_JSON.is_file():
        data = json.loads(RETIRED_JSON.read_text(encoding="utf-8"))
        for slug, target in (data.get("redirects") or {}).items():
            mapping[norm(slug)] = norm(target)
    csv_path = ROOT / "data" / "guide_articles.csv"
    if csv_path.is_file():
        with csv_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if norm(row.get("content_status")) != "archived":
                    continue
                slug = norm(row.get("slug"))
                note = norm(row.get("original_note"))
                target = ""
                for part in note.split(";"):
                    if part.startswith("retire_redirect:"):
                        target = part.split(":", 1)[1].strip()
                        break
                if slug and target:
                    mapping.setdefault(slug, target)
    return mapping


def write_redirect(articles_dir: Path, slug: str, target_slug: str) -> None:
    out_dir = articles_dir / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    rel = f"../{target_slug}/index.html"
    esc = html.escape(rel, quote=True)
    (out_dir / "index.html").write_text(
        REDIRECT_HTML.format(url=esc, url_js=repr(rel)),
        encoding="utf-8",
    )
    marker = out_dir / ".generated-by-exam-site"
    if marker.is_file():
        marker.unlink()


def main() -> int:
    mapping = load_retired_map()
    articles_dir = ROOT / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for slug, target in sorted(mapping.items()):
        if not target:
            continue
        write_redirect(articles_dir, slug, target)
        count += 1
    print(f"Wrote {count} retired guide redirect(s) under articles/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
