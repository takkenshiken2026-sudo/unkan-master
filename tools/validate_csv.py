#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate template CSV files before generating the site."""

from __future__ import annotations

import csv
import io
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_glossary_pages import make_term_lookup
from tools.glossary_term_rules import (
    GLOSSARY_BASE_REQUIRED,
    GLOSSARY_PRODUCTION_TARGET,
    check_glossary_row,
)
from tools.guide_article_rules import check_guide_row
from tools.knowledge_hub_rules import (
    HUB_CSV_NAMES,
    HUB_LABELS,
    check_compare_row,
    check_mistakes_row,
    check_numbers_row,
    production_count_message,
)
from tools.site_config import category_to_field_map, guide_genre_labels
from tools.term_diagram import DIAGRAM_ID_RE, diagram_id_exists


def split_semicolon(value: str) -> list[str]:
    return [x.strip() for x in value.split(";") if x.strip()]

DATA_DIR = ROOT / "data"

# Guide rows with this tag in `tags` are counted as affiliate articles (production target: 10).
AFFILIATE_TAG = "アフィリエイト"
AFFILIATE_TARGET_COUNT = 10
AFFILIATE_GENRES = frozenset(
    {"独学対策", "学習計画", "過去問活用", "直前・当日", "試験概要", "受験・申込"}
)
AFFILIATE_PR_MARKERS = ("アフィリエイト", "広告", "PR", "プロモーション")

# Must not appear in published section headings / body (guide_articles.csv).
OPERATOR_CONTENT_FRAGMENTS: list[tuple[str, str]] = [
    ("記事を増やす", "編集者向け見出し"),
    ("テンプレの増やし", "編集者向け見出し"),
    ("共通テンプレ", "運用説明"),
    ("差し替え時の注意", "サンプル差し替え指示"),
    ("このテンプレートでは", "テンプレ説明の本文"),
    ("glossary_terms.csv", "CSV運用の説明"),
    ("guide_articles.csv", "CSV運用の説明"),
    ("related_terms に", "CSV列名の説明"),
    ("term_detail_body", "CSV列名の説明"),
]


@dataclass
class Issue:
    level: str
    path: Path
    line: int | None
    message: str

    def format(self) -> str:
        rel = self.path.relative_to(ROOT)
        loc = f"{rel}:{self.line}" if self.line else str(rel)
        return f"[{self.level}] {loc} - {self.message}"


