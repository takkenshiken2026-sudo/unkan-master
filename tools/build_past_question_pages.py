#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/past_questions.csv から静的問題ページ q/past/... を生成し、
q/index.html・robots.txt を更新する（sitemap は build_sitemap.py）。

解説（テンプレ）:
  - explanation … 必須。従来の1段落も可（自動で「正解の理由」「他の選択肢」「学習のヒント」に展開）
  - explanation_summary … 任意。冒頭の要約
  - explanation_correct … 任意。正解の詳述
  - explanation_choices … 任意。「2:理由;3:理由」または「（2）理由」改行区切り。
    各誤肢は「なぜ正答でないか」「正答肢との対比」を具体的に（「本肢は妥当」だけの1文は不可。
    薄い記述はビルド時に推論で置き換えます）
  - explanation_point … 任意。学習のヒント（未記入時は分野別の定型文）

関連ページ（related_links、セミコロン区切り。未記入時は一覧・同年問・用語・ガイド等を自動補完）:
  - guide:slug:ラベル / term:用語名 / past:2026-2 / qindex / terms / review / practice / field
  - page:path/to.html:ラベル
"""

from __future__ import annotations

import csv
import html
import json
import re
import shutil
import sys
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.q_explanation import build_explanation_html
from tools.q_similar_questions import build_similar_questions_html, load_question_catalog
from tools.html_footer import (
    ROBOTS_INDEX_FOLLOW,
    breadcrumb_html,
    q_hub_links_html,
    q_index_filters_details_html,
    q_index_stats_line,
    q_index_tools_close_html,
    q_index_tools_open_html,
    shell_body_class,
    site_page_footer,
    site_page_header,
    site_page_wrap_close,
    site_page_wrap_open,
    static_footer_block,
    static_site_header,
)
from tools.site_config import brand_name, clean_origin, exam_name

DATA_CSV = ROOT / "data" / "past_questions.csv"
Q_ROOT = ROOT / "q"
BASE_DEFAULT = clean_origin()
HEAD_FONTS = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&display=swap" rel="stylesheet">"""

LABELS = [("ア", "statement_a"), ("イ", "statement_b"), ("ウ", "statement_c"), ("エ", "statement_d")]


def norm(s: str | None) -> str:
    return (s or "").strip()


def parse_correct(raw: str, *, max_choice: int = 5) -> int | str | None:
    """一問一答ビルド等からの互換 API。"""
    from tools.correct_answer_format import (
        is_valid_correct,
        parse_correct_page_value,
    )
    from tools.site_config import extended_correct_answers

    cor_raw = norm(raw)
    cor = parse_correct_page_value(
        cor_raw, extended=extended_correct_answers(), max_choice=max_choice
    )
    if cor is None and extended_correct_answers() and is_valid_correct(
        cor_raw, max_choice=max_choice
    ):
        return cor_raw
    return cor


def build_stem_html(row: dict) -> str:
    parts: list[str] = []
    stem = norm(row.get("stem"))
    preamble = norm(row.get("preamble"))
    br = "<br>\n"
    if stem:
        parts.append(f"<p>{html.escape(stem).replace(chr(10), br)}</p>")
    if preamble:
        parts.append(f"<p>{html.escape(preamble).replace(chr(10), br)}</p>")
    stmts: list[tuple[str, str]] = []
    for lab, key in LABELS:
        t = norm(row.get(key))
        if t:
            stmts.append((lab, t))
    if stmts:
        lis = "".join(
            f"<li><strong>{html.escape(lab)}</strong> {html.escape(t).replace(chr(10), br)}</li>"
            for lab, t in stmts
        )
        parts.append(f'<ol class="q-stmt-list" style="list-style:none;padding-left:0;">{lis}</ol>')
    return "\n".join(parts) if parts else "<p>（問題文なし）</p>"


def meta_description(text: str, limit: int = 155) -> str:
    one = re.sub(r"\s+", " ", text).strip()
    if len(one) <= limit:
        return one
    return one[: limit - 1] + "…"


def stem_preview(text: str, limit: int = 52) -> str:
    one = re.sub(r"\s+", " ", text).strip()
    if not one:
        return ""
    if len(one) <= limit:
        return one
    return one[: limit - 1] + "…"


def page_heading(page: dict) -> str:
    from tools.q_page_seo import question_h1

    return question_h1(
        "past",
        year=page["year"],
        qno=page["qno"],
        category=page["category"],
    )


