#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/glossary_terms.csv から用語ページ terms/g-*.html と terms/index.html を生成し、
過去問と合わせた sitemap.xml を書き直す。

用語一覧（terms/index.html）は検索・分野絞り込みのみ。件数が増えてもページネーションは付けない。
"""

from __future__ import annotations

import csv
import hashlib
import html
import shutil
import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.html_footer import (
    ROBOTS_INDEX_FOLLOW,
    breadcrumb_html,
    shell_body_class,
    site_page_footer,
    site_page_header,
    site_page_wrap_close,
    site_page_wrap_open,
)
from tools.knowledge_hub_tabs import knowledge_hub_tab_hrefs, knowledge_hub_tabs_html
from tools.seo_utils import (
    content_date_from_row,
    json_ld_date_modified,
    latest_content_date,
    meta_updated_html,
    robots_meta_for_slug,
)
from tools.term_diagram import diagram_body_html
from tools.seo_body_markup import seo_section_body_html  # noqa: E402
from tools.site_config import (
    brand_name,
    category_order,
    category_to_field_map,
    clean_origin,
    css_safe_field_id,
    exam_name,
    external_links,
    field_labels,
    primary_external_link,
)

from tools.seo_editorial_chrome import (  # noqa: E402
    seo_editorial_article_class,
    seo_editorial_head_fonts,
    seo_editorial_stylesheet_links,
)

PRESERVED_TERM_SUBDIRS = frozenset({"compare", "numbers", "mistakes", "priority", "samples", "diagram-samples"})
PRESERVED_TERM_HTML = frozenset({"index.html", "g-writing-sample.html", "g-diagram-sample.html"})

GLOSSARY_CSV = ROOT / "data" / "glossary_terms.csv"
TERMS_DIR = ROOT / "terms"
BASE_DEFAULT = clean_origin()

# site-config.json の fields[].aliases / name と揃える
FIELD_LABELS = field_labels()
GLOSSARY_CAT_TO_FIELD: dict[str, str] = category_to_field_map()

# 用語索引ページの科目チップ・見出しの並び（CSV のカテゴリ名と一致）
GLOSSARY_CAT_ORDER = tuple(category_order())

RELATED_TERM_ALIASES: dict[str, str] = {
    "一括再委託": "学習範囲の一括再委託の禁止",
    "一括再委託の禁止": "学習範囲の一括再委託の禁止",
    "実務論点ガイドライン": "実務論点をめぐるトラブルとガイドライン",
    "原契約": "原契約契約",
    "原契約契約終了": "原契約契約の終了と転貸借",
    "重要事項説明": "重要事項説明（宅建業法）",
    "定期建物契約": "定期建物契約契約",
    "普通建物契約": "普通建物契約契約",
    "同時履行の抗弁": "同時履行の抗弁権",
    "改正民法": "改正民法（2020年4月施行）",
    "無断転貸": "無断譲渡・無断転貸",
    "個人根保証": "個人根保証契約",
    "住宅宿泊事業法": "住宅宿泊事業法（民泊新法）",
    "ビルマネジメント": "ビルマネジメント（BM）",
    "プロパティマネジメント": "プロパティマネジメント（PM）",
    "LPガス": "LPガス（プロパンガス）",
    "RC造": "鉄筋コンクリート造（RC造）",
    "SRC造": "鉄骨鉄筋コンクリート造（SRC造）",
    "DX": "DXによる学習テーマ経営",
    "バリアフリー新法": "バリアフリー",
    "不動産鑑定": "不動産鑑定評価",
    "事故物件ガイドライン": "人の死の告知に関するガイドライン",
    "人の死の告知ガイドライン": "人の死の告知に関するガイドライン",
    "クリーニング費用特約": "クリーニング費用",
    "借主負担": "借主負担特約",
    "借地権者": "借地権",
    "封水": "封水切れ",
    "建物の引渡し": "建物の引渡しによる対抗要件",
    "強迫": "詐欺・強迫",
    "従業者": "従業者証明書",
    "換気": "換気設備",
    "断熱": "断熱性能",
    "更新拒絶": "更新拒絶通知",
    "消防用設備": "消防用設備等点検",
    "特定空家": "特定空家等",
    "瑕疵担保責任": "瑕疵担保責任から契約不適合責任へ",
    "管理規約": "管理規約・使用細則",
    "規約": "管理規約・使用細則",
    "紛争解決": "ADR（裁判外紛争解決手続）",
    "近隣対応": "近隣対応・周辺対応",
    "高置水槽": "高置水槽方式",
    "防犯": "防犯カメラ",
    "長期・短期譲渡所得": "譲渡所得",
}


def norm(s: str | None) -> str:
    return (s or "").strip()


def lookup_key(s: str) -> str:
    return re.sub(r"\s+", "", s)


def term_alias_variants(term: str) -> set[str]:
    variants = {term, lookup_key(term)}
    no_paren = re.sub(r"（[^）]+）|\([^)]*\)", "", term).strip()
    if no_paren and no_paren != term:
        variants.add(no_paren)
        variants.add(lookup_key(no_paren))
    for part in re.findall(r"（([^）]+)）|\(([^)]*)\)", term):
        inner = next((x for x in part if x), "").strip()
        if inner:
            variants.add(inner)
            variants.add(lookup_key(inner))
    return {v for v in variants if v}


def term_slug(term: str, reading: str | dict[str, str] = "", used: dict[str, str] | None = None) -> str:
    """用語+読みで安定したスラッグ。衝突時は連番を付与。

    テンプレ互換: term_slug(term, used_slugs) も可（reading 省略）。
    """
    if isinstance(reading, dict):
        used = reading
        reading = ""
    if used is None:
        used = {}
    reading = str(reading).strip() if not isinstance(reading, dict) else ""
    # reading なしは term のみでハッシュ（既存公開 URL との互換）
    base = f"{term.strip()}|{reading}" if reading else term.strip()
    h = hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]
    s = f"g-{h}"
    if s not in used:
        used[s] = base
        return s
    n = 2
    while True:
        cand = f"g-{h}-{n}"
        if cand not in used:
            used[cand] = base
            return cand
        n += 1

def slug_file_for_glossary_row(row: dict, used_slugs: dict[str, str]) -> str:
    """build_glossary_pages とハブ lookup で同一 slug を使う。"""
    term = norm(row.get("term"))
    if not term:
        raise ValueError("term が空です")
    legacy_slug = norm(row.get("slug")) or norm(row.get("url_slug"))
    if legacy_slug:
        slug_file = f"{legacy_slug}.html"
    else:
        reading = norm(row.get("reading"))
        slug_file = term_slug(term, reading, used_slugs) + ".html"
    used_slugs[slug_file] = term
    return slug_file



def public_url(base: str, rel_path: str) -> str:
    return f"{base.rstrip('/')}/{rel_path.lstrip('/')}"


def rel_to_root(rel_file: Path) -> str:
    depth = len(rel_file.parent.parts)
    return "/".join([".."] * depth) + "/index.html"


def rel_css(rel_file: Path) -> str:
    depth = len(rel_file.parent.parts)
    return "/".join([".."] * depth) + f"/site-pages.css?v={TERMS_INDEX_CSS_VER}"


def rel_theme_css(rel_file: Path) -> str:
    depth = len(rel_file.parent.parts)
    return "/".join([".."] * depth) + "/site-theme.css"


def rel_editorial_css(rel_file: Path) -> str:
    return seo_editorial_stylesheet_links(rel_file, site_pages_ver=TERMS_INDEX_CSS_VER)


# 後方互換（他スクリプトが HEAD_FONTS を import する場合）
HEAD_FONTS = seo_editorial_head_fonts()


def glossary_field_id(category: str) -> str | None:
    return GLOSSARY_CAT_TO_FIELD.get(norm(category))


def glossary_field_badge_html(category: str) -> str:
    fid = glossary_field_id(category)
    if not fid:
        return ""
    label = FIELD_LABELS.get(fid, fid)
    return f'<span class="term-field-badge term-field-{css_safe_field_id(fid)}">{html.escape(label)}</span>'


def ordered_term_categories(by_cat: dict[str, list]) -> list[str]:
    keys = set(by_cat.keys())
    out: list[str] = [c for c in GLOSSARY_CAT_ORDER if c in keys]
    for c in sorted(keys):
        if c not in out:
            out.append(c)
    return out


def meta_description(text: str, limit: int = 155) -> str:
    one = re.sub(r"\s+", " ", text).strip()
    if len(one) <= limit:
        return one
    return one[: limit - 1] + "…"


def split_semicolon(s: str) -> list[str]:
    return [x.strip() for x in re.split(r"[;；]", s or "") if x.strip()]


TERMS_INDEX_CSS_VER = "20260524-terms-table-14px"
TERMS_INDEX_JS_VER = "20260521-terms-snippet"
TERMS_INDEX_SEARCH_PLACEHOLDER = "例：ストレスチェック、ラインケア、うつ病…"

# CSV enrich 時の分野テンプレ（一覧の定義抜粋には出さない）
_GENERIC_SNIPPET_SUFFIXES = (
    "に関わる用語です。",
    "を整理する際に使われます。",
    "と関係します。",
    "を確認します。",
    "を確認するために使われます。",
    "を考える場面で出てきます。",
    "につながる経営課題として捉えます。",
    "を説明する際に使われます。",
    "を検討します。",
)


def parse_term_tags(raw: str) -> list[str]:
    return [t.strip() for t in re.split(r"[,、/|]", raw or "") if t.strip()]


def terms_index_href(slug_file: str) -> str:
    """用語一覧からのリンク（/terms/ 配下）。pathname が /terms のときも壊れないようルート相対にする。"""
    return f"/terms/{slug_file.lstrip('/')}"



def sort_terms_index_entries(entries: list[dict]) -> list[dict]:
    return sorted(
        entries,
        key=lambda e: (
            e.get("category") or "",
            e.get("term") or "",
        ),
    )


def _is_generic_index_snippet(text: str, term: str) -> bool:
    t = (text or "").strip()
    if not t or not term or not t.startswith(term):
        return False
    return any(t.endswith(suffix) for suffix in _GENERIC_SNIPPET_SUFFIXES)


def terms_index_snippet(entry: dict) -> str:
    """一覧・検索用の定義抜粋。enrich テンプレ文は definition から実義を拾う。"""
    term = (entry.get("term") or "").strip()
    short = (entry.get("short_def") or "").strip()
    definition = (entry.get("definition") or "").strip()

    if definition and term:
        # まず「用語」は、本文…（kikenbutsu 等）— 引用符内の用語名だけを拾わない
        lead = re.search(
            rf"まず「{re.escape(term)}」(?:は|とは)?[、,]?\s*(.+)",
            definition,
        )
        if lead:
            body = lead.group(1).strip()
            first = re.split(r"(?<=[。！？])", body, maxsplit=1)[0].strip()
            if first and not _is_generic_index_snippet(first, term):
                if not first.endswith(("。", "！", "？")):
                    first = f"{first}。"
                return first[:200]

    if definition:
        m = re.search(r"まず「([^」]+)」", definition)
        if m:
            clause = m.group(1).strip()
            if (
                clause
                and clause != term
                and not _is_generic_index_snippet(clause, term)
            ):
                if clause.startswith(term):
                    return clause if clause.endswith("。") else f"{clause}。"
                body = clause.rstrip("。")
                return f"{term}は、{body}。" if body else short

    if short and not _is_generic_index_snippet(short, term):
        return short

    if definition:
        for part in re.split(r"(?<=[。！？])", definition):
            part = part.strip()
            if part and part != short and not _is_generic_index_snippet(part, term):
                return part[:200]
    return short


def render_terms_index_tbody(entries: list[dict]) -> str:
    """JS 未実行時も一覧が見えるよう、全件の tbody をサーバー側で生成する（1語1行・3列）。"""
    items = sort_terms_index_entries(entries)
    rows: list[str] = []

    for item in items:
        href = html.escape(terms_index_href(item["slug_file"]))
        href_attr = f' data-entry-href="{href}"'
        short_def = html.escape(terms_index_snippet(item))
        rows.append(
            "<tr class=\"terms-idx-table-row\">"
            f'<td class="terms-idx-td-term" data-label="用語"{href_attr} tabindex="0">'
            f'<div class="terms-idx-term-cell"><a href="{href}">{html.escape(item["term"])}</a>'
            f"</div></td>"
            f'<td class="terms-idx-td-cat" data-label="分野"{href_attr}>'
            f'{html.escape(item.get("category") or "")}</td>'
            f'<td class="terms-idx-td-snippet" data-label="定義"{href_attr}>'
            f"{short_def}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def terms_index_item_dict(entry: dict) -> dict:
    tags = parse_term_tags(entry.get("tags") or "")
    snippet = terms_index_snippet(entry)
    search_bits = [
        entry["term"],
        entry.get("category") or "",
        snippet,
        *tags,
    ]
    return {
        "term": entry["term"],
        "category": entry.get("category") or "",
        "tags": tags,
        "shortDef": snippet,
        "href": terms_index_href(entry["slug_file"]),
        "fieldHub": entry.get("field_hub") or "",
        "search": " ".join(x for x in search_bits if x),
    }


def build_terms_list_item(entry: dict) -> str:
    href = html.escape(terms_index_href(entry["slug_file"]))
    term = html.escape(entry["term"])
    snippet = html.escape(terms_index_snippet(entry))
    snippet_html = (
        f'<span class="terms-idx-snippet">{snippet}</span>' if snippet else ""
    )
    search_attr = html.escape(
        terms_index_item_dict(entry)["search"], quote=True
    )
    return (
        f'    <li class="terms-idx-item" data-search="{search_attr}">'
        f'<a href="{href}">'
        f'<span class="terms-idx-item-main">'
        f'<span class="terms-idx-term">{term}</span>'
        f"</span>{snippet_html}</a></li>"
    )


def split_sentences(s: str) -> list[str]:
    text = re.sub(r"\s+", " ", s or "").strip()
    if not text:
        return []
    return [p.strip() for p in re.findall(r"[^。！？]+[。！？]?", text) if p.strip()]


def study_points(explanation: str, limit: int = 4) -> list[str]:
    points: list[str] = []
    for sentence in split_sentences(explanation):
        s = sentence.rstrip("。")
        if len(s) < 14:
            continue
        if s.endswith("です") and "とは、" in s:
            continue
        points.append(s + "。")
        if len(points) >= limit:
            break
    return points


def make_term_lookup(entries: list[dict]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    conflicts: set[str] = set()
    exact_keys: set[str] = set()

    def add(key: str, href: str, *, exact: bool = False) -> None:
        if not key or key in conflicts:
            return
        existing = lookup.get(key)
        if existing and existing != href:
            if key in exact_keys:
                return
            lookup.pop(key, None)
            conflicts.add(key)
            return
        lookup[key] = href
        if exact:
            exact_keys.add(key)

    for e in entries:
        term = e["term"]
        add(term, e["slug_file"], exact=True)
        add(lookup_key(term), e["slug_file"], exact=True)
    for e in entries:
        term = e["term"]
        for key in term_alias_variants(term):
            add(key, e["slug_file"])
    for alias, target in RELATED_TERM_ALIASES.items():
        target_href = lookup.get(target) or lookup.get(lookup_key(target))
        if target_href:
            add(alias, target_href)
            add(lookup_key(alias), target_href)
    return lookup


def field_hub_slug(category: str) -> str:
    fid = glossary_field_id(category)
    if fid:
        return f"field-{css_safe_field_id(fid)}"
    safe = css_safe_field_id(re.sub(r"\s+", "-", norm(category)))
    return f"field-{safe}" if safe and safe != "field" else "field-other"


def load_guide_slugs() -> list[dict[str, str]]:
    path = ROOT / "data" / "guide_articles.csv"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8-sig")
    rows: list[dict[str, str]] = []
    for row in csv.DictReader(text.splitlines()):
        slug = norm(row.get("slug"))
        title = norm(row.get("title"))
        if slug and title:
            try:
                priority = int(norm(row.get("priority")) or 9999)
            except ValueError:
                priority = 9999
            rows.append(
                {
                    "slug": slug,
                    "title": title,
                    "genre": norm(row.get("genre")),
                    "tags": norm(row.get("tags")),
                    "priority": priority,
                }
            )
    rows.sort(key=lambda r: r["priority"])
    return rows


GUIDE_LINK_FALLBACK_SLUGS = (
    "exam-overview",
    "study-plan",
    "past-question-strategy",
    "glossary-how-to",
    "self-study-roadmap",
)


def guide_related_link_items(
    category: str,
    guides: list[dict[str, str]],
    *,
    limit: int = 3,
    articles_prefix: str = "../articles/",
) -> list[str]:
    if not guides:
        return []
    by_slug = {g["slug"]: g for g in guides}
    picked: list[str] = []
    seen: set[str] = set()
    cat = norm(category)
    for g in guides:
        blob = f"{g['genre']} {g['tags']} {g['title']}"
        if cat and cat in blob:
            slug = g["slug"]
            if slug not in seen:
                seen.add(slug)
                picked.append(
                    f'<a class="related-link" href="{articles_prefix}{html.escape(slug)}/">'
                    f"{html.escape(g['title'])}</a>"
                )
        if len(picked) >= limit:
            return picked
    for slug in GUIDE_LINK_FALLBACK_SLUGS:
        if len(picked) >= limit:
            break
        g = by_slug.get(slug)
        if not g or slug in seen:
            continue
        seen.add(slug)
        picked.append(
            f'<a class="related-link" href="{articles_prefix}{html.escape(slug)}/">'
            f"{html.escape(g['title'])}</a>"
        )
    return picked


def next_links_html(
    root_idx: str,
    field_hub: str | None,
    category: str,
    guide_links: list[str],
    *,
    rel_path: Path,
) -> str:
    from tools.internal_links import term_next_hub_links

    links = [
        '<a class="related-link" href="index.html">用語解説一覧へ戻る</a>',
    ]
    if field_hub and category:
        links.append(
            f'<a class="related-link" href="{html.escape(field_hub)}/index.html">'
            f"{html.escape(category)}の用語一覧</a>"
        )
    for href, label in term_next_hub_links(rel_path):
        links.append(f'<a class="related-link" href="{html.escape(href)}">{html.escape(label)}</a>')
    links.append(f'<a class="related-link" href="{html.escape(root_idx)}#past">過去問演習で確認する</a>')
    links.extend(guide_links)
    return (
        '<div class="related-box" aria-labelledby="term-next-title">'
        '<div id="term-next-title" class="related-box-title">次に確認するページ</div>'
        f'<div class="related-links">{"".join(links)}</div></div>'
    )


def related_terms_html(
    related: str,
    term_lookup: dict[str, str],
    *,
    current: dict,
    entries: list[dict],
    limit: int = 6,
) -> str:
    from tools.internal_links import collect_related_term_link_items

    items = collect_related_term_link_items(
        related,
        term_lookup,
        entries=entries,
        current=current,
        limit=limit,
    )
    return "".join(items)


def legal_basis_html(legal: str) -> str:
    legal = norm(legal)
    if not legal:
        return ""
    items = split_semicolon(legal)
    if len(items) <= 1:
        inner = html.escape(legal).replace("\n", "<br>\n")
        return f"<p>{inner}</p>"
    return '<ul class="term-legal-list">' + "".join(f"<li>{html.escape(x)}</li>" for x in items) + "</ul>"


def faq_items_for_term(term: str, short_def: str, definition: str, explanation: str) -> list[dict[str, str]]:
    first_points = study_points(explanation, limit=2)
    exam_answer = " ".join(first_points) if first_points else explanation
    return [
        {
            "question": f"{term}とは何ですか？",
            "answer": f"{term}とは、{short_def.rstrip('。')}。{definition}",
        },
        {
            "question": f"{term}は試験でどう押さえればよいですか？",
            "answer": exam_answer,
        },
    ]


def faq_section_html(items: list[dict[str, str]]) -> str:
    from tools.knowledge_hub_seo import faq_items_html

    return faq_items_html(items)


def custom_faq_items(entry: dict, fallback: list[dict[str, str]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for idx in range(1, 5):
        q = norm(entry.get(f"faq_{idx}_question"))
        a = norm(entry.get(f"faq_{idx}_answer"))
        if q and a:
            items.append({"question": q, "answer": a})
    return items or fallback


def multi_paragraph_html(value: str, css_class: str = "article-lead") -> str:
    """改行2つ区切りで複数段落の HTML を返す。"""
    text = norm(value)
    if not text:
        return ""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paras) <= 1:
        return f'<p class="{css_class}">{html.escape(text)}</p>'
    return "".join(f'<p class="{css_class}">{html.escape(p)}</p>' for p in paras)


def semicolon_list_html(value: str) -> str:
    items = split_semicolon(value)
    if not items:
        return ""
    return '<ol class="term-point-list">' + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ol>"


def semicolon_field_html(value: str) -> str:
    """セミコロン区切りの学習メモを箇条書き化（改行のみの場合は段落のまま）。"""
    if ";" in value:
        listed = semicolon_list_html(value)
        if listed:
            return listed
    return ""


def peer_comparison_table_html(
    term: str,
    related: str,
    by_term: dict[str, dict],
) -> str:
    peer_names = [x for x in split_semicolon(related) if x and x != term][:4]
    if len(peer_names) < 2:
        return ""
    rows: list[tuple[str, str]] = [(term, by_term.get(term, {}).get("short_def") or "—")]
    for name in peer_names:
        snippet = by_term.get(name, {}).get("short_def") or "関連用語ページで定義を確認"
        rows.append((name, snippet))
    body = "".join(
        "<tr>"
        f"<th>{html.escape(label)}</th>"
        f"<td>{html.escape(snippet.rstrip('。'))}</td>"
        "</tr>"
        for label, snippet in rows
    )
    return (
        '<h3 class="term-subheading">混同しやすい用語との違い（一覧）</h3>'
        '<table class="seo-info-table term-compare-table"><thead><tr>'
        "<th>用語</th><th>押さえる要点</th>"
        "</tr></thead><tbody>"
        f"{body}</tbody></table>"
        '<p class="term-compare-note">数値・手続の正誤は演習と公式テキストで必ず確認してください。</p>'
    )


def build_term_html(
    entry: dict,
    rel_path: Path,
    base_url: str,
    term_lookup: dict[str, str],
    entries: list[dict],
    guides: list[dict[str, str]],
    *,
    by_term: dict[str, dict] | None = None,
) -> str:
    term = entry["term"]
    category = entry["category"]
    tags = entry["tags"]
    short_def = entry["short_def"]
    definition = entry["definition"]
    related = entry["related_terms"]
    legal = entry["legal_basis"]
    importance = entry["importance"]
    explanation = entry["explanation"]
    slug_file = entry["slug_file"]
    article_title = norm(entry.get("article_title"))
    article_lead = norm(entry.get("article_lead"))
    term_detail_body = norm(entry.get("term_detail_body"))
    exam_points = norm(entry.get("exam_points"))
    common_mistakes = norm(entry.get("common_mistakes"))
    memory_tip = norm(entry.get("memory_tip"))
    example_question = norm(entry.get("example_question"))
    example_answer = norm(entry.get("example_answer"))

    title = f"{article_title or term + 'とは？意味・根拠・試験ポイント'}｜{brand_name()}"
    desc = meta_description(
        f"{term}の意味、法令・根拠、試験で押さえるポイントを{exam_name()}向けに整理。{short_def or definition}"
    )
    canonical = public_url(base_url, f"terms/{slug_file}")
    root_idx = rel_to_root(rel_path)
    css_links = rel_editorial_css(rel_path)

    tags_list = split_semicolon(tags)
    field_hub = entry.get("field_hub") or ""
    rel_html = related_terms_html(
        related, term_lookup, current=entry, entries=entries
    )
    guide_links = guide_related_link_items(category, guides)

    def text_paragraphs(body: str) -> str:
        return seo_section_body_html(body)

    def article_section(sec_id: str, label: str, body_html: str, number: int | None = None) -> str:
        if not body_html.strip():
            return ""
        hid = f"term-sec-{sec_id}"
        num_html = f'<span class="section-heading-num">{number}</span>' if number is not None else ""
        section_class = "seo-article-section term-definition-section" if sec_id == "definition" else "seo-article-section"
        if sec_id == "diagram":
            section_class = "seo-article-section term-diagram-section"
        return (
            f'<section class="{section_class}" aria-labelledby="{hid}">'
            f'<h2 id="{hid}">{num_html}{html.escape(label)}</h2>'
            f"{body_html}</section>"
        )

    info_rows: list[tuple[str, str]] = [
        ("対象試験", exam_name()),
    ]
    if category:
        info_rows.append(("分野", category))
    if importance:
        info_rows.append(("重要度", importance))
    if legal:
        info_rows.append(("法令・根拠", " / ".join(split_semicolon(legal))))
    if tags_list:
        info_rows.append(("関連タグ", " / ".join(tags_list)))
    info_table = ""
    if info_rows:
        info_table = (
            '<section class="seo-article-section" aria-labelledby="article-info-title">'
            '<h2 id="article-info-title">記事の基本情報</h2>'
            '<table class="seo-info-table"><tbody>'
            + "".join(
                f"<tr><th>{html.escape(k)}</th><td>{html.escape(v)}</td></tr>"
                for k, v in info_rows
            )
            + "</tbody></table></section>"
        )

    rel_section = ""
    if rel_html:
        rel_section = (
            '<div class="related-box" aria-labelledby="term-related-title"><div id="term-related-title" class="related-box-title">関連用語</div>'
            f'<div class="related-links term-related-links">{rel_html}</div></div>'
        )

    lead = (
        f"{term}は、{short_def.rstrip('。')}。"
        f"{exam_name()}では、{category}分野の用語として、意味・根拠・似た用語との違いをセットで押さえると理解しやすくなります。"
    )
    points = study_points(explanation)
    from tools.knowledge_hub_seo import (  # noqa: E402
        _term_item_label,
        glossary_definition_body_text,
        glossary_exam_choices_body_html,
        glossary_exam_points_body_html,
        glossary_memory_body_html,
        glossary_mistakes_body_html,
        hub_prose_html,
    )

    points_html = glossary_exam_points_body_html(entry)
    if not points_html and points:
        points_html = hub_prose_html([p for p in points])
    entries_by_term = by_term or {e["term"]: e for e in entries}
    compare_html = peer_comparison_table_html(term, related, entries_by_term)
    detail_html = text_paragraphs(glossary_definition_body_text(entry))
    if compare_html:
        detail_html = (detail_html + compare_html) if detail_html else compare_html
    diagram_id = norm(entry.get("diagram_id"))
    diagram_html = diagram_body_html(diagram_id) if diagram_id else ""
    mistakes_html = glossary_mistakes_body_html(entry)
    if not mistakes_html and common_mistakes:
        mistakes_html = text_paragraphs(common_mistakes)
    memory_html = glossary_memory_body_html(entry)
    exam_choices_html = glossary_exam_choices_body_html(entry)
    if not exam_choices_html and explanation:
        exam_choices_html = text_paragraphs(explanation)
    example_html = ""
    if example_question or example_answer:
        example_html = (
            '<div class="related-box"><div class="related-box-title">例題</div>'
            f"<p>{_term_item_label('問題')}：{html.escape(example_question)}</p>"
            f"<p>{_term_item_label('答え')}：{html.escape(example_answer)}</p></div>"
        )
    faq_items = custom_faq_items(entry, faq_items_for_term(term, short_def, definition, explanation))
    faq_html = faq_section_html(faq_items)

    from tools.knowledge_hub_seo import glossary_key_points_items, seo_key_points_box_html

    key_points_source = glossary_key_points_items(entry)

    key_points_intro = f"この記事では、{term}の意味と試験での見方を、問題の解説に沿って整理します。"
    key_points_html = seo_key_points_box_html(
        key_points_source[:5],
        intro=key_points_intro,
    )

    badge_html = glossary_field_badge_html(category)
    meta_bits: list[str] = ['<span class="q-id">用語</span>']
    if badge_html:
        meta_bits.append(badge_html)
    if category and not badge_html:
        meta_bits.append(f"<span>{html.escape(category)}</span>")
    meta_line = " · ".join(meta_bits)

    crumb_items: list[tuple[str, str | None]] = [
        ("トップ", "index.html"),
        ("用語解説一覧", "terms/index.html"),
    ]
    if field_hub and category:
        crumb_items.append((category, f"{field_hub}/index.html"))
    crumb_items.append((term, None))
    page_header = site_page_header(rel_path, current="terms")
    page_breadcrumb = breadcrumb_html(rel_path, crumb_items)
    page_footer = site_page_footer(rel_path, current="terms")
    hub_tabs = knowledge_hub_tabs_html(
        current="terms",
        **knowledge_hub_tab_hrefs(here="terms"),
    )

    updated = content_date_from_row(entry)
    robots_meta = robots_meta_for_slug(slug_file)

    quality_html = (
        '<section class="seo-quality-panel" aria-labelledby="quality-panel-title">'
        '<h2 id="quality-panel-title">この記事の信頼性について</h2>'
        '<table class="seo-info-table"><tbody>'
        f"<tr><th>執筆</th><td>{html.escape(brand_name())}編集部（学習用語、過去問の復習導線、試験ガイドを整理する編集チーム）</td></tr>"
        f"<tr><th>確認</th><td>{html.escape(brand_name())}編集部（公開前に公式情報、法令情報、サイト内の関連ページとの整合性を確認）</td></tr>"
    )
    if updated:
        quality_html += f"<tr><th>事実確認日</th><td>{html.escape(updated)}</td></tr>"

    official_links = external_links() or [primary_external_link()]
    quality_source_items = "".join(
        f'<li><a href="{html.escape(link["url"])}" target="_blank" rel="noopener noreferrer">{html.escape(link["label"])}</a></li>'
        for link in official_links
    )
    quality_html += f'<tr><th>主な参照元</th><td><ul class="quality-source-list">{quality_source_items}</ul></td></tr></tbody></table></section>'
    official_items = "".join(
        f'<li><a href="{html.escape(link["url"])}" target="_blank" rel="noopener noreferrer">{html.escape(link["label"])}</a>'
        + (f' … {html.escape(link.get("description", ""))}' if link.get("description") else "")
        + "</li>"
        for link in official_links
    )
    official_html = (
        '<section class="seo-article-section" aria-labelledby="official-info-title">'
        '<h2 id="official-info-title">公式情報の確認</h2>'
        f"<p>{html.escape(term)}は、{html.escape(exam_name())}の学習で押さえたい用語です。制度、数値、義務の有無は年度や法令改正で変わることがあるため、受験前には公式情報も確認してください。</p>"
        f"<ul>{official_items}</ul>"
        "<blockquote><p><strong>注意：</strong>"
        "本ページは学習用の要点整理です。出題範囲・法令・公式見解は変更される場合があります。"
        "本番前には必ず試験実施団体や法令原文などの公式情報を確認してください。"
        "</p></blockquote></section>"
    )

    content_sections: list[str] = []
    body_toc_items: list[tuple[str, str]] = []
    from tools.knowledge_hub_seo import glossary_summary_body_html, glossary_legal_body_html

    section_plan: list[tuple[str, str, str]] = [
        ("summary", "まず押さえる要点", glossary_summary_body_html(short_def)),
        ("points", "試験で押さえるポイント", points_html),
        ("definition", "定義と基本理解", detail_html),
    ]
    if diagram_html:
        section_plan.append(("diagram", "図解で理解する", diagram_html))
    section_plan.extend(
        [
            ("legal", "法令・根拠", glossary_legal_body_html(entry)),
            ("exam", "選択肢で問われやすい点", exam_choices_html),
            ("mistakes", "よくある誤解・注意点", mistakes_html),
            ("memory", "覚え方・整理のコツ", memory_html),
            ("example", "例題で確認", example_html),
        ]
    )
    for sec_id, label, body_html in section_plan:
        html_text = article_section(sec_id, label, body_html, len(content_sections) + 1)
        if html_text:
            content_sections.append(html_text)
            body_toc_items.append((f"term-sec-{sec_id}", label))
    content_sections_html = "\n    ".join(content_sections)

    from tools.glossary_past_questions import find_past_questions_for_term, past_questions_section_html

    past_hits = find_past_questions_for_term(
        term,
        related_terms=related,
        legal_basis=legal,
        limit=3,
    )
    past_section = past_questions_section_html(
        past_hits,
        rel_path,
        section_num=len(content_sections) + 1,
    )
    if past_section:
        content_sections_html = (
            f"{content_sections_html}\n    {past_section}" if content_sections_html else past_section
        )
        body_toc_items.append(("term-past-title", "関連する過去問"))

    toc_items: list[tuple[str, str]] = [
        ("key-points-title", "この記事の要点"),
        ("quality-panel-title", "この記事の信頼性について"),
        *body_toc_items,
        ("term-sec-faq", "よくある質問"),
        ("article-info-title", "記事の基本情報"),
        ("official-info-title", "公式情報の確認"),
    ]
    if rel_section:
        toc_items.append(("term-related-title", "関連用語"))
    toc_items.append(("term-next-title", "次に確認するページ"))
    toc_links = "".join(f'<li><a href="#{html.escape(anchor)}">{html.escape(label)}</a></li>' for anchor, label in toc_items)
    toc_html = (
        '<nav class="seo-toc" aria-labelledby="seo-toc-title">'
        '<h2 id="seo-toc-title">目次</h2>'
        f"<ol>{toc_links}</ol></nav>"
    )

    next_links = next_links_html(root_idx, field_hub or None, category, guide_links, rel_path=rel_path)

    official_links_ld = external_links() or [primary_external_link()]
    defined_term: dict = {
        "@type": "DefinedTerm",
        "@id": canonical + "#term",
        "name": term,
        "description": desc,
        "url": canonical,
        "inDefinedTermSet": public_url(base_url, "terms/index.html"),
        **json_ld_date_modified(updated),
    }
    if category:
        defined_term["category"] = category
    defined_term["author"] = {"@type": "Organization", "name": brand_name() + "編集部"}
    citations = [link["url"] for link in official_links_ld if link.get("url")]
    if citations:
        defined_term["citation"] = citations
    breadcrumb_items = [
        {"@type": "ListItem", "position": 1, "name": "トップ", "item": public_url(base_url, "index.html")},
        {"@type": "ListItem", "position": 2, "name": "用語解説", "item": public_url(base_url, "terms/index.html")},
    ]
    pos = 3
    if field_hub and category:
        breadcrumb_items.append(
            {
                "@type": "ListItem",
                "position": pos,
                "name": category,
                "item": public_url(base_url, f"terms/{field_hub}/index.html"),
            }
        )
        pos += 1
    breadcrumb_items.append({"@type": "ListItem", "position": pos, "name": term, "item": canonical})
    graph: list[dict] = [
        defined_term,
        {
            "@type": "WebPage",
            "@id": canonical + "#webpage",
            "url": canonical,
            "name": title,
            "description": desc,
            "inLanguage": "ja-JP",
            **json_ld_date_modified(updated),
            "mainEntity": {"@id": canonical + "#term"},
        },
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
    json_ld = {"@context": "https://schema.org", "@graph": graph}

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
{robots_meta}
<link rel="canonical" href="{html.escape(canonical)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="{html.escape(canonical)}">
<meta name="twitter:card" content="summary">
<script type="application/ld+json">
{json.dumps(json_ld, ensure_ascii=False, indent=2)}
</script>
{seo_editorial_head_fonts()}
{css_links}
</head>
<body class="{shell_body_class('term-article-page')}">
{site_page_wrap_open()}
{page_header}
<main class="seo-article-main">
  {page_breadcrumb}
  {hub_tabs}
  <article class="{seo_editorial_article_class()}">
    <div class="article-meta">
      <span class="meta-category">用語解説</span>
      {meta_updated_html(updated)}
      <span class="meta-updated">{meta_line}</span>
    </div>
    <h1 class="article-title">{html.escape(article_title or term + 'とは？意味・根拠・試験ポイントを整理')}</h1>
    <p class="article-lead"><strong>{html.escape(term)}</strong>について、定義・根拠・試験での押さえ方をまとめます。{html.escape(article_lead or lead)}</p>
    {key_points_html}
    {toc_html}
    {quality_html}
    {content_sections_html}
    {article_section("faq", "よくある質問", faq_html, len(content_sections) + (1 if past_section else 0) + 1) if faq_html else ""}
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



def build_field_hub_html(
    category: str,
    field_slug: str,
    cat_entries: list[dict],
    base_url: str,
) -> str:
    rel_path = Path("terms") / field_slug / "index.html"
    updated = latest_content_date(cat_entries)
    canonical = public_url(base_url, f"terms/{field_slug}/index.html")
    title = f"{category}の用語一覧｜{brand_name()}（{exam_name()}）"
    desc = meta_description(
        f"{exam_name()}の{category}分野に関する用語を一覧し、各用語の解説記事へリンクします。"
    )
    lis = [
        f'    <li><a href="../{html.escape(e["slug_file"])}">{html.escape(e["term"])}</a></li>'
        for e in sorted(cat_entries, key=lambda x: x["term"])
    ]
    list_html = "\n".join(lis)
    crumb_items = [
        ("トップ", "index.html"),
        ("用語解説一覧", "terms/index.html"),
        (category, None),
    ]
    page_header = site_page_header(rel_path, current="terms")
    page_breadcrumb = breadcrumb_html(rel_path, crumb_items)
    page_footer = site_page_footer(rel_path, current="terms")
    hub_tabs = knowledge_hub_tabs_html(
        current="field",
        **knowledge_hub_tab_hrefs(here="field"),
    )
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": canonical + "#collection",
                "name": title,
                "description": desc,
                "url": canonical,
                **json_ld_date_modified(updated),
                "inLanguage": "ja-JP",
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "トップ", "item": public_url(base_url, "index.html")},
                    {"@type": "ListItem", "position": 2, "name": "用語解説", "item": public_url(base_url, "terms/index.html")},
                    {"@type": "ListItem", "position": 3, "name": category, "item": canonical},
                ],
            },
        ],
    }
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
{ROBOTS_INDEX_FOLLOW}
<link rel="canonical" href="{html.escape(canonical)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="{html.escape(canonical)}">
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=2)}
</script>
{HEAD_FONTS}
<link rel="stylesheet" href="{html.escape(rel_css(rel_path))}">
<link rel="stylesheet" href="{html.escape(rel_theme_css(rel_path))}">
</head>
<body class="{shell_body_class('terms-field-hub-page')}">
{site_page_wrap_open()}
{page_header}
<main class="site-page-main terms-idx-main">
  {page_breadcrumb}
  {hub_tabs}
  <h1 class="terms-idx-page-title">{html.escape(category)}の用語一覧</h1>
  <p class="terms-idx-lead">{html.escape(exam_name())}の{html.escape(category)}分野で押さえたい用語をまとめています。各リンクから用語の意味・試験ポイント・関連用語を確認できます。</p>
  <p class="terms-idx-lead"><a href="../index.html">用語解説一覧（全分野）</a>へ戻る</p>
  <section class="terms-idx-panel" aria-label="{html.escape(category)}の用語一覧">
    <ul class="terms-idx-list">
{list_html}
    </ul>
  </section>
</main>
{page_footer}
{site_page_wrap_close()}
</body>
</html>
"""


