#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知識ハブ詳細ページ（比較・数値・誤答・頻出）向けの SEO 共通部品。"""

from __future__ import annotations

import html
import re
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

HUB_CROSS_LINKS: dict[str, list[tuple[str, str]]] = {}


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


def seo_hub_key_points_box_html(*, subject: str, hub_label: str) -> str:
    """比較・数値・誤答ハブ向け要点ボックス（旧「この記事でできること」を統合）。"""
    intro = (
        f"この記事では、{subject}について{hub_label}形式で整理し、"
        f"{exam_name()}で迷いやすい部分を短時間で復習できます。"
        "表を読んだあとは、関連用語と過去問を合わせて確認し、選択肢で使える状態に近づけてください。"
    )
    items = [
        f"{subject}の違い・数値・誤答パターンを一覧で確認する",
        "試験で問われやすい条件や表現を整理する",
        "混同しやすい選択肢や注意点を復習する",
        "関連する用語解説や過去問へ進む",
    ]
    return seo_key_points_box_html(items, intro=intro)


def seo_key_points_box_html(
    items: list[str],
    *,
    title: str = "この記事の要点",
    heading_id: str = "key-points-title",
    intro: str = "",
) -> str:
    """リード直後に置く要点ボックス（導入文 + 3〜5項目）。"""
    cleaned = [item.strip() for item in items if item and item.strip()]
    intro_text = intro.strip()
    if not cleaned and not intro_text:
        return ""
    intro_html = ""
    if intro_text:
        if "[" in intro_text:
            from tools.inline_markup import render_inline_markup

            intro_html = f"<p>{render_inline_markup(intro_text)}</p>"
        else:
            intro_html = f"<p>{html.escape(intro_text)}</p>"
    list_html = ""
    if cleaned:
        lis = "".join(f"<li>{html.escape(item)}</li>" for item in cleaned[:5])
        list_html = f'<ul class="seo-key-points-list">{lis}</ul>'
    return (
        f'<section class="seo-key-points-box" aria-labelledby="{html.escape(heading_id)}">'
        f'<h2 id="{html.escape(heading_id)}">{html.escape(title)}</h2>'
        f"{intro_html}{list_html}"
        "</section>"
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


def faq_items_html(items: list[dict[str, str]]) -> str:
    """FAQ を details で出力（FAQPage JSON-LD と併用）。すべて open。"""
    from tools.inline_markup import render_inline_markup

    if not items:
        return ""
    return "".join(
        '<details class="term-faq-item" open>'
        f'<summary>{html.escape(item["question"])}</summary>'
        f'<div>{render_inline_markup(item["answer"])}</div>'
        "</details>"
        for item in items
    )


def faq_section_html(
    items: list[dict[str, str]],
    *,
    heading_id: str,
    section_num: int | None = None,
) -> str:
    """「よくある質問」セクション。H2 見出しにのみ section-heading-num を付ける。"""
    body = faq_items_html(items)
    if not body:
        return ""
    num_html = f'<span class="section-heading-num">{section_num}</span>' if section_num is not None else ""
    return (
        f'<section class="seo-article-section" aria-labelledby="{heading_id}">'
        f'<h2 id="{heading_id}">{num_html}よくある質問</h2>'
        f"{body}</section>"
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


def _norm(value: str | None) -> str:
    return (value or "").strip()


def _term_item_label(text: str) -> str:
    """用語記事内の行ラベル（seo-editorial の青 strong は使わない）。"""
    return f'<span class="term-item-label">{html.escape(text.rstrip("：:"))}</span>'


def hub_field_items(value: str) -> list[str]:
    return [x.strip() for x in split_semicolon(value) if x.strip()]


def hub_field_is_stub(value: str, *, min_len: int = 28) -> bool:
    """セミコロン区切りが短いメモ片（scaffold 残存）か。"""
    items = hub_field_items(value)
    if not items:
        return False
    short = sum(1 for item in items if len(item) < min_len)
    return short >= max(1, int(len(items) * 0.75))


def hub_prose_html(paragraphs: list[str]) -> str:
    cleaned = [p.strip() for p in paragraphs if p and p.strip()]
    return "".join(f"<p>{html.escape(p)}</p>" for p in cleaned)


def _hub_row_is_placeholder(row: dict) -> bool:
    item = _norm(row.get("item"))
    value = _norm(row.get("value"))
    note = _norm(row.get("note"))
    if item.startswith("【"):
        return True
    if "試験要項" in value and "確認" in value:
        return True
    if value in {"定義確認のメモ", "基準値は試験要項・省令で確認"}:
        return True
    if not note and len(value) < 12:
        return True
    return False


GENERIC_NUMBER_MATRIX_ITEMS = frozenset(
    {"確認テーマ", "試験の確認点", "数値・条件", "記録・保存", "関連制度"}
)
GENERIC_NUMBER_MATRIX_VALUES = frozenset(
    {
        "基準値は試験要項・省令で確認",
        "定義確認のメモ",
        "過去問の条件メモ",
        "運転日誌・報告書",
        "主語→目的→対象",
        "誰が・いつ・何を",
        "逆転肢の型分類",
        "弱点タグ付きノート",
        "条文×通知の対応表",
    }
)
EXAM_POINTS_SCAFFOLD_MARKERS = (
    "用語の境界を表で整理",
    "類似語の入替肢に注意",
    "定義と主体を固定",
    "数値+条件+主体",
)


def sanitize_hub_article_lead(lead: str) -> str:
    """早見表 scaffold の重複リード（「Xでは… Xは用語の定義…」）を1文に整理。"""
    text = _norm(lead)
    if not text:
        return text
    if "用語の定義と義務主体を先に固定" in text:
        parts = [p.strip() for p in re.split(r"。+", text) if p.strip()]
        cleaned: list[str] = []
        for part in parts:
            if "用語の定義と義務主体を先に固定" in part:
                continue
            if cleaned and part in cleaned[-1]:
                continue
            cleaned.append(part)
        if cleaned:
            return "。".join(c.rstrip("。") for c in cleaned) + "。"
    return text


def _hub_exam_points_are_scaffold(items: list[str]) -> bool:
    if not items:
        return True
    return all(any(marker in item for marker in EXAM_POINTS_SCAFFOLD_MARKERS) for item in items)


def _hub_numeric_row_is_substantive(row: dict, *, title: str = "") -> bool:
    if _hub_row_is_placeholder(row):
        return False
    item = _norm(row.get("item"))
    value = _norm(row.get("value"))
    if item in GENERIC_NUMBER_MATRIX_ITEMS:
        return False
    if value in GENERIC_NUMBER_MATRIX_VALUES:
        return False
    if title and (value == title or title in value):
        return False
    if len(value) < 4:
        return False
    return True


def _hub_numeric_row_point(row: dict) -> str:
    item = _norm(row.get("item"))
    value = _norm(row.get("value"))
    note = _norm(row.get("note"))
    if not item or not value:
        return ""
    skip_notes = ("異常時", "口述", "横串", "現場フロー", "逆転肢", "記録様式")
    para = f"{item}は{value.rstrip('。')}。"
    if note and not any(marker in note for marker in skip_notes):
        para += note if note.endswith("。") else note + "。"
    return para


def _compare_labels_usable(labels: list[str]) -> bool:
    if len(labels) < 2:
        return False
    bad_markers = ("S40", "S42", "頻出", "逆転", "論点", "【", "（", "）")
    for lab in labels[:2]:
        if len(lab) > 24 or any(m in lab for m in bad_markers):
            return False
    return True


def _axis_kind(axis: str) -> str:
    if "根拠" in axis:
        return "根拠"
    if "論点" in axis:
        return "論点"
    if "期間" in axis:
        return "期間"
    if "時点" in axis:
        return "時点"
    if "主体" in axis:
        return "主体"
    if "対象" in axis:
        return "対象"
    if "試験" in axis:
        return "試験"
    if "混同" in axis:
        return "混同"
    return axis


def _compare_axis_paragraph(
    axis: str,
    labels: list[str],
    cols: list[str],
    *,
    title: str = "",
) -> str:
    if len(cols) < 2:
        return ""
    left_val, right_val = cols[0], cols[1]
    kind = _axis_kind(axis)
    usable = _compare_labels_usable(labels)
    left_label = labels[0] if usable and len(labels) >= 2 else "一方"
    right_label = labels[1] if usable and len(labels) >= 2 else "もう一方"
    subject = f"「{title}」" if title else "この論点"

    if kind == "根拠":
        return (
            f"{left_label}は{left_val}に基づく制度です。"
            f"一方、{right_label}は{right_val}として整理され、要件・効果・手続のルールが異なります。"
        )
    if kind == "論点":
        return (
            f"{subject}では、{left_val}と{right_val}の取り違えが論点になります。"
            f"定義だけでなく、誰が・いつ・何をするかまでセットで確認してください。"
        )
    if kind == "期間":
        return (
            f"期間の違いが試験で最も問われます。"
            f"{left_label}は{left_val}が目安です。"
            f"{right_label}は{right_val}までに手続をとる必要があり、"
            f"一方の数字や期限を他方に当てはめる誤答に注意してください。"
        )
    if kind == "時点":
        return (
            f"手続の時点が焦点です。"
            f"{left_val}と{right_val}を逆転させた肢が誤答として出やすいため、"
            f"契約前後・申込前後などの時間軸を表に沿って整理してください。"
        )
    if kind == "主体":
        return (
            f"義務主体の違いに注意です。"
            f"{left_val}が中心になる場面と{right_val}が中心になる場面を分け、"
            f"選択肢の主語がどちらの制度に属するかを確認してください。"
        )
    if kind == "対象":
        return (
            f"適用場面も切り分けが必要です。"
            f"{left_label}は{left_val}が典型例、"
            f"{right_label}は{right_val}の場面で論点になります。"
        )
    if kind == "試験":
        return (
            f"過去問では「{left_val}」「{right_val}」のように、"
            f"一方の制度の特徴だけを他方に当てはめる肢が誤答として出やすいです。"
            f"比較表の「{axis.split('（')[0]}」行を見ながら、別制度として確認してください。"
        )
    if kind == "混同":
        return (
            f"「{left_val}」と「{right_val}」を取り違えると誤答になります。"
            f"数字・主体・返還ルールのいずれかがずれた肢は、もう一方の説明が混ざっていないか確認してください。"
        )
    return (
        f"【{axis}】{left_val}と{right_val}を対照すると、"
        f"{subject}の論点整理がしやすくなります。"
    )


def hub_compare_points_body_html(entry: dict) -> str:
    exam_points = _norm(entry.get("exam_points"))
    if exam_points and not hub_field_is_stub(exam_points):
        items = hub_field_items(exam_points)
        if items:
            return hub_prose_html([i if i.endswith("。") else i + "。" for i in items])

    labels = entry.get("col_labels") or []
    rows = entry.get("compare_rows") or []
    lead = _norm(entry.get("article_lead")) or _norm(entry.get("summary"))
    title = _norm(entry.get("title"))

    paras: list[str] = []
    if lead:
        paras.append(lead)
    elif title:
        paras.append(f"{title}の違いは、根拠・期間・要件・返還のルールをセットで押さえることが重要です。")

    for row in rows:
        axis = _norm(row.get("axis"))
        if _axis_kind(axis) in {"試験", "混同"}:
            continue
        cols = row.get("cols") or []
        para = _compare_axis_paragraph(axis, labels, cols, title=title)
        if para:
            paras.append(para)

    category = _norm(entry.get("category"))
    if category:
        paras.append(
            f"{exam_name()}の{category}分野では、比較表を読んだあと関連用語の定義と過去問の条件文を照合すると定着しやすくなります。"
        )

    if len(paras) <= 1 and exam_points:
        for item in hub_field_items(exam_points):
            paras.append(
                f"試験では「{item}」のように短く問われるため、"
                f"比較表の該当行と関連条文をセットで確認してください。"
            )

    return hub_prose_html(paras)


def hub_compare_mistakes_body_html(entry: dict) -> str:
    common_mistakes = _norm(entry.get("common_mistakes"))
    labels = entry.get("col_labels") or []
    rows = entry.get("compare_rows") or []

    if common_mistakes and not hub_field_is_stub(common_mistakes):
        items = hub_field_items(common_mistakes)
        if items:
            return hub_prose_html([i if i.endswith("。") else i + "。" for i in items])
        return hub_prose_html([common_mistakes])

    paras: list[str] = []
    for row in rows:
        axis = _norm(row.get("axis"))
        if _axis_kind(axis) in {"混同", "試験"}:
            para = _compare_axis_paragraph(axis, labels, row.get("cols") or [], title=_norm(entry.get("title")))
            if para:
                paras.append(para)

    if not paras and common_mistakes:
        for item in hub_field_items(common_mistakes):
            paras.append(
                f"過去問では「{item}」のように、一方の制度の要件や期間を他方に当てはめる誤答が選ばれやすいです。"
                f"比較表と用語解説で定義を確認してから演習に進んでください。"
            )

    if not paras and len(labels) >= 2:
        paras.append(
            f"{labels[0]}と{labels[1]}は別制度です。"
            f"数字・主体・返還ルールのいずれかがずれた肢は、もう一方の制度の説明が混ざっていないか確認してください。"
        )

    return hub_prose_html(paras)


def hub_compare_memory_body_html(entry: dict) -> str:
    memory_tip = _norm(entry.get("memory_tip"))
    labels = entry.get("col_labels") or []
    rows = entry.get("compare_rows") or []
    title = _norm(entry.get("title"))

    if memory_tip and len(memory_tip) >= 48 and not hub_field_is_stub(memory_tip):
        return f'<div class="term-memory-guide"><p>{html.escape(memory_tip)}</p></div>'

    parts: list[str] = []
    if memory_tip:
        parts.append(memory_tip.rstrip("。") + "。")

    period_row = next((r for r in rows if _norm(r.get("axis")) == "期間"), None)
    basis_row = next((r for r in rows if _norm(r.get("axis")) == "根拠"), None)
    if period_row and len(labels) >= 2:
        cols = period_row.get("cols") or []
        if len(cols) >= 2:
            parts.append(
                f"比較表の「期間」行で{labels[0]}は{cols[0]}、{labels[1]}は{cols[1]}と対照して覚えます。"
            )
    if basis_row and len(labels) >= 2:
        cols = basis_row.get("cols") or []
        if len(cols) >= 2:
            parts.append(
                f"根拠もセットで整理すると定着しやすいです（{labels[0]}＝{cols[0]}／{labels[1]}＝{cols[1]}）。"
            )

    if title:
        parts.append(
            f"表を読んだあとは関連用語の用語解説で定義を確認し、"
            f"「{title}」に関する過去問を1問解いて返還ルールまで含めて整理してください。"
        )

    text = " ".join(parts)
    return f'<div class="term-memory-guide"><p>{html.escape(text)}</p></div>' if text else ""


def hub_numbers_points_body_html(entry: dict) -> str:
    exam_points = _norm(entry.get("exam_points"))
    item_rows = entry.get("item_rows") or entry.get("detail_rows") or []
    title = _norm(entry.get("title"))
    highlight = _norm(entry.get("highlight"))

    exam_items = hub_field_items(exam_points)
    if exam_items and not hub_field_is_stub(exam_points) and not _hub_exam_points_are_scaffold(exam_items):
        return hub_prose_html([i if i.endswith("。") else i + "。" for i in exam_items])

    paras: list[str] = []
    seen: set[str] = set()

    def _add(para: str) -> None:
        p = para.strip()
        if not p or p in seen:
            return
        seen.add(p)
        paras.append(p if p.endswith("。") else p + "。")

    if highlight and len(highlight) >= 16:
        _add(highlight)

    substantive_rows = [r for r in item_rows if _hub_numeric_row_is_substantive(r, title=title)]
    for row in substantive_rows[:8]:
        _add(_hub_numeric_row_point(row))

    if exam_items and not _hub_exam_points_are_scaffold(exam_items):
        for item in exam_items:
            _add(item)
    elif exam_items:
        for item in exam_items:
            if "定義と主体" in item:
                _add("試験では、用語の定義と義務主体を先に固定してから数値・期限を当てはめてください。")
            elif "類似語" in item or "入替" in item:
                _add("似た制度名や近い数字を入れ替えた肢が誤答として出やすいため、比較表で整理してください。")
            elif "境界" in item:
                _add("関連制度との境界（期間・主体・手続の時点）を表で照合してから暗記してください。")
            else:
                _add(item)

    if title and len(paras) <= 1:
        _add(
            f"「{title}」は数字だけでなく、義務主体・手続の時点・記録保存まで一体で確認する問題が多いです。"
            f"表の各行を過去問の条件文に当てはめて演習してください。"
        )
    return hub_prose_html(paras)


def hub_mistakes_points_body_html(entry: dict) -> str:
    exam_points = _norm(entry.get("exam_points"))
    pattern_rows = entry.get("pattern_rows") or entry.get("detail_rows") or []
    lead = _norm(entry.get("article_lead")) or _norm(entry.get("summary"))
    confusion = _norm(entry.get("confusion_point"))

    if exam_points and not hub_field_is_stub(exam_points):
        items = hub_field_items(exam_points)
        if items:
            return hub_prose_html([i if i.endswith("。") else i + "。" for i in items])

    paras: list[str] = []
    if lead:
        paras.append(lead)
    if confusion and len(confusion) >= 20:
        paras.append(confusion if confusion.endswith("。") else confusion + "。")
    for row in pattern_rows:
        topic = _norm(row.get("topic"))
        wrong = _norm(row.get("wrong"))
        correct = _norm(row.get("correct"))
        trap = _norm(row.get("trap"))
        if not (topic and wrong and correct):
            continue
        para = (
            f"「{topic}」では「{wrong.rstrip('。')}」と誤解しやすいですが、"
            f"正しくは{correct.rstrip('。')}。"
        )
        if trap:
            para += trap if trap.endswith("。") else trap + "。"
        else:
            para += "選択肢で主語や数字だけが正しい肢に注意してください。"
        paras.append(para)

    title = _norm(entry.get("title"))
    if title and not paras:
        paras.append(
            f"「{title}」では、似た制度名や近い数値を入れ替えた肢が誤答として出やすいです。"
            f"正誤の根拠となる条文・数値・主体をセットで確認してください。"
        )
    return hub_prose_html(paras)


def hub_stub_mistakes_body_html(entry: dict, *, fallback_field: str = "common_mistakes") -> str:
    """数値・誤答ハブ共通の誤解セクション。"""
    common_mistakes = _norm(entry.get(fallback_field))
    if common_mistakes and not hub_field_is_stub(common_mistakes):
        items = hub_field_items(common_mistakes)
        if items:
            return hub_prose_html([i if i.endswith("。") else i + "。" for i in items])
        return hub_prose_html([common_mistakes])

    paras: list[str] = []
    for item in hub_field_items(common_mistakes):
        paras.append(
            f"「{item}」と短く覚えると、選択肢の微妙な差（期間・主体・数値）を見落としやすくなります。"
            f"表の該当行と公式情報で最新の数値・要件を確認してください。"
        )
    highlight = _norm(entry.get("highlight")) or _norm(entry.get("confusion_point"))
    if highlight and len(highlight) >= 16:
        paras.insert(0, highlight if highlight.endswith("。") else highlight + "。")
    return hub_prose_html(paras)


def hub_stub_memory_body_html(entry: dict) -> str:
    memory_tip = _norm(entry.get("memory_tip"))
    title = _norm(entry.get("title"))
    item_rows = entry.get("item_rows") or entry.get("detail_rows") or []
    if memory_tip and len(memory_tip) >= 48 and not hub_field_is_stub(memory_tip):
        return f'<div class="term-memory-guide"><p>{html.escape(memory_tip)}</p></div>'

    parts: list[str] = []
    if memory_tip:
        parts.append(memory_tip.rstrip("。") + "。")

    substantive = [r for r in item_rows if not _hub_row_is_placeholder(r)][:3]
    if substantive:
        bits = []
        for row in substantive:
            item = _norm(row.get("item"))
            value = _norm(row.get("value"))
            if item and value:
                bits.append(f"{item}＝{value}")
        if bits:
            parts.append(f"表では{'／'.join(bits)}を対照して覚えます。")

    if title:
        parts.append(
            f"数値・期限は年度で変わることがあるため、"
            f"「{title}」の表を見たあとは試験要項と公式情報で最新を確認し、関連する過去問で当てはめ問題を1問解いてください。"
        )
    text = " ".join(parts)
    return f'<div class="term-memory-guide"><p>{html.escape(text)}</p></div>' if text else ""


def hub_faq_items_resolved(
    entry: dict,
    fallback: list[dict[str, str]],
    *,
    hub_type: str = "compare",
) -> list[dict[str, str]]:
    """CSV FAQ を採用。同一回答のコピペがあれば差し替える。"""

    def _plain(body_html: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body_html or "")).strip()

    items: list[dict[str, str]] = []
    for n in range(1, 5):
        q = _norm(entry.get(f"faq_{n}_question"))
        a = _norm(entry.get(f"faq_{n}_answer"))
        if q and a:
            items.append({"question": q, "answer": a})
    if not items:
        return fallback

    answers = [i["answer"] for i in items]
    unique_count = len(set(answers))
    all_substantive = unique_count == len(answers) and all(len(a) >= 80 for a in answers)
    if all_substantive:
        return items

    title = _norm(entry.get("title"))
    lead = _norm(entry.get("article_lead")) or _norm(entry.get("summary"))
    if hub_type == "compare":
        points_text = _plain(hub_compare_points_body_html(entry))
        mistakes_text = _plain(hub_compare_mistakes_body_html(entry))
        memory_text = _plain(hub_compare_memory_body_html(entry))
    elif hub_type == "numbers":
        points_text = _plain(hub_numbers_points_body_html(entry))
        mistakes_text = _plain(hub_stub_mistakes_body_html(entry))
        memory_text = _plain(hub_stub_memory_body_html(entry))
    elif hub_type == "mistakes":
        points_text = _plain(hub_mistakes_points_body_html(entry))
        mistakes_text = _plain(hub_stub_mistakes_body_html(entry, fallback_field="confusion_point"))
        if not mistakes_text:
            mistakes_text = _plain(hub_stub_mistakes_body_html(entry))
        memory_text = _plain(hub_stub_memory_body_html(entry))
    else:
        points_text = lead
        mistakes_text = _plain(hub_stub_mistakes_body_html(entry))
        memory_text = _plain(hub_stub_memory_body_html(entry))

    official = external_links() or [primary_external_link()]
    official_names = "・".join(link["label"] for link in official[:2])

    rebuilt: list[dict[str, str]] = []
    for item in items:
        q = item["question"]
        if "位置づけ" in q or "試験での" in q:
            rebuilt.append({"question": q, "answer": points_text or lead or item["answer"]})
        elif "誤答" in q or "誤解" in q:
            rebuilt.append({"question": q, "answer": mistakes_text or item["answer"]})
        elif "覚え方" in q or "確認手順" in q:
            rebuilt.append({"question": q, "answer": memory_text or item["answer"]})
        elif "公式" in q:
            rebuilt.append(
                {
                    "question": q,
                    "answer": (
                        f"「{title}」の数値・手続・要件は年度で見直されることがあります。"
                        f"受験前には{official_names}などの公式情報で最新を確認してください。"
                    ),
                }
            )
        else:
            rebuilt.append(item)
    return rebuilt


_EXAM_POINT_FRAGMENT_ENDINGS = ("で", "を", "に", "が", "と", "へ", "や")


def _exam_points_look_low_quality(items: list[str]) -> bool:
    if any(item.startswith("数値・期限：") for item in items):
        return True
    if any(item.startswith("根拠：") for item in items[:-1]):
        return True
    for item in items:
        text = item.rstrip("。").strip()
        if text.endswith(_EXAM_POINT_FRAGMENT_ENDINGS) and len(text) < 40:
            if not text.endswith(("ないで", "として", "について", "において")):
                return True
    if len(items) >= 2 and items[0].rstrip("。").endswith("で"):
        if not items[0].rstrip("。").endswith("ないで"):
            return True
    return False


def _glossary_study_point_items(entry: dict, *, max_items: int = 3) -> list[str]:
    """定義文から完結した学習要点を組み立てる（読点分割は使わない）。"""
    short_def = _norm(entry.get("short_def"))
    definition = (
        _norm(entry.get("term_detail_body"))
        or _norm(entry.get("definition"))
        or short_def
    )
    exam_points = split_semicolon(_norm(entry.get("exam_points")))

    if exam_points and not any(
        any(marker in item for marker in _MISTAKE_POINT_MARKERS) for item in exam_points
    ):
        cleaned = [item.strip() for item in exam_points if len(item.strip()) >= 8]
        cleaned = [item for item in cleaned if not item.startswith("根拠：")]
        if cleaned and not _exam_points_look_low_quality(cleaned):
            return cleaned[:max_items]

    items: list[str] = []
    core = short_def
    if "とは、" in core:
        core = core.split("とは、", 1)[1]
    core = core.strip().lstrip("「").rstrip("」")
    core = re.sub(r"です$", "", core).strip()
    if core:
        items.append(core)

    first_norm = short_def.replace(" ", "")
    for sent in _definition_sentences(definition):
        text = sent.rstrip("。").strip()
        if len(text) < 12:
            continue
        text_norm = text.replace(" ", "")
        if text_norm in first_norm or first_norm in text_norm:
            continue
        items.append(text)
        if len(items) >= max_items:
            break

    return items[:max_items]


def glossary_exam_points_items(entry: dict) -> list[str]:
    """section 2 用。完結した学習要点を箇条書き用に返す。"""
    legal = _norm(entry.get("legal_basis"))
    items = _glossary_study_point_items(entry, max_items=3)

    legal_first = split_semicolon(legal)[0].strip() if legal else ""
    if legal_first and not any(legal_first in item for item in items):
        items.append(f"根拠：{legal_first}")
    return items[:5]


def glossary_exam_points_body_html(entry: dict) -> str:
    """用語ページの試験ポイント（exam_points を箇条書きでそのまま表示）。"""
    items = glossary_exam_points_items(entry)
    if not items:
        return ""
    lis: list[str] = []
    for item in items:
        text = item.rstrip("。").strip()
        if text.startswith("根拠："):
            lis.append(f"{text}を条文とセットで確認する")
        else:
            lis.append(text)
    return "<ul>" + "".join(f"<li>{html.escape(t)}</li>" for t in lis[:5]) + "</ul>"


_DEFINITION_STRIP_RES = (
    re.compile(r"【(?:専門家の視点|現場での意味|試験で差がつく見方|まとめ)】[^。\n]*。"),
    re.compile(r"有害要因では[^。\n]*。"),
    re.compile(r"ここでは[^。\n]*整理します。"),
    re.compile(r"条文番号だけでなく[^。\n]*。"),
    re.compile(r"過去問では[^。\n]*見られます。"),
    re.compile(r"まとめると、[^。\n]*。"),
    re.compile(r"本記事の表と[^。\n]*。"),
    re.compile(r"※上記は[^。\n]*。"),
    re.compile(r"定義＋数値＋手続」の5点[^。\n]*。"),
    re.compile(r"失点差がつきやすい[^。\n]*。"),
    re.compile(r"試験対策では[^。\n]*。"),
    re.compile(r"過去問演習では[^。\n]*。"),
    re.compile(r"実務目線では[^。\n]*。"),
)
_DEFINITION_NUM_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(人|時間|か月|月|年|日|回|週|mSv|mg/m³|mg|dB|ppm|%|時間以内|年間|回まで|回以上|人以上|時間超)"
)
_DEFINITION_SKIP_SENTENCE = (
    "管理業務主任者試験では",
    "第一種衛生管理者試験では",
    "頻出となる基礎用語",
    "失点差がつきやすい",
    "試験対策では",
    "過去問演習では",
    "実務目線では",
    "条文根拠と実務場面を往復",
    "手続・判断基準を押さえる論点",
)
_DEFINITION_BODY_MAX_CHARS = 600
_DEFINITION_DETAIL_MAX_PARAS = 2
_TERM_DETAIL_SECTION_HEADERS = frozenset(
    {
        "定義",
        "条文上の根拠",
        "試験で問われやすいポイント",
        "よくある誤解",
        "記憶のコツ",
        "関連分野",
        "根拠",
        "試験のポイント",
        "具体例",
    }
)
_TERM_DETAIL_SKIP_SECTIONS = frozenset(
    {
        "試験で問われやすいポイント",
        "よくある誤解",
        "記憶のコツ",
        "関連分野",
    }
)
_TERM_DETAIL_PARA_SKIP_RES = (
    re.compile(r"^誤り。"),
    re.compile(r"^【試験"),
    re.compile(r"正しいものはどれか"),
    re.compile(r"記述のうち、正しい"),
    re.compile(r"^肢の数字・主体・期限"),
)