def page_context_line(page: dict) -> str:
    return f"{page['year']}年 · {page['category']}"


def page_title_seo(page: dict) -> str:
    from tools.q_page_seo import question_page_title

    return question_page_title(
        "past",
        year=page["year"],
        qno=page["qno"],
        category=page["category"],
    )


def page_meta_description(page: dict) -> str:
    from tools.q_page_seo import question_meta_description, question_meta_headline

    return question_meta_description(
        "past",
        headline=question_meta_headline(
            "past", year=page["year"], qno=page["qno"]
        ),
        category=page["category"],
        body=norm(page.get("stem_plain")),
    )


Q_INDEX_CSS_VER = "20260526-q-index-mobile"

GLOSSARY_CSV = ROOT / "data" / "glossary_terms.csv"


def q_index_filter_chip_btn(
    class_name: str,
    data_attr: str,
    data_value: str,
    label: str,
    *,
    count: int | None = None,
    on: bool = False,
) -> str:
    """過去問一覧フィルタ（テキストリンク風）。"""
    on_cls = " on" if on else ""
    count_html = ""
    if count is not None:
        count_html = f'<span class="q-index-filter-count">（{count}）</span>'
    return (
        f'<button type="button" class="q-index-filter-opt {class_name}{on_cls}" '
        f'{data_attr}="{html.escape(data_value, quote=True)}">'
        f"{html.escape(label)}{count_html}</button>"
    )


def parse_tags(raw: str) -> list[str]:
    """CSV tags（; 区切りが多い）。一覧表示用の内部タグは除外。"""
    skip_prefixes = ("otsu4-sample-", "kikenbutsu_", "p")
    skip_exact = {"過去問", "乙4", "要確認"}
    out: list[str] = []
    for t in re.split(r"[,、/|;]+", raw or ""):
        t = t.strip()
        if not t or t in skip_exact:
            continue
        if any(t.startswith(p) for p in skip_prefixes if p != "p"):
            continue
        if re.fullmatch(r"p\d+", t):
            continue
        if t.endswith(".pdf"):
            continue
        out.append(t)
    return out


def load_glossary_lookup() -> dict[str, str]:
    from tools.build_glossary_pages import lookup_key, make_term_lookup, term_slug

    if not GLOSSARY_CSV.is_file():
        return {}
    rows = list(csv.DictReader(GLOSSARY_CSV.read_text(encoding="utf-8-sig").splitlines()))
    used: dict[str, str] = {}
    entries = []
    for row in rows:
        term = norm(row.get("term"))
        if not term:
            continue
        reading = norm(row.get("reading"))
        legacy_slug = norm(row.get("slug"))
        if legacy_slug:
            slug_file = legacy_slug if legacy_slug.endswith(".html") else f"{legacy_slug}.html"
            if slug_file in used:
                raise ValueError(f"glossary_terms.csv: slug が重複しています: {legacy_slug}")
            used[slug_file] = term
        else:
            slug_file = f"{term_slug(term, reading, used)}.html"
        entries.append({"term": term, "slug_file": slug_file})
    lookup = make_term_lookup(entries)
    return {k: f"../terms/{v}" for k, v in lookup.items()}


def glossary_links_for_tags(tags: list[str], lookup: dict[str, str]) -> list[dict]:
    from tools.build_glossary_pages import lookup_key

    out: list[dict] = []
    seen: set[str] = set()
    for tag in tags:
        for key in (lookup_key(tag), tag):
            href = lookup.get(key)
            if not href or href in seen:
                continue
            seen.add(href)
            out.append({"label": tag, "href": href})
            break
        if len(out) >= 3:
            break
    return out


def index_item_dict(page: dict) -> dict:
    preview = stem_preview(page.get("stem_plain") or "")
    tags = page.get("tags") or []
    search_bits = [
        f"第{page['qno']}問",
        page["category"],
        str(page["year"]),
        page.get("wareki", ""),
        preview,
        *tags,
    ]
    return {
        "appId": page["app_id"],
        "year": page["year"],
        "qno": page["qno"],
        "category": page["category"],
        "wareki": page.get("wareki", ""),
        "href": page["href_rel"],
        "preview": preview,
        "tags": tags,
        "exempt": bool(page.get("is_exempt")),
        "invalidated": bool(page.get("is_invalidated")),
        "correct": page.get("correct"),
        "search": " ".join(x for x in search_bits if x),
    }


