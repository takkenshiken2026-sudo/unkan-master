#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate SEO guide articles from data/guide_articles.csv."""

from __future__ import annotations

import csv
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.html_footer import (  # noqa: E402
    ROBOTS_INDEX_FOLLOW,
    breadcrumb_html,
    shell_body_class,
    site_page_footer,
    site_page_header,
    site_page_wrap_close,
    site_page_wrap_open,
)
from tools.seo_utils import content_date_from_row, json_ld_date_modified, meta_updated_html  # noqa: E402
from tools.site_config import (  # noqa: E402
    brand_name,
    clean_origin,
    exam_name,
    external_links,
    guide_article_genres,
    guide_genre_order_index,
    guide_genre_style_by_label,
    primary_external_link,
)

from tools.seo_editorial_chrome import (  # noqa: E402
    seo_editorial_article_class,
    seo_editorial_head_fonts,
    seo_editorial_stylesheet_links,
)

ARTICLES_CSV = ROOT / "data" / "guide_articles.csv"
ARTICLES_DIR = ROOT / "articles"
GEN_MARKER = ".generated-by-exam-site"
GUIDE_PAGES_CSS_VER = "20260527-guide"


def norm(value: str | None) -> str:
    return (value or "").strip()


def apply_vars(value: str) -> str:
    text = norm(value)
    return (
        text.replace("Sampleマスター", brand_name())
        .replace("◯◯試験（プレースホルダー）", exam_name())
        .replace("◯◯試験", exam_name())
    )


def public_url(rel_path: str) -> str:
    return f"{clean_origin().rstrip('/')}/{rel_path.lstrip('/')}"


def rel_prefix(rel_path: Path) -> str:
    depth = len(rel_path.parent.parts)
    return "" if depth == 0 else "/".join([".."] * depth) + "/"


def css_href(rel_path: Path, filename: str) -> str:
    return rel_prefix(rel_path) + filename


def meta_description(text: str, limit: int = 155) -> str:
    one = re.sub(r"\s+", " ", text).strip()
    return one if len(one) <= limit else one[: limit - 1] + "…"


def split_semicolon(value: str) -> list[str]:
    return [x.strip() for x in (value or "").split(";") if x.strip()]


from tools.seo_body_markup import seo_section_body_html  # noqa: E402


def paragraphs(text: str) -> str:
    return seo_section_body_html(text, transform=apply_vars)


def list_or_paragraph(
    text: str,
    *,
    term_hrefs: dict[str, str] | None = None,
    linked_terms: set[str] | None = None,
) -> str:
    return seo_section_body_html(
        text,
        transform=apply_vars,
        term_hrefs=term_hrefs,
        linked_terms=linked_terms,
    )


def resolve_guide_section_body(article: dict[str, str], body: str) -> str:
    """量産テンプレの冒頭をリード文ベースの本文に差し替える。"""
    text = norm(body)
    if not text or "の観点で整理します" not in text:
        return body
    lead = norm(article.get("lead"))
    if not lead:
        return body
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    rest = [
        p
        for p in paras[1:]
        if "このサイトでは過去問・用語解説・比較表を組み合わせ" not in p
        and "間違えた問題は理由を短くメモし" not in p
    ]
    lead_paras = [p.strip() for p in re.split(r"\n\s*\n", lead) if p.strip()]
    merged = lead_paras + rest
    return "\n\n".join(merged)


def section_html(
    article: dict[str, str],
    idx: int,
    display_num: int,
    *,
    term_hrefs: dict[str, str] | None = None,
    linked_terms: set[str] | None = None,
) -> str:
    heading = apply_vars(article.get(f"section_{idx}_heading", ""))
    body = resolve_guide_section_body(article, article.get(f"section_{idx}_body", ""))
    if not heading or not norm(body):
        return ""
    sid = f"article-sec-{idx}"
    return (
        f'<section class="seo-article-section" aria-labelledby="{sid}">'
        f'<h2 id="{sid}"><span class="section-heading-num">{display_num}</span>{html.escape(heading)}</h2>'
        f"{list_or_paragraph(body, term_hrefs=term_hrefs, linked_terms=linked_terms)}</section>"
    )