def _definition_body_keys(text: str) -> set[str]:
    keys: set[str] = set()
    compact = re.sub(r"\s+", "", text or "")
    if compact:
        keys.add(compact[:80])
    for sent in _definition_sentences(text or ""):
        sk = re.sub(r"\s+", "", sent)[:48]
        if sk:
            keys.add(sk)
    return keys


def _term_detail_prose_paragraphs(raw_body: str) -> list[str]:
    """term_detail_body から表・見出し・箇条書きを除いた説明段落を返す。"""
    text = re.sub(r"<table[\s\S]*?</table>", "", raw_body or "", flags=re.I).strip()
    if not text:
        return []

    def _finalize(lines: list[str], section: str) -> str | None:
        if section in _TERM_DETAIL_SKIP_SECTIONS or not lines:
            return None
        if all(ln.startswith(("・", "-", "◆")) for ln in lines):
            return None
        para = " ".join(ln for ln in lines if not ln.startswith(("・", "-", "◆")))
        para = re.sub(r"\s+", " ", para).strip()
        if len(para) < 20:
            return None
        if any(skip in para for skip in _DEFINITION_SKIP_SENTENCE):
            return None
        if any(pat.search(para) for pat in _TERM_DETAIL_PARA_SKIP_RES):
            return None
        return para

    paras: list[str] = []
    section = ""
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf, section
        para = _finalize(buf, section)
        if para:
            paras.append(para)
        buf = []

    for line in text.splitlines():
        s = line.strip()
        if not s:
            flush()
            continue
        if s in _TERM_DETAIL_SECTION_HEADERS:
            flush()
            section = s
            continue
        if section in _TERM_DETAIL_SKIP_SECTIONS:
            continue
        if s.startswith(("・", "-", "◆")):
            continue
        buf.append(s)
    flush()
    return paras


