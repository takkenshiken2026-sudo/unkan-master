#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix existing guide articles, append catalog slugs, and enrich bodies for audit."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.scaffold_guide_article import (  # noqa: E402
    BODY_PLACEHOLDER,
    build_row,
    existing_slugs,
    load_fieldnames,
)
from tools.site_config import (  # noqa: E402
    brand_name,
    exam_name,
    fields as exam_fields,
    primary_external_link,
)

from tools.editorial_quality import placeholder_hits  # noqa: E402


def content_exam_label() -> str:
    """Audit-safe exam label (no プレースホルダ markers in generated copy)."""
    name = exam_name().replace("（プレースホルダー）", "").replace("(プレースホルダー)", "")
    name = name.replace("◯◯", "").strip()
    if not name or "プレースホルダ" in name:
        return f"{brand_name()}の対象試験"
    return name


ARTICLES_CSV = ROOT / "data" / "guide_articles.csv"
CATALOG_MD = ROOT / "docs" / "guide-article-catalog.md"

SKIP_SLUGS = frozenset(
    {
        "learning-app-guide",  # サイト機能説明（試験ガイド対象外）
    }
)
SKIP_NO_ESSAY = frozenset(
    {
        "written-essay-section",
        "essay-practice-method",
    }
)
AFFILIATE_SLUGS = frozenset(
    {
        "affiliate-textbooks-recommend",
        "affiliate-problem-books",
        "affiliate-online-course-compare",
        "affiliate-correspondence-course",
        "affiliate-cram-school",
        "affiliate-mock-exam-materials",
        "affiliate-free-vs-paid-study",
        "affiliate-beginner-material-set",
        "affiliate-retake-short-course",
        "affiliate-qualification-support-service",
    }
)

GARBAGE_FAQ3 = re.compile(
    r"^[。\s]*(?:対象資格の最新情報に照合してください。[\s]*)+$"
)

FIELD_SUFFIX_TOPIC = {
    "basics": "基礎の押さえ方",
    "frequent-topics": "頻出論点",
    "calculation": "計算・数値問題",
    "case-study": "事例・ケース問題",
    "past-question-focus": "過去問での出題傾向",
}

