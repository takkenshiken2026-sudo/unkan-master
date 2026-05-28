#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知識ハブ詳細ページ（比較・数値・誤答・頻出）向けの SEO 共通部品。"""

from __future__ import annotations

import html
from pathlib import Path

from tools.build_glossary_pages import (  # noqa: E402
    field_hub_slug,
    glossary_field_badge_html,
    glossary_field_id,
    guide_related_link_items,
    rel_to_root,
    split_semicolon,
)
ROOT = Path(__file__).resolve().parents[1]


def field_hub_page_exists(category: str) -> bool:
    if not category or not glossary_field_id(category):
        return False
    hub = field_hub_slug(category)
    return (ROOT / "terms" / hub / "index.html").is_file()

from tools.glossary_past_questions import (  # noqa: E402
    find_past_questions_for_term,
    past_questions_section_html,
)
from tools.html_footer import breadcrumb_html  # noqa: E402
from tools.seo_utils import json_ld_date_modified  # noqa: E402
from tools.site_config import (  # noqa: E402
    brand_name,
    exam_name,
    external_links,
    primary_external_link,
)

HUB_CROSS_LINKS: dict[str, list[tuple[str, str]]] = {
    "compare": [
        ("数値・期限早見表", "../numbers/index.html"),
        ("よくある誤答", "../mistakes/index.html"),
        ("用語解説一覧", "../index.html"),
    ],
    "numbers": [
        ("比較・整理表", "../compare/index.html"),
        ("よくある誤答", "../mistakes/index.html"),
        ("用語解説一覧", "../index.html"),
    ],
    "mistakes": [
        ("比較・整理表", "../compare/index.html"),
        ("数値・期限早見表", "../numbers/index.html"),
        ("用語解説一覧", "../index.html"),
    ],
}


def seo_quality_panel_html(*, updated: str = "") -> str:
    panel = (
        '<section class="seo-quality-panel" aria-labelledby="quality-panel-title">'
        '<h2 id="quality-panel-title">この記事の信頼性について</h2>'
        '<table class="seo-info-table"><tbody>'
        f"<tr><th>執筆</th><td>{html.escape(brand_name())}編集部（学習用語、過去問の復習導線、試験ガイドを整理する編集チーム）</td></tr>"
        f"<tr><th>確認</th><td>{html.escape(brand_name())}編集部（公開前に公式情報、法令情報、サイト内の関連ページとの整合性を確認）</td></tr>"
    )
    if updated:
        panel += f"<tr><th>事実確認日</th><td>{html.escape(updated)}</td></tr>"
    official_links = external_links() or [primary_external_link()]
    source_items = "".join(
        f'<li><a href="{html.escape(link["url"])}" target="_blank" rel="noopener noreferrer">{html.escape(link["label"])}</a></li>'
        for link in official_links
    )
    panel += (
        f'<tr><th>主な参照元</th><td><ul class="quality-source-list">{source_items}</ul></td></tr>'
        "</tbody></table></section>"
    )
    return panel


def seo_action_box_html(*, subject: str, hub_label: str) -> str:
    return (
        '<section class="seo-action-box" aria-labelledby="action-box-title">'
        '<h2 id="action-box-title">この記事でできること</h2>'
        f"<p>この記事では、{html.escape(subject)}について{html.escape(hub_label)}形式で整理し、"
        f"{html.escape(exam_name())}で迷いやすい部分を短時間で復習できます。"
        "表を読んだあとは、関連用語と過去問を合わせて確認し、選択肢で使える状態に近づけてください。</p>"
        "<ul>"
        f"<li>{html.escape(subject)}の違い・数値・誤答パターンを一覧で確認する</li>"
        "<li>試験で問われやすい条件や表現を整理する</li>"
        "<li>混同しやすい選択肢や注意点を復習する</li>"
        "<li>関連する用語解説や過去問へ進む</li>"
        "</ul></section>"
    )