def _append_index_search_keywords(item: dict) -> dict:
    from tools.q_page_seo import index_search_index_suffix

    item = dict(item)
    item["search"] = f"{item.get('search', '')} {index_search_index_suffix()}".strip()
    return item


def build_index_table_row(page: dict) -> str:
    href = html.escape(page["href_rel"])
    label = f"第{page['qno']}問"
    preview = stem_preview(page.get("stem_plain") or "")
    preview_cell = (
        html.escape(preview)
        if preview
        else '<span class="q-year-table-desc--empty">問題文は各ページで確認できます</span>'
    )
    return (
        '<tr class="q-year-table-row" tabindex="0"'
        f' data-app-id="{page["app_id"]}"'
        f' data-href="{html.escape(page["href_rel"], quote=True)}"'
        f' data-category="{html.escape(page["category"], quote=True)}">'
        f'<td class="q-year-table-no" data-label="問"><a href="{href}">{html.escape(label)}</a></td>'
        f'<td class="q-year-table-cat" data-label="分野">{html.escape(page["category"])}</td>'
        f'<td class="q-year-table-desc" data-label="問題文">{preview_cell}</td>'
        "</tr>"
    )




def rel_to_root(rel_file: Path) -> str:
    depth = len(rel_file.parent.parts)
    return "/".join([".."] * depth) + "/index.html"


def rel_to_q_index(rel_file: Path) -> str:
    """q/past/.../index.html から q/index.html へ"""
    depth = len(rel_file.parent.parts)
    up = max(depth - 1, 1)
    return "/".join([".."] * up) + "/index.html"


def rel_css(rel_file: Path) -> str:
    depth = len(rel_file.parent.parts)
    return "/".join([".."] * depth) + f"/site-pages.css?v={Q_INDEX_CSS_VER}"


def rel_theme_css(rel_file: Path) -> str:
    depth = len(rel_file.parent.parts)
    return "/".join([".."] * depth) + "/site-theme.css"


def public_url(base: str, rel_path: str) -> str:
    return f"{base.rstrip('/')}/{rel_path.lstrip('/')}"


def rel_href(rel_file: Path, target: str) -> str:
    """q/past/y2026/q01/index.html からサイト内パスへの相対リンク。"""
    depth = len(rel_file.parent.parts)
    prefix = "/".join([".."] * depth)
    target = target.lstrip("/")
    return f"{prefix}/{target}" if prefix else target


def text_to_html(text: str) -> str:
    if not text:
        return ""
    return html.escape(text).replace("\n", "<br>\n")


def normalize_glossary_href(href: str) -> str:
    return re.sub(r"^(?:\.\./)+", "", href.lstrip("/"))


GUIDE_LINK_FALLBACK_SLUGS = (
    "past-question-strategy",
    "study-plan",
    "exam-overview",
    "glossary-how-to",
)


def load_guide_articles() -> list[dict[str, str]]:
    from tools.build_glossary_pages import load_guide_slugs

    return load_guide_slugs()


def guide_links_for_page(category: str, guides: list[dict[str, str]], *, limit: int = 2) -> list[tuple[str, str]]:
    """(href_rel_from_site_root, label) — rel_href で結合する。"""
    if not guides:
        return []
    picked: list[tuple[str, str]] = []
    seen: set[str] = set()
    cat = norm(category)
    for g in guides:
        blob = f"{g.get('genre', '')} {g.get('tags', '')} {g.get('title', '')}"
        if cat and cat in blob:
            slug = g["slug"]
            if slug not in seen:
                seen.add(slug)
                picked.append((f"articles/{slug}/index.html", g["title"]))
        if len(picked) >= limit:
            return picked
    by_slug = {g["slug"]: g for g in guides}
    for slug in GUIDE_LINK_FALLBACK_SLUGS:
        if len(picked) >= limit:
            break
        g = by_slug.get(slug)
        if g and slug not in seen:
            seen.add(slug)
            picked.append((f"articles/{slug}/index.html", g["title"]))
    return picked