def sections_html(
    article: dict[str, str],
    *,
    term_hrefs: dict[str, str] | None = None,
    linked_terms: set[str] | None = None,
) -> str:
    sections: list[str] = []
    display_num = 1
    for idx in range(1, 9):
        html_text = section_html(
            article,
            idx,
            display_num,
            term_hrefs=term_hrefs,
            linked_terms=linked_terms,
        )
        if html_text:
            sections.append(html_text)
            display_num += 1
    return "\n".join(sections)


def key_points_items(article: dict[str, str]) -> list[str]:
    explicit = split_semicolon(apply_vars(article.get("key_points", "")))
    if explicit:
        return explicit[:5]
    action = split_semicolon(apply_vars(article.get("action_items", "")))
    if action:
        return action[:5]
    from_headings: list[str] = []
    for idx in range(1, 9):
        heading = apply_vars(article.get(f"section_{idx}_heading", ""))
        body = norm(article.get(f"section_{idx}_body", ""))
        if heading and body:
            from_headings.append(heading)
    return from_headings[:3]


def key_points_box_html(article: dict[str, str]) -> str:
    from tools.knowledge_hub_seo import seo_key_points_box_html

    items = key_points_items(article)
    intro = apply_vars(article.get("user_intent", ""))
    return seo_key_points_box_html(items, intro=intro)


def toc_html(article: dict[str, str], has_faq: bool) -> str:
    items: list[tuple[str, str]] = []
    if key_points_items(article) or norm(apply_vars(article.get("user_intent", ""))):
        items.append(("key-points-title", "この記事の要点"))
    items.append(("quality-panel-title", "この記事の信頼性について"))
    for idx in range(1, 9):
        heading = apply_vars(article.get(f"section_{idx}_heading", ""))
        body = norm(article.get(f"section_{idx}_body", ""))
        if heading and body:
            items.append((f"article-sec-{idx}", heading))
    if has_faq:
        items.append(("article-sec-faq", "よくある質問"))
    items.append(("article-info-title", "記事の基本情報"))
    items.append(("official-info-title", "公式情報の確認"))
    if not items:
        return ""
    links = "".join(f'<li><a href="#{html.escape(anchor)}">{html.escape(label)}</a></li>' for anchor, label in items)
    return (
        '<nav class="seo-toc" aria-labelledby="seo-toc-title">'
        '<h2 id="seo-toc-title">目次</h2>'
        f"<ol>{links}</ol></nav>"
    )


