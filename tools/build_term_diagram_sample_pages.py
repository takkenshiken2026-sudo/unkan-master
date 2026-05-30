#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用語解説向け HTML 図解のサンプルページを生成する。

- terms/diagram-samples/index.html … 図解サンプル一覧
- terms/diagram-samples/kenpei-yoseki.html … 図解単体プレビュー
- terms/g-diagram-sample.html … 用語記事内への差し込み見本
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_glossary_pages import (  # noqa: E402
    HEAD_FONTS,
    TERMS_INDEX_CSS_VER,
    build_term_html,
    load_guide_slugs,
    load_glossary_rows,
    make_term_lookup,
    term_slug,
)
from tools.build_knowledge_hub_sample_pages import patch_writing_sample_page  # noqa: E402
from tools.html_footer import (  # noqa: E402
    breadcrumb_html,
    shell_body_class,
    site_page_footer,
    site_page_header,
    site_page_wrap_close,
    site_page_wrap_open,
)
from tools.knowledge_hub_tabs import knowledge_hub_tab_hrefs, knowledge_hub_tabs_html  # noqa: E402
from tools.knowledge_hub_writing_samples import (  # noqa: E402
    GLOSSARY_DIAGRAM_SAMPLE,
    sample_banner_html,
    sample_robots_meta,
)
from tools.site_config import brand_name, clean_origin, exam_name  # noqa: E402
from tools.term_diagram import diagram_body_html, load_diagram  # noqa: E402

DIAGRAM_SAMPLES_DIR = ROOT / "terms" / "diagram-samples"
BASE_DEFAULT = clean_origin()

DIAGRAM_SAMPLE_CARDS = [
    (
        "kenpei-yoseki",
        "建ぺい率と容積率の違い",
        "2項目比較型（compare_dual）。平面図と階別積み上げの図解付き。",
    ),
]


def glossary_entries_for_diagram_sample() -> tuple[list[dict], dict[str, str], dict[str, dict]]:
    if not (ROOT / "data" / "glossary_terms.csv").is_file():
        return [], {}, {}
    rows = load_glossary_rows()
    used: dict[str, str] = {}
    entries: list[dict] = []
    for row in rows:
        term = row.get("term", "").strip()
        if not term:
            continue
        legacy = row.get("slug", "").strip() or row.get("url_slug", "").strip()
        slug_file = f"{legacy}.html" if legacy else term_slug(term, used) + ".html"
        entries.append(
            {
                "term": term,
                "category": row.get("category", ""),
                "slug_file": slug_file,
                "related_terms": row.get("related_terms", ""),
            }
        )
    sample = dict(GLOSSARY_DIAGRAM_SAMPLE)
    if not any(e["term"] == sample["term"] for e in entries):
        entries.append(sample)
    term_lookup = make_term_lookup(entries)
    by_term = {e["term"]: e for e in entries}
    return entries, term_lookup, by_term


def build_diagram_samples_index() -> str:
    idx_path = Path("terms/diagram-samples/index.html")
    page_header = site_page_header(idx_path, current="terms", wide=True)
    page_footer = site_page_footer(idx_path, current="terms", wide=True)
    page_breadcrumb = breadcrumb_html(
        idx_path,
        [
            ("トップ", "index.html"),
            ("用語解説一覧", "../index.html"),
            ("図解サンプル", None),
        ],
    )
    tabs_html = knowledge_hub_tabs_html(current="diagram-samples", **knowledge_hub_tab_hrefs(here="diagram-samples"))

    cards = []
    for diagram_id, title, desc in DIAGRAM_SAMPLE_CARDS:
        cards.append(
            '<article class="knowledge-hub-sample-card">'
            f'<h2><a href="{html.escape(diagram_id)}.html">{html.escape(title)}</a></h2>'
            f"<p>{html.escape(desc)}</p>"
            f'<p class="knowledge-hub-sample-card-meta">'
            f'<code>diagram_id={html.escape(diagram_id)}</code></p>'
            f'<p><a class="knowledge-hub-sample-card-link" href="{html.escape(diagram_id)}.html">'
            "図解プレビューを開く</a></p>"
            "</article>"
        )

    title = f"用語解説 図解サンプル｜{brand_name()}（{exam_name()}）"
    lead = (
        "用語解説記事に差し込む HTML 図解の見本です。"
        "glossary_terms.csv の diagram_id 列に ID を指定すると、"
        "「定義と基本理解」セクションの直後に図解ブロックが挿入されます。"
    )
    doc_note = (
        '<p class="knowledge-hub-sample-doc-note">'
        "図解データ: <code>data/term_diagrams/{id}.json</code>。"
        "差し込み見本: <code>terms/g-diagram-sample.html</code>。"
        "新規図解は JSON を追加し、diagram_id で参照します。"
        "</p>"
    )

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="用語解説記事向け HTML 図解の執筆サンプル一覧。">
{sample_robots_meta()}
{HEAD_FONTS}
<link rel="stylesheet" href="../../site-pages.css?v={TERMS_INDEX_CSS_VER}">
<link rel="stylesheet" href="../../site-theme.css">
<script>document.documentElement.classList.add("js");</script>
</head>
<body class="{shell_body_class('term-diagram-samples-page')}">
{site_page_wrap_open()}
{page_header}
<main class="site-page-main">
  {page_breadcrumb}
  <h1>用語解説 図解サンプル</h1>
  <p class="site-page-lead">{html.escape(lead)}</p>
  {tabs_html}
  {doc_note}
  <section class="knowledge-hub-sample-grid" aria-label="図解サンプル一覧">
    {"".join(cards)}
  </section>
  <p class="term-diagram-sample-embed-link">
    <a href="../g-diagram-sample.html">用語記事への差し込み見本を開く</a>
  </p>