def parse_related_link_tokens(
    raw: str,
    page: dict,
    rel_path: Path,
    pages_by_key: dict[tuple[int, int], dict],
    glossary_lookup: dict[str, str],
    guides: list[dict[str, str]],
) -> list[tuple[str, str]]:
    """(相対href, ラベル)"""
    from tools.build_glossary_pages import field_hub_slug, lookup_key
    from tools.knowledge_hub_seo import field_hub_page_exists

    items: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(href: str, label: str) -> None:
        if href in seen:
            return
        seen.add(href)
        items.append((href, label))

    for token in split_semicolon(raw):
        if ":" in token:
            kind, rest = token.split(":", 1)
            kind = kind.strip().lower()
            if ":" in rest:
                target, label = [x.strip() for x in rest.split(":", 1)]
            else:
                target, label = rest.strip(), ""
        else:
            kind, target, label = "page", token.strip(), ""

        if kind in ("guide", "article"):
            slug = target
            g = next((x for x in guides if x["slug"] == slug), None)
            add(
                rel_href(rel_path, f"articles/{slug}/index.html"),
                label or (g["title"] if g else slug),
            )
        elif kind == "term":
            href = glossary_lookup.get(target) or glossary_lookup.get(lookup_key(target))
            if href:
                add(rel_href(rel_path, normalize_glossary_href(href)), label or target)
        elif kind == "past":
            m = re.match(r"^(\d{4})[-/](\d+)$", target.replace(" ", ""))
            if m:
                y, qn = int(m.group(1)), int(m.group(2))
                pg = pages_by_key.get((y, qn))
                if pg:
                    add(
                        rel_href(rel_path, pg["rel_path"]),
                        label or f"{y}年 第{qn}問",
                    )
        elif kind in ("page", "path"):
            add(rel_href(rel_path, target), label or target)
        elif kind == "qindex":
            add(rel_href(rel_path, "q/index.html"), label or "過去問一覧")
        elif kind == "terms":
            add(rel_href(rel_path, "terms/index.html"), label or "用語解説一覧")
        elif kind == "review":
            add(rel_href(rel_path, "index.html#review"), label or "復習リスト")
        elif kind == "practice":
            add(rel_href(rel_path, "index.html#past"), label or "アプリで演習する")
        elif kind == "field":
            cat = page.get("category") or ""
            if field_hub_page_exists(cat):
                hub = field_hub_slug(cat)
                add(
                    rel_href(rel_path, f"terms/{hub}/index.html"),
                    label or f"{cat}の用語一覧",
                )

    return items


def build_related_links_html(
    page: dict,
    row: dict,
    rel_path: Path,
    all_pages: list[dict],
    glossary_lookup: dict[str, str],
    guides: list[dict[str, str]],
) -> str:
    pages_by_key = {(p["year"], p["qno"]): p for p in all_pages}
    manual = parse_related_link_tokens(
        norm(row.get("related_links")),
        page,
        rel_path,
        pages_by_key,
        glossary_lookup,
        guides,
    )

    links: list[tuple[str, str]] = list(manual)
    seen = {h for h, _ in links}

    def add_auto(href: str, label: str) -> None:
        if href not in seen:
            seen.add(href)
            links.append((href, label))

    add_auto(rel_href(rel_path, "q/index.html"), "過去問一覧")
    y, qn = page["year"], page["qno"]
    for other_q in (qn - 1, qn + 1):
        if other_q < 1:
            continue
        pg = pages_by_key.get((y, other_q))
        if pg:
            ylabel = pg.get("year_label") or pg.get("wareki") or f"{y}年"
            add_auto(
                rel_href(rel_path, pg["rel_path"]),
                f"{ylabel} 第{other_q}問",
            )

    for gl in glossary_links_for_tags(page.get("tags") or [], glossary_lookup):
        href = rel_href(rel_path, normalize_glossary_href(gl["href"]))
        add_auto(href, gl["label"])

    from tools.build_glossary_pages import field_hub_slug
    from tools.knowledge_hub_seo import field_hub_page_exists

    cat = page.get("category") or ""
    if field_hub_page_exists(cat):
        hub = field_hub_slug(cat)
        add_auto(
            rel_href(rel_path, f"terms/{hub}/index.html"),
            f"{cat}の用語一覧",
        )

    for href_rel, title in guide_links_for_page(page.get("category") or "", guides):
        add_auto(rel_href(rel_path, href_rel), title)

    add_auto(rel_href(rel_path, "index.html#review"), "復習リストで解き直す")
    add_auto(rel_href(rel_path, "index.html#past"), "アプリで演習する")

    if not links:
        return ""

    limit = 8
    link_html = "".join(
        f'<a class="related-link" href="{html.escape(href)}">{html.escape(label)}</a>'
        for href, label in links[:limit]
    )
    return (
        '<section class="q-block q-related" aria-labelledby="q-related-h">'
        '<h2 id="q-related-h" class="q-h2">関連ページ</h2>'
        '<div class="related-box">'
        '<div class="related-links">'
        f"{link_html}"
        "</div></div></section>"
    )


