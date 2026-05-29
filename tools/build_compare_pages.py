#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/comparisons.csv から terms/compare/index.html と terms/compare/c-*.html を生成する。

用語一覧（terms/index.html）とは別 URL。タブで横断（tools/knowledge_hub_tabs.py）。
"""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_glossary_pages import (  # noqa: E402
    HEAD_FONTS,
    GLOSSARY_CSV,
    TERMS_INDEX_CSS_VER,
    custom_faq_items,
    faq_items_for_term,
    faq_section_html,
    field_hub_slug,
    glossary_field_id,
    load_glossary_rows,
    load_guide_slugs,
    make_term_lookup,
    slug_file_for_glossary_row,
    meta_description,
    norm,
    ordered_term_categories,
    parse_term_tags,
    public_url,
    rel_css,
    rel_theme_css,
    multi_paragraph_html,
    semicolon_field_html,
    semicolon_list_html,
    split_semicolon,
    term_slug,
)
from tools.glossary_past_questions import past_questions_section_html  # noqa: E402
from tools.knowledge_hub_seo import (
    field_hub_page_exists,  # noqa: E402
    build_numbered_sections,
    find_past_questions_for_hub,
    hub_article_json_ld,
    hub_breadcrumb_json_ld,
    hub_detail_breadcrumb,
    hub_guide_links,
    hub_meta_line,
    hub_next_links_html,
    official_info_html,
    seo_action_box_html,
    seo_quality_panel_html,
    seo_toc_html,
)
from tools.html_footer import (  # noqa: E402
    ROBOTS_INDEX_FOLLOW,
    analytics_snippet,
    breadcrumb_html,
    shell_body_class,
    site_page_footer,
    site_page_header,
    site_page_wrap_close,
    site_page_wrap_open,
)
from tools.knowledge_hub_tabs import knowledge_hub_tab_hrefs, knowledge_hub_tabs_html  # noqa: E402
from tools.seo_utils import content_date_from_row, meta_updated_html  # noqa: E402
from tools.hub_collapse_angles import redirect_page_html  # noqa: E402
from tools.site_config import brand_name, exam_name, clean_origin  # noqa: E402

COMPARE_CSV = ROOT / "data" / "comparisons.csv"
COMPARE_DIR = ROOT / "terms" / "compare"
BASE_DEFAULT = clean_origin()

COMPARE_INDEX_JS_VER = "20260527-compare-index"
COMPARE_INDEX_SEARCH_PLACEHOLDER = "例：過去問、模擬試験、公式情報…"
PRESERVED_COMPARE_GLOB = "c-*.html"


def compare_slug(title: str, used: dict[str, str]) -> str:
    base = title.strip()
    h = hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]
    s = f"c-{h}"
    if s not in used:
        used[s] = base
        return s
    n = 2
    while True:
        cand = f"c-{h}-{n}"
        if cand not in used:
            used[cand] = base
            return cand
        n += 1


def compare_index_href(slug_file: str) -> str:
    return f"/terms/compare/{slug_file.lstrip('/')}"


def parse_compare_rows(raw: str, *, line: int) -> list[dict]:
    text = norm(raw)
    if not text:
        raise ValueError(f"line {line}: compare_rows が空です")
    try:
        rows = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"line {line}: compare_rows の JSON が不正です: {exc}") from exc
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"line {line}: compare_rows は空でない配列にしてください")
    out: list[dict] = []
    for i, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"line {line}: compare_rows[{i - 1}] はオブジェクトにしてください")
        axis = norm(row.get("axis"))
        cols = row.get("cols")
        if not axis:
            raise ValueError(f"line {line}: compare_rows[{i - 1}].axis が空です")
        if not isinstance(cols, list) or len(cols) < 2:
            raise ValueError(f"line {line}: compare_rows[{i - 1}].cols は2件以上必要です")
        out.append({"axis": axis, "cols": [norm(c) for c in cols]})
    return out


def load_compare_rows() -> list[dict]:
    if not COMPARE_CSV.is_file():
        raise FileNotFoundError(str(COMPARE_CSV))
    text = COMPARE_CSV.read_text(encoding="utf-8-sig")
    used: dict[str, str] = {}
    entries: list[dict] = []
    for i, row in enumerate(csv.DictReader(io.StringIO(text)), start=2):
        title = norm(row.get("title"))
        if not title:
            raise ValueError(f"line {i}: title が空です")
        legacy_slug = norm(row.get("slug"))
        if legacy_slug:
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", legacy_slug):
                raise ValueError(f"line {i}: slug は半角英数字とハイフンのみ: {legacy_slug!r}")
            slug_file = f"{legacy_slug}.html"
            if slug_file in used:
                raise ValueError(f"line {i}: slug が重複しています: {legacy_slug}")
            used[slug_file] = title
        else:
            slug_file = compare_slug(title, used) + ".html"
        col_labels = split_semicolon(norm(row.get("col_labels")))
        if len(col_labels) < 2:
            raise ValueError(f"line {i}: col_labels は2件以上必要です")
        compare_rows = parse_compare_rows(row.get("compare_rows") or "", line=i)
        for cr in compare_rows:
            if len(cr["cols"]) != len(col_labels):
                raise ValueError(
                    f"line {i}: compare_rows の列数が col_labels と一致しません "
                    f"({len(cr['cols'])} vs {len(col_labels)})"
                )
        entries.append(
            {
                "title": title,
                "category": norm(row.get("category")),
                "tags": norm(row.get("tags")),
                "summary": norm(row.get("summary")),
                "col_labels": col_labels,
                "compare_rows": compare_rows,
                "article_title": norm(row.get("article_title")),
                "article_lead": norm(row.get("article_lead")),
                "exam_points": norm(row.get("exam_points")),
                "common_mistakes": norm(row.get("common_mistakes")),
                "memory_tip": norm(row.get("memory_tip")),
                "related_terms": norm(row.get("related_terms")),
                "faq_1_question": norm(row.get("faq_1_question")),
                "faq_1_answer": norm(row.get("faq_1_answer")),
                "faq_2_question": norm(row.get("faq_2_question")),
                "faq_2_answer": norm(row.get("faq_2_answer")),
                "faq_3_question": norm(row.get("faq_3_question")),
                "faq_3_answer": norm(row.get("faq_3_answer")),
                "faq_4_question": norm(row.get("faq_4_question")),
                "faq_4_answer": norm(row.get("faq_4_answer")),
                "slug_file": slug_file,
                "fact_checked_at": norm(row.get("fact_checked_at")),
                "last_reviewed_at": norm(row.get("last_reviewed_at")),
                "source_checked_at": norm(row.get("source_checked_at")),
            }
        )
    return entries


def compare_index_item_dict(entry: dict) -> dict:
    tags = parse_term_tags(entry.get("tags") or "")
    subjects = " / ".join(entry.get("col_labels") or [])
    search_bits = [
        entry["title"],
        entry.get("category") or "",
        entry.get("summary") or "",
        subjects,
        *tags,
    ]
    return {
        "title": entry["title"],
        "category": entry.get("category") or "",
        "tags": tags,
        "summary": entry.get("summary") or "",
        "subjects": subjects,
        "href": compare_index_href(entry["slug_file"]),
        "search": " ".join(x for x in search_bits if x),
    }


def render_compare_index_tbody(entries: list[dict]) -> str:
    items = sorted(entries, key=lambda e: (e.get("category") or "", e.get("title") or ""))
    rows: list[str] = []
    for item in items:
        href = html.escape(compare_index_href(item["slug_file"]))
        href_attr = f' data-entry-href="{href}"'
        summary = html.escape(item.get("summary") or "")
        rows.append(
            "<tr class=\"terms-idx-table-row compare-idx-table-row\">"
            f'<td class="terms-idx-td-term compare-idx-td-title" data-label="項目"{href_attr} tabindex="0">'
            f'<div class="terms-idx-term-cell"><a href="{href}">{html.escape(item["title"])}</a>'
            f"</div></td>"
            f'<td class="terms-idx-td-cat" data-label="分野"{href_attr}>'
            f'{html.escape(item.get("category") or "")}</td>'
            f'<td class="terms-idx-td-snippet compare-idx-td-summary" data-label="概要"{href_attr}>'
            f"{summary}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def compare_matrix_table_html(col_labels: list[str], compare_rows: list[dict]) -> str:
    head = "<th scope=\"col\">比較軸</th>" + "".join(
        f'<th scope="col">{html.escape(label)}</th>' for label in col_labels
    )
    body_rows: list[str] = []
    for row in compare_rows:
        cells = "".join(f"<td>{html.escape(c)}</td>" for c in row["cols"])
        body_rows.append(
            f'<tr><th scope="row">{html.escape(row["axis"])}</th>{cells}</tr>'
        )
    return (
        '<table class="seo-info-table compare-matrix-table">'
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody></table>"
        '<p class="term-compare-note">数値・手続の正誤は演習と公式テキストで必ず確認してください。</p>'
    )


def related_terms_links_html(related: str, term_lookup: dict[str, str]) -> str:
    items: list[str] = []
    seen: set[str] = set()
    for label in split_semicolon(related):
        href = term_lookup.get(label)
        if href and href not in seen:
            seen.add(href)
            items.append(
                f'<a class="related-link" href="../{html.escape(href)}">{html.escape(label)}</a>'
            )
    if not items:
        return ""
    return (
        '<div class="related-box" aria-labelledby="compare-related-title">'
        '<div id="compare-related-title" class="related-box-title">関連用語</div>'
        f'<div class="related-links term-related-links">{"".join(items)}</div></div>'
    )


def build_compare_detail_html(
    entry: dict,
    rel_path: Path,
    base_url: str,
    term_lookup: dict[str, str],
    guides: list[dict[str, str]],
) -> str:
    title_text = entry["title"]
    category = entry.get("category") or ""
    summary = entry.get("summary") or ""
    col_labels = entry["col_labels"]
    compare_rows = entry["compare_rows"]
    article_title = entry.get("article_title") or f"{title_text}｜{exam_name()}"
    article_lead = entry.get("article_lead") or summary
    exam_points = entry.get("exam_points") or ""
    common_mistakes = entry.get("common_mistakes") or ""
    memory_tip = entry.get("memory_tip") or ""
    related = entry.get("related_terms") or ""

    page_title = f"{article_title}｜{brand_name()}"
    desc = meta_description(
        f"{title_text}を表で整理。{exam_name()}向けに{summary or '似た概念の使い分けを解説します。'}"
    )
    canonical = public_url(base_url, f"terms/compare/{entry['slug_file']}")
    updated = content_date_from_row(entry)
    css_href = rel_css(rel_path)
    theme_href = rel_theme_css(rel_path)

    matrix_html = compare_matrix_table_html(col_labels, compare_rows)
    points_html = semicolon_list_html(exam_points)
    mistakes_html = semicolon_field_html(common_mistakes) or (
        f"<p>{html.escape(common_mistakes)}</p>" if common_mistakes else ""
    )
    memory_html = (
        f"<blockquote><p>{html.escape(memory_tip)}</p></blockquote>" if memory_tip else ""
    )

    fallback_faq = faq_items_for_term(
        title_text,
        summary,
        summary,
        exam_points or summary,
    )
    faq_items = custom_faq_items(entry, fallback_faq)
    faq_html = faq_section_html(faq_items)

    rel_path_breadcrumb = rel_path
    page_header = site_page_header(rel_path_breadcrumb, current="terms")
    page_footer = site_page_footer(rel_path_breadcrumb, current="terms")
    page_breadcrumb = hub_detail_breadcrumb(
        rel_path_breadcrumb,
        hub_index_label="比較・整理表",
        title=title_text,
        category=category,
    )
    tabs_html = knowledge_hub_tabs_html(current="compare", **knowledge_hub_tab_hrefs(here="compare"))
    rel_section = related_terms_links_html(related, term_lookup)
    subjects_line = " / ".join(col_labels)

    info_rows = [
        ("対象試験", exam_name()),
        ("分野", category),
        ("比較対象", subjects_line),
    ]
    info_table = (
        '<section class="seo-article-section" aria-labelledby="hub-info-title">'
        '<h2 id="hub-info-title">記事の基本情報</h2>'
        '<table class="seo-info-table"><tbody>'
        + "".join(
            f"<tr><th>{html.escape(k)}</th><td>{html.escape(v)}</td></tr>"
            for k, v in info_rows
            if v
        )
        + "</tbody></table></section>"
    )

    content_sections_html, body_toc = build_numbered_sections(
        [
            ("matrix", "比較表", matrix_html),
            ("points", "試験で押さえるポイント", points_html),
            ("mistakes", "よくある誤解・注意点", mistakes_html),
            ("memory", "覚え方・整理のコツ", memory_html),
        ]
    )
    past_hits = find_past_questions_for_hub(
        title=title_text,
        related_terms=related,
        extra_terms=col_labels,
        limit=3,
    )
    past_section = past_questions_section_html(
        past_hits,
        rel_path,
        section_num=len(body_toc) + 1,
    )
    if past_section:
        content_sections_html = f"{content_sections_html}\n    {past_section}" if content_sections_html else past_section
        body_toc.append(("term-past-title", "関連する過去問"))

    faq_section = ""
    if faq_html:
        faq_section = (
            '<section class="seo-article-section" aria-labelledby="hub-sec-faq">'
            f'<h2 id="hub-sec-faq">よくある質問</h2>{faq_html}</section>'
        )

    quality_html = seo_quality_panel_html(updated=updated)
    action_html = seo_action_box_html(subject=title_text, hub_label="比較・整理表")
    official_html = official_info_html(subject=title_text)
    guide_links = hub_guide_links(category, guides)
    next_links = hub_next_links_html(
        rel_path,
        hub_type="compare",
        hub_index_label="比較・整理表",
        category=category,
        guide_links=guide_links,
    )

    toc_items: list[tuple[str, str]] = [
        ("quality-panel-title", "この記事の信頼性について"),
        ("action-box-title", "この記事でできること"),
        *body_toc,
    ]
    if faq_section:
        toc_items.append(("hub-sec-faq", "よくある質問"))
    toc_items.append(("hub-info-title", "記事の基本情報"))
    toc_items.append(("official-info-title", "公式情報の確認"))
    if rel_section:
        toc_items.append(("compare-related-title", "関連用語"))
    toc_items.append(("hub-next-title", "次に確認するページ"))
    toc_html = seo_toc_html(toc_items)

    graph = hub_article_json_ld(
        canonical=canonical,
        page_title=page_title,
        article_title=article_title,
        desc=desc,
        updated=updated,
        breadcrumb_items=hub_breadcrumb_json_ld(
            base_url=base_url,
            hub_index_name="比較・整理表",
            hub_index_url="terms/compare/index.html",
            title=title_text,
            canonical=canonical,
            category=category,
            field_hub=field_hub_slug(category) if category and field_hub_page_exists(category) else "",
        ),
        faq_items=faq_items or None,
    )
    meta_line = hub_meta_line(hub_short="比較", category=category)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(page_title)}</title>
<meta name="description" content="{html.escape(desc)}">
{ROBOTS_INDEX_FOLLOW}
<link rel="canonical" href="{html.escape(canonical)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{html.escape(page_title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="{html.escape(canonical)}">
<meta name="twitter:card" content="summary">
<script type="application/ld+json">
{json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=2)}
</script>
{HEAD_FONTS}
<link rel="stylesheet" href="{html.escape(css_href)}">
<link rel="stylesheet" href="{html.escape(theme_href)}">
</head>
<body class="{shell_body_class('compare-article-page')}">
{site_page_wrap_open()}
{page_header}
<main class="seo-article-main">
  {page_breadcrumb}
  {tabs_html}
  <article class="seo-article-card article-body">
    <div class="article-meta">
      <span class="meta-category">比較・整理表</span>
      {meta_updated_html(updated)}
      <span class="meta-updated">{meta_line} · <span>{html.escape(subjects_line)}</span></span>
    </div>
    <h1 class="article-title">{html.escape(article_title)}</h1>
    {multi_paragraph_html(article_lead)}
    {toc_html}
    {quality_html}
    {action_html}
    {content_sections_html}
    {faq_section}
    {info_table}
    {official_html}
    {rel_section}
    {next_links}
  </article>
</main>
{page_footer}
{site_page_wrap_close()}
</body>
</html>
"""