</main>
{page_footer}
{site_page_wrap_close()}
</body>
</html>
"""


def build_standalone_diagram_page(diagram_id: str, base_url: str) -> str:
    data = load_diagram(diagram_id)
    if not data:
        raise ValueError(f"diagram not found: {diagram_id}")
    diagram_html = diagram_body_html(diagram_id)
    title = str(data.get("title") or diagram_id)
    page_title = f"【図解サンプル】{title}｜{brand_name()}（{exam_name()}）"
    rel_path = Path(f"terms/diagram-samples/{diagram_id}.html")
    page_header = site_page_header(rel_path, current="terms", wide=True)
    page_footer = site_page_footer(rel_path, current="terms", wide=True)
    page_breadcrumb = breadcrumb_html(
        rel_path,
        [
            ("トップ", "index.html"),
            ("用語解説一覧", "../index.html"),
            ("図解サンプル", "index.html"),
            (title, None),
        ],
    )
    banner = sample_banner_html(
        samples_href="../samples/index.html",
        type_href="index.html",
        type_label="図解サンプル",
        doc_href="../../docs/knowledge-hub-article-templates.md",
    )
    note = (
        '<p class="term-diagram-standalone-note">'
        f"このページは <code>data/term_diagrams/{html.escape(diagram_id)}.json</code> "
        f"から生成した図解の単体プレビューです。"
        f"用語記事では <code>diagram_id={html.escape(diagram_id)}</code> を指定して差し込みます。"
        "</p>"
    )

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(page_title)}</title>
<meta name="description" content="{html.escape(title)}の HTML 図解サンプル。">
{sample_robots_meta()}
{HEAD_FONTS}
<link rel="stylesheet" href="../../site-pages.css?v={TERMS_INDEX_CSS_VER}">
<link rel="stylesheet" href="../../site-theme.css">
<script>document.documentElement.classList.add("js");</script>
</head>
<body class="{shell_body_class('term-diagram-preview-page')}">
{site_page_wrap_open()}
{page_header}
<main class="site-page-main">
  {page_breadcrumb}
  {banner}
  {note}
  <article class="seo-article-card article-body term-diagram-standalone">
    {diagram_html}
  </article>
</main>
{page_footer}
{site_page_wrap_close()}
</body>
</html>
"""


def build_all(*, base_url: str = BASE_DEFAULT) -> int:
    count = 0
    DIAGRAM_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    (DIAGRAM_SAMPLES_DIR / "index.html").write_text(build_diagram_samples_index(), encoding="utf-8")
    count += 1

    for diagram_id, _, _ in DIAGRAM_SAMPLE_CARDS:
        out = DIAGRAM_SAMPLES_DIR / f"{diagram_id}.html"
        out.write_text(build_standalone_diagram_page(diagram_id, base_url), encoding="utf-8")
        count += 1

    entries, gl_lookup, by_term = glossary_entries_for_diagram_sample()
    guides = load_guide_slugs()
    sample_entry = dict(GLOSSARY_DIAGRAM_SAMPLE)
    glossary_path = ROOT / "terms" / sample_entry["slug_file"]
    glossary_rel = glossary_path.relative_to(ROOT)
    glossary_html = build_term_html(
        sample_entry,
        glossary_rel,
        base_url,
        gl_lookup or make_term_lookup([sample_entry]),
        entries or [sample_entry],
        guides,
        by_term=by_term or {sample_entry["term"]: sample_entry},
    )
    banner = sample_banner_html(
        samples_href="samples/index.html",
        type_href="diagram-samples/index.html",
        type_label="図解サンプル",
        doc_href="../docs/knowledge-hub-article-templates.md",
    )
    glossary_path.write_text(
        patch_writing_sample_page(glossary_html, banner), encoding="utf-8"
    )
    count += 1

    print(f"Wrote {count} term diagram sample pages (including g-diagram-sample.html)")
    return count


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=BASE_DEFAULT)
    args = ap.parse_args()
    build_all(base_url=args.base_url.rstrip("/"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
