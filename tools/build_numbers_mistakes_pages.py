#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/numbers.csv / data/mistakes.csv から terms/numbers/ と terms/mistakes/ を生成する。
"""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_glossary_pages import (  # noqa: E402
    GLOSSARY_CSV,
    HEAD_FONTS,
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
    multi_paragraph_html,
    norm,
    ordered_term_categories,
    parse_term_tags,
    public_url,
    rel_css,
    rel_theme_css,
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
    breadcrumb_html,
    shell_body_class,
    site_page_footer,
    site_page_header,
    site_page_wrap_close,
    site_page_wrap_open,
)
from tools.knowledge_hub_tabs import knowledge_hub_tab_hrefs, knowledge_hub_tabs_html  # noqa: E402
from tools.seo_utils import content_date_from_row, meta_updated_html  # noqa: E402
from tools.site_config import brand_name, clean_origin, exam_name  # noqa: E402

BASE_DEFAULT = clean_origin()
HUB_INDEX_JS_VER = "20260527-knowledge-hub-index"


@dataclass(frozen=True)
class HubSpec:
    hub_id: str
    csv_path: Path
    out_dir: Path
    slug_prefix: str
    glob_pattern: str
    index_body_class: str
    article_body_class: str
    hub_label: str
    index_col1: str
    index_col3: str
    index_detail_field: str
    search_placeholder: str
    js_prefix: str
    table_section_title: str
    matrix_table_class: str
    index_panel_class: str
    index_table_class: str
    data_total_attr: str
    lead: str
    index_desc: str
    index_list_desc: str
    empty_title: str
    note_html: str
    tabs_current: str
    tabs_hrefs: dict[str, str]
    breadcrumb_label: str


def hub_slug(title: str, used: dict[str, str], *, prefix: str) -> str:
    base = title.strip()
    h = hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]
    s = f"{prefix}{h}"
    if s not in used:
        used[s] = base
        return s
    n = 2
    while True:
        cand = f"{prefix}{h}-{n}"
        if cand not in used:
            used[cand] = base
            return cand
        n += 1


def parse_json_rows(raw: str, *, line: int, field: str) -> list[dict]:
    text = norm(raw)
    if not text:
        raise ValueError(f"line {line}: {field} が空です")
    try:
        rows = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"line {line}: {field} の JSON が不正です: {exc}") from exc
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"line {line}: {field} は空でない配列にしてください")
    return rows


def parse_numbers_rows(raw: str, *, line: int) -> list[dict]:
    rows = parse_json_rows(raw, line=line, field="item_rows")
    out: list[dict] = []
    for i, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"line {line}: item_rows[{i - 1}] はオブジェクトにしてください")
        item = norm(row.get("item"))
        value = norm(row.get("value"))
        note = norm(row.get("note"))
        if not item or not value:
            raise ValueError(f"line {line}: item_rows[{i - 1}] に item/value が必要です")
        out.append({"item": item, "value": value, "note": note})
    return out


def parse_mistakes_rows(raw: str, *, line: int) -> list[dict]:
    rows = parse_json_rows(raw, line=line, field="pattern_rows")
    out: list[dict] = []
    for i, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"line {line}: pattern_rows[{i - 1}] はオブジェクトにしてください")
        topic = norm(row.get("topic"))
        wrong = norm(row.get("wrong"))
        correct = norm(row.get("correct"))
        trap = norm(row.get("trap"))
        if not topic or not wrong or not correct:
            raise ValueError(f"line {line}: pattern_rows[{i - 1}] に topic/wrong/correct が必要です")
        out.append({"topic": topic, "wrong": wrong, "correct": correct, "trap": trap})
    return out


def load_hub_rows(spec: HubSpec, *, row_parser: Callable[[str, int], list[dict]]) -> list[dict]:
    if not spec.csv_path.is_file():
        raise FileNotFoundError(str(spec.csv_path))
    text = spec.csv_path.read_text(encoding="utf-8-sig")
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
            slug_file = hub_slug(title, used, prefix=spec.slug_prefix) + ".html"
        detail_rows = row_parser(row.get("item_rows") or row.get("pattern_rows") or "", line=i)
        entries.append(
            {
                "title": title,
                "category": norm(row.get("category")),
                "tags": norm(row.get("tags")),
                "summary": norm(row.get("summary")),
                spec.index_detail_field: norm(row.get(spec.index_detail_field)),
                "detail_rows": detail_rows,
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


def hub_index_href(spec: HubSpec, slug_file: str) -> str:
    rel = spec.out_dir.relative_to(ROOT)
    return f"/{rel.as_posix()}/{slug_file.lstrip('/')}"


def hub_index_item_dict(spec: HubSpec, entry: dict) -> dict:
    tags = parse_term_tags(entry.get("tags") or "")
    detail = entry.get(spec.index_detail_field) or entry.get("summary") or ""
    search_bits = [entry["title"], entry.get("category") or "", entry.get("summary") or "", detail, *tags]
    return {
        "title": entry["title"],
        "category": entry.get("category") or "",
        "tags": tags,
        "summary": entry.get("summary") or "",
        "subjects": detail,
        "href": hub_index_href(spec, entry["slug_file"]),
        "search": " ".join(x for x in search_bits if x),
    }


def numbers_matrix_table_html(rows: list[dict], *, note_html: str) -> str:
    body = "".join(
        "<tr>"
        f'<th scope="row">{html.escape(r["item"])}</th>'
        f'<td>{html.escape(r["value"])}</td>'
        f'<td>{html.escape(r.get("note") or "")}</td>'
        "</tr>"
        for r in rows
    )
    return (
        '<table class="seo-info-table numbers-matrix-table">'
        '<thead><tr><th scope="col">項目</th><th scope="col">数値・期限</th><th scope="col">補足</th></tr></thead>'
        f"<tbody>{body}</tbody></table>{note_html}"
    )


def mistakes_matrix_table_html(rows: list[dict], *, note_html: str) -> str:
    body = "".join(
        "<tr>"
        f'<th scope="row">{html.escape(r["topic"])}</th>'
        f'<td>{html.escape(r["wrong"])}</td>'
        f'<td>{html.escape(r["correct"])}</td>'
        f'<td>{html.escape(r.get("trap") or "")}</td>'
        "</tr>"
        for r in rows
    )
    return (
        '<table class="seo-info-table mistakes-matrix-table">'
        '<thead><tr><th scope="col">論点</th><th scope="col">誤答例</th><th scope="col">正解</th>'
        '<th scope="col">引っかけポイント</th></tr></thead>'
        f"<tbody>{body}</tbody></table>{note_html}"
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
        '<div class="related-box" aria-labelledby="hub-related-title">'
        '<div id="hub-related-title" class="related-box-title">関連用語</div>'
        f'<div class="related-links term-related-links">{"".join(items)}</div></div>'
    )


def render_index_tbody(spec: HubSpec, entries: list[dict]) -> str:
    items = sorted(entries, key=lambda e: (e.get("category") or "", e.get("title") or ""))
    rows: list[str] = []
    for item in items:
        href = html.escape(hub_index_href(spec, item["slug_file"]))
        href_attr = f' data-entry-href="{href}"'
        detail = html.escape(item.get(spec.index_detail_field) or item.get("summary") or "")
        rows.append(
            f'<tr class="terms-idx-table-row {spec.index_table_class}-row">'
            f'<td class="terms-idx-td-term {spec.index_table_class}-td-title" data-label="{html.escape(spec.index_col1)}"{href_attr} tabindex="0">'
            f'<div class="terms-idx-term-cell"><a href="{href}">{html.escape(item["title"])}</a></div></td>'
            f'<td class="terms-idx-td-cat" data-label="分野"{href_attr}>{html.escape(item.get("category") or "")}</td>'
            f'<td class="terms-idx-td-snippet {spec.index_table_class}-td-detail" data-label="{html.escape(spec.index_col3)}"{href_attr}>{detail}</td>'
            "</tr>"
        )
    return "\n".join(rows)


def build_detail_html(
    spec: HubSpec,
    entry: dict,
    rel_path: Path,
    base_url: str,
    term_lookup: dict[str, str],
    guides: list[dict[str, str]],
    *,
    matrix_html_fn: Callable[[list[dict], str], str],
) -> str:
    title_text = entry["title"]
    category = entry.get("category") or ""
    summary = entry.get("summary") or ""
    detail_line = entry.get(spec.index_detail_field) or ""
    article_title = entry.get("article_title") or f"{title_text}｜{exam_name()}"
    article_lead = entry.get("article_lead") or summary
    exam_points = entry.get("exam_points") or ""
    common_mistakes = entry.get("common_mistakes") or ""
    memory_tip = entry.get("memory_tip") or ""
    related = entry.get("related_terms") or ""

    page_title = f"{article_title}｜{brand_name()}"
    desc = meta_description(f"{title_text}を整理。{exam_name()}向けに{summary or '試験対策の要点を解説します。'}")
    canonical = public_url(base_url, f"{spec.out_dir.relative_to(ROOT).as_posix()}/{entry['slug_file']}")
    updated = content_date_from_row(entry)

    matrix_html = matrix_html_fn(entry["detail_rows"], note_html=spec.note_html)
    points_html = semicolon_list_html(exam_points)
    mistakes_html = semicolon_field_html(common_mistakes) or (
        f"<p>{html.escape(common_mistakes)}</p>" if common_mistakes else ""
    )
    memory_html = (
        f"<blockquote><p>{html.escape(memory_tip)}</p></blockquote>" if memory_tip else ""
    )

    fallback_faq = faq_items_for_term(title_text, summary, summary, exam_points or summary)
    faq_items = custom_faq_items(entry, fallback_faq)
    faq_html = faq_section_html(faq_items)

    page_header = site_page_header(rel_path, current="terms")
    page_footer = site_page_footer(rel_path, current="terms")
    hub_index_rel = f"{spec.out_dir.relative_to(ROOT).as_posix()}/index.html"
    page_breadcrumb = hub_detail_breadcrumb(
        rel_path,
        hub_index_label=spec.breadcrumb_label,
        title=title_text,
        category=category,
    )
    tabs_html = knowledge_hub_tabs_html(current=spec.tabs_current, **knowledge_hub_tab_hrefs(here=spec.tabs_current))
    rel_section = related_terms_links_html(related, term_lookup)

    info_rows = [
        ("対象試験", exam_name()),
        ("分野", category),
        (spec.index_col3, detail_line),
    ]
    info_table = (
        '<section class="seo-article-section" aria-labelledby="hub-info-title">'
        '<h2 id="hub-info-title">記事の基本情報</h2>'
        '<table class="seo-info-table"><tbody>'
        + "".join(
            f"<tr><th>{html.escape(k)}</th><td>{html.escape(v)}</td></tr>" for k, v in info_rows if v
        )
        + "</tbody></table></section>"
    )

    extra_terms = [detail_line] if detail_line else []
    if spec.hub_id == "numbers":
        extra_terms.extend(r.get("item") or "" for r in entry["detail_rows"][:5])
    elif spec.hub_id == "mistakes":
        extra_terms.extend(r.get("topic") or "" for r in entry["detail_rows"][:5])

    content_sections_html, body_toc = build_numbered_sections(
        [
            ("matrix", spec.table_section_title, matrix_html),
            ("points", "試験で押さえるポイント", points_html),
            ("mistakes", "よくある誤解・注意点", mistakes_html),
            ("memory", "覚え方・整理のコツ", memory_html),
        ]
    )
    past_hits = find_past_questions_for_hub(
        title=title_text,
        related_terms=related,
        extra_terms=extra_terms,
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
    action_html = seo_action_box_html(subject=title_text, hub_label=spec.hub_label)
    official_html = official_info_html(subject=title_text)
    guide_links = hub_guide_links(category, guides)
    next_links = hub_next_links_html(
        rel_path,
        hub_type=spec.hub_id,
        hub_index_label=spec.breadcrumb_label,
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
        toc_items.append(("hub-related-title", "関連用語"))
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
            hub_index_name=spec.breadcrumb_label,
            hub_index_url=hub_index_rel,
            title=title_text,
            canonical=canonical,
            category=category,
            field_hub=field_hub_slug(category) if category and field_hub_page_exists(category) else "",
        ),
        faq_items=faq_items or None,
    )
    hub_short = spec.hub_label[:2]
    meta_line = hub_meta_line(hub_short=hub_short, category=category)

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
<link rel="stylesheet" href="{html.escape(rel_css(rel_path))}">
<link rel="stylesheet" href="{html.escape(rel_theme_css(rel_path))}">
</head>
<body class="{shell_body_class(spec.article_body_class)}">
{site_page_wrap_open()}
{page_header}
<main class="seo-article-main">
  {page_breadcrumb}
  {tabs_html}
  <article class="seo-article-card article-body">
    <div class="article-meta">
      <span class="meta-category">{html.escape(spec.hub_label)}</span>
      {meta_updated_html(updated)}
      <span class="meta-updated">{meta_line} · <span>{html.escape(detail_line)}</span></span>
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


def build_index_html(spec: HubSpec, entries: list[dict], base_url: str) -> str:
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
                    "item": public_url(base_url, f"{spec.out_dir.relative_to(ROOT).as_posix()}/{e['slug_file']}"),
                }
            )
            pos += 1

    ld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": f"{exam_name()} {spec.hub_label}一覧",
        "description": spec.index_desc,
        "numberOfItems": n_items,
        "itemListElement": list_items_ld,
    }

    json_data = json.dumps([hub_index_item_dict(spec, e) for e in entries], ensure_ascii=False)
    tbody_html = render_index_tbody(spec, entries)
    idx_rel = Path(spec.out_dir.relative_to(ROOT)) / "index.html"
    page_header = site_page_header(idx_rel, current="terms", wide=True)
    page_footer = site_page_footer(idx_rel, current="terms", wide=True)
    page_breadcrumb = breadcrumb_html(idx_rel, [("トップ", "index.html"), (spec.breadcrumb_label, None)])
    tabs_html = knowledge_hub_tabs_html(current=spec.tabs_current, **knowledge_hub_tab_hrefs(here=spec.tabs_current))

    canonical = public_url(base_url, idx_rel.as_posix())
    title = f"{spec.hub_label}｜{brand_name()}（{exam_name()}）"

    seo_links = []
    for e in sorted(entries, key=lambda x: (x.get("category") or "", x["title"])):
        href = hub_index_href(spec, e["slug_file"])
        seo_links.append(f'<li><a href="{html.escape(href)}">{html.escape(e["title"])}</a></li>')
    seo_html = '<ul class="terms-idx-seo-list">\n    ' + "\n    ".join(seo_links) + "\n  </ul>"

    prefix = spec.js_prefix
    hub_base = f"/{spec.out_dir.relative_to(ROOT).as_posix()}/"

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(spec.index_desc)}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{html.escape(canonical)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{html.escape(canonical)}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(spec.index_desc)}">
<meta property="og:locale" content="ja_JP">
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=2)}
</script>
{HEAD_FONTS}
<link rel="stylesheet" href="../../site-pages.css?v={TERMS_INDEX_CSS_VER}">
<link rel="stylesheet" href="../../site-theme.css">
<script>document.documentElement.classList.add("js");</script>
</head>
<body class="{shell_body_class(spec.index_body_class)}" {spec.data_total_attr}="{n_items}" data-hub-index-prefix="{prefix}" data-hub-base="{html.escape(hub_base, quote=True)}" data-hub-col1="{html.escape(spec.index_col1, quote=True)}" data-hub-col3="{html.escape(spec.index_col3, quote=True)}">
{site_page_wrap_open()}
{page_header}
<main class="site-page-main">
  {page_breadcrumb}
  <h1>{html.escape(spec.hub_label)}</h1>
  <p class="site-page-lead">{html.escape(spec.lead)}</p>
  {tabs_html}
  <section class="terms-index-panel {spec.index_panel_class}" aria-labelledby="{prefix}-heading">
    <div class="terms-index-head">
      <div>
        <h2 id="{prefix}-heading">{html.escape(spec.breadcrumb_label)}一覧</h2>
        <p>全{n_items}件・{n_cats}分野。キーワード検索と分野で絞り込めます。</p>
      </div>
    </div>
    <div class="terms-index-tools">
      <div class="terms-index-tools-primary">
      <label class="terms-index-search" for="{prefix}-q">
        <span class="u-visually-hidden">{html.escape(spec.hub_label)}検索</span>
        <input id="{prefix}-q" type="search" inputmode="search" autocomplete="off" placeholder="{html.escape(spec.search_placeholder, quote=True)}">
      </label>
      <span id="{prefix}-hit" class="terms-index-hit" aria-live="polite">{n_items} / {n_items} 件</span>
      </div>
      <div class="terms-idx-chips" aria-label="分野フィルタ">
{chips_html}
      </div>
      <button type="button" class="terms-idx-reset hide" id="{prefix}-reset">条件をクリア</button>
      <div class="terms-idx-active-filters hide" id="{prefix}-active-filters" aria-live="polite"></div>
    </div>
    <div class="terms-idx-empty-panel hide" id="{prefix}-empty" role="status" hidden>
      <p class="terms-idx-empty-title">{html.escape(spec.empty_title)}</p>
      <p class="terms-idx-empty-hint">検索語を短くするか、分野を「すべて」に戻してお試しください。</p>
      <button type="button" class="terms-idx-reset" id="{prefix}-empty-reset">条件をクリア</button>
    </div>
    <div class="terms-idx-layout" aria-label="{html.escape(spec.breadcrumb_label)}一覧">
      <div class="terms-idx-table-wrap">
        <table class="terms-idx-table {spec.index_table_class}">
          <thead><tr>
            <th scope="col" class="terms-idx-th-term">{html.escape(spec.index_col1)}</th>
            <th scope="col" class="terms-idx-th-cat">分野</th>
            <th scope="col" class="terms-idx-th-def">{html.escape(spec.index_col3)}</th>
          </tr></thead>
          <tbody id="{prefix}-flat-body">
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
<button type="button" class="terms-idx-top {prefix}-top" id="{prefix}-top" aria-label="ページ上部へ">↑</button>
<script type="application/json" id="{prefix}-data">{json_data}</script>
<script defer src="../../site-knowledge-hub-index.js?v={HUB_INDEX_JS_VER}"></script>
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


NUMBERS_SPEC = HubSpec(
    hub_id="numbers",
    csv_path=ROOT / "data" / "numbers.csv",
    out_dir=ROOT / "terms" / "numbers",
    slug_prefix="n-",
    glob_pattern="n-*.html",
    index_body_class="numbers-index-page",
    article_body_class="numbers-article-page",
    hub_label="数値・期限早見表",
    index_col1="項目",
    index_col3="代表的な数値・期限",
    index_detail_field="highlight",
    search_placeholder="例：8日、20%、30年、18歳…",
    js_prefix="numbers-idx",
    table_section_title="早見表",
    matrix_table_class="numbers-matrix-table",
    index_panel_class="numbers-index-panel",
    index_table_class="numbers-idx-table",
    data_total_attr="data-numbers-total",
    lead="試験で問われる期間・割合・年数などの数字を、一覧表で素早く確認できます。用語解説とあわせて読むと定義と数値の両方を押さえられます。",
    index_desc="期間・割合・人数など、試験頻出の数字を早見表で整理した索引です。",
    index_list_desc="数値・期限早見一覧",
    empty_title="条件に一致する早見表がありません",
    note_html='<p class="term-compare-note">数値・手続の正誤は演習と公式テキストで必ず確認してください。</p>',
    tabs_current="numbers",
    tabs_hrefs={
        "terms_href": "../index.html",
        "compare_href": "../compare/index.html",
        "numbers_href": "index.html",
        "mistakes_href": "../mistakes/index.html",
    },
    breadcrumb_label="数値・期限早見表",
)

MISTAKES_SPEC = HubSpec(
    hub_id="mistakes",
    csv_path=ROOT / "data" / "mistakes.csv",
    out_dir=ROOT / "terms" / "mistakes",
    slug_prefix="m-",
    glob_pattern="m-*.html",
    index_body_class="mistakes-index-page",
    article_body_class="mistakes-article-page",
    hub_label="よくある誤答",
    index_col1="パターン",
    index_col3="混同しやすい点",
    index_detail_field="confusion_point",
    search_placeholder="例：35条、媒介、先取特権、税率…",
    js_prefix="mistakes-idx",
    table_section_title="誤答パターン一覧",
    matrix_table_class="mistakes-matrix-table",
    index_panel_class="mistakes-index-panel",
    index_table_class="mistakes-idx-table",
    data_total_attr="data-mistakes-total",
    lead="過去問で繰り返し出る「紛らわしい肢」の典型パターンを整理しています。正解と誤答の差分を表で確認できます。",
    index_desc="混同しやすい制度・用語・数字の誤答パターンを整理した索引です。",
    index_list_desc="誤答パターン一覧",
    empty_title="条件に一致するパターンがありません",
    note_html='<p class="term-compare-note">肢の正誤は演習と公式テキストで必ず確認してください。</p>',
    tabs_current="mistakes",
    tabs_hrefs={
        "terms_href": "../index.html",
        "compare_href": "../compare/index.html",
        "numbers_href": "../numbers/index.html",
        "mistakes_href": "index.html",
    },
    breadcrumb_label="よくある誤答",
)


def build_hub(
    spec: HubSpec,
    *,
    base_url: str,
    row_parser: Callable[[str, int], list[dict]],
    matrix_html_fn: Callable[[list[dict], str], str],
    guides: list[dict[str, str]],
) -> int:
    entries = load_hub_rows(spec, row_parser=row_parser)
    term_lookup = glossary_term_lookup()

    spec.out_dir.mkdir(parents=True, exist_ok=True)
    for stale in spec.out_dir.glob(spec.glob_pattern):
        stale.unlink()

    for entry in entries:
        out_file = spec.out_dir / entry["slug_file"]
        rel_path = out_file.relative_to(ROOT)
        out_file.write_text(
            build_detail_html(
                spec,
                entry,
                rel_path,
                base_url,
                term_lookup,
                guides,
                matrix_html_fn=matrix_html_fn,
            ),
            encoding="utf-8",
        )

    (spec.out_dir / "index.html").write_text(build_index_html(spec, entries, base_url), encoding="utf-8")
    print(f"Wrote {len(entries)} pages under {spec.out_dir}")
    print(f"Wrote {spec.out_dir / 'index.html'}")
    return len(entries)


def build_all(*, base_url: str = BASE_DEFAULT) -> int:
    guides = load_guide_slugs()
    n1 = build_hub(
        NUMBERS_SPEC,
        base_url=base_url,
        row_parser=parse_numbers_rows,
        matrix_html_fn=numbers_matrix_table_html,
        guides=guides,
    )
    n2 = build_hub(
        MISTAKES_SPEC,
        base_url=base_url,
        row_parser=parse_mistakes_rows,
        matrix_html_fn=mistakes_matrix_table_html,
        guides=guides,
    )
    return n1 + n2


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