def build_compare_index(entries: list[dict], base_url: str) -> str:
    by_cat: dict[str, list[dict]] = {}
    for e in entries:
        by_cat.setdefault(e.get("category") or "その他", []).append(e)
    cat_keys = ordered_term_categories(by_cat)

    n_items = len(entries)
    n_cats = len(cat_keys)

    chip_lines = [
        '    <button type="button" class="terms-idx-chip on" data-cat="all">すべて<b>'
        f"{n_items}</b></button>"
    ]
    for cat in cat_keys:
        count = len(by_cat[cat])
        chip_lines.append(
            "    "
            f'<button type="button" class="terms-idx-chip" data-cat="{html.escape(cat, quote=True)}">'
            f"{html.escape(cat)}<b>{count}</b></button>"
        )
    chips_html = "\n".join(chip_lines)

    list_items_ld: list[dict] = []
    pos = 1
    for cat in cat_keys:
        for e in sorted(by_cat[cat], key=lambda x: x["title"]):
            list_items_ld.append(
                {
                    "@type": "ListItem",
                    "position": pos,
                    "name": e["title"],
                    "item": public_url(base_url, f"terms/compare/{e['slug_file']}"),
                }
            )
            pos += 1

    ld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": f"{exam_name()} 比較・整理表一覧",
        "description": "似た制度・用語・演習形式の違いを表で整理した索引です。",
        "numberOfItems": n_items,
        "itemListElement": list_items_ld,
    }

    json_data = json.dumps([compare_index_item_dict(e) for e in entries], ensure_ascii=False)
    tbody_html = render_compare_index_tbody(entries)

    idx_path = Path("terms/compare/index.html")
    page_header = site_page_header(idx_path, current="terms", wide=True)
    page_footer = site_page_footer(idx_path, current="terms", wide=True)
    page_breadcrumb = breadcrumb_html(
        idx_path,
        [("トップ", "index.html"), ("比較・整理表", None)],
    )
    tabs_html = knowledge_hub_tabs_html(current="compare", **knowledge_hub_tab_hrefs(here="compare"))

    canonical = public_url(base_url, "terms/compare/index.html")
    title = f"比較・整理表｜{brand_name()}（{exam_name()}）"
    desc = (
        f"{exam_name()}で混同しやすい制度・用語・演習形式の違いを表で整理。"
        "分野別に検索・絞り込みして、目的の比較ページへ進めます。"
    )
    lead = (
        f"{exam_name()}で押さえたい「似ているが違う」項目を、比較表で横並びに整理しています。"
        "用語解説とあわせて読むと、定義と差分の両方を効率よく確認できます。"
    )

    seo_links = []
    for e in sorted(entries, key=lambda x: (x.get("category") or "", x["title"])):
        href = compare_index_href(e["slug_file"])
        seo_links.append(f'<li><a href="{html.escape(href)}">{html.escape(e["title"])}</a></li>')
    seo_html = '<ul class="terms-idx-seo-list">\n    ' + "\n    ".join(seo_links) + "\n  </ul>"

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{html.escape(canonical)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{html.escape(canonical)}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:locale" content="ja_JP">
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=2)}
</script>
{HEAD_FONTS}
<link rel="stylesheet" href="../../site-pages.css?v={TERMS_INDEX_CSS_VER}">
<link rel="stylesheet" href="../../site-theme.css">
<script>document.documentElement.classList.add("js");</script>
</head>
<body class="{shell_body_class('compare-index-page')}" data-compare-total="{n_items}">
{site_page_wrap_open()}
{page_header}
<main class="site-page-main">
  {page_breadcrumb}
  <h1>比較・整理表</h1>
  <p class="site-page-lead">{html.escape(lead)}</p>
  {tabs_html}
  <section class="terms-index-panel compare-index-panel" aria-labelledby="compare-index-heading">
    <div class="terms-index-head">
      <div>
        <h2 id="compare-index-heading">比較一覧</h2>
        <p>全{n_items}件・{n_cats}分野。キーワード検索と分野で絞り込めます。</p>
      </div>
    </div>
    <div class="terms-index-tools">
      <div class="terms-index-tools-primary">
      <label class="terms-index-search" for="compare-idx-q">
        <span class="u-visually-hidden">比較検索</span>
        <input id="compare-idx-q" type="search" inputmode="search" autocomplete="off" placeholder="{html.escape(COMPARE_INDEX_SEARCH_PLACEHOLDER, quote=True)}">
      </label>
      <span id="compare-idx-hit" class="terms-index-hit" aria-live="polite">{n_items} / {n_items} 件</span>
      </div>
      <div class="terms-idx-chips" aria-label="分野フィルタ">
{chips_html}
      </div>
      <button type="button" class="terms-idx-reset hide" id="compare-idx-reset">条件をクリア</button>
      <div class="terms-idx-active-filters hide" id="compare-idx-active-filters" aria-live="polite"></div>
    </div>
    <div class="terms-idx-empty-panel hide" id="compare-idx-empty" role="status" hidden>
      <p class="terms-idx-empty-title">条件に一致する比較がありません</p>
      <p class="terms-idx-empty-hint">検索語を短くするか、分野を「すべて」に戻してお試しください。</p>
      <button type="button" class="terms-idx-reset" id="compare-idx-empty-reset">条件をクリア</button>
    </div>
    <div class="terms-idx-layout" aria-label="比較一覧">
      <div class="terms-idx-table-wrap">
        <table class="terms-idx-table compare-idx-table">
          <thead><tr>
            <th scope="col" class="terms-idx-th-term">項目</th>
            <th scope="col" class="terms-idx-th-cat">分野</th>
            <th scope="col" class="terms-idx-th-def">概要</th>
          </tr></thead>
          <tbody id="compare-idx-flat-body">
{tbody_html}
          </tbody>
        </table>
      </div>
      <div class="terms-idx-seo-fallback" aria-hidden="true" hidden>
{seo_html}
      </div>
    </div>
  </section>