def split_semicolon(s: str) -> list[str]:
    return [x.strip() for x in (s or "").split(";") if x.strip()]


def load_rows() -> list[dict]:
    text = DATA_CSV.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(text.splitlines()))


def page_dict(row: dict, line_no: int) -> dict:
    year = int(row["exam_year"])
    qno = int(row["question_no"])
    from tools.correct_answer_format import collect_choice_texts

    opts = collect_choice_texts(row)
    from tools.site_config import extended_correct_answers

    min_choices = 2 if extended_correct_answers() else 4
    if len(opts) < min_choices:
        raise ValueError(f"line {line_no}: 選択肢欠け {year}-{qno}")
    max_choice = len(opts)
    inv = norm(row.get("is_invalidated", "")).upper() == "TRUE"
    from tools.correct_answer_format import is_valid_correct, parse_correct_page_value

    cor_raw = norm(row.get("correct"))
    cor = parse_correct_page_value(
        cor_raw, extended=extended_correct_answers(), max_choice=max_choice
    )
    if cor is None and not inv:
        if extended_correct_answers() and is_valid_correct(cor_raw, max_choice=max_choice):
            cor = cor_raw
        else:
            raise ValueError(f"line {line_no}: 正答なし {year}-{qno}")
    wareki = norm(row.get("exam_wareki"))
    cat = norm(row.get("category"))
    typ = norm(row.get("type")) or "single"
    stem_plain = norm(row.get("stem"))
    exp = norm(row.get("explanation")) or "（解説は未入力です。）"
    return {
        "year": year,
        "qno": qno,
        "wareki": wareki,
        "category": cat,
        "type": typ,
        "stem_html": build_stem_html(row),
        "stem_plain": stem_plain,
        "opts": opts,
        "correct": cor,
        "is_exempt": norm(row.get("is_exempt", "")).upper() == "TRUE",
        "is_invalidated": inv,
        "note": norm(row.get("note")),
        "exp": exp,
        "id": f"past-{year}-{qno:02d}",
        "app_id": year * 100 + qno,
        "tags": parse_tags(norm(row.get("tags"))),
        "rel_path": f"q/past/y{year}/q{qno:02d}/index.html",
    }