def _merge_term_detail_prose(parts: list[str], raw_body: str, *, max_chars: int) -> None:
    """short_def / definition 後に term_detail_body の散文を最大2段落まで追補。"""
    joined = "\n\n".join(parts)
    if len(joined) >= max_chars or not raw_body.strip():
        return
    existing = _definition_body_keys(joined)
    added = 0
    for para in _term_detail_prose_paragraphs(raw_body):
        if added >= _DEFINITION_DETAIL_MAX_PARAS:
            break
        new_sents: list[str] = []
        for sent in _definition_sentences(para):
            if any(skip in sent for skip in _DEFINITION_SKIP_SENTENCE):
                continue
            if any(pat.search(sent) for pat in _TERM_DETAIL_PARA_SKIP_RES):
                continue
            if re.match(r"^まず「", sent):
                continue
            sk = re.sub(r"\s+", "", sent)[:48]
            if not sk or sk in existing:
                continue
            new_sents.append(sent)
            existing.add(sk)
        if not new_sents:
            continue
        chunk = " ".join(new_sents)
        room = max_chars - len(joined) - (2 if parts else 0)
        if room < 40:
            break
        if len(chunk) > room:
            trimmed = chunk[:room]
            cut = trimmed.rfind("。")
            chunk = trimmed[: cut + 1] if cut >= 20 else trimmed
        if not chunk.strip():
            continue
        parts.append(chunk.strip())
        joined = "\n\n".join(parts)
        added += 1
        if len(joined) >= max_chars:
            break


