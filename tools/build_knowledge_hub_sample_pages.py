#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知識ハブ執筆サンプル HTML を生成する。

- terms/samples/index.html … サンプル一覧
- terms/compare/c-writing-sample.html
- terms/numbers/n-writing-sample.html
- terms/mistakes/m-writing-sample.html
- terms/g-writing-sample.html
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_compare_pages import (  # noqa: E402
    build_compare_detail_html,
    glossary_term_lookup,
)
from tools.build_glossary_pages import (  # noqa: E402
    HEAD_FONTS,
    TERMS_INDEX_CSS_VER,
    build_term_html,
    load_guide_slugs,
    load_glossary_entries,
    load_glossary_rows,
    make_term_lookup,
    term_slug,
)
from tools.build_numbers_mistakes_pages import (  # noqa: E402
    MISTAKES_SPEC,
    NUMBERS_SPEC,
    build_detail_html,
    mistakes_matrix_table_html,
    numbers_matrix_table_html,
)
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
    COMPARE_WRITING_SAMPLE,
    GLOSSARY_WRITING_SAMPLE,
    MISTAKES_WRITING_SAMPLE,
    NUMBERS_WRITING_SAMPLE,
    sample_banner_html,
    sample_robots_meta,
)
from tools.site_config import brand_name, clean_origin, exam_name  # noqa: E402

SAMPLES_DIR = ROOT / "terms" / "samples"
BASE_DEFAULT = clean_origin()


def patch_writing_sample_page(page_html: str, banner: str) -> str:
    out = page_html
    for robots in (
        '<meta name="robots" content="index, follow">',
        '<meta name="robots" content="index,follow">',
    ):
        out = out.replace(robots, sample_robots_meta())
    marker = '<article class="seo-article-card article-body">'
    if marker in out:
        return out.replace(marker, banner + "\n  " + marker, 1)
    marker = '<h1 class="article-title">'
    if marker in out:
        return out.replace(marker, banner + "\n    " + marker, 1)
    return out + "\n" + banner


def build_samples_index(base_url: str) -> str:
    idx_path = Path("terms/samples/index.html")
    page_header = site_page_header(idx_path, current="terms", wide=True)
    page_footer = site_page_footer(idx_path, current="terms", wide=True)
    page_breadcrumb = breadcrumb_html(idx_path, [("トップ", "index.html"), ("執筆サンプル", None)])
    tabs_html = knowledge_hub_tabs_html(current="samples", **knowledge_hub_tab_hrefs(here="samples"))

    cards = [
        (
            "用語解説",
            "1語1ページの詳細記事。定義・試験論点・FAQ・関連用語まで含む標準構成。",
            "../g-writing-sample.html",
            "g-writing-sample",
        ),
        (
            "比較・整理表",
            "2〜3項目の差分を compare_rows の表で横並びに整理する記事。",
            "../compare/c-writing-sample.html",
            "c-writing-sample",
        ),
        (
            "数値・期限早見表",
            "数字・日数・割合を item_rows で一覧化する記事。",
            "../numbers/n-writing-sample.html",
            "n-writing-sample",
        ),
        (
            "よくある誤答",
            "過去問の引っかけ肢を wrong / correct / trap で整理する記事。",
            "../mistakes/m-writing-sample.html",
            "m-writing-sample",
        ),
        (
            "用語解説（図解差し込み）",
            "diagram_id で HTML 図解を記事内に挿入する見本。建ぺい率 vs 容積率の compare_dual 型。",
            "../g-diagram-sample.html",
            "g-diagram-sample",
        ),
    ]
    card_html = []
    for title, desc, href, slug in cards:
        card_html.append(
            '<article class="knowledge-hub-sample-card">'
            f'<h2><a href="{html.escape(href)}">{html.escape(title)}</a></h2>'
            f"<p>{html.escape(desc)}</p>"
            f'<p class="knowledge-hub-sample-card-meta">'
            f'<code>{html.escape(slug)}.html</code></p>'
            f'<p><a class="knowledge-hub-sample-card-link" href="{html.escape(href)}">サンプルを開く</a></p>'
            "</article>"
        )

    title = f"知識ハブ執筆サンプル｜{brand_name()}（{exam_name()}）"
    lead = (
        "用語解説・比較・早見表・誤答パターンの4種類について、"
        "執筆時の構成・文体・CSV の書き方の見本ページです。"
        "図解差し込みの見本（g-diagram-sample.html）も含みます。"
        "本番記事を追加する前に、レイアウトと情報量の目安として参照してください。"
    )
    doc_note = (
        '<p class="knowledge-hub-sample-doc-note">'
        "執筆ルール・CSV列の意味・記事ネタ例: "
        "<code>docs/knowledge-hub-article-templates.md</code>（リポジトリ内）。"
        "雛形生成: <code>python3 tools/scaffold_knowledge_hub_article.py</code> / "
        "<code>python3 tools/scaffold_glossary_term.py</code>"
        "</p>"
    )

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="知識ハブ4種の執筆サンプルページ一覧。用語・比較・早見・誤答の見本HTML。">
{sample_robots_meta()}
{HEAD_FONTS}
<link rel="stylesheet" href="../../site-pages.css?v={TERMS_INDEX_CSS_VER}">
<link rel="stylesheet" href="../../site-theme.css">
<script>document.documentElement.classList.add("js");</script>
</head>
<body class="{shell_body_class('knowledge-hub-samples-page')}">
{site_page_wrap_open()}
{page_header}
<main class="site-page-main">
  {page_breadcrumb}
  <h1>知識ハブ執筆サンプル</h1>
  <p class="site-page-lead">{html.escape(lead)}</p>
  {tabs_html}
  {doc_note}
  <section class="knowledge-hub-sample-grid" aria-label="執筆サンプル一覧">
    {"".join(card_html)}
  </section>