class Validator:
    def __init__(self) -> None:
        self.issues: list[Issue] = []
        self.category_map = category_to_field_map()

    def error(self, path: Path, line: int | None, message: str) -> None:
        self.issues.append(Issue("ERROR", path, line, message))

    def warn(self, path: Path, line: int | None, message: str) -> None:
        self.issues.append(Issue("WARN", path, line, message))

    def read_csv(self, path: Path, required: set[str]) -> tuple[list[str], list[dict[str, str]]]:
        if not path.is_file():
            self.error(path, None, "CSVファイルが見つかりません")
            return [], []
        text = path.read_text(encoding="utf-8-sig")
        if not text.strip():
            self.error(path, None, "CSVが空です")
            return [], []

        first_line = text.splitlines()[0] if text.splitlines() else ""
        headers = next(csv.reader([first_line])) if first_line else []
        dupes = sorted({h for h in headers if headers.count(h) > 1})
        for h in dupes:
            self.error(path, 1, f"列名が重複しています: {h}")

        rows = list(csv.DictReader(io.StringIO(text)))
        fieldnames = list(rows[0].keys()) if rows else (headers or [])
        missing = sorted(required - set(fieldnames))
        for col in missing:
            self.error(path, 1, f"必須列がありません: {col}")
        if missing:
            return fieldnames, rows
        if not rows:
            if path.name in ("comparisons.csv", "numbers.csv", "mistakes.csv"):
                self.warn(
                    path,
                    None,
                    "データ行がありません（知識ハブは執筆拡充前でも可。目標件数は validate_knowledge_hub の WARN を参照）",
                )
            else:
                self.error(path, None, "データ行がありません")
        return fieldnames, rows

    @staticmethod
    def norm(value: object) -> str:
        return str(value or "").strip()

    @staticmethod
    def truthy(value: object) -> bool:
        return str(value or "").strip().upper() == "TRUE"

    def require_text(self, path: Path, row: dict[str, str], line: int, col: str) -> str:
        value = self.norm(row.get(col))
        if not value:
            self.error(path, line, f"{col} が空です")
        return value

    def require_int(self, path: Path, row: dict[str, str], line: int, col: str, *, min_value: int | None = None) -> int | None:
        raw = self.require_text(path, row, line, col)
        if not raw:
            return None
        try:
            value = int(raw)
        except ValueError:
            self.error(path, line, f"{col} は整数で入力してください: {raw!r}")
            return None
        if min_value is not None and value < min_value:
            self.error(path, line, f"{col} は {min_value} 以上にしてください: {value}")
        return value

    def validate_category(self, path: Path, row: dict[str, str], line: int) -> str:
        category = self.require_text(path, row, line, "category")
        if category and category not in self.category_map:
            allowed = ", ".join(sorted(self.category_map.keys()))
            self.error(path, line, f"未登録の category です: {category!r}（site-config.json の fields[].name / aliases に追加してください。利用可能: {allowed}）")
        return category

    def validate_choices_and_correct(self, path: Path, row: dict[str, str], line: int, *, allow_invalidated: bool) -> None:
        for i in range(1, 5):
            self.require_text(path, row, line, f"choice_{i}")
        invalidated = allow_invalidated and self.truthy(row.get("is_invalidated"))
        correct = self.norm(row.get("correct"))
        if invalidated and not correct:
            return
        if not correct:
            self.error(path, line, "correct が空です")
            return
        try:
            n = int(correct)
        except ValueError:
            self.error(path, line, f"correct は 1〜5 の整数で入力してください: {correct!r}")
            return
        choices = [self.norm(row.get(f"choice_{i}")) for i in range(1, 6)]
        max_choice = max([i for i, value in enumerate(choices, start=1) if value] or [4])
        if not 1 <= n <= max_choice:
            self.error(path, line, f"correct は 1〜{max_choice} の範囲で入力してください: {n}")

    def validate_past_questions(self) -> None:
        path = DATA_DIR / "past_questions.csv"
        required = {
            "exam_year",
            "exam_wareki",
            "question_no",
            "type",
            "category",
            "stem",
            "choice_1",
            "choice_2",
            "choice_3",
            "choice_4",
            "correct",
            "is_invalidated",
            "explanation",
        }
        _, rows = self.read_csv(path, required)
        seen: set[tuple[int, int]] = set()
        for idx, row in enumerate(rows, start=2):
            year = self.require_int(path, row, idx, "exam_year", min_value=1900)
            qno = self.require_int(path, row, idx, "question_no", min_value=1)
            if year is not None and qno is not None:
                key = (year, qno)
                if key in seen:
                    self.error(path, idx, f"exam_year + question_no が重複しています: {year}-{qno}")
                seen.add(key)
            self.require_text(path, row, idx, "exam_wareki")
            self.require_text(path, row, idx, "type")
            self.validate_category(path, row, idx)
            self.require_text(path, row, idx, "stem")
            self.require_text(path, row, idx, "explanation")
            self.validate_choices_and_correct(path, row, idx, allow_invalidated=True)
            related = self.norm(row.get("related_links"))
            if related:
                for token in split_semicolon(related):
                    if ":" not in token:
                        self.warn(
                            path,
                            idx,
                            f"related_links の形式を確認してください（例: guide:slug:ラベル）: {token!r}",
                        )
            self._validate_diagram_id(path, row, idx)

    def validate_practice_questions(self) -> None:
        path = DATA_DIR / "practice_questions.csv"
        required = {
            "question_no",
            "type",
            "category",
            "stem",
            "choice_1",
            "choice_2",
            "choice_3",
            "choice_4",
            "correct",
            "explanation",
        }
        _, rows = self.read_csv(path, required)
        seen: set[int] = set()
        for idx, row in enumerate(rows, start=2):
            qno = self.require_int(path, row, idx, "question_no", min_value=1)
            if qno is not None:
                if qno in seen:
                    self.error(path, idx, f"question_no が重複しています: {qno}")
                seen.add(qno)
            self.require_text(path, row, idx, "type")
            self.validate_category(path, row, idx)
            self.require_text(path, row, idx, "stem")
            self.require_text(path, row, idx, "explanation")
            self.validate_choices_and_correct(path, row, idx, allow_invalidated=False)
            self._validate_diagram_id(path, row, idx)

    def validate_ichimon_questions(self) -> None:
        path = DATA_DIR / "ichimon_questions.csv"
        required = {"id", "question", "answer", "explanation", "category"}
        _, rows = self.read_csv(path, required)
        seen: set[str] = set()
        for idx, row in enumerate(rows, start=2):
            rid = self.require_text(path, row, idx, "id")
            if rid:
                if rid in seen:
                    self.error(path, idx, f"id が重複しています: {rid}")
                seen.add(rid)
                if len(rid.split("-")) != 3:
                    self.warn(path, idx, f"id は YYYY-問番号-枝番 形式を推奨します: {rid}")
            self.validate_category(path, row, idx)
            self.require_text(path, row, idx, "question")
            self.require_text(path, row, idx, "explanation")
            answer = self.require_text(path, row, idx, "answer")
            if answer and answer not in {"○", "〇", "×", "✕", "╳"}:
                self.error(path, idx, f"answer は ○ または × で入力してください: {answer!r}")
            self._validate_diagram_id(path, row, idx)

    def validate_glossary(self) -> None:
        path = DATA_DIR / "glossary_terms.csv"
        _, rows = self.read_csv(path, set(GLOSSARY_BASE_REQUIRED))
        entries: list[dict[str, str]] = []
        for row in rows:
            term = self.norm(row.get("term"))
            if term:
                entries.append(
                    {
                        "term": term,
                        "slug_file": "g-dummy.html",
                    }
                )
        term_lookup = make_term_lookup(entries)
        if len(entries) < GLOSSARY_PRODUCTION_TARGET:
            self.warn(
                path,
                None,
                f"用語数が {GLOSSARY_PRODUCTION_TARGET} 件未満です（現在 {len(entries)} 件）。本番は詳細記事を {GLOSSARY_PRODUCTION_TARGET} 件以上推奨",
            )
        seen: set[str] = set()
        for idx, row in enumerate(rows, start=2):
            term = self.require_text(path, row, idx, "term")
            if term:
                if term in seen:
                    self.error(path, idx, f"term が重複しています: {term}")
                seen.add(term)
            self.validate_category(path, row, idx)
            for col in ("short_def", "definition", "explanation", "term_detail_body"):
                body = self.norm(row.get(col))
                if not body:
                    continue
                for fragment, reason in OPERATOR_CONTENT_FRAGMENTS:
                    if fragment in body:
                        self.error(
                            path,
                            idx,
                            f"{col} に公開禁止の文言「{fragment}」: {reason}",
                        )
            for issue in check_glossary_row(row, term_lookup=term_lookup, line=idx):
                if issue.level == "ERROR":
                    self.error(path, idx, issue.message)
                else:
                    self.warn(path, idx, issue.message)
            self._validate_diagram_id(path, row, idx)

    def _validate_diagram_id(self, path: Path, row: dict[str, str], line: int) -> None:
        raw = self.norm(row.get("diagram_id"))
        if not raw:
            return
        if not DIAGRAM_ID_RE.fullmatch(raw):
            self.error(
                path,
                line,
                f"diagram_id は半角英小文字・数字・ハイフンのみ: {raw!r}",
            )
            return
        if not diagram_id_exists(raw):
            self.error(
                path,
                line,
                f"diagram_id に対応する JSON がありません: data/term_diagrams/{raw}.json",
            )

    def validate_guide_articles(self) -> None:
        path = DATA_DIR / "guide_articles.csv"
        required = {
            "slug",
            "genre",
            "title",
            "meta_description",
            "lead",
            "priority",
            "section_1_heading",
            "section_1_body",
        }
        _, rows = self.read_csv(path, required)
        if len(rows) < 100:
            self.warn(
                path,
                None,
                f"試験ガイドは本番テンプレート標準で100本以上を推奨します（現在 {len(rows)} 本）。"
                " docs/guide-article-catalog.md の記事カタログを参照してください。",
            )
        slugs: set[str] = {self.norm(r.get("slug")) for r in rows if self.norm(r.get("slug"))}
        seen: set[str] = set()
        affiliate_count = 0
        for idx, row in enumerate(rows, start=2):
            slug = self.require_text(path, row, idx, "slug")
            if slug:
                if slug in seen:
                    self.error(path, idx, f"slug が重複しています: {slug}")
                seen.add(slug)
                if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
                    self.error(path, idx, f"slug は半角英数字とハイフンで入力してください: {slug}")
            genre = self.require_text(path, row, idx, "genre")
            if genre and genre not in guide_genre_labels():
                allowed = "、".join(guide_genre_labels())
                self.error(
                    path,
                    idx,
                    f"genre は site-config.json の guideArticleGenres に定義したラベルにしてください（許可: {allowed}）。現在: {genre!r}",
                )
            self.require_text(path, row, idx, "title")
            self.require_text(path, row, idx, "meta_description")
            self.require_text(path, row, idx, "lead")
            self.require_int(path, row, idx, "priority", min_value=1)
            self.require_text(path, row, idx, "section_1_heading")
            self.require_text(path, row, idx, "section_1_body")
            for n in range(1, 8):
                for kind in ("heading", "body"):
                    col = f"section_{n}_{kind}"
                    value = self.norm(row.get(col))
                    if not value:
                        continue
                    for fragment, reason in OPERATOR_CONTENT_FRAGMENTS:
                        if fragment in value:
                            self.error(
                                path,
                                idx,
                                f"{col} に公開禁止の文言「{fragment}」: {reason}",
                            )
            for col in ("author_name", "fact_checked_at", "primary_sources", "original_note", "action_items"):
                if col in row and not self.norm(row.get(col)):
                    self.warn(path, idx, f"{col} はSEO品質確認用の推奨列です")
            for item in [x.strip() for x in self.norm(row.get("primary_sources")).split(";") if x.strip()]:
                if "|" in item:
                    label, url = [x.strip() for x in item.split("|", 1)]
                    if not label or not url.startswith(("http://", "https://")):
                        self.warn(path, idx, f"primary_sources は ラベル|URL 形式を推奨します: {item}")
            for n in range(1, 4):
                q = self.norm(row.get(f"faq_{n}_question"))
                a = self.norm(row.get(f"faq_{n}_answer"))
                if bool(q) != bool(a):
                    self.warn(path, idx, f"faq_{n}_question と faq_{n}_answer はセットで入力してください")
                if q and not q.endswith(("?", "？")):
                    self.warn(path, idx, f"faq_{n}_question は質問文として入力してください: {q}")
                if a and re.fullmatch(r"[a-z0-9][a-z0-9-]*:.+", a):
                    self.warn(path, idx, f"faq_{n}_answer に related_links らしき値が入っています: {a}")
                for fragment, reason in OPERATOR_CONTENT_FRAGMENTS:
                    if (q and fragment in q) or (a and fragment in a):
                        self.error(
                            path,
                            idx,
                            f"faq_{n} に公開禁止の文言「{fragment}」: {reason}",
                        )
            related = self.norm(row.get("related_links"))
            if related:
                for item in split_semicolon(related):
                    target = item.split(":", 1)[0].strip()
                    if target.startswith(("http://", "https://")):
                        continue
                    if not target:
                        continue
                    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", target):
                        self.error(
                            path,
                            idx,
                            f"related_links の内部 slug 形式が不正です: {target!r}",
                        )
                        continue
                    if target not in slugs:
                        self.error(
                            path,
                            idx,
                            f"related_links の slug が guide_articles.csv に存在しません: {target!r}",
                        )
            tags = split_semicolon(self.norm(row.get("tags")))
            if AFFILIATE_TAG in tags:
                affiliate_count += 1
                if genre and genre not in AFFILIATE_GENRES:
                    self.warn(
                        path,
                        idx,
                        f"アフィリエイト記事の genre は通常 {sorted(AFFILIATE_GENRES)} のいずれかにしてください（現在: {genre!r}）",
                    )
                lead = self.norm(row.get("lead"))
                if lead and not any(marker in lead for marker in AFFILIATE_PR_MARKERS):
                    self.warn(
                        path,
                        idx,
                        "アフィリエイト記事の lead に広告・PR（アフィリエイト）である旨を含めてください",
                    )
                internal_related = 0
                if related:
                    for item in split_semicolon(related):
                        target = item.split(":", 1)[0].strip()
                        if target and not target.startswith(("http://", "https://")):
                            internal_related += 1
                if internal_related < 2:
                    self.warn(
                        path,
                        idx,
                        "アフィリエイト記事の related_links には、試験ガイド・無料コンテンツへ向ける内部 slug を2件以上推奨します",
                    )

            for issue in check_guide_row(row, slug_set=slugs, line=idx):
                if issue.level == "ERROR":
                    self.error(path, idx, f"[{issue.column}] {issue.message}")
                else:
                    self.warn(path, idx, f"[{issue.column}] {issue.message}")

        if affiliate_count < AFFILIATE_TARGET_COUNT:
            self.warn(
                path,
                None,
                f"アフィリエイト記事は本番テンプレート標準で{AFFILIATE_TARGET_COUNT}本を目安にしてください"
                f"（tags に「{AFFILIATE_TAG}」を含む行: 現在 {affiliate_count} 本）。"
                " docs/guide-article-catalog.md の「アフィリエイト記事（10本目安）」を参照してください。",
            )
        elif affiliate_count > 18:
            self.warn(
                path,
                None,
                f"アフィリエイト記事が {affiliate_count} 本あります（目安は{AFFILIATE_TARGET_COUNT}本前後）。"
                " 検索意図の重複と更新負荷がないか確認してください。",
            )

    def validate_knowledge_hub(self) -> None:
        entries: list[dict[str, str]] = []
        glossary_path = DATA_DIR / "glossary_terms.csv"
        if glossary_path.is_file():
            _, gloss_rows = self.read_csv(glossary_path, set(GLOSSARY_BASE_REQUIRED))
            for row in gloss_rows:
                term = self.norm(row.get("term"))
                if term:
                    entries.append({"term": term, "slug_file": "g-dummy.html"})
        term_lookup = make_term_lookup(entries)

        validators = {
            "compare": (check_compare_row, {"title", "category", "col_labels", "compare_rows"}),
            "numbers": (check_numbers_row, {"title", "category", "highlight", "item_rows"}),
            "mistakes": (check_mistakes_row, {"title", "category", "confusion_point", "pattern_rows"}),
        }
        for hub_type, (checker, required) in validators.items():
            path = DATA_DIR / HUB_CSV_NAMES[hub_type]
            if not path.is_file():
                self.warn(
                    path,
                    None,
                    f"{HUB_LABELS[hub_type]} の CSV がありません: {HUB_CSV_NAMES[hub_type]}",
                )
                continue
            _, rows = self.read_csv(path, required | {"article_title", "article_lead", "exam_points", "related_terms"})
            published = [row for row in rows if self.norm(row.get("title"))]
            msg = production_count_message(hub_type, len(published))
            if msg:
                self.warn(path, None, msg)
            seen_titles: set[str] = set()
            for idx, row in enumerate(rows, start=2):
                title = self.norm(row.get("title"))
                if not title:
                    continue
                if title in seen_titles:
                    self.error(path, idx, f"title が重複しています: {title}")
                seen_titles.add(title)
                self.validate_category(path, row, idx)
                for issue in checker(row, term_lookup=term_lookup, line=idx):
                    if issue.level == "ERROR":
                        self.error(path, idx, f"[{issue.column}] {issue.message}")
                    else:
                        self.warn(path, idx, f"[{issue.column}] {issue.message}")

    def run(self) -> int:
        self.validate_past_questions()
        self.validate_practice_questions()
        self.validate_ichimon_questions()
        self.validate_glossary()
        self.validate_guide_articles()
        self.validate_knowledge_hub()

        for issue in self.issues:
            print(issue.format(), file=sys.stderr if issue.level == "ERROR" else sys.stdout)

        errors = [i for i in self.issues if i.level == "ERROR"]
        warnings = [i for i in self.issues if i.level == "WARN"]
        if errors:
            print(f"CSV validation failed: {len(errors)} error(s), {len(warnings)} warning(s)", file=sys.stderr)
            return 1
        print(f"CSV validation passed: {warnings and str(len(warnings)) + ' warning(s)' or 'no warnings'}")
        return 0


def main() -> int:
    return Validator().run()


if __name__ == "__main__":
    raise SystemExit(main())