def _definition_sentences(text: str) -> list[str]:
    parts: list[str] = []
    for chunk in re.split(r"(?<=[。．])", text.strip()):
        s = chunk.strip()
        if s:
            parts.append(s if s.endswith("。") else s + "。")
    return parts


def glossary_definition_body_text(entry: dict) -> str:
    """定義セクション用。short_def / definition に加え term_detail_body の散文も反映。"""
    term = _norm(entry.get("term"))
    category = _norm(entry.get("category"))
    short_def = _norm(entry.get("short_def"))
    definition = _norm(entry.get("definition"))
    raw_body = _norm(entry.get("term_detail_body"))

    tables = re.findall(r"<table[\s\S]*?</table>", raw_body, flags=re.I)

    parts: list[str] = []
    if short_def:
        parts.append(short_def if short_def.endswith("。") else short_def + "。")

    defn = definition or short_def
    body_so_far = "".join(parts)
    for sent in _definition_sentences(defn):
        if term:
            lead = re.match(
                rf"^まず「{re.escape(term)}」(?:は|とは)?[、,]?\s*(.+)",
                sent,
            )
            if lead:
                sent = lead.group(1).strip()
                if sent and not sent.endswith("。"):
                    sent += "。"
        if any(skip in sent for skip in _DEFINITION_SKIP_SENTENCE):
            continue
        key = re.sub(r"\s+", "", sent)[:48]
        if not key or key in re.sub(r"\s+", "", body_so_far):
            continue
        parts.append(sent)
        body_so_far = "".join(parts)
        if len(parts) >= 3:
            break

    nums: list[str] = []
    for m in _DEFINITION_NUM_RE.finditer(defn):
        val = m.group(1) + m.group(2)
        if val not in nums:
            nums.append(val)
    joined = "".join(parts)
    if nums and not any(n in joined for n in nums):
        parts.append(f"押さえる数値・期限：{'、'.join(nums[:4])}。")

    _merge_term_detail_prose(parts, raw_body, max_chars=_DEFINITION_BODY_MAX_CHARS)

    body = "\n\n".join(parts)
    if "有害" not in category:
        for pat in _DEFINITION_STRIP_RES:
            body = pat.sub("", body)
    else:
        for pat in _DEFINITION_STRIP_RES[:1]:
            body = pat.sub("", body)

    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if tables:
        body = body + "\n\n" + "\n\n".join(tables[:1])
    return body.strip() or definition or short_def