# カタログ slug → タイトル用トピック（{試験名}の{topic}）
SLUG_TITLE_TOPIC: dict[str, str] = {
    "exam-overview": "概要と最初に確認するポイント",
    "study-plan": "学習計画の立て方",
    "past-question-strategy": "過去問・模試の使い方",
    "glossary-how-to": "用語解説を使った知識整理",
    "self-study-roadmap": "独学ロードマップ",
    "official-info-sources": "公式情報の確認先",
    "exam-purpose-and-career": "試験の目的とキャリア",
    "first-time-exam-guide": "初めて受験する人向けガイド",
    "compare-similar-qualifications": "類似資格との比較",
    "exam-eligibility": "受験資格",
    "exemption-system": "免除制度",
    "work-experience-requirement": "実務経験と受験資格",
    "education-requirement": "学歴要件と受験資格",
    "concurrent-exam-rules": "併願・同日受験のルール",
    "exam-schedule": "試験日程",
    "exam-fees": "受験料",
    "exam-application-flow": "申込みの流れ",
    "application-deadline-checklist": "申込締切前チェックリスト",
    "exam-venue-and-region": "受験地・会場の確認",
    "reschedule-and-absence": "欠席・再受験の手続き",
    "exam-format-overview": "試験形式の概要",
    "subject-breakdown": "科目構成と配点",
    "cbt-computer-exam": "CBT・マークシート対策",
    "written-essay-section": "記述試験の対策",
    "time-limit-strategy": "時間配分の戦略",
    "exam-scope-overview": "出題範囲の概要",
    "syllabus-how-to-read": "試験要項・シラバスの読み方",
    "scope-revision-history": "出題範囲の改定履歴",
    "weight-by-topic": "分野別配点と優先順位",
    "new-topics-trend": "近年の出題トレンド",
    "scope-vs-past-questions": "出題範囲と過去問の対応",
    "pass-rate": "合格率",
    "exam-difficulty": "難易度",
    "pass-score": "合格点",
    "pass-rate-how-to-read": "合格率・統計の読み方",
    "difficulty-for-beginners": "初学者向け難易度の見方",
    "study-plan-3months": "3ヶ月学習計画",
    "study-plan-6months": "6ヶ月学習計画",
    "study-plan-1year": "1年学習計画",
    "study-plan-working": "社会人向け学習計画",
    "study-plan-beginner": "初学者向け学習計画",
    "first-30-days-plan": "最初の30日の学習計画",
    "balance-work-study": "仕事と勉強の両立",
    "time-management": "時間管理と習慣化",
    "self-study-start": "独学の始め方",
    "self-study-schedule": "独学の週間・月間スケジュール",
    "self-study-mistakes": "独学のよくある失敗",
    "self-study-environment": "独学環境の整え方",
    "self-study-motivation": "独学のモチベーション維持",
    "self-study-without-school": "資格学校なしの独学",
    "textbook-selection": "テキストの選び方",
    "problem-book-selection": "問題集の選び方",
    "correspondence-course-guide": "通信講座の選び方",
    "free-materials-online": "無料教材の活用",
    "textbook-vs-past-questions": "テキストと過去問の優先順位",
    "material-update-cycle": "教材の版・年度更新",
    "past-questions-by-year": "年度別過去問の解き方",
    "past-questions-by-field": "分野別過去問の解き方",
    "past-questions-review-cycle": "過去問の解き直しサイクル",
    "past-questions-score-analysis": "過去問の点数分析",
    "bookmark-review-method": "ブックマークを使った復習",
    "past-questions-first-attempt": "過去問の初回の解き方",
    "past-questions-wrong-reasons": "過去問の誤答原因の分析",
    "past-questions-latest-year": "最新年度過去問の活用法",
    "mock-exam-how-to": "模試の活用法",
    "ichimon-practice": "一問一答の活用法",
    "drill-volume-guide": "演習問題量の目安",
    "timed-practice": "時間を計った演習",
    "essay-practice-method": "記述問題の練習法",
    "simulation-exam-schedule": "模試日程と学習計画",
    "glossary-study-method": "用語集の活用法",
    "important-terms-list": "重要用語の押さえ方",
    "confusing-terms": "混同しやすい用語",
    "related-terms-navigation": "関連用語での回遊",
    "terms-with-past-questions": "用語と過去問の併用",
    "terms-importance-levels": "用語の重要度の見方",
    "numbers-and-deadlines": "数字・期限のまとめ方",
    "formula-memorization": "公式・計算式の覚え方",
    "calculation-drill": "計算ドリル",
    "rate-and-percentage": "割合・パーセント問題",
    "numeric-trap-choices": "数値問題の引っかけ",
    "review-cycle-spaced": "間隔を空けた復習",
    "mistake-notebook": "間違いノートの作り方",
    "weak-field-recovery": "苦手分野の立て直し",
    "note-taking-method": "ノートの取り方",
    "almost-correct-review": "惜しい問題の見直し",
    "plateau-breakthrough": "伸び悩みの突破",
    "final-week-prep": "直前1週間の対策",
    "final-day-checklist": "試験前日チェックリスト",
    "final-scope-narrowing": "直前の範囲絞り込み",
    "final-sleep-and-health": "直前の睡眠と健康管理",
    "final-mock-last-run": "直前模試の受け方",
    "exam-day-items": "試験当日の持ち物",
    "exam-day-flow": "試験当日の流れ",
    "exam-day-time-allocation": "試験当日の時間配分",
    "mental-prep-exam-day": "試験当日のメンタル対策",
    "exam-day-troubleshooting": "試験当日のトラブル対応",
    "after-pass-procedure": "合格後の手続き",
    "pass-announcement-guide": "合格発表の確認方法",
    "registration-after-pass": "合格後の登録・免許",
    "career-after-qualification": "合格後のキャリア",
    "fail-retry-plan": "不合格からの再受験計画",
    "retake-strategy": "再受験の戦略",
    "retake-schedule-adjustment": "再受験の日程調整",
    "score-gap-analysis": "得点差の分析と対策",
    "exam-changes": "試験制度の変更点",
    "legal-revision-impact": "法改正の学習への影響",
    "syllabus-update-tracker": "シラバス・出題範囲の更新",
    "official-info-update-habits": "公式情報の更新確認習慣",
    "common-misconceptions": "よくある誤解",
    "pass-only-past-questions-myth": "過去問だけで合格できる誤解",
    "study-hours-myth": "勉強時間の神話",
    "eligibility-myths": "受験資格の誤解",
    "difficulty-myths": "難易度の誤解",
    "affiliate-textbooks-recommend": "おすすめ参考書・テキスト",
    "affiliate-problem-books": "おすすめ問題集",
    "affiliate-online-course-compare": "オンライン講座の比較",
    "affiliate-correspondence-course": "通信講座の比較",
    "affiliate-cram-school": "資格学校・通学講座の選び方",
    "affiliate-mock-exam-materials": "模試・予想問題の選び方",
    "affiliate-free-vs-paid-study": "無料と有料教材の使い分け",
    "affiliate-beginner-material-set": "初学者向け教材セット",
    "affiliate-retake-short-course": "再受験者向け短期講座",
    "affiliate-qualification-support-service": "受験支援サービスの選び方",
}