def faq_items(article: dict[str, str]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for idx in range(1, 4):
        q = apply_vars(article.get(f"faq_{idx}_question", ""))
        a = apply_vars(article.get(f"faq_{idx}_answer", ""))
        if q and a:
            items.append({"question": q, "answer": a})
    return items


def faq_html(items: list[dict[str, str]], *, section_num: int) -> str:
    from tools.knowledge_hub_seo import faq_section_html

    return faq_section_html(items, heading_id="article-sec-faq", section_num=section_num)


def article_body_section_count(article: dict[str, str]) -> int:
    count = 0
    for idx in range(1, 9):
        heading = apply_vars(article.get(f"section_{idx}_heading", ""))
        body = norm(article.get(f"section_{idx}_body", ""))
        if heading and body:
            count += 1
    return count


def parse_related_links(
    value: str,
    by_slug: dict[str, dict[str, str]],
    article: dict[str, str] | None = None,
) -> str:
    links: list[str] = []
    seen: set[str] = set()
    for item in split_semicolon(value):
        target, label = item, item
        if ":" in item:
            target, label = [x.strip() for x in item.split(":", 1)]
        if not target:
            continue
        if target in by_slug and target not in seen:
            seen.add(target)
            href = f"../{html.escape(target)}/"
            text_label = label or by_slug[target]["title"]
            links.append(f'<a class="related-link" href="{href}">{html.escape(apply_vars(text_label))}</a>')
        elif target.startswith(("http://", "https://")):
            text_label = label or target
            links.append(
                f'<a class="related-link" href="{html.escape(target)}" target="_blank" rel="noopener noreferrer">{html.escape(apply_vars(text_label))}</a>'
            )
    if len(links) < 2 and article:
        genre = apply_vars(article.get("genre", ""))
        tags = set(split_semicolon(apply_vars(article.get("tags", ""))))
        current_slug = article.get("slug", "")
        candidates: list[tuple[int, dict[str, str]]] = []
        for other in by_slug.values():
            other_slug = other.get("slug", "")
            if not other_slug or other_slug == current_slug or other_slug in seen:
                continue
            score = 0
            if genre and apply_vars(other.get("genre", "")) == genre:
                score += 2
            other_tags = set(split_semicolon(apply_vars(other.get("tags", ""))))
            score += len(tags & other_tags)
            try:
                score += max(0, 3 - abs(int(article.get("priority") or 9999) - int(other.get("priority") or 9999)) // 10)
            except ValueError:
                pass
            if score > 0:
                candidates.append((score, other))
        candidates.sort(key=lambda x: (-x[0], int(x[1].get("priority") or 9999)))
        for _, other in candidates:
            slug = other["slug"]
            if slug in seen:
                continue
            seen.add(slug)
            links.append(
                f'<a class="related-link" href="../{html.escape(slug)}/">'
                f"{html.escape(apply_vars(other['title']))}</a>"
            )
            if len(links) >= 2:
                break
        for slug in ("exam-overview", "study-plan", "past-question-strategy", "glossary-how-to"):
            if len(links) >= 2:
                break
            if slug in by_slug and slug not in seen and slug != current_slug:
                seen.add(slug)
                links.append(
                    f'<a class="related-link" href="../{html.escape(slug)}/">'
                    f"{html.escape(apply_vars(by_slug[slug]['title']))}</a>"
                )
    if not links:
        return ""
    return (
        '<div class="related-box"><div class="related-box-title">関連記事</div><div class="related-links">'
        + "".join(links)
        + "</div></div>"
    )



def parse_source_links(value: str) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    for item in split_semicolon(value):
        label = item
        url = ""
        if "|" in item:
            label, url = [x.strip() for x in item.split("|", 1)]
        elif item.startswith(("http://", "https://")):
            url = item
        if url:
            sources.append({"label": apply_vars(label or url), "url": url})
        elif label:
            sources.append({"label": apply_vars(label), "url": ""})
    return sources


def quality_panel_html(article: dict[str, str]) -> str:
    author = apply_vars(article.get("author_name", ""))
    author_profile = apply_vars(article.get("author_profile", ""))
    reviewer = apply_vars(article.get("reviewer_name", ""))
    reviewer_profile = apply_vars(article.get("reviewer_profile", ""))
    fact_checked_at = apply_vars(article.get("fact_checked_at", ""))
    sources = parse_source_links(article.get("primary_sources", ""))

    rows: list[str] = []
    if author:
        text = author + (f"（{author_profile}）" if author_profile else "")
        rows.append(f"<tr><th>執筆</th><td>{html.escape(text)}</td></tr>")
    if reviewer:
        text = reviewer + (f"（{reviewer_profile}）" if reviewer_profile else "")
        rows.append(f"<tr><th>確認</th><td>{html.escape(text)}</td></tr>")
    if fact_checked_at:
        rows.append(f"<tr><th>事実確認日</th><td>{html.escape(fact_checked_at)}</td></tr>")
    if sources:
        source_items = []
        for source in sources:
            label = html.escape(source["label"])
            if source["url"]:
                source_items.append(f'<li><a href="{html.escape(source["url"])}" target="_blank" rel="noopener noreferrer">{label}</a></li>')
            else:
                source_items.append(f"<li>{label}</li>")
        rows.append(f'<tr><th>主な参照元</th><td><ul class="quality-source-list">{"".join(source_items)}</ul></td></tr>')
    if not rows:
        return ""
    return (
        '<section class="seo-quality-panel" aria-labelledby="quality-panel-title">'
        '<h2 id="quality-panel-title">この記事の信頼性について</h2>'
        '<table class="seo-info-table"><tbody>'
        + "".join(rows)
        + "</tbody></table></section>"
    )


def article_info_table(article: dict[str, str]) -> str:
    rows = [
        ("ジャンル", apply_vars(article.get("genre", ""))),
        ("タグ", " / ".join(split_semicolon(apply_vars(article.get("tags", ""))))),
    ]
    rows = [(k, v) for k, v in rows if v]
    if not rows:
        return ""
    return (
        '<section class="seo-article-section" aria-labelledby="article-info-title">'
        '<h2 id="article-info-title">記事の基本情報</h2>'
        '<table class="seo-info-table"><tbody>'
        + "".join(f"<tr><th>{html.escape(k)}</th><td>{html.escape(v)}</td></tr>" for k, v in rows)
        + "</tbody></table></section>"
    )


def build_article_html(
    article: dict[str, str],
    by_slug: dict[str, dict[str, str]],
    *,
    term_hrefs: dict[str, str] | None = None,
    glossary_categories: list[str] | None = None,
) -> str:
    slug = article["slug"]
    rel_path = Path("articles") / slug / "index.html"
    title = apply_vars(article["title"])
    desc = meta_description(apply_vars(article.get("meta_description") or article.get("lead") or title))
    canonical = public_url(f"articles/{slug}/")
    updated = content_date_from_row(article)
    genre = apply_vars(article.get("genre", "試験ガイド"))
    tags = split_semicolon(apply_vars(article.get("tags", "")))
    linked_terms: set[str] = set()
    sections = sections_html(article, term_hrefs=term_hrefs, linked_terms=linked_terms)
    faqs = faq_items(article)
    faq_section = faq_html(faqs, section_num=article_body_section_count(article) + 1) if faqs else ""
    toc = toc_html(article, bool(faqs))
    key_points_box = key_points_box_html(article)
    from tools.build_glossary_pages import field_hub_slug  # noqa: E402
    from tools.internal_links import (  # noqa: E402
        guide_knowledge_hub_link_items,
        merge_related_boxes,
    )
    from tools.knowledge_hub_seo import field_hub_page_exists  # noqa: E402

    article_links = parse_related_links(article.get("related_links", ""), by_slug, article)
    hub_items = guide_knowledge_hub_link_items(
        {
            "genre": genre,
            "tags": apply_vars(article.get("tags", "")),
            "title": title,
        },
        categories=glossary_categories or [],
        field_hub_slug_fn=field_hub_slug,
        field_hub_exists_fn=field_hub_page_exists,
    )
    hub_box = (
        '<div class="related-box" aria-labelledby="guide-hub-links-title">'
        '<div id="guide-hub-links-title" class="related-box-title">知識ハブ</div>'
        f'<div class="related-links">{"".join(hub_items)}</div></div>'
        if hub_items
        else ""
    )
    related = merge_related_boxes(article_links, hub_box)
    quality_panel = quality_panel_html(article)
    author = apply_vars(article.get("author_name", ""))
    reviewer = apply_vars(article.get("reviewer_name", ""))
    sources = parse_source_links(article.get("primary_sources", ""))
    official = primary_external_link()
    official_box = (
        '<section class="seo-article-section" aria-labelledby="official-info-title">'
        '<h2 id="official-info-title">公式情報の確認</h2>'
        '<blockquote><p><strong>公式情報の確認：</strong>'
        f'{html.escape(exam_name())}の最新情報は、'
        f'<a href="{html.escape(official["url"])}" target="_blank" rel="noopener noreferrer">{html.escape(official["label"])}</a>'
        "などの公式情報を必ず確認してください。</p></blockquote></section>"
    )
    info_table = article_info_table(article)
    crumb_items = [("トップ", "index.html"), ("試験ガイド", "articles/index.html"), (title, None)]
    article_schema = {
        "@type": "Article",
        "@id": canonical + "#article",
        "headline": title,
        "description": desc,
        "mainEntityOfPage": canonical,
        "inLanguage": "ja-JP",
        "about": [genre, *tags],
        "isPartOf": public_url("articles/index.html"),
        **json_ld_date_modified(updated),
    }
    if author:
        article_schema["author"] = {"@type": "Person", "name": author}
    if reviewer:
        article_schema["reviewedBy"] = {"@type": "Person", "name": reviewer}
    if sources:
        article_schema["citation"] = [source["url"] or source["label"] for source in sources]

    json_ld = {
        "@context": "https://schema.org",
        "@graph": [
            article_schema,
            {"@type": "WebPage", "@id": canonical + "#webpage", "url": canonical, "name": title, "description": desc, "inLanguage": "ja-JP"},
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "トップ", "item": public_url("index.html")},
                    {"@type": "ListItem", "position": 2, "name": "試験ガイド", "item": public_url("articles/index.html")},
                    {"@type": "ListItem", "position": 3, "name": title, "item": canonical},
                ],
            },
        ],
    }
    if faqs:
        json_ld["@graph"].append(
            {
                "@type": "FAQPage",
                "@id": canonical + "#faq",
                "mainEntity": [
                    {"@type": "Question", "name": item["question"], "acceptedAnswer": {"@type": "Answer", "text": item["answer"]}}
                    for item in faqs
                ],
            }
        )
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}｜{html.escape(brand_name())}</title>
<meta name="description" content="{html.escape(desc)}">
{ROBOTS_INDEX_FOLLOW}
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
{seo_editorial_stylesheet_links(rel_path, site_pages_ver=GUIDE_PAGES_CSS_VER)}
</head>
<body class="{shell_body_class('guide-article-page')}">
{site_page_wrap_open()}
{site_page_header(rel_path, current="articles")}
<main class="seo-article-main">
  {breadcrumb_html(rel_path, crumb_items)}
  <article class="{seo_editorial_article_class()}">
    <div class="article-meta">
      <span class="meta-category">{html.escape(genre)}</span>
      {meta_updated_html(updated)}
    </div>
    <h1 class="article-title">{html.escape(title)}</h1>
    <p class="article-lead">{html.escape(apply_vars(article.get("lead", "")))}</p>
    {key_points_box}
    {toc}
    {quality_panel}
    {sections}
    {faq_section}
    {info_table}
    {official_box}
    {related}
  </article>