def official_info_html(*, subject: str) -> str:
    official_links = external_links() or [primary_external_link()]
    items = "".join(
        f'<li><a href="{html.escape(link["url"])}" target="_blank" rel="noopener noreferrer">{html.escape(link["label"])}</a>'
        + (f' … {html.escape(link.get("description", ""))}' if link.get("description") else "")
        + "</li>"
        for link in official_links
    )
    return (
        '<section class="seo-article-section" aria-labelledby="official-info-title">'
        '<h2 id="official-info-title">公式情報の確認</h2>'
        f"<p>{html.escape(subject)}は、{html.escape(exam_name())}の学習で押さえたい論点です。"
        "制度、数値、義務の有無は年度や法令改正で変わることがあるため、受験前には公式情報も確認してください。</p>"
        f"<ul>{items}</ul>"
        "<blockquote><p><strong>注意：</strong>"
        "本ページは学習用の要点整理です。出題範囲・法令・公式見解は変更される場合があります。"
        "本番前には必ず試験実施団体や法令原文などの公式情報を確認してください。"
        "</p></blockquote></section>"
    )


def seo_toc_html(items: list[tuple[str, str]]) -> str:
    if not items:
        return ""
    links = "".join(
        f'<li><a href="#{html.escape(anchor)}">{html.escape(label)}</a></li>'
        for anchor, label in items
    )
    return (
        '<nav class="seo-toc" aria-labelledby="seo-toc-title">'
        '<h2 id="seo-toc-title">目次</h2>'
        f"<ol>{links}</ol></nav>"
    )


def hub_article_section(sec_id: str, label: str, body_html: str, number: int | None = None) -> str:
    if not body_html.strip():
        return ""
    hid = f"hub-sec-{sec_id}"
    num_html = f'<span class="section-heading-num">{number}</span>' if number is not None else ""
    return (
        f'<section class="seo-article-section" aria-labelledby="{hid}">'
        f'<h2 id="{hid}">{num_html}{html.escape(label)}</h2>'
        f"{body_html}</section>"
    )


def build_numbered_sections(
    sections: list[tuple[str, str, str]],
) -> tuple[str, list[tuple[str, str]]]:
    html_parts: list[str] = []
    toc_items: list[tuple[str, str]] = []
    number = 1
    for sec_id, label, body_html in sections:
        block = hub_article_section(sec_id, label, body_html, number)
        if not block:
            continue
        html_parts.append(block)
        toc_items.append((f"hub-sec-{sec_id}", label))
        number += 1
    return "\n    ".join(html_parts), toc_items


def hub_detail_breadcrumb(
    rel_path: Path,
    *,
    hub_index_label: str,
    title: str,
    category: str,
) -> str:
    field_hub = field_hub_slug(category) if category and field_hub_page_exists(category) else ""
    hub_index_href = f"{rel_path.parent.as_posix()}/index.html"
    items: list[tuple[str, str | None]] = [
        ("トップ", "index.html"),
        (hub_index_label, hub_index_href),
    ]
    if field_hub and category and field_hub_page_exists(category):
        items.append((category, f"terms/{field_hub}/index.html"))
    items.append((title, None))
    return breadcrumb_html(rel_path, items)


def hub_next_links_html(
    rel_path: Path,
    *,
    hub_type: str,
    hub_index_label: str,
    category: str,
    guide_links: list[str] | None = None,
) -> str:
    root_idx = rel_to_root(rel_path)
    field_hub = field_hub_slug(category) if category and field_hub_page_exists(category) else ""
    links = [f'<a class="related-link" href="index.html">{html.escape(hub_index_label)}一覧へ戻る</a>']
    if field_hub and category and field_hub_page_exists(category):
        links.append(
            f'<a class="related-link" href="../{html.escape(field_hub)}/index.html">'
            f"{html.escape(category)}の用語一覧</a>"
        )
    for label, href in HUB_CROSS_LINKS.get(hub_type, []):
        links.append(f'<a class="related-link" href="{html.escape(href)}">{html.escape(label)}</a>')
    links.append(f'<a class="related-link" href="{html.escape(root_idx)}#past">過去問演習で確認する</a>')
    if guide_links:
        links.extend(guide_links)
    return (
        '<div class="related-box" aria-labelledby="hub-next-title">'
        '<div id="hub-next-title" class="related-box-title">次に確認するページ</div>'
        f'<div class="related-links">{"".join(links)}</div></div>'
    )


