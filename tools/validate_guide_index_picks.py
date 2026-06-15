#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公開済みアフィリエイト記事と guideIndexPicks・一覧 HTML の整合を検証。"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.affiliate_links import affiliate_article_is_buildable, is_affiliate_article  # noqa: E402


@dataclass
class Issue:
    message: str


def _slug_from_href(href: str) -> str:
    raw = (href or "").strip().rstrip("/")
    if not raw:
        return ""
    if raw.startswith("articles/"):
        raw = raw[len("articles/") :]
    return raw.split("/")[-1]


def published_affiliate_slugs(root: Path) -> set[str]:
    csv_path = root / "data" / "guide_articles.csv"
    if not csv_path.is_file():
        return set()
    slugs: set[str] = set()
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if (
                is_affiliate_article(row)
                and (row.get("content_status") or "").strip() == "published"
                and affiliate_article_is_buildable(row)
            ):
                slug = (row.get("slug") or "").strip()
                if slug:
                    slugs.add(slug)
    return slugs


def validate_guide_index_picks(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    pub = published_affiliate_slugs(root)
    if not pub:
        return issues

    cfg_path = root / "site-config.json"
    if not cfg_path.is_file():
        issues.append(Issue("公開済みアフィリエイトがあるのに site-config.json がありません"))
        return issues

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    picks = cfg.get("guideIndexPicks")
    if not isinstance(picks, dict):
        issues.append(
            Issue(
                f"公開済みアフィリエイト {len(pub)} 本あり。"
                " site-config.json に guideIndexPicks を設定してください（articles/terms/q 一覧カード）。"
            )
        )
        return issues

    items = picks.get("items")
    if not isinstance(items, list) or not items:
        issues.append(Issue("guideIndexPicks.items が空です。公開済み affiliate-* を最大3枚設定してください。"))
        return issues

    pick_slugs: list[str] = []
    for idx, item in enumerate(items[:3], start=1):
        if not isinstance(item, dict):
            issues.append(Issue(f"guideIndexPicks.items[{idx}] がオブジェクトではありません"))
            continue
        href = str(item.get("href") or "").strip()
        slug = _slug_from_href(href)
        if not slug:
            issues.append(Issue(f"guideIndexPicks.items[{idx}] の href が空です"))
            continue
        pick_slugs.append(slug)
        if slug not in pub:
            issues.append(
                Issue(
                    f"guideIndexPicks.items[{idx}] の href={slug!r} は"
                    f" 公開済みアフィリエイトではありません（公開: {sorted(pub)!r}）"
                )
            )
        image = str(item.get("image") or "").strip()
        if image:
            img_path = root / image.lstrip("/")
            if not img_path.is_file():
                issues.append(Issue(f"guideIndexPicks.items[{idx}] の画像がありません: {image}"))

    if not pick_slugs:
        return issues

    for hub, label in (
        ("articles", "試験ガイド一覧"),
        ("terms", "用語一覧"),
        ("q", "過去問一覧"),
    ):
        index_path = root / hub / "index.html"
        if not index_path.is_file():
            issues.append(Issue(f"{label} ({hub}/index.html) がありません"))
            continue
        html = index_path.read_text(encoding="utf-8", errors="replace")
        if "article-index-picks" not in html:
            issues.append(
                Issue(
                    f"{label} に guideIndexPicks カードがありません。"
                    " build_article_pages / build_glossary_pages / build_past_question_pages を実行してください"
                )
            )

    return issues


def main() -> int:
    root = ROOT
    if len(sys.argv) > 1 and sys.argv[1] == "--root":
        root = Path(sys.argv[2]).resolve()

    issues = validate_guide_index_picks(root)
    if not issues:
        print("validate_guide_index_picks: OK")
        return 0
    for issue in issues:
        print(f"error: {issue.message}", file=sys.stderr)
    print(f"validate_guide_index_picks: {len(issues)} error(s)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