</main>
{site_page_footer(rel_path, current="articles")}
{site_page_wrap_close()}
</body>
</html>
"""


def sort_articles_for_index(articles: list[dict[str, str]]) -> list[dict[str, str]]:
    order = guide_genre_order_index()
    return sorted(
        articles,
        key=lambda a: (
            order.get(apply_vars(a.get("genre", "")), 999),
            int(a.get("priority") or 9999),
        ),
    )


def build_index_html(articles: list[dict[str, str]]) -> str:
    rel_path = Path("articles/index.html")
    articles = sort_articles_for_index(articles)
    genre_styles = guide_genre_style_by_label()
    by_genre: dict[str, list[dict[str, str]]] = {}
    for article in articles:
        by_genre.setdefault(apply_vars(article.get("genre", "試験ガイド")), []).append(article)
    genre_counts = {genre: len(group) for genre, group in by_genre.items()}
    genre_chips = ['<button type="button" class="article-index-chip on" data-genre="all">すべて</button>']
    for genre_def in guide_article_genres():
        genre = genre_def["label"]
        count = genre_counts.get(genre, 0)
        if count == 0:
            continue
        style = genre_styles.get(genre, "meta")
        genre_chips.append(
            f'<button type="button" class="article-index-chip" data-genre="{html.escape(genre, quote=True)}" '
            f'data-genre-style="{html.escape(style, quote=True)}">'
            f"{html.escape(genre)}<span>{count}</span></button>"
        )
    article_cards: list[str] = []
    for article in articles:
        title_text = apply_vars(article["title"])
        desc_text = meta_description(apply_vars(article.get("meta_description") or article.get("lead") or title_text), 130)
        genre = apply_vars(article.get("genre", "試験ガイド"))
        style = genre_styles.get(genre, "meta")
        tags = " / ".join(split_semicolon(apply_vars(article.get("tags", ""))))
        search_text = " ".join([title_text, desc_text, genre, tags, apply_vars(article.get("lead", ""))])
        article_cards.append(
            '<article class="article-index-card" '
            f'data-genre="{html.escape(genre, quote=True)}" '
            f'data-genre-style="{html.escape(style, quote=True)}" '
            f'data-search="{html.escape(search_text, quote=True)}">'
            f'<a class="article-index-card-link" href="{html.escape(article["slug"])}/">'
            f'<span class="article-index-card-genre">{html.escape(genre)}</span>'
            f"<h2>{html.escape(title_text)}</h2>"
            f"<p>{html.escape(desc_text)}</p>"
            + (f'<div class="article-index-card-tags">{html.escape(tags)}</div>' if tags else "")
            + "</a></article>"
        )
    article_index_script = """<script>