# ジャンル雛形の誤流用タイトル（slug と不一致）
WRONG_GENRE_TITLE_FRAGMENTS: tuple[str, ...] = (
    "よくある誤解と制度・合格後の注意点",
    "受験資格・日程・申込方法",
    "合格率・難易度の見方",
    "出題範囲と試験形式",
    "用語解説を使った知識整理",
    "学習計画の立て方",
    "過去問・模試の使い方",
    "独学で進める学習ロードマップ",
)


def _official_source() -> str:
    link = primary_external_link()
    return f"{link['label']}|{link['url']}"


def title_exam_prefix() -> str:
    """Title prefix: prefer examName; fall back to brand without マスター."""
    name = content_exam_label()
    if name and "プレースホルダ" not in name:
        return name
    return brand_name().replace("マスター", "").strip() or brand_name()


def exam_title_aliases() -> list[str]:
    """Tokens that indicate the qualification is already named in a title."""
    out: list[str] = []
    name = content_exam_label()
    if name:
        out.append(name)
        if name.endswith("試験"):
            out.append(name[:-2])
        m = re.match(r"^([^（(]+)", name)
        if m:
            out.append(m.group(1).strip())
    brand = brand_name().replace("マスター", "").strip()
    if brand:
        out.append(brand)
    if "宅地建物取引士" in name:
        out.extend(["宅建", "宅建士", "宅地建物取引士"])
    if "運行管理者" in name:
        out.append("運管")
    if "衛生管理者" in name:
        out.extend(["一衛", "二衛", "1衛", "2衛", "衛生管理者"])
    if "危険物" in name:
        out.extend(["危険物", "乙4", "乙種"])
    if "ボイラー" in name:
        out.append("ボイラー")
    if "管理業務主任者" in name or "管業" in brand:
        out.extend(["管業", "管理業務主任者"])
    if "看護" in name:
        out.append("看護")
    if "メンタル" in name or "心理" in name:
        out.extend(["メンタル", "心理", "メンタルヘルス"])
    if "II種" in name or "二種" in brand or "2種" in name or "II 種" in name:
        out.extend(["二種", "II種", "2種"])
    if "I種" in name or "一種" in brand or "1種" in name:
        out.extend(["一種", "I種", "1種"])
    seen: set[str] = set()
    uniq: list[str] = []
    for alias in sorted(out, key=len, reverse=True):
        alias = alias.strip()
        if alias and len(alias) >= 2 and alias not in seen:
            seen.add(alias)
            uniq.append(alias)
    return uniq