def build_question_html(
    page: dict,
    row: dict,
    rel_path: Path,
    base_url: str,
    *,
    all_pages: list[dict],
    glossary_lookup: dict[str, str],
    guides: list[dict[str, str]],
    question_catalog: list[dict],
) -> str:
    heading = page_heading(page)
    title = page_title_seo(page)
    desc = page_meta_description(page)
    context_line = page_context_line(page)
    lead = norm(page.get("stem_plain"))
    lead_html = (
        f'<p class="q-page-lead">{html.escape(lead)}</p>' if lead else ""
    )
    canonical = public_url(base_url, page["rel_path"])
    root_idx = rel_to_root(rel_path)
    css_href = rel_css(rel_path)
    theme_href = rel_theme_css(rel_path)

    opts_html = "".join(
        f'<li class="q-opt"><span class="q-opt-num">（{i}）</span> {html.escape(o)}</li>'
        for i, o in enumerate(page["opts"], start=1)
    )

    if page["is_invalidated"] or page["correct"] is None:
        ans_block = (
            "<p>本問は試験上「出題無効」となった年度があります（"
            + html.escape(page["note"] or "公式の扱いを確認してください")
            + "）。学習用に選択肢のみ掲載します。</p>"
        )
    else:
        ans_block = f'<p>正答は <strong>（{page["correct"]}）</strong> です。</p>'

    badges = []
    if page["is_exempt"]:
        badges.append('<span class="q-badge">試験免除出題</span>')
    if page["is_invalidated"]:
        badges.append('<span class="q-badge q-badge-warn">出題無効</span>')
    badge_html = ("<p class=\"q-badges\">" + " ".join(badges) + "</p>") if badges else ""

    exp_html = build_explanation_html(page, row)
    similar_html = build_similar_questions_html(
        page,
        rel_path,
        question_catalog,
        mode="past",
        rel_href=rel_href,
        publish_root=ROOT,
    )
    related_html = build_related_links_html(
        page, row, rel_path, all_pages, glossary_lookup, guides
    )

    json_ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": canonical + "#webpage",
                "url": canonical,
                "name": title,
                "description": desc,
                "inLanguage": "ja-JP",
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "トップ", "item": public_url(base_url, "index.html")},
                    {"@type": "ListItem", "position": 2, "name": "過去問一覧", "item": public_url(base_url, "q/index.html")},
                    {"@type": "ListItem", "position": 3, "name": heading, "item": canonical},
                ],
            },
        ],
    }

    site_header = site_page_header(
        rel_path,
        current="q",
    )
    site_breadcrumb = breadcrumb_html(
        rel_path,
        [("トップ", "index.html"), ("過去問一覧", "q/index.html"), (heading, None)],
    )
    site_footer = site_page_footer(rel_path, current="q")
    from tools.q_page_seo import study_modes_note_html

    study_modes_note = study_modes_note_html()

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
{ROBOTS_INDEX_FOLLOW}
<link rel="canonical" href="{html.escape(canonical)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="{html.escape(canonical)}">
<meta name="twitter:card" content="summary">
{HEAD_FONTS}
<link rel="stylesheet" href="{html.escape(css_href)}">
<link rel="stylesheet" href="{html.escape(theme_href)}">
<script type="application/ld+json">
{json.dumps(json_ld, ensure_ascii=False, indent=2)}
</script>
</head>
<body class="{shell_body_class('q-static-page')}">
{site_page_wrap_open()}
{site_header}
<main class="q-static-main">
  {site_breadcrumb}
  {study_modes_note}
  <p class="q-meta-line">{html.escape(context_line)}</p>
  {badge_html}
  <h1 class="q-h1">{html.escape(heading)}</h1>
  {lead_html}
  <section class="q-block" aria-labelledby="q-stem-h">
    <h2 id="q-stem-h" class="q-h2">問題</h2>
    <div class="q-stem">{page["stem_html"]}</div>
  </section>
  <section class="q-block" aria-labelledby="q-opts-h">
    <h2 id="q-opts-h" class="q-h2">選択肢</h2>
    <ol class="q-opts">
      {opts_html}
    </ol>
  </section>
  <section class="q-block q-answer" aria-labelledby="q-ans-h">
    <h2 id="q-ans-h" class="q-h2">正答</h2>
    {ans_block}
  </section>
  <section class="q-block" aria-labelledby="q-exp-h">
    <h2 id="q-exp-h" class="q-h2">解説</h2>
    {exp_html}
  </section>
  {similar_html}
  {related_html}
  <p class="q-app-link"><a href="{html.escape(rel_href(rel_path, 'index.html#past'))}">アプリで演習する</a></p>
