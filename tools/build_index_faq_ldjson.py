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
FAQ_SCRIPT_RE = re.compile(
    r'<script type="application/ld\+json">\s*\{\s*"@context":\s*"https://schema\.org",\s*"@type":\s*"FAQPage".*?</script>\s*',
    re.DOTALL,
)
TEMPLATE_STEMS = (
    "Aが自己所有の甲土地をBに売却する契約",
    "宅地建物取引業者Aが、自ら売主として",
    "AB間の売買契約において、AがBに対して代金の支払いを請求",
    "Sample試験の制度に関する",
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


def is_usable_faq_answer(text: str) -> bool:
    t = norm(text)
    if not t or len(t) < 30:
        return False
    if "（解説は未入力です。）" in t or t.startswith("（解説は未入力"):
        return False
    if has_template_leak(t):
        return False
    return True


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
        ans = answer_text(row)
        if not is_usable_faq_answer(ans):
            continue
        if has_template_leak(stem):
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


def inject_index_faq_ldjson(text: str) -> str:
    """FAQPage JSON-LD を site CSV から差し替え（Sample試験テンプレ除去）。"""
    if not FAQ_SCRIPT_RE.search(text):
        return text
    rows = load_rows()
    picked = pick_questions(rows)
    if not picked:
        return FAQ_SCRIPT_RE.sub("", text, count=1)
    payload = faq_payload(picked)
    generated = render_script(payload)
    if has_template_leak(json.dumps(payload, ensure_ascii=False)):
        return text
    return FAQ_SCRIPT_RE.sub(generated, text, count=1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    index_path = ROOT / "index.html"
    if not index_path.is_file():
        print(f"build_index_faq_ldjson.py: index.html がありません: {index_path}")
        return 0

    html = index_path.read_text(encoding="utf-8")
    new_html = inject_index_faq_ldjson(html)
    if new_html == html:
        print("build_index_faq_ldjson.py: 変更なし")
        return 0

    if args.dry_run:
        print("build_index_faq_ldjson.py: dry-run updated")
        return 0

    index_path.write_text(new_html, encoding="utf-8")
    print("build_index_faq_ldjson.py: updated FAQPage JSON-LD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