</main>
{page_footer}
{site_page_wrap_close()}
</body>
</html>
"""


def glossary_entries_for_sample() -> tuple[list[dict], dict[str, str], dict[str, dict]]:
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
    # サンプル用語をエントリ一覧に含めて関連リンク解決
    sample = dict(GLOSSARY_WRITING_SAMPLE)
    if not any(e["term"] == sample["term"] for e in entries):
        entries.append(sample)
    term_lookup = make_term_lookup(entries)
    by_term = {e["term"]: e for e in entries}
    return entries, term_lookup, by_term


def build_all(*, base_url: str = BASE_DEFAULT) -> int:
    term_lookup = glossary_term_lookup()
    glossary_entries = load_glossary_entries(strict=False) if (ROOT / "data" / "glossary_terms.csv").is_file() else []
    guides = load_guide_slugs()
    count = 0

    # 比較サンプル
    compare_path = ROOT / "terms" / "compare" / COMPARE_WRITING_SAMPLE["slug_file"]
    compare_rel = compare_path.relative_to(ROOT)
    compare_html = build_compare_detail_html(
        COMPARE_WRITING_SAMPLE, compare_rel, base_url, term_lookup, guides, glossary_entries
    )
    banner = sample_banner_html(
        samples_href="../samples/index.html",
        type_href="index.html",
        type_label="比較・整理表",
        doc_href="../../docs/knowledge-hub-article-templates.md",
    )
    compare_path.parent.mkdir(parents=True, exist_ok=True)
    compare_path.write_text(
        patch_writing_sample_page(compare_html, banner), encoding="utf-8"
    )
    count += 1

    # 早見表サンプル
    numbers_entry = dict(NUMBERS_WRITING_SAMPLE)
    numbers_path = ROOT / "terms" / "numbers" / numbers_entry["slug_file"]
    numbers_rel = numbers_path.relative_to(ROOT)
    numbers_html = build_detail_html(
        NUMBERS_SPEC,
        numbers_entry,
        numbers_rel,
        base_url,
        term_lookup,
        guides,
        glossary_entries,
        matrix_html_fn=numbers_matrix_table_html,
    )
    banner = sample_banner_html(
        samples_href="../samples/index.html",
        type_href="index.html",
        type_label="数値・期限早見表",
        doc_href="../../docs/knowledge-hub-article-templates.md",
    )
    numbers_path.parent.mkdir(parents=True, exist_ok=True)
    numbers_path.write_text(
        patch_writing_sample_page(numbers_html, banner), encoding="utf-8"
    )
    count += 1

    # 誤答サンプル
    mistakes_entry = dict(MISTAKES_WRITING_SAMPLE)
    mistakes_path = ROOT / "terms" / "mistakes" / mistakes_entry["slug_file"]
    mistakes_rel = mistakes_path.relative_to(ROOT)
    mistakes_html = build_detail_html(
        MISTAKES_SPEC,
        mistakes_entry,
        mistakes_rel,
        base_url,
        term_lookup,
        guides,
        glossary_entries,
        matrix_html_fn=mistakes_matrix_table_html,
    )
    banner = sample_banner_html(
        samples_href="../samples/index.html",
        type_href="index.html",
        type_label="よくある誤答",
        doc_href="../../docs/knowledge-hub-article-templates.md",
    )
    mistakes_path.parent.mkdir(parents=True, exist_ok=True)
    mistakes_path.write_text(
        patch_writing_sample_page(mistakes_html, banner), encoding="utf-8"
    )
    count += 1

    # 用語解説サンプル
    entries, gl_lookup, by_term = glossary_entries_for_sample()
    sample_entry = dict(GLOSSARY_WRITING_SAMPLE)
    glossary_path = ROOT / "terms" / sample_entry["slug_file"]
    glossary_rel = glossary_path.relative_to(ROOT)
    term_kwargs: dict = {}
    import inspect

    if "by_term" in inspect.signature(build_term_html).parameters:
        term_kwargs["by_term"] = by_term or {sample_entry["term"]: sample_entry}
    glossary_html = build_term_html(
        sample_entry,
        glossary_rel,
        base_url,
        gl_lookup or term_lookup,
        entries or [sample_entry],
        guides,
        **term_kwargs,
    )
    banner = sample_banner_html(
        samples_href="samples/index.html",
        type_href="index.html",
        type_label="用語解説",
        doc_href="../docs/knowledge-hub-article-templates.md",
    )
    glossary_path.write_text(
        patch_writing_sample_page(glossary_html, banner), encoding="utf-8"
    )
    count += 1

    # サンプル一覧
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    (SAMPLES_DIR / "index.html").write_text(build_samples_index(base_url), encoding="utf-8")
    count += 1

    print(f"Wrote {count} knowledge hub writing sample pages (including terms/samples/index.html)")
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