def find_past_questions_for_hub(
    *,
    title: str,
    related_terms: str = "",
    extra_terms: list[str] | None = None,
    limit: int = 3,
) -> list[dict]:
    candidates: list[str] = [title.strip()]
    candidates.extend(split_semicolon(related_terms))
    if extra_terms:
        candidates.extend(extra_terms)
    seen: set[tuple[int, int]] = set()
    hits: list[dict] = []
    for term in candidates:
        term = term.strip()
        if len(term) < 2:
            continue
        for hit in find_past_questions_for_term(term, limit=limit, related_terms=related_terms):
            key = (hit["year"], hit["qno"])
            if key in seen:
                continue
            seen.add(key)
            hits.append(hit)
            if len(hits) >= limit:
                return hits
    hits.sort(key=lambda p: (p["year"], p["qno"]), reverse=True)
    return hits[:limit]


def hub_article_json_ld(
    *,
    canonical: str,
    page_title: str,
    article_title: str,
    desc: str,
    updated: str,
    breadcrumb_items: list[dict],
    faq_items: list[dict[str, str]] | None = None,
) -> list[dict]:
    webpage: dict = {
        "@type": "WebPage",
        "@id": canonical + "#webpage",
        "url": canonical,
        "name": page_title,
        "description": desc,
        "inLanguage": "ja-JP",
        "mainEntity": {"@id": canonical + "#article"},
    }
    if updated:
        webpage["dateModified"] = updated
    graph: list[dict] = [
        {
            "@type": "Article",
            "@id": canonical + "#article",
            "headline": article_title,
            "description": desc,
            "url": canonical,
            **json_ld_date_modified(updated),
            "inLanguage": "ja-JP",
            "author": {"@type": "Organization", "name": brand_name() + "編集部"},
        },
        webpage,
        {"@type": "BreadcrumbList", "itemListElement": breadcrumb_items},
    ]
    if faq_items:
        graph.append(
            {
                "@type": "FAQPage",
                "@id": canonical + "#faq",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": item["question"],
                        "acceptedAnswer": {"@type": "Answer", "text": item["answer"]},
                    }
                    for item in faq_items
                ],
            }
        )
    return graph


def hub_meta_line(*, hub_short: str, category: str) -> str:
    bits = [f'<span class="q-id">{html.escape(hub_short)}</span>']
    badge = glossary_field_badge_html(category)
    if badge:
        bits.append(badge)
    if category:
        bits.append(f"<span>{html.escape(category)}</span>")
    return " · ".join(bits)


def hub_breadcrumb_json_ld(
    *,
    base_url: str,
    hub_index_name: str,
    hub_index_url: str,
    title: str,
    canonical: str,
    category: str = "",
    field_hub: str = "",
) -> list[dict]:
    from tools.build_glossary_pages import public_url

    items = [
        {"@type": "ListItem", "position": 1, "name": "トップ", "item": public_url(base_url, "index.html")},
        {
            "@type": "ListItem",
            "position": 2,
            "name": hub_index_name,
            "item": public_url(base_url, hub_index_url),
        },
    ]
    pos = 3
    if field_hub and category:
        items.append(
            {
                "@type": "ListItem",
                "position": pos,
                "name": category,
                "item": public_url(base_url, f"terms/{field_hub}/index.html"),
            }
        )
        pos += 1
    items.append({"@type": "ListItem", "position": pos, "name": title, "item": canonical})
    return items


def hub_guide_links(category: str, guides: list[dict[str, str]]) -> list[str]:
    return guide_related_link_items(category, guides, articles_prefix="../../articles/")