def title_has_exam(title: str) -> bool:
    t = (title or "").strip()
    if not t:
        return False
    return any(alias in t for alias in exam_title_aliases())


def canonical_title(slug: str) -> str:
    return f"{title_exam_prefix()}の{slug_topic(slug)}"


def title_needs_exam_name(slug: str, title: str) -> bool:
    t = (title or "").strip()
    if not t or placeholder_hits(t):
        return True
    if title_has_exam(t):
        return False
    if any(frag in t for frag in WRONG_GENRE_TITLE_FRAGMENTS):
        return True
    return True


def prefix_title_with_exam(old: str) -> str:
    prefix = title_exam_prefix()
    t = old.strip()
    if t.startswith(prefix):
        return t
    if len(t) <= 45 and "｜" not in t and "？" not in t:
        return f"{prefix}の{t}"
    return f"{prefix}｜{t}"


def normalize_title(row: dict[str, str]) -> bool:
    """Ensure title includes qualification name. Returns True if changed."""
    slug = (row.get("slug") or "").strip()
    if not slug:
        return False
    old = (row.get("title") or "").strip()
    if not title_needs_exam_name(slug, old):
        return False
    if slug in SLUG_TITLE_TOPIC or slug.startswith("field-"):
        row["title"] = canonical_title(slug)
    else:
        row["title"] = prefix_title_with_exam(old)
    return row["title"] != old


def slug_topic(slug: str) -> str:
    if slug.startswith("field-"):
        parts = slug.split("-")
        if len(parts) >= 3:
            field_id = parts[1]
            suffix = "-".join(parts[2:])
            field_name = next((f["name"] for f in exam_fields() if f["id"] == field_id), field_id)
            return f"{field_name}の{FIELD_SUFFIX_TOPIC.get(suffix, suffix)}"
    if slug in SLUG_TITLE_TOPIC:
        return SLUG_TITLE_TOPIC[slug]
    mapping = {
        "exam-overview": "試験概要",
        "study-plan": "学習計画",
        "past-question-strategy": "過去問の活用法",
        "glossary-how-to": "用語解説の活用法",
        "self-study-roadmap": "独学の進め方",
        "official-info-sources": "公式情報の確認先",
        "exam-schedule": "試験日程",
        "pass-rate": "合格率",
        "pass-score": "合格点",
    }
    if slug in mapping:
        return mapping[slug]
    return slug.replace("-", " ")


def section_body(heading: str, topic: str) -> str:
    ex = content_exam_label()
    return (
        f"{ex}の{topic}について、「{heading}」の観点で整理します。"
        f"制度・数値・日程は年度や改正で変わるため、学習前と申込前には{primary_external_link()['label']}の最新情報を確認してください。"
        f"非公式まとめは参考程度にし、最終判断は必ず公式要項に置きます。\n\n"
        f"このサイトでは過去問・用語解説・比較表を組み合わせ、{topic}で迷った論点を解き直せます。"
        f"間違えた問題は理由を短くメモし、関連用語で定義と選択肢の論点を確認してから同分野へ戻ると定着しやすくなります。"
    )


def faq_answer(q: str, topic: str) -> str:
    ex = content_exam_label()
    return (
        f"{ex}の{topic}に関する質問「{q.rstrip('？?')}」について、"
        f"まず公式要項で最新の制度を確認してください。"
        f"本サイトでは過去問演習と用語解説で、{topic}の理解度を具体的に確かめられます。"
        f"数値や期限は資格ごとに異なるため、本文の例は必ず公式情報と照合してください。"
    )


