#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate generated SEO article and term pages."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.seo_utils import is_noindex_html, is_sitemap_excluded_rel  # noqa: E402


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

    def validate_common_leaks(self, path: Path, text: str) -> None:
        if "<th>更新方針</th>" in text or "update_policy" in text:
            self.error(path, "公開ページに更新方針を表示しないでください")
        if "<th>独自メモ</th>" in text:
            self.error(path, "公開ページの表に独自メモを表示しないでください（CSV内部用）")
        for internal_row in ("検索意図", "記事種別"):
            if f"<th>{internal_row}</th>" in text:
                self.error(path, f"公開ページの表に {internal_row} を表示しないでください")
        if re.search(r'href="https://example\.com/?', text):
            self.warn(path, "本番サイトでは example.com の公式リンクを実URLに差し替えてください")

    def validate_full_seo_page(self, path: Path, *, require_fact_checked: bool) -> None:
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
            (
                pos
                for pos in (
                    self.index_of(text, 'id="article-sec-faq"'),
                    self.index_of(text, 'id="term-sec-faq"'),
                )
                if pos >= 0
            ),
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

        for row_name in ("執筆", "確認", "主な参照元"):
            if f"<th>{row_name}</th>" not in text:
                self.error(path, f"信頼性表に {row_name} がありません")

        if require_fact_checked:
            if "<th>事実確認日</th>" not in text:
                self.error(path, "信頼性表に 事実確認日 がありません")
        elif "<th>事実確認日</th>" not in text:
            self.warn(path, "事実確認日が未設定です（CSV の fact_checked_at を設定してください）")

        if "quality-source-list" not in text:
            self.error(path, "主な参照元は quality-source-list のリストで表示してください")

        self.validate_common_leaks(path, text)

    def validate_hub_detail_page(self, path: Path) -> None:
        text = self.text(path)
        info_marker = 'id="hub-info-title"'
        faq_marker = 'id="hub-sec-faq"'

        if self.index_of(text, info_marker) < 0:
            self.error(path, "記事の基本情報 が生成されていません")
        if self.index_of(text, faq_marker) < 0:
            self.error(path, "FAQ が生成されていません")
        if 'rel="canonical"' not in text:
            self.error(path, "canonical が生成されていません")
        if 'name="description"' not in text:
            self.error(path, "meta description が生成されていません")

        self.validate_common_leaks(path, text)

    def page_profile(self, path: Path) -> str | None:
        rel = path.relative_to(ROOT).as_posix()
        if is_sitemap_excluded_rel(rel) or is_noindex_html(path):
            return None
        if path.match("articles/*/index.html") and path.parent.name != "chapters":
            return "full"
        if path.match("terms/g-*.html"):
            return "term"
        if path.match("terms/compare/c-*.html"):
            return "hub"
        if path.match("terms/numbers/n-*.html") or path.match("terms/mistakes/m-*.html"):
            return "hub"
        return None

    def pages(self) -> list[Path]:
        patterns = (
            "articles/*/index.html",
            "terms/g-*.html",
            "terms/compare/c-*.html",
            "terms/numbers/n-*.html",
            "terms/mistakes/m-*.html",
        )
        out: list[Path] = []
        for pattern in patterns:
            out.extend(sorted(ROOT.glob(pattern)))
        return out

    def run(self) -> int:
        pages = self.pages()
        validated = 0
        if not pages:
            self.error(ROOT, "生成済みSEOページが見つかりません")
        for path in pages:
            profile = self.page_profile(path)
            if profile is None:
                continue
            validated += 1
            if profile == "full":
                self.validate_full_seo_page(path, require_fact_checked=True)
            elif profile == "term":
                self.validate_full_seo_page(path, require_fact_checked=False)
            elif profile == "hub":
                self.validate_hub_detail_page(path)

        for issue in self.issues:
            print(issue.format(), file=sys.stderr if issue.level == "ERROR" else sys.stdout)

        errors = [i for i in self.issues if i.level == "ERROR"]
        warnings = [i for i in self.issues if i.level == "WARN"]
        if errors:
            print(
                f"Generated SEO validation failed: {len(errors)} error(s), {len(warnings)} warning(s)",
                file=sys.stderr,
            )
            return 1
        print(
            f"Generated SEO validation passed: {validated} page(s), "
            f"{warnings and str(len(warnings)) + ' warning(s)' or 'no warnings'}"
        )
        return 0


def main() -> int:
    return GeneratedSeoValidator().run()


if __name__ == "__main__":
    raise SystemExit(main())