_LAW_CITATION_TAIL_RE = re.compile(r"（[^）]*(?:法|令|則|規則|条例)[^）]*）\s*$")


def _law_matches(sent: str, law: str) -> bool:
    if law in sent:
        return True
    base = re.sub(r"第?\d+条.*", "", law).strip()
    return len(base) >= 2 and base in sent


def _definition_core_from_sentence(sent: str, term: str) -> str:
    s = sent.strip().rstrip("。")
    if term:
        quoted = f"「{term}」とは、"
        if s.startswith(quoted):
            s = s[len(quoted) :]
        elif "とは、" in s:
            s = s.split("とは、", 1)[1]
    s = _LAW_CITATION_TAIL_RE.sub("", s).strip()
    s = re.sub(
        r"です?（[^）]*(?:法|令|則|規則|条例)[^）]*）\s*$",
        "",
        s,
    ).strip()
    s = s.lstrip("「").rstrip("」").rstrip("。")
    s = re.sub(r"です$", "", s).strip()
    return s


def _legal_source_text(entry: dict) -> str:
    return (
        _norm(entry.get("term_detail_body"))
        or _norm(entry.get("definition"))
        or _norm(entry.get("short_def"))
    )


def _legal_explain_sentence(law: str, entry: dict) -> str:
    """根拠条文を、定義文から平易な解説1文（＋必要なら補足1文）に整える。"""
    term = _norm(entry.get("term"))
    short_def = _norm(entry.get("short_def"))
    sentences = _definition_sentences(_legal_source_text(entry))

    main_core = ""
    extras: list[str] = []
    matched_first = False
    for sent in sentences:
        if any(skip in sent for skip in _DEFINITION_SKIP_SENTENCE):
            continue
        if _law_matches(sent, law):
            core = _definition_core_from_sentence(sent, term)
            if core:
                main_core = core
                matched_first = True
                continue
        if matched_first:
            extra = sent.rstrip("。").strip()
            if len(extra) >= 12:
                extras.append(extra)
                break

    if main_core:
        if main_core.endswith("について"):
            text = f"{law}は、{main_core}定めた条文です"
        else:
            text = f"{law}は、{main_core}について定めた条文です"
        if extras:
            text += f"。{extras[0]}"
        return text + "。"

    core = _definition_core_from_sentence(short_def, term)
    if core and not any(skip in core for skip in _DEFINITION_SKIP_SENTENCE):
        return f"{law}は、{core}に関する根拠法令です。"

    label = term.split("（")[0].strip() if term else "この用語"
    return f"{law}は、{label}の要件・手続を定める根拠法令です。"