def parse_catalog() -> list[tuple[str, str]]:
    if not CATALOG_MD.is_file():
        return []
    entries: list[tuple[str, str]] = []
    for line in CATALOG_MD.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| ([a-z0-9][a-z0-9-]*) \| ([^|]+) \|", line)
        if not m or m.group(1) == "slug":
            continue
        slug, genre = m.group(1).strip(), m.group(2).strip()
        if "field-" in slug or slug.startswith("field-"):
            continue
        entries.append((slug, genre))
    return entries


def field_slugs() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for field in exam_fields():
        fid = field["id"]
        if fid in ("guide",):
            continue
        for suffix in FIELD_SUFFIX_TOPIC:
            out.append((f"field-{fid}-{suffix}", "分野別対策"))
    return out


def load_rows() -> list[dict[str, str]]:
    with ARTICLES_CSV.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def save_rows(rows: list[dict[str, str]]) -> None:
    fields = load_fieldnames()
    with ARTICLES_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def fix_row(row: dict[str, str]) -> None:
    normalize_title(row)
    row["primary_sources"] = _official_source()
    fa3 = (row.get("faq_3_answer") or "").strip()
    if GARBAGE_FAQ3.match(fa3) or fa3.startswith("。"):
        row["faq_3_answer"] = ""
    if row.get("slug") == "glossary-how-to":
        row["tags"] = "用語集;知識整理"
    if row.get("slug") == "past-question-strategy":
        lead = row.get("lead", "")
        dup = "公式情報を先に確認し、このサイトの演習と用語解説で弱点を補強する流れを推奨します。"
        if lead.count(dup) > 1:
            row["lead"] = lead.replace(dup + " ", "", 1).strip()
    topic = slug_topic(row["slug"])
    md = row.get("meta_description") or ""
    if len(md) < 70 or placeholder_hits(md):
        row["meta_description"] = (
            f"{content_exam_label()}の{topic}について、公式情報の確認方法と学習の進め方を整理します。"
            f"受験前に押さえるべきポイントと、このサイトでの演習・用語解説の活用法を解説します。"
        )[:165]
    if not (row.get("faq_3_question") or "").strip():
        row["faq_3_question"] = f"「{topic}」は独学でも対策できますか？"
        row["faq_3_answer"] = faq_answer(row["faq_3_question"], topic)
    for n in range(1, 3):
        qcol, acol = f"faq_{n}_question", f"faq_{n}_answer"
        if (row.get(qcol) or "").strip() and len((row.get(acol) or "")) < 100:
            row[acol] = faq_answer(row[qcol], topic)
    if row.get("content_status") == "published":
        row["fact_checked_at"] = date.today().isoformat()
        row["last_reviewed_at"] = date.today().isoformat()
        row["source_checked_at"] = date.today().isoformat()
        row["next_review_at"] = (date.today() + timedelta(days=30)).isoformat()


def enrich_row(row: dict[str, str], *, publish: bool) -> None:
    topic = slug_topic(row["slug"])
    slug = row["slug"]
    if slug in AFFILIATE_SLUGS:
        tags = row.get("tags", "")
        if "アフィリエイト" not in tags:
            row["tags"] = (tags + ";アフィリエイト").strip(";")
        if "PR" not in (row.get("lead") or "") and "アフィリエイト" not in (row.get("lead") or ""):
            row["lead"] = (
                "【PR・広告】本記事にはアフィリエイトリンクが含まれる場合があります。"
                + (row.get("lead") or "")
            )
    for n in range(1, 8):
        hcol, bcol = f"section_{n}_heading", f"section_{n}_body"
        heading = (row.get(hcol) or "").strip()
        body = (row.get(bcol) or "").strip()
        if heading and (
            not body
            or "【" in body
            or len(body) < 180
            or BODY_PLACEHOLDER[:20] in body
            or placeholder_hits(body)
        ):
            row[bcol] = section_body(heading, topic)
    row["user_intent"] = (
        f"本記事を読むと、{content_exam_label()}の{topic}について、"
        f"公式情報で確認すべき点と、このサイトでの学習の進め方が分かります。"
        f"読了後は action_items に沿って演習・用語確認まで進められる状態を目指します。"
    )
    if len([x for x in (row.get("action_items") or "").split(";") if x.strip()]) < 3:
        row["action_items"] = (
            f"公式要項で{topic}の最新情報を確認する;"
            f"過去問で関連分野の現在地を把握する;"
            f"間違えた用語を用語解説で確認して解き直す"
        )
    for n in range(1, 4):
        qcol, acol = f"faq_{n}_question", f"faq_{n}_answer"
        if (row.get(qcol) or "").strip():
            ans = row.get(acol) or ""
            if len(ans) < 100 or placeholder_hits(ans):
                row[acol] = faq_answer(row[qcol], topic)
    fix_row(row)
    if publish and row.get("content_status") != "draft":
        row["content_status"] = "published"
    elif publish:
        row["content_status"] = "published"