(() => {
  const q = document.getElementById('article-index-q');
  const chips = Array.from(document.querySelectorAll('.article-index-chip[data-genre]'));
  const cards = Array.from(document.querySelectorAll('.article-index-card'));
  const hit = document.getElementById('article-index-hit');
  const empty = document.getElementById('article-index-empty');
  let activeGenre = 'all';
  const norm = (s) => (s || '').toString().trim().toLowerCase();
  function apply() {
    const query = norm(q?.value || '');
    let shown = 0;
    cards.forEach((card) => {
      const genreOk = activeGenre === 'all' || card.dataset.genre === activeGenre;
      const textOk = !query || norm(card.dataset.search).includes(query);
      const ok = genreOk && textOk;
      card.classList.toggle('hide', !ok);
      if (ok) shown++;
    });
    if (hit) hit.textContent = `${shown} / ${cards.length} 記事`;
    if (empty) empty.classList.toggle('hide', shown !== 0);
  }
  q?.addEventListener('input', apply);
  chips.forEach((btn) => {
    btn.addEventListener('click', () => {
      chips.forEach((b) => b.classList.remove('on'));
      btn.classList.add('on');
      activeGenre = btn.dataset.genre || 'all';
      apply();
    });
  });
  apply();
})();
</script>"""
    canonical = public_url("articles/index.html")
    title = f"試験ガイド｜{brand_name()}（{exam_name()}）"
    desc = f"{exam_name()}の受験フェーズ別ガイド（制度・学習計画・演習・直前・再受験）一覧です。用語の定義は用語解説（知識ハブ）をご覧ください。"
    item_list = [
        {"@type": "ListItem", "position": i, "name": apply_vars(a["title"]), "item": public_url(f"articles/{a['slug']}/")}
        for i, a in enumerate(articles, start=1)
    ]
    ld_json = json.dumps(
        {"@context": "https://schema.org", "@type": "ItemList", "name": f"{exam_name()} 試験ガイド", "numberOfItems": len(articles), "itemListElement": item_list},
        ensure_ascii=False,
        indent=2,
    )
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
{ld_json}
</script>
{seo_editorial_head_fonts()}
<link rel="stylesheet" href="../site-pages.css">
<link rel="stylesheet" href="../site-theme.css">
</head>
<body class="{shell_body_class('articles-index-page')}">
{site_page_wrap_open()}
{site_page_header(rel_path, current="articles")}
<main class="site-page-main">
  {breadcrumb_html(rel_path, [("トップ", "index.html"), ("試験ガイド", None)])}
  <h1>試験ガイド</h1>
  <p class="site-page-lead">{html.escape(exam_name())}の制度理解から学習計画・演習・直前対策まで、受験フェーズ別の<strong>進め方</strong>をまとめています。用語の意味・比較・数値は<a href="../terms/index.html">用語解説（知識ハブ）</a>、問題演習は<a href="../q/index.html">過去問一覧</a>からどうぞ。</p>
  <section class="article-index-panel" aria-labelledby="article-index-heading">
    <div class="article-index-head">
      <div>
        <h2 id="article-index-heading">記事一覧</h2>
        <p>全{len(articles)}記事。キーワード検索とジャンルで絞り込めます。</p>
      </div>
      <span id="article-index-hit" class="article-index-hit">{len(articles)} / {len(articles)} 記事</span>
    </div>
    <div class="article-index-tools">
      <label class="article-index-search" for="article-index-q">
        <span>記事検索</span>
        <input id="article-index-q" type="search" inputmode="search" autocomplete="off" placeholder="例：独学、過去問、申込、用語…">
      </label>
      <div class="article-index-chips" aria-label="ジャンル絞り込み">
        {"".join(genre_chips)}
      </div>
    </div>
    <div class="article-index-grid" aria-label="記事一覧">
      {"".join(article_cards)}
    </div>
    <p id="article-index-empty" class="article-index-empty hide">条件に合う記事がありません。検索語を短くするか、ジャンルを「すべて」に戻してください。</p>
  </section>
</main>
{site_page_footer(rel_path, current="articles")}
{site_page_wrap_close()}
{article_index_script}
</body>
</html>
"""