</main>
{site_footer}
{site_page_wrap_close()}
</body>
</html>
"""


def build_q_index(pages: list[dict], base_url: str) -> str:
    index_pages: list[dict] = []
    for page in pages:
        pg = dict(page)
        pg["href_rel"] = (
            page["rel_path"][2:] if page["rel_path"].startswith("q/") else page["rel_path"]
        )
        index_pages.append(pg)

    by_year = {}
    by_category = {}
    for pg in index_pages:
        by_year.setdefault(pg["year"], []).append(pg)
        by_category[pg["category"]] = by_category.get(pg["category"], 0) + 1
    for y in by_year:
        by_year[y].sort(key=lambda x: x["qno"])

    sorted_years = sorted(by_year.keys(), reverse=True)
    open_years = set(sorted_years[:2])

    year_blocks = []
    year_jump_links = []
    for y in sorted_years:
        rows_html = "".join(build_index_table_row(pg) for pg in by_year[y])
        sample = by_year[y][0]
        year_label = norm(sample.get("year_label") or "")
        heading = year_label or (
            sample["wareki"]
            if y > 9999
            else f"{y}年（{sample['wareki']}）"
        )
        jump_label = year_label or (f"{y}年" if y <= 9999 else sample["wareki"])
        expanded = "true" if y in open_years else "false"
        collapsed = "" if y in open_years else " is-collapsed"
        year_jump_links.append(
            f'<a class="q-index-filter-opt q-index-year-link" href="#year-{y}" data-year="{y}">'
            f'{html.escape(jump_label)}<span class="q-index-filter-count">（{len(by_year[y])}）</span></a>'
        )
        year_blocks.append(
            f'<section class="q-index-year-block{collapsed}" id="year-{y}">'
            f'<div class="q-index-year-head">'
            f'<div class="q-index-year-head-main">'
            f'<button type="button" class="q-index-year-toggle" aria-expanded="{expanded}" '
            f'aria-controls="year-body-{y}"><span class="q-index-year-chevron" aria-hidden="true"></span></button>'
            f'<h2 id="year-{y}-heading">{html.escape(heading)}</h2>'
            f"</div>"
            f'<span class="q-index-year-count" data-total="{len(by_year[y])}">{len(by_year[y])}問</span>'
            f"</div>"
            f'<div class="q-year-table-wrap" id="year-body-{y}">'
            f'<table class="q-year-table" aria-labelledby="year-{y}-heading">'
            "<thead><tr>"
            '<th scope="col">問</th><th scope="col">分野</th>'
            '<th scope="col">問題文（抜粋）</th>'
            "</tr></thead>"
            f"<tbody>{rows_html}</tbody>"
            "</table></div></section>"
        )
    year_blocks_html = (
        "".join(year_blocks).replace("<motion ", "<div ").replace("</motion>", "</div>")
    )


    status_chips = [
        q_index_filter_chip_btn("q-index-status-btn", "data-status", "all", "すべて", on=True),
        q_index_filter_chip_btn("q-index-status-btn", "data-status", "wrong", "不正解"),
        q_index_filter_chip_btn("q-index-status-btn", "data-status", "bookmark", "ブックマーク"),
        q_index_filter_chip_btn("q-index-status-btn", "data-status", "exempt", "免除"),
        q_index_filter_chip_btn("q-index-status-btn", "data-status", "invalid", "無効"),
    ]
    json_data = json.dumps(
        [_append_index_search_keywords(index_item_dict(pg)) for pg in index_pages],
        ensure_ascii=False,
    )
    status_chips_html = "".join(status_chips)
    category_chips = [
        q_index_filter_chip_btn("q-index-chip-btn", "data-cat", "all", "すべて", on=True)
    ]
    for cat, count in sorted(by_category.items()):
        category_chips.append(
            q_index_filter_chip_btn("q-index-chip-btn", "data-cat", cat, cat, count=count)
        )
    category_chips_html = "".join(category_chips)
    year_jump_html = "".join(year_jump_links)
    year_count = len(by_year)

    rel_path = Path("q/index.html")
    q_index_header = site_page_header(
        rel_path,
        current="q",
    )
    q_index_breadcrumb = breadcrumb_html(rel_path, [("トップ", "index.html"), ("過去問一覧", None)])
    q_index_footer = site_page_footer(rel_path, current="q")

    from tools.q_page_seo import (
        index_h1,
        index_lead,
        index_meta_description,
        index_page_title,
        index_search_placeholder,
        study_modes_note_html,
    )

    page_title = index_page_title("past")
    index_h1_text = index_h1("past")
    page_desc = index_meta_description("past", count=len(pages))
    page_lead = index_lead("past")
    search_placeholder = index_search_placeholder("past")
    study_modes_note = study_modes_note_html()

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(page_title)}</title>
<meta name="description" content="{html.escape(page_desc)}">
<meta property="og:title" content="{html.escape(page_title)}">
<meta property="og:description" content="{html.escape(page_desc)}">
{ROBOTS_INDEX_FOLLOW}
<link rel="canonical" href="{html.escape(public_url(base_url, "q/index.html"))}">
{HEAD_FONTS}
<link rel="stylesheet" href="../site-pages.css?v={Q_INDEX_CSS_VER}">
<link rel="stylesheet" href="../site-theme.css">
</head>
<body class="{shell_body_class('q-index-page')}">
{site_page_wrap_open()}
{q_index_header}
<main class="site-page-main">
  {q_index_breadcrumb}
  <h1>{html.escape(index_h1_text)}</h1>
  <p class="site-page-lead">{html.escape(page_lead)}</p>
  {study_modes_note}
  {q_hub_links_html(rel_path, current="past")}
  <section class="past-index-panel" aria-labelledby="past-index-heading">
    <div class="past-index-head">
      <div>
        <h2 id="past-index-heading">過去問一覧</h2>
        <p>{html.escape(q_index_stats_line(question_count=len(pages), mode="past", year_count=year_count, category_count=len(by_category)))}。キーワード検索と絞り込みで探せます。</p>
      </div>
    </div>
    {q_index_tools_open_html(
        search_label="過去問検索",
        search_placeholder=search_placeholder,
        hit_text=f"{len(pages)} / {len(pages)} 問",
    )}
      {q_index_filters_details_html(
          year_row_label="年度",
          year_jump_html=year_jump_html,
          category_chips_html=category_chips_html,
          status_chips_html=status_chips_html,
      )}
    {q_index_tools_close_html()}
    <div class="q-index-empty-panel hide" id="q-index-empty" role="status">
      <p class="q-index-empty-title">条件に一致する過去問がありません</p>
      <p class="q-index-empty-hint">検索語を短くするか、分野・学習状況を「すべて」に戻してお試しください。</p>
      <button type="button" class="q-index-reset" id="q-index-empty-reset">条件をクリア</button>
    </div>
    <div class="q-index-layout">
      <div class="q-index-content">
        <section class="q-index-years q-index-view-panel" id="q-index-view-year" aria-label="年度別過去問">{year_blocks_html}</section>
        <section class="q-index-view-panel hide" id="q-index-view-cat" aria-label="分野別過去問"><div id="q-index-cat-mount"></div></section>
        <section class="q-index-view-panel hide" id="q-index-view-flat" aria-label="過去問一覧">
          <div class="q-year-table-wrap">
            <table class="q-year-table">
              <thead><tr>
                <th scope="col">問</th><th scope="col">分野</th>
                <th scope="col">問題文（抜粋）</th>
              </tr></thead>
              <tbody id="q-index-flat-body"></tbody>
            </table>
          </div>
        </section>
        <nav class="q-index-pagination hide" id="q-index-pagination" aria-label="ページ送り"></nav>
      </div>
    </div>
  </section>
</main>
{q_index_footer}
{site_page_wrap_close()}
<button type="button" class="q-index-top" id="q-index-top" aria-label="ページ上部へ">↑</button>
<script type="application/json" id="q-index-config">{{"variant":"past"}}</script>
<script type="application/json" id="q-index-data">{json_data}</script>
<script defer src="../site-q-index.js"></script>
</body>
</html>
"""


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=BASE_DEFAULT)
    args = ap.parse_args()
    base = args.base_url.rstrip("/")

    rows = load_rows()
    pages = [page_dict(r, i) for i, r in enumerate(rows, start=2)]
    glossary_lookup = load_glossary_lookup()
    guides = load_guide_articles()
    question_catalog = load_question_catalog(ROOT)

    past_root = Q_ROOT / "past"
    if past_root.is_dir():
        shutil.rmtree(past_root)
    for p, row in zip(pages, rows):
        rel = Path(p["rel_path"])
        out_file = ROOT / rel
        out_file.parent.mkdir(parents=True, exist_ok=True)
        html_out = build_question_html(
            p,
            row,
            out_file.relative_to(ROOT),
            base,
            all_pages=pages,
            glossary_lookup=glossary_lookup,
            guides=guides,
            question_catalog=question_catalog,
        )
        out_file.write_text(html_out, encoding="utf-8")

    q_index = ROOT / "q" / "index.html"
    q_index.parent.mkdir(parents=True, exist_ok=True)
    q_index.write_text(build_q_index(pages, base), encoding="utf-8")

    try:
        from tools.past_question_seo import build_past_root_hub_html  # noqa: WPS433
        from tools.site_config import brand_name, clean_origin, exam_name

        years = sorted({int(p["year"]) for p in pages})
        past_hub = ROOT / "q" / "past" / "index.html"
        past_hub.parent.mkdir(parents=True, exist_ok=True)
        past_hub.write_text(
            build_past_root_hub_html(
                years, pages, clean_origin(), brand_name(), exam_name()
            ),
            encoding="utf-8",
        )
        print(f"Wrote {past_hub}")
    except ImportError:
        pass

    # sitemap.xml は tools/build_sitemap.py が生成

    robots = ROOT / "robots.txt"
    robots.write_text(
        "User-agent: *\nAllow: /\n\nSitemap: "
        + f"{base}/sitemap.xml\n",
        encoding="utf-8",
    )

    print(f"Wrote {len(pages)} question pages under {past_root}")
    print(f"Wrote {q_index}")
    print("Sitemap: tools/build_sitemap.py で生成します")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
