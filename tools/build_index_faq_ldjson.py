#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""index.html の FAQPage JSON-LD を past_questions.csv から再生成する。"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.site_config import brand_name, exam_name  # noqa: E402

CSV_PATH = ROOT / "data" / "past_questions.csv"
INDEX_PATH = ROOT / "index.html"
FAQ_SCRIPT_RE = re.compile(
    r'<script type="application/ld\+json">\s*\{\s*"@context":\s*"https://schema\.org",\s*"@type":\s*"FAQPage".*?</script>\s*',
    re.DOTALL,
)
TEMPLATE_STEMS = (
    "Aが自己所有の甲土地をBに売却する契約",
    "宅地建物取引業者Aが、自ら売主として",
    "AB間の売買契約において、AがBに対して代金の支払いを請求",
)


def has_template_leak(text: str) -> bool:
    return any(stem in text for stem in TEMPLATE_STEMS)


def norm(value: str | None) -> str:
    return (value or "").strip()


def answer_text(row: dict[str, str]) -> str:
    for key in ("explanation_summary", "explanation_correct", "explanation"):
        text = norm(row.get(key))
        if text:
            return text[:800]
    return ""


def load_rows() -> list[dict[str, str]]:
    if not CSV_PATH.is_file():
        return []
    with CSV_PATH.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def pick_questions(rows: list[dict[str, str]], limit: int = 10) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    for row in rows:
        stem = norm(row.get("stem"))
        if not stem:
            continue
        if norm(row.get("is_exempt")).upper() == "TRUE":
            continue
        if norm(row.get("is_invalidated")).upper() == "TRUE":
            continue
        if not answer_text(row):
            continue
        candidates.append(row)

    def year_key(row: dict[str, str]) -> tuple[int, int]:
        try:
            year = int(norm(row.get("exam_year")) or "0")
        except ValueError:
            year = 0
        try:
            qno = int(norm(row.get("question_no")) or "0")
        except ValueError:
            qno = 0
        return (year, -qno)

    candidates.sort(key=year_key, reverse=True)

    picked: list[dict[str, str]] = []
    seen_categories: set[str] = set()
    for row in candidates:
        category = norm(row.get("category")) or "_"
        if category in seen_categories:
            continue
        picked.append(row)
        seen_categories.add(category)
        if len(picked) >= limit:
            break

    if len(picked) < limit:
        seen_stems = {norm(r.get("stem")) for r in picked}
        for row in candidates:
            stem = norm(row.get("stem"))
            if stem in seen_stems:
                continue
            picked.append(row)
            seen_stems.add(stem)
            if len(picked) >= limit:
                break
    return picked


def faq_payload(rows: list[dict[str, str]]) -> dict[str, object]:
    title = f"{exam_name()} よく出る問題と解説"
    main_entity = []
    for row in rows:
        main_entity.append(
            {
                "@type": "Question",
                "name": norm(row.get("stem")),
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": answer_text(row),
                },
            }
        )
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "name": title,
        "mainEntity": main_entity,
    }


def render_script(payload: dict[str, object]) -> str:
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return f'<script type="application/ld+json">\n{body}\n</script>\n'


def looks_like_takken_template(text: str) -> bool:
    return has_template_leak(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--remove-if-empty", action="store_true")
    args = parser.parse_args()

    if not INDEX_PATH.is_file():
        print(f"build_index_faq_ldjson.py: index.html がありません: {INDEX_PATH}")
        return 0

    html = INDEX_PATH.read_text(encoding="utf-8")
    if not FAQ_SCRIPT_RE.search(html):
        print("build_index_faq_ldjson.py: FAQPage ブロックなし（スキップ）")
        return 0

    rows = load_rows()
    picked = pick_questions(rows)
    if not picked:
        if args.remove_if_empty or brand_name().endswith("プレースホルダー") or "プレースホルダー" in exam_name():
            new_html = FAQ_SCRIPT_RE.sub("", html, count=1)
            action = "removed"
        else:
            print("build_index_faq_ldjson.py: 候補なし（スキップ）")
            return 0
    else:
        payload = faq_payload(picked)
        generated = render_script(payload)
        new_html = FAQ_SCRIPT_RE.sub(generated, html, count=1)
        action = f"updated ({len(picked)} items)"

    if new_html == html:
        print("build_index_faq_ldjson.py: 変更なし")
        return 0

    if args.dry_run:
        print(f"build_index_faq_ldjson.py: dry-run {action}")
        if picked:
            print("  first:", norm(picked[0].get("stem"))[:80])
        return 0

    INDEX_PATH.write_text(new_html, encoding="utf-8")
    print(f"build_index_faq_ldjson.py: {action}")
    if picked and looks_like_takken_template(json.dumps(faq_payload(picked), ensure_ascii=False)):
        if "宅建" not in exam_name() and "宅地建物" not in exam_name():
            print("build_index_faq_ldjson.py: error: 宅建テンプレFAQが残っています", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