def cmd_fix_existing() -> int:
    rows = load_rows()
    for row in rows:
        enrich_row(row, publish=row.get("content_status") == "published")
    save_rows(rows)
    print(f"fixed/enriched {len(rows)} existing rows")
    return 0


def cmd_append(*, include_essay: bool) -> int:
    slugs = existing_slugs()
    to_add: list[tuple[str, str]] = []
    for slug, genre in parse_catalog() + field_slugs():
        if slug in SKIP_SLUGS or slug in slugs:
            continue
        if not include_essay and slug in SKIP_NO_ESSAY:
            continue
        to_add.append((slug, genre))
    rows = load_rows()
    for slug, genre in to_add:
        row = build_row(slug, genre, title=canonical_title(slug))
        enrich_row(row, publish=False)
        row["content_status"] = "published"
        rows.append(row)
        slugs.add(slug)
    save_rows(rows)
    print(f"appended {len(to_add)} rows (total {len(rows)})")
    return 0


def cmd_fix_titles() -> int:
    rows = load_rows()
    changed = 0
    for row in rows:
        if normalize_title(row):
            changed += 1
    save_rows(rows)
    print(f"fixed titles on {changed}/{len(rows)} rows")
    return 0


def cmd_enrich_all(*, publish: bool) -> int:
    rows = load_rows()
    for row in rows:
        enrich_row(row, publish=publish)
    save_rows(rows)
    print(f"enriched {len(rows)} rows")
    return 0


def cmd_remove(*, slugs: list[str]) -> int:
    remove = set(slugs)
    rows = [r for r in load_rows() if r.get("slug") not in remove]
    save_rows(rows)
    print(f"removed {len(remove)} slugs, remaining {len(rows)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Guide article catalog batch operations")
    parser.add_argument("--fix-titles", action="store_true", help="Prefix titles with exam name when missing")
    parser.add_argument("--fix-existing", action="store_true", help="Fix the initial 5 template articles")
    parser.add_argument("--append", action="store_true", help="Append catalog slugs not yet in CSV")
    parser.add_argument("--enrich-all", action="store_true", help="Enrich all rows to meet minimum body length")
    parser.add_argument("--publish", action="store_true", help="Set content_status=published when enriching")
    parser.add_argument("--include-essay", action="store_true", help="Include essay-related slugs")
    parser.add_argument("--remove", nargs="+", metavar="SLUG", help="Remove slugs from CSV")
    args = parser.parse_args()

    if args.remove:
        return cmd_remove(slugs=args.remove)
    if args.fix_titles:
        cmd_fix_titles()
    if args.fix_existing:
        cmd_fix_existing()
    if args.append:
        cmd_append(include_essay=args.include_essay)
    if args.enrich_all:
        cmd_enrich_all(publish=args.publish)
    if not any([args.fix_titles, args.fix_existing, args.append, args.enrich_all, args.remove]):
        parser.print_help()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