def glossary_legal_body_html(entry: dict) -> str:
    """法令・根拠セクション。条文名と平易な解説文をセットで出力する。"""
    legal = _norm(entry.get("legal_basis"))
    if not legal:
        return ""
    blocks: list[str] = []
    for law in split_semicolon(legal):
        law = law.strip()
        if not law:
            continue
        explain = _legal_explain_sentence(law, entry)
        blocks.append(f'<p class="term-legal-cite">{html.escape(law)}</p>')
        blocks.append(f"<p>{html.escape(explain)}</p>")
    return "\n".join(blocks)


def _glossary_field_items(value: str) -> list[str]:
    return [x.strip() for x in re.split(r"[;；]", value or "") if x.strip()]


def _parse_trap_pair(item: str) -> tuple[str, str] | None:
    text = item.strip()
    if not text:
        return None
    m = re.match(r"^誤り肢の型\d+[：:]\s*(.+?)\s*→\s*(.+)$", text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m = re.match(r"^×\s*(.+?)\s*→\s*[○◯]?\s*(.+)$", text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m = re.match(r"^「(.+?)」\s*→\s*誤り[（(](.+?)[）)]", text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m = re.match(r"^(.+?)\s*→\s*誤り[（(](.+?)[）)]", text)
    if m:
        return m.group(1).strip().strip("「」"), m.group(2).strip()
    if " → " in text:
        left, right = text.split(" → ", 1)
        left = re.sub(r"^誤り肢の型\d+[：:]", "", left).strip().strip("「」")
        right = re.sub(r"^[○◯]\s*", "", right).strip()
        if left and right and len(left) >= 4:
            if (
                "誤り" in text
                or "誤り肢" in text
                or "要件" in left
                or "根拠" in left
                or text.strip().startswith("「")
            ):
                return left, right
    return None


def _trap_list_html(pairs: list[tuple[str, str]]) -> str:
    if not pairs:
        return ""
    lis: list[str] = []
    for wrong, correct in pairs:
        correct = correct.rstrip("。").strip()
        lis.append(
            f"<li>{_term_item_label('誤り')}：{html.escape(wrong)}"
            f"<br>{_term_item_label('正解の考え方')}：{html.escape(correct)}。</li>"
        )
    return '<ul class="term-trap-list">' + "".join(lis) + "</ul>"


def _checklist_html(items: list[str]) -> str:
    cleaned = [item.rstrip("。").strip() for item in items if item.strip()]
    if not cleaned:
        return ""
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in cleaned) + "</ul>"


def glossary_exam_choices_body_html(entry: dict) -> str:
    """section 4「選択肢で問われやすい点」。区切り記号で分割し、観点と誤り肢を整理して表示。"""
    explanation = _norm(entry.get("explanation"))
    if not explanation:
        return ""

    items = _glossary_field_items(explanation)
    if len(items) <= 1 and "；" not in explanation and ";" not in explanation:
        sentences = _definition_sentences(explanation)
        return hub_prose_html(sentences[:4] if sentences else [explanation])

    intro = ""
    checks: list[str] = []
    traps: list[tuple[str, str]] = []

    for item in items:
        pair = _parse_trap_pair(item)
        if pair:
            traps.append(pair)
            continue
        if not intro and ("問われます" in item or "問われやすい" in item):
            intro = item if item.endswith("。") else item + "。"
            continue
        if item.startswith("試験での確認"):
            continue
        if len(item) >= 6:
            checks.append(item)

    parts: list[str] = []
    if intro:
        parts.append(f"<p>{html.escape(intro)}</p>")
    if checks:
        parts.append('<h3 class="term-subheading">確認する観点</h3>')
        parts.append(_checklist_html(checks))
    if traps:
        parts.append('<h3 class="term-subheading">出やすい誤り肢</h3>')
        parts.append(_trap_list_html(traps))

    if parts:
        return "\n".join(parts)

    traps = [pair for item in items if (pair := _parse_trap_pair(item))]
    if traps:
        return (
            '<h3 class="term-subheading">出やすい誤り肢</h3>'
            + _trap_list_html(traps)
        )

    return hub_prose_html([explanation])


def glossary_mistakes_body_html(entry: dict) -> str:
    common_mistakes = _norm(entry.get("common_mistakes"))
    term = _norm(entry.get("term"))
    related = _norm(entry.get("related_terms"))

    if common_mistakes:
        items = _glossary_field_items(common_mistakes)
        pairs = [pair for item in items if (pair := _parse_trap_pair(item))]
        if pairs:
            return _trap_list_html(pairs)

        prose = [item for item in items if len(item) >= 40]
        if prose and all(len(i) >= 40 for i in prose):
            return hub_prose_html(prose)

        short = [item for item in items if len(item) >= 8]
        if len(short) >= 2:
            return _checklist_html(short)

        if len(items) == 1 and len(items[0]) >= 40:
            return hub_prose_html(items)

    paras: list[str] = []
    if related:
        peers = [x for x in split_semicolon(related) if x and x != term][:2]
        if peers:
            paras.append(
                f"{term}は{'・'.join(peers)}などと混同しやすい用語です。"
                f"定義・数値・主体のいずれかがずれた肢は、関連用語の説明が混ざっていないか確認してください。"
            )
    if term and not paras:
        paras.append(
            f"{term}では、定義の言い換えだけが正しく見える選択肢に注意してください。"
            f"条文上の要件や数値まで一致しているかを確認する習慣をつけましょう。"
        )
    return hub_prose_html(paras)


def _memory_tip_lines(memory_tip: str) -> list[str]:
    text = memory_tip.strip()
    if not text:
        return []
    if text.count("■") > 1:
        parts = re.split(r"(?=■)", text)
        return [part.strip() for part in parts if part.strip()]
    return [line.strip() for line in text.splitlines() if line.strip()]


def glossary_memory_body_html(entry: dict) -> str:
    memory_tip = _norm(entry.get("memory_tip"))
    term = _norm(entry.get("term"))
    short_def = _norm(entry.get("short_def"))

    if not memory_tip:
        if short_def and term:
            text = f"「{term}」は{short_def.rstrip('。')}。定義を声に出してから関連する過去問を1問解くと定着しやすくなります。"
            return f'<div class="term-memory-guide"><p>{html.escape(text)}</p></div>'
        return ""

    labeled: list[tuple[str, str]] = []
    free_lines: list[str] = []
    for line in _memory_tip_lines(memory_tip):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^■\s*([^：:]+)[：:]\s*(.+)$", line)
        if m:
            labeled.append((m.group(1).strip(), m.group(2).strip()))
        elif line.startswith("■"):
            free_lines.append(line.lstrip("■").strip())
        else:
            free_lines.append(line)

    parts: list[str] = []
    if labeled:
        lis = []
        for label, content in labeled:
            content = content.rstrip("。").strip()
            lis.append(
                f"<li>{_term_item_label(label)}：{html.escape(content)}。</li>"
            )
        parts.append("<ul>" + "".join(lis) + "</ul>")
    elif free_lines:
        parts.append(hub_prose_html(free_lines[:5]))

    if term:
        parts.append(
            f"<p>最後に「{html.escape(term)}」が登場する過去問を1問解き、"
            "選択肢の根拠まで言語化して整理してください。</p>"
        )

    body = "\n".join(parts)
    return f'<div class="term-memory-guide">{body}</div>' if body else ""


_MISTAKE_POINT_MARKERS = ("→ 誤り", "誤り（", "誤答", "入れ替えに注意")


def glossary_summary_body_html(short_def: str) -> str:
    """「まず押さえる要点」用。定義文を1段落のまま出力する。"""
    text = _norm(short_def)
    if not text:
        return ""
    return f"<p>{html.escape(text)}</p>"


def glossary_key_points_items(entry: dict) -> list[str]:
    """要点ボックス用。誤答パターンではなく、定義・根拠から学習要点を組み立てる。"""
    term = _norm(entry.get("term"))
    legal = _norm(entry.get("legal_basis"))
    items = list(_glossary_study_point_items(entry, max_items=3))

    legal_first = split_semicolon(legal)[0].strip() if legal else ""
    if legal_first and not any(legal_first in item for item in items):
        items.append(f"根拠：{legal_first}")

    if len(items) < 3:
        items.append(f"{term or '用語'}の定義と数値・主体を条文とセットで確認する")
    if not any("過去問" in item for item in items):
        items.append("関連する用語解説や過去問へ進む")
    return items[:5]
