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

SCRIPT_STYLE_RE = re.compile(
    r"<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>",
    re.IGNORECASE | re.DOTALL,
)
TAG_RE = re.compile(r"<[^>]+>")
# 同一文字が3回以上連続（句読点・装飾記号は除外）
DUPLICATE_CHAR_RE = re.compile(r"([^\s\d\u3000])\1{2,}")
DUPLICATE_CHAR_ALLOWED = frozenset("…・ー-_=*~.☆★•―")

# 生成物に混入しやすい重複語・誤字パターン（CSV/生成元で直す）
KNOWN_TYPO_PATTERNS: list[tuple[str, str]] = [
    ("ことこと", "重複語「ことこと」"),
    ("するする", "重複語「するする」"),
    ("についてについて", "重複句「についてについて」"),
    ("ですです", "重複語「ですです」"),
    ("的な的な", "重複句「的な的な」"),
    ("場合場合", "重複語「場合場合」"),
    ("必要必要", "重複語「必要必要」"),
    ("行行行", "誤字の可能性（「行」が3連続）"),
    ("精神保健福社士", "誤字（精神保健福祉士）"),
    ("ストレスチェックック", "誤字（ストレスチェック）"),
    ("メンタルヘルスス", "誤字（メンタルヘルス）"),
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


def visible_text(html: str) -> str:
    text = SCRIPT_STYLE_RE.sub(" ", html)
    return TAG_RE.sub(" ", text)


class PublicContentValidator:
    def __init__(self) -> None:
        self.issues: list[Issue] = []

    def error(self, path: Path, message: str) -> None:
        self.issues.append(Issue("ERROR", path, message))

    def check_duplicate_characters(self, path: Path, plain: str) -> None:
        for match in DUPLICATE_CHAR_RE.finditer(plain):
            ch = match.group(1)
            if ch in DUPLICATE_CHAR_ALLOWED:
                continue
            snippet = match.group(0)
            if ch == "I" and re.fullmatch(r"I+", snippet) and len(snippet) <= 4:
                continue
            if re.fullmatch(r"[A-D]{3,4}", snippet):
                continue
            start = max(0, match.start() - 12)
            end = min(len(plain), match.end() + 12)
            context = plain[start:end].replace("\n", " ")
            if (
                "http://" in context
                or "https://" in context
                or "%2F%2F" in context
                or "www." in context
            ):
                continue
            self.error(
                path,
                f"同一文字の連続「{snippet}」: 誤入力の可能性（…{context}…）",
            )
            return

    def check_known_typos(self, path: Path, plain: str) -> None:
        for typo, reason in KNOWN_TYPO_PATTERNS:
            if typo in plain:
                self.error(path, f"誤字・重複の疑い「{typo}」: {reason}")
                return

    def scan_file(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        if 'name="robots"' in text and "noindex" in text.lower():
            return
        rel = str(path.relative_to(ROOT))
        for snippet, reason in FORBIDDEN_SNIPPETS:
            if snippet in text:
                self.error(path, f"禁止コンテンツ「{snippet}」: {reason}")
        if rel == "articles/index.html":
            for snippet in ARTICLE_INDEX_FORBIDDEN:
                if snippet in text:
                    self.error(path, f"試験ガイド一覧に禁止語「{snippet}」")
        plain = visible_text(text)
        self.check_duplicate_characters(path, plain)
        self.check_known_typos(path, plain)

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
