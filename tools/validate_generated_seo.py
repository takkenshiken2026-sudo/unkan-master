#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate generated SEO article and term pages."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Issue:
    level: str
    path: Path
    message: str

    def format(self) -> str:
        return f"[{self.level}] {self.path.relative_to(ROOT)} - {self.message}"


class GeneratedSeoValidator:
    def __init__(self) -> None:
        self.issues: list[Issue] = []

    def error(self, path: Path, message: str) -> None:
        self.issues.append(Issue("ERROR", path, message))

    def warn(self, path: Path, message: str) -> None:
        self.issues.append(Issue("WARN", path, message))

    @staticmethod
    def text(path: Path) -> str:
        return path.read_text(encoding="utf-8")

    @staticmethod
    def index_of(text: str, marker: str) -> int:
        return text.find(marker)

    def validate_page(self, path: Path) -> None:
        text = self.text(path)
        required_markers = {
            "信頼性ブロック": 'id="quality-panel-title"',
            "この記事でできること": 'id="action-box-title"',
            "記事の基本情報": 'id="article-info-title"',
            "公式情報の確認": 'id="official-info-title"',
        }
        positions: dict[str, int] = {}
        for label, marker in required_markers.items():
            pos = self.index_of(text, marker)
            positions[label] = pos
            if pos < 0:
                self.error(path, f"{label} が生成されていません")
        faq_pos = min(
            (pos for pos in (self.index_of(text, 'id="article-sec-faq"'), self.index_of(text, 'id="term-sec-faq"')) if pos >= 0),
            default=-1,
        )
        positions["FAQ"] = faq_pos
        if faq_pos < 0:
            self.error(path, "FAQ が生成されていません")

        if all(pos >= 0 for pos in positions.values()):
            ordered = [
                ("信頼性ブロック", "この記事でできること"),
                ("この記事でできること", "FAQ"),
                ("FAQ", "記事の基本情報"),
                ("記事の基本情報", "公式情報の確認"),
            ]
            for before, after in ordered:
                if positions[before] > positions[after]:
                    self.error(path, f"{before} は {after} より前に配置してください")

        for row_name in ("執筆", "確認", "事実確認日", "主な参照元"):
            if f"<th>{row_name}</th>" not in text:
                self.error(path, f"信頼性表に {row_name} がありません")

        if "<th>更新方針</th>" in text or "update_policy" in text:
            self.error(path, "公開ページに更新方針を表示しないでください")
        if "<th>独自メモ</th>" in text:
            self.error(path, "公開ページの表に独自メモを表示しないでください（CSV内部用）")
        for internal_row in ("検索意図", "記事種別"):
            if f"<th>{internal_row}</th>" in text:
                self.error(path, f"公開ページの表に {internal_row} を表示しないでください")

        if "quality-source-list" not in text:
            self.error(path, "主な参照元は quality-source-list のリストで表示してください")

        if re.search(r'href="https://example\.com/?', text):
            self.warn(path, "本番サイトでは example.com の公式リンクを実URLに差し替えてください")

    def pages(self) -> list[Path]:
        article_pages = sorted(
            p
            for p in (ROOT / "articles").glob("*/index.html")
            if p.parent.name != "chapters"
        )
        term_pages = sorted(
            p
            for p in (ROOT / "terms").glob("*.html")
            if p.name != "index.html"
        )
        return article_pages + term_pages

    def run(self) -> int:
        pages = self.pages()
        if not pages:
            self.error(ROOT, "生成済みSEOページが見つかりません")
        for path in pages:
            self.validate_page(path)

        for issue in self.issues:
            print(issue.format(), file=sys.stderr if issue.level == "ERROR" else sys.stdout)

        errors = [i for i in self.issues if i.level == "ERROR"]
        warnings = [i for i in self.issues if i.level == "WARN"]
        if errors:
            print(f"Generated SEO validation failed: {len(errors)} error(s), {len(warnings)} warning(s)", file=sys.stderr)
            return 1
        print(f"Generated SEO validation passed: {len(pages)} page(s), {warnings and str(len(warnings)) + ' warning(s)' or 'no warnings'}")
        return 0


def main() -> int:
    return GeneratedSeoValidator().run()


if __name__ == "__main__":
    raise SystemExit(main())