</main>
{page_footer}
{site_page_wrap_close()}
<button type="button" class="terms-idx-top compare-idx-top" id="compare-idx-top" aria-label="ページ上部へ">↑</button>
<script type="application/json" id="compare-index-data">{json_data}</script>
<script defer src="../../site-compare-index.js?v={COMPARE_INDEX_JS_VER}"></script>
</body>
</html>
"""


def glossary_term_lookup() -> dict[str, str]:
    if not GLOSSARY_CSV.is_file():
        return {}
    rows = load_glossary_rows()
    used_slugs: dict[str, str] = {}
    entries: list[dict] = []
    for row in rows:
        term = norm(row.get("term"))
        if not term:
            continue
        slug_file = slug_file_for_glossary_row(row, used_slugs)
        entries.append({"term": term, "slug_file": slug_file})
    return make_term_lookup(entries)


def load_compare_redirects() -> dict[str, str]:
    raw_path = ROOT / "data" / "hub_redirects.json"
    if not raw_path.is_file():
        return {}
    try:
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    section = raw.get("compare") if isinstance(raw.get("compare"), dict) else {}
    return {str(k): str(v) for k, v in section.items()}


def build_all(*, base_url: str = BASE_DEFAULT) -> int:
    entries = load_compare_rows()
    term_lookup = glossary_term_lookup()
    guides = load_guide_slugs()
    redirects = load_compare_redirects()

    COMPARE_DIR.mkdir(parents=True, exist_ok=True)
    canonical_files = {entry["slug_file"] for entry in entries}
    redirect_files = {f"{old}.html" for old in redirects}

    for stale in COMPARE_DIR.glob("*.html"):
        if stale.name == "index.html":
            continue
        if stale.name in canonical_files or stale.name in redirect_files:
            continue
        stale.unlink()

    for entry in entries:
        out_file = COMPARE_DIR / entry["slug_file"]
        rel_path = out_file.relative_to(ROOT)
        out_file.write_text(
            build_compare_detail_html(entry, rel_path, base_url, term_lookup, guides),
            encoding="utf-8",
        )

    for old_slug, new_slug in redirects.items():
        target = f"{new_slug}.html"
        out_file = COMPARE_DIR / f"{old_slug}.html"
        rel_path = out_file.relative_to(ROOT)
        out_file.write_text(
            redirect_page_html(
                target,
                title=old_slug,
                analytics_html=analytics_snippet(rel_path),
            ),
            encoding="utf-8",
        )

    (COMPARE_DIR / "index.html").write_text(
        build_compare_index(entries, base_url),
        encoding="utf-8",
    )

    print(f"Wrote {len(entries)} compare pages under {COMPARE_DIR}")
    if redirects:
        print(f"Wrote {len(redirects)} compare redirect pages under {COMPARE_DIR}")
    print(f"Wrote {COMPARE_DIR / 'index.html'}")
    return len(entries)


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=BASE_DEFAULT)
    args = ap.parse_args()
    build_all(base_url=args.base_url.rstrip("/"))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)