def build_terms_index(entries: list[dict], base_url: str) -> str:
    by_cat: dict[str, list[dict]] = {}
    for e in entries:
        by_cat.setdefault(e["category"] or "その他", []).append(e)
    for c in by_cat:
        by_cat[c].sort(key=lambda x: x["term"])

    cat_keys = ordered_term_categories(by_cat)
    n_terms = len(entries)
    n_cats = len(cat_keys)

    seo_links: list[str] = []
    for cat in cat_keys:
        for e in by_cat[cat]:
            seo_links.append(
                f'<li><a href="{html.escape(terms_index_href(e["slug_file"]))}">'
                f"{html.escape(e['term'])}</a></li>"
            )
    seo_html = (
        '<ul class="terms-idx-seo-list">\n    '
        + "\n    ".join(seo_links)
        + "\n  </ul>"
    )

    chip_lines = [
        '    <button type="button" class="terms-idx-chip on" data-cat="all">すべて<b>'
        f"{n_terms}</b></button>"
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
        for e in by_cat[cat]:
            list_items_ld.append(
                {
                    "@type": "ListItem",
                    "position": pos,
                    "name": e["term"],
                    "item": public_url(base_url, f"terms/{e['slug_file']}"),
                }
            )
            pos += 1
    ld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": f"{exam_name()} 用語解説一覧",
        "description": "試験で出やすい用語ごとの解説記事への索引です。",
        "numberOfItems": n_terms,
        "itemListElement": list_items_ld,
    }
    ld_json = json.dumps(ld, ensure_ascii=False, indent=2)
    json_data = json.dumps(
        [terms_index_item_dict(e) for e in entries], ensure_ascii=False
    )
    tbody_html = render_terms_index_tbody(entries)

    idx_path = Path("terms/index.html")
    terms_header = site_page_header(idx_path, current="terms", wide=True)
    terms_footer = site_page_footer(idx_path, current="terms", wide=True)
    page_breadcrumb = breadcrumb_html(idx_path, [("トップ", "index.html"), ("用語解説", None)])

    canonical = public_url(base_url, "terms/index.html")
    title = f"用語解説｜{brand_name()}（{exam_name()}）"
    desc = (
        f"{exam_name()}の重要用語を一覧し、各用語の解説記事へリンクします。"
        "分野別に整理し、検索と絞り込みで目的の語句を探せます。"
    )
    lead = (
        f"{exam_name()}の試験で押さえたい用語を、分野別にまとめています。"
        "各ページで意味や試験での論点を確認できます。学習の進め方は試験ガイド（articles/）をご覧ください。"
    )
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
{ld_json}
</script>
{HEAD_FONTS}
<link rel="stylesheet" href="../site-pages.css?v={TERMS_INDEX_CSS_VER}">
<link rel="stylesheet" href="../site-theme.css">
<script>document.documentElement.classList.add("js");</script>
</head>
<body class="{shell_body_class('terms-index-page')}" data-terms-total="{n_terms}">
{site_page_wrap_open()}
{terms_header}
<main class="site-page-main">
  {page_breadcrumb}
  <h1>用語解説</h1>
  <p class="site-page-lead">{html.escape(lead)}</p>
  {knowledge_hub_tabs_html(current="terms", **knowledge_hub_tab_hrefs(here="terms"))}
  <section class="terms-index-panel" aria-labelledby="terms-index-heading">
    <div class="terms-index-head">
      <div>
        <h2 id="terms-index-heading">用語一覧</h2>
        <p>全{n_terms}語・{n_cats}分野。キーワード検索と分野で絞り込めます。</p>
      </div>
    </div>
    <div class="terms-index-tools">
      <div class="terms-index-tools-primary">
      <label class="terms-index-search" for="terms-idx-q">
        <span class="u-visually-hidden">用語検索</span>
        <input id="terms-idx-q" type="search" inputmode="search" autocomplete="off" placeholder="{html.escape(TERMS_INDEX_SEARCH_PLACEHOLDER, quote=True)}">
      </label>
      <span id="terms-idx-hit" class="terms-index-hit" aria-live="polite">{n_terms} / {n_terms} 語</span>
      </div>
      <div class="terms-idx-chips" aria-label="分野フィルタ">
{chips_html}
      </div>
      <button type="button" class="terms-idx-reset hide" id="terms-idx-reset">条件をクリア</button>
      <div class="terms-idx-active-filters hide" id="terms-idx-active-filters" aria-live="polite"></div>
    </div>
    <div class="terms-idx-empty-panel hide" id="terms-idx-empty" role="status" hidden>
      <p class="terms-idx-empty-title">条件に一致する用語がありません</p>
      <p class="terms-idx-empty-hint">検索語を短くするか、分野を「すべて」に戻してお試しください。</p>
      <button type="button" class="terms-idx-reset" id="terms-idx-empty-reset">条件をクリア</button>
    </div>
    <div class="terms-idx-layout" aria-label="用語一覧">
      <div class="terms-idx-table-wrap">
        <table class="terms-idx-table">
          <thead><tr>
            <th scope="col" class="terms-idx-th-term">用語</th>
            <th scope="col" class="terms-idx-th-cat">分野</th>
            <th scope="col" class="terms-idx-th-def">定義</th>
          </tr></thead>
          <tbody id="terms-idx-flat-body">
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
{terms_footer}
{site_page_wrap_close()}
<button type="button" class="terms-idx-top" id="terms-idx-top" aria-label="ページ上部へ">↑</button>
<script type="application/json" id="terms-index-data">{json_data}</script>
<script defer src="../site-terms-index.js?v={TERMS_INDEX_JS_VER}"></script>
</body>
</html>
"""

GLOSSARY_SLUG_MAP_JSON = ROOT / "docs" / "glossary-article-slugs.json"
INDEX_HTML = ROOT / "index.html"
GLOS_SLUG_MAP_SCRIPT_RE = re.compile(
    r'<script type="application/json" id="glos-article-slug-map-json"[^>]*>.*?</script>\s*',
    re.DOTALL,
)


def write_glossary_article_slug_map(entries: list[dict]) -> None:
    """トップ SPA 用語カード → terms/{slug}.html の対応表。"""
    data = {e["term"]: e["slug_file"].removesuffix(".html") for e in entries}
    GLOSSARY_SLUG_MAP_JSON.parent.mkdir(parents=True, exist_ok=True)
    GLOSSARY_SLUG_MAP_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sync_index_glossary_slug_map(entries: list[dict]) -> None:
    """index.html にスラッグ JSON を埋め込み（fetch 失敗時のフォールバック）。"""
    if not INDEX_HTML.is_file():
        return
    payload = json.dumps(
        {e["term"]: e["slug_file"].removesuffix(".html") for e in entries},
        ensure_ascii=False,
    )
    script = (
        f'<script type="application/json" id="glos-article-slug-map-json">'
        f"{payload}</script>\n"
    )
    text = INDEX_HTML.read_text(encoding="utf-8")
    if GLOS_SLUG_MAP_SCRIPT_RE.search(text):
        text = GLOS_SLUG_MAP_SCRIPT_RE.sub(script, text, count=1)
    else:
        needle = '<div id="glossary-list">'
        if needle not in text:
            return
        text = text.replace(needle, needle + "\n" + script, 1)
    INDEX_HTML.write_text(text, encoding="utf-8")


def load_glossary_rows() -> list[dict]:
    if not GLOSSARY_CSV.is_file():
        raise FileNotFoundError(str(GLOSSARY_CSV))
    with GLOSSARY_CSV.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_glossary_entries(*, strict: bool = True) -> list[dict]:
    """CSV から slug_file 付き用語エントリ一覧を返す。"""
    rows = load_glossary_rows()
    used_slugs: dict[str, str] = {}
    entries: list[dict] = []
    for i, row in enumerate(rows, start=2):
        term = norm(row.get("term"))
        if not term:
            if strict:
                raise ValueError(f"line {i}: term が空です")
            continue
        legacy_slug = norm(row.get("slug")) or norm(row.get("url_slug"))
        if legacy_slug:
            if strict and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", legacy_slug):
                raise ValueError(f"line {i}: slug は半角英数字とハイフンのみ: {legacy_slug!r}")
            slug_file = f"{legacy_slug}.html"
            if strict and slug_file in used_slugs:
                raise ValueError(f"line {i}: slug が重複しています: {legacy_slug}")
            used_slugs[slug_file] = term
        else:
            reading = norm(row.get("reading"))
            slug_file = term_slug(term, reading, used_slugs) + ".html"
        entries.append(
            {
                "term": term,
                "category": norm(row.get("category")),
                "tags": norm(row.get("tags")),
                "short_def": norm(row.get("short_def")),
                "definition": norm(row.get("definition")),
                "related_terms": norm(row.get("related_terms")),
                "legal_basis": norm(row.get("legal_basis")),
                "importance": norm(row.get("importance")),
                "explanation": norm(row.get("explanation")),
                "article_title": norm(row.get("article_title")),
                "article_lead": norm(row.get("article_lead")),
                "term_detail_body": norm(row.get("term_detail_body")),
                "exam_points": norm(row.get("exam_points")),
                "common_mistakes": norm(row.get("common_mistakes")),
                "memory_tip": norm(row.get("memory_tip")),
                "example_question": norm(row.get("example_question")),
                "example_answer": norm(row.get("example_answer")),
                "faq_1_question": norm(row.get("faq_1_question")),
                "faq_1_answer": norm(row.get("faq_1_answer")),
                "faq_2_question": norm(row.get("faq_2_question")),
                "faq_2_answer": norm(row.get("faq_2_answer")),
                "faq_3_question": norm(row.get("faq_3_question")),
                "faq_3_answer": norm(row.get("faq_3_answer")),
                "faq_4_question": norm(row.get("faq_4_question")),
                "faq_4_answer": norm(row.get("faq_4_answer")),
                "diagram_id": norm(row.get("diagram_id")),
                "slug_file": slug_file,
                "field_hub": field_hub_slug(norm(row.get("category"))),
                "fact_checked_at": norm(row.get("fact_checked_at")),
                "last_reviewed_at": norm(row.get("last_reviewed_at")),
                "source_checked_at": norm(row.get("source_checked_at")),
            }
        )
    return entries


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=BASE_DEFAULT)
    args = ap.parse_args()
    base = args.base_url.rstrip("/")

    entries = load_glossary_entries()
    term_lookup = make_term_lookup(entries)
    entries_by_term = {e["term"]: e for e in entries}
    guides = load_guide_slugs()

    TERMS_DIR.mkdir(parents=True, exist_ok=True)
    for stale in TERMS_DIR.glob("*.html"):
        if stale.name not in PRESERVED_TERM_HTML:
            stale.unlink()
    for stale in TERMS_DIR.iterdir():
        if stale.is_dir() and stale.name not in PRESERVED_TERM_SUBDIRS:
            shutil.rmtree(stale)

    for e in entries:
        out_file = TERMS_DIR / e["slug_file"]
        rel_path = out_file.relative_to(ROOT)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(
            build_term_html(
                e, rel_path, base, term_lookup, entries, guides, by_term=entries_by_term
            ),
            encoding="utf-8",
        )

    by_cat: dict[str, list[dict]] = {}
    for e in entries:
        by_cat.setdefault(e["category"] or "その他", []).append(e)
    hub_count = 0
    for cat in ordered_term_categories(by_cat):
        hub = field_hub_slug(cat)
        hub_dir = TERMS_DIR / hub
        hub_dir.mkdir(parents=True, exist_ok=True)
        (hub_dir / "index.html").write_text(
            build_field_hub_html(cat, hub, by_cat[cat], base),
            encoding="utf-8",
        )
        hub_count += 1

    (TERMS_DIR / "index.html").write_text(build_terms_index(entries, base), encoding="utf-8")

    from tools.build_term_diagram_sample_pages import build_all as build_term_diagram_samples

    build_term_diagram_samples(base_url=base)

    write_glossary_article_slug_map(entries)
    sync_index_glossary_slug_map(entries)

    print(f"Wrote {len(entries)} term pages under {TERMS_DIR}")
    print(f"Wrote {GLOSSARY_SLUG_MAP_JSON}")
    print(f"Updated {INDEX_HTML} (glos-article-slug-map-json)")
    print(f"Wrote {hub_count} field hub pages under {TERMS_DIR}/field-*/")
    print(f"Wrote {TERMS_DIR / 'index.html'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        raise SystemExit(1)
