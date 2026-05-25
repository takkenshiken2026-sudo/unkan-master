#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ensure public HTML matches template rules (no operator-only content)."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Substrings that must not appear in published HTML (tables, headings, body).
FORBIDDEN_SNIPPETS: list[tuple[str, str]] = [
    ("<th>独自メモ</th>", "信頼性表に独自メモ"),
    ("<th>更新方針</th>", "信頼性表に更新方針"),
    ("<th>検索意図</th>", "表に検索意図"),
    ("<th>記事種別</th>", "表に記事種別"),
    ("共通テンプレの増やし方", "試験ガイド一覧の運用説明"),
    ("sec-template-note", "試験ガイド一覧の運用セクション"),
    ("記事を増やすときの例", "編集者向け見出し"),
    ("テンプレの増やし方", "編集者向け見出し"),
    ("差し替え時の注意", "編集者向け見出し（サンプル差し替え指示）"),
    ("このテンプレートでは、", "テンプレ説明の本文"),
    ("glossary_terms.csv", "CSV運用の説明"),
    ("guide_articles.csv", "CSV運用の説明"),
    ("related_terms に", "CSV列名の説明（FAQ・本文）"),
    ("term_detail_body、", "CSV列名の説明"),
]

ARTICLE_INDEX_FORBIDDEN = [
    "共通テンプレ",
    "テンプレの増やし",
    "記事を増やすとき",
]

PUBLIC_HTML_GLOBS = [
    "index.html",
    "about.html",
    "privacy.html",
    "related-sites.html",
    "articles/index.html",
    "articles/*/index.html",
    "terms/index.html",
    "terms/field-*/index.html",
    "terms/g-*.html",
    "q/index.html",
    "q/past/**/index.html",
]


@dataclass
class Issue:
    level: str
    path: Path
    message: str

    def format(self) -> str:
        return f"[{self.level}] {self.path.relative_to(ROOT)} - {self.message}"


def collect_html_files() -> list[Path]:
    out: list[Path] = []
    for pattern in PUBLIC_HTML_GLOBS:
        out.extend(sorted(ROOT.glob(pattern)))
    # Deduplicate while preserving order
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in out:
        resolved = path.resolve()
        if resolved not in seen and path.is_file():
            seen.add(resolved)
            unique.append(path)
    return unique


class PublicContentValidator:
    def __init__(self) -> None:
        self.issues: list[Issue] = []

    def error(self, path: Path, message: str) -> None:
        self.issues.append(Issue("ERROR", path, message))

    def scan_file(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        rel = str(path.relative_to(ROOT))
        for snippet, reason in FORBIDDEN_SNIPPETS:
            if snippet in text:
                self.error(path, f"禁止コンテンツ「{snippet}」: {reason}")
        if rel == "articles/index.html":
            for snippet in ARTICLE_INDEX_FORBIDDEN:
                if snippet in text:
                    self.error(path, f"試験ガイド一覧に禁止語「{snippet}」")

    def run(self) -> int:
        files = collect_html_files()
        if not files:
            self.error(ROOT, "検証対象の公開 HTML がありません")
        for path in files:
            self.scan_file(path)

        for issue in self.issues:
            print(issue.format(), file=sys.stderr)

        errors = [i for i in self.issues if i.level == "ERROR"]
        if errors:
            print(f"Public content validation failed: {len(errors)} error(s)", file=sys.stderr)
            return 1
        print(f"Public content validation passed: {len(files)} file(s)")
        return 0


def main() -> int:
    return PublicContentValidator().run()


if __name__ == "__main__":
    raise SystemExit(main())