def load_articles() -> list[dict[str, str]]:
    if not ARTICLES_CSV.is_file():
        raise FileNotFoundError(str(ARTICLES_CSV))
    rows = list(csv.DictReader(ARTICLES_CSV.read_text(encoding="utf-8-sig").splitlines()))
    return sorted(rows, key=lambda x: int(norm(x.get("priority")) or 9999))


def clean_generated_dirs() -> None:
    if not ARTICLES_DIR.is_dir():
        return
    for child in ARTICLES_DIR.iterdir():
        if child.is_dir() and (child / GEN_MARKER).is_file():
            shutil.rmtree(child)


def main() -> int:
    articles = load_articles()
    by_slug = {norm(a.get("slug")): a for a in articles if norm(a.get("slug"))}
    term_hrefs: dict[str, str] | None = None
    glossary_categories: list[str] = []
    try:
        from tools.build_glossary_pages import load_glossary_entries, make_term_lookup  # noqa: E402
        from tools.internal_links import term_hrefs_for_auto_link  # noqa: E402

        glossary_entries = load_glossary_entries()
        if glossary_entries:
            term_hrefs = term_hrefs_for_auto_link(make_term_lookup(glossary_entries))
            glossary_categories = sorted(
                {norm(e.get("category")) for e in glossary_entries if norm(e.get("category"))}
            )
    except Exception as exc:
        print(f"Warning: glossary auto-link disabled: {exc}", file=sys.stderr)
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    clean_generated_dirs()
    for article in articles:
        slug = norm(article.get("slug"))
        if not slug:
            continue
        out_dir = ARTICLES_DIR / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / GEN_MARKER).write_text("generated\n", encoding="utf-8")
        (out_dir / "index.html").write_text(
            build_article_html(
                article,
                by_slug,
                term_hrefs=term_hrefs,
                glossary_categories=glossary_categories,
            ),
            encoding="utf-8",
        )
    (ARTICLES_DIR / "index.html").write_text(build_index_html(articles), encoding="utf-8")
    print(f"Wrote {len(articles)} guide articles under {ARTICLES_DIR}")
    print(f"Wrote {ARTICLES_DIR / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
