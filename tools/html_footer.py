# -*- coding: utf-8 -*-
"""静的 HTML 用フッター（相対パス付き）と GA4 共通タグ。

- 測定IDを変えるときは GA4_MEASUREMENT_ID と site-analytics.js 内の DEFAULT_MID を揃える。
- 新規の手書き HTML では </body> 直前に analytics_snippet(Path('相対パス')) と同等の2行を置くか、
  生成ページでは site_page_footer の直後に analytics が付くので head に GA を書かない。
- ヘッダー・フッターは index.html の topnav / site-footer と同型（site-pages.css の site-shell）。
- ヘッダー・フッターの契約: docs/site-chrome.md（フッター遷移でヘッダー構造が変わらないこと）
"""

from __future__ import annotations

import html
from pathlib import Path

from tools.site_config import (
    brand_logo_lines,
    brand_logo_size_class,
    brand_name,
    contact_url,
    copyright_text,
    exam_name,
    footer_disclaimer,
    ga4_measurement_id,
    learning_nav_label,
    navigation_items,
)

FORM_URL = contact_url()

# GA4 測定ID（site-analytics.js の DEFAULT_MID と揃えること）
GA4_MEASUREMENT_ID = ga4_measurement_id()

# フッター注記・著作権（共通フッター・静的ガイドの表記揃え）
FOOTER_DISCLAIMER = footer_disclaimer()
SITE_COPYRIGHT = copyright_text()

# 静的ページ・生成 HTML 共通（Search Console / クローラ向け）
ROBOTS_INDEX_FOLLOW = '<meta name="robots" content="index, follow">'

SITE_FOOTER_NAV = navigation_items("footer")

# 共通フッター shell：復習ページ同型（サイドグレー・中央白カラム）。site-pages.css とセット。
SHELL_COLUMN_PAGE_CLASS = "site-shell-column-page"


def shell_body_class(*parts: str) -> str:
    """<body class=\"...\"> 用。フッター付き静的ページは必ず SHELL_COLUMN_PAGE_CLASS を含める。"""
    merged: list[str] = []
    for part in parts:
        for token in part.split():
            if token and token not in merged:
                merged.append(token)
    if SHELL_COLUMN_PAGE_CLASS not in merged:
        merged.append(SHELL_COLUMN_PAGE_CLASS)
    return " ".join(merged)


# index.html topnav と同じ学習ナビ（用語解説のみ静的一覧、他は SPA ハッシュへ）
LEARNING_NAV_ITEMS: list[tuple[str, str, str, str]] = [
    (
        "tnav-ichimondou",
        "一問一答",
        "#ichimondou",
        '<svg viewBox="0 0 16 16"><path d="M8 2v12M4 4h8M4 8h8M4 12h8"/></svg>',
    ),
    (
        "tnav-past",
        "過去問",
        "#past",
        '<svg viewBox="0 0 16 16"><path d="M3 2h10v12H3z"/><path d="M5 5h6M5 8h6M5 11h4"/></svg>',
    ),
    (
        "tnav-orig",
        "実践演習",
        "#orig",
        '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="6"/><path d="M8 5v3l2 1"/></svg>',
    ),
    (
        "tnav-dash",
        "記録・分析",
        "#dash",
        '<svg viewBox="0 0 16 16"><path d="M2 13L5 8l3 2 3-5 3 2"/></svg>',
    ),
    (
        "tnav-review",
        "復習",
        "#review",
        '<svg viewBox="0 0 16 16"><path d="M2 4h12M2 8h8M2 12h10"/></svg>',
    ),
    (
        "tnav-glossary",
        "用語解説",
        "terms/index.html",
        '<svg viewBox="0 0 16 16"><rect x="2.5" y="2" width="11" height="12" rx="1.5"/><path d="M5 6h6M5 9h4"/></svg>',
    ),
]

# site_page_header(current=...) で学習ナビの active を付ける。
# ヘッダー「過去問」は SPA 演習（#past）。フッター「過去問一覧」（q/index.html）とは別コンテンツのため q は含めない。
LEARNING_NAV_ACTIVE_BY_PAGE: dict[str, str] = {
    "terms": "tnav-glossary",
    "practice": "tnav-orig",
    "ichimon": "tnav-ichimondou",
}

# ヘッダー・フッターが同じ静的一覧を指す項目では、フッター側 aria-current を抑制（二重ハイライト防止）
FOOTER_SUPPRESS_CURRENT_WHEN_HEADER: frozenset[str] = frozenset(LEARNING_NAV_ACTIVE_BY_PAGE.keys())


def _in_q_section(rel_path: Path) -> bool:
    return bool(rel_path.parts) and rel_path.parts[0] == "q"


def html_rel_href(from_file: str, to_site_rel: str) -> str:
    """HTML 文書 from_file から site 相対 to_site_rel への相対 href。"""
    to = to_site_rel.lstrip("/")
    if to.startswith("..") or "://" in to:
        return to_site_rel
    from_s = [p for p in from_file.split("/") if p]
    to_s = [p for p in to.split("/") if p]
    if from_s == to_s:
        return to_s[-1]
    from_dir = from_s[:-1] if from_s and from_s[-1].endswith(".html") else from_s
    to_dir = to_s[:-1] if to_s and to_s[-1].endswith(".html") else to_s
    if from_dir == to_dir and to_s:
        return to_s[-1]
    if to_s == ["index.html"] and not to_dir:
        if not from_dir:
            return "index.html"
        return "/".join([".."] * len(from_dir) + ["index.html"])
    i = 0
    while i < len(from_dir) and i < len(to_dir) and from_dir[i] == to_dir[i]:
        i += 1
    if i == 0 and len(to_s) == 1:
        ups = len(from_dir)
    else:
        ups = len(from_dir) - i
    downs = to_s[i:]
    out = "/".join([".."] * ups + downs)
    return out or "."


def footer_href(rel_path: Path, site_rel: str) -> str:
    """rel_path: ROOT からの相対パス（例 q/past/y2025/q01/index.html）。site_rel: index.html / q/index.html 等。"""
    site_rel = site_rel.lstrip("/")
    if site_rel.startswith(".."):
        return site_rel
    parent = rel_path.parent
    parts = parent.parts
    if parent.as_posix() == "q" and site_rel == "q/index.html":
        return "index.html"
    if parts and parts[0] == "terms" and len(parts) == 1 and site_rel.startswith("field-") and site_rel.endswith("/index.html"):
        return site_rel
    if parts and parts[0] == "q" and site_rel.startswith("q/"):
        q_rel = site_rel[2:]
        depth = len(parts) - 1
        prefix = "/".join([".."] * depth)
        return f"{prefix}/{q_rel}" if prefix else q_rel
    if (
        len(parts) >= 4
        and parts[0] == "q"
        and parts[1] == "past"
        and site_rel.startswith("past/y")
        and site_rel.endswith("/index.html")
    ):
        up = len(parts) - 3
        return ("/".join([".."] * up) + "/index.html") if up else "index.html"
    return html_rel_href(rel_path.as_posix(), site_rel)


def ga4_head_snippet() -> str:
    """生成 HTML の <head> 内用 Google タグ（site-analytics.js の二重初期化を防ぐ）。"""
    mid = html.escape(GA4_MEASUREMENT_ID)
    return (
        "<!-- Google tag (gtag.js) -->\n"
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={mid}"></script>\n'
        "<script>\n"
        "window.dataLayer = window.dataLayer || [];\n"
        "function gtag(){dataLayer.push(arguments);}\n"
        "window.gtag = gtag;\n"
        f'window.__GA4_HEAD_INIT__ = "{mid}";\n'
        'gtag("js", new Date());\n'
        f'gtag("config", "{mid}");\n'
        "</script>"
    )


def analytics_snippet(rel_path: Path) -> str:
    """全静的ページ共通: フッター直後（</body> 直前想定）に置く GA4 タグ。相対パスで site-analytics.js を読む。"""
    src = html.escape(footer_href(rel_path, "site-analytics.js"))
    mid = html.escape(GA4_MEASUREMENT_ID)
    return (
        "<!-- GA4: tools/html_footer.analytics_snippet（測定IDは GA4_MEASUREMENT_ID） -->\n"
        f'<script>window.__GA4_MEASUREMENT_ID__="{mid}";</script>\n'
        f'<script defer src="{src}"></script>'
    )


def static_q_site_header(*, root_href: str, breadcrumb_items: list[tuple[str, str | None]]) -> str:
    """CSV 未配置時の q/index プレースホルダー用（宅建マスター互換）。"""
    lis: list[str] = []
    for text, href in breadcrumb_items:
        if href:
            lis.append(f'<li><a href="{html.escape(href)}">{html.escape(text)}</a></li>')
        else:
            lis.append(f'<li aria-current="page">{html.escape(text)}</li>')
    crumbs = "\n      ".join(lis)
    return f"""<header class="q-static-header">
  <p class="q-static-brand"><a href="{html.escape(root_href)}">{html.escape(brand_name())}</a>（{html.escape(exam_name())}）</p>
  <nav aria-label="パンくず">
    <ol class="q-breadcrumb">
      {crumbs}
    </ol>
  </nav>
</header>"""


def static_q_footer_block(rel_path: Path) -> str:
    """CSV 未配置時の q/index プレースホルダー用フッター + GA4。"""

    def h(dest: str) -> str:
        return html.escape(footer_href(rel_path, dest))

    return f"""<footer class="q-static-footer">
  <nav class="q-static-footer-nav" aria-label="サイトの他ページ">
    <a href="{h("index.html")}">トップ</a>
    <a href="{h("about.html")}">このサイトについて</a>
    <a href="{h("q/index.html")}">過去問一覧</a>
    <a href="{h("terms/index.html")}">用語集</a>
    <a href="{h("articles/index.html")}">試験ガイド</a>
    <a href="{h("related-sites.html")}">関連リンク</a>
    <a href="{h("privacy.html")}">プライバシー</a>
    <a href="{html.escape(FORM_URL)}" target="_blank" rel="noopener noreferrer">お問い合わせ</a>
  </nav>
  <p><small>{html.escape(FOOTER_DISCLAIMER)}</small></p>
  <p><small>{html.escape(SITE_COPYRIGHT)}</small></p>
</footer>
{analytics_snippet(rel_path)}"""


def _breadcrumb_ol(rel_path: Path, items: list[tuple[str, str | None]]) -> str:
    lis: list[str] = []
    for text, href in items:
        if href:
            h = footer_href(rel_path, href) if not href.startswith("http") else href
            lis.append(f'<li><a href="{html.escape(h)}">{html.escape(text)}</a></li>')
        else:
            lis.append(f'<li aria-current="page">{html.escape(text)}</li>')
    crumbs = "\n        ".join(lis)
    return f"""<nav class="site-page-header-crumb" aria-label="パンくず">
      <ol class="q-breadcrumb">
        {crumbs}
      </ol>
    </nav>"""


def _brand_logo_mark_html(*, variant: str = "header") -> str:
    top, bottom = brand_logo_lines()
    size_cls = brand_logo_size_class(top)
    if variant == "footer":
        base = "site-footer-logo-mark"
    else:
        base = "topnav-logo-mark"
    cls = base + (f" {size_cls}" if size_cls else "")
    top_h = html.escape(top)
    bottom_h = html.escape(bottom)
    return (
        f'<div class="{cls}" aria-hidden="true">'
        f'<span class="logo-mark-line">{top_h}</span>'
        f'<span class="logo-mark-line logo-mark-line--sub">{bottom_h}</span>'
        f"</div>"
        if variant == "header"
        else f'<span class="{cls}" aria-hidden="true">'
        f'<span class="logo-mark-line">{top_h}</span>'
        f'<span class="logo-mark-line logo-mark-line--sub">{bottom_h}</span>'
        f"</span>"
    )


def _topnav_logo(rel_path: Path) -> str:
    root = html.escape(footer_href(rel_path, "index.html"))
    name = html.escape(brand_name())
    exam = html.escape(exam_name())
    mark = _brand_logo_mark_html(variant="header")
    return f"""<a class="topnav-logo" href="{root}" aria-label="{name}、{exam}対策のトップへ">
          {mark}
          <span class="topnav-logo-stack">
            <span class="topnav-logo-sub">{exam}</span>
          </span>
        </a>"""


def _learning_nav_href(rel_path: Path, dest: str) -> str:
    """学習ナビのリンク先（#hash は SPA トップ、それ以外は site 相対パス）。"""
    if dest.startswith("#"):
        return "/" + dest
    return footer_href(rel_path, dest)


def _learning_nav_links(rel_path: Path, *, current: str | None = None) -> str:
    """静的ページ用: SPA 学習ナビ（用語解説は terms/index.html）。"""
    active_id = LEARNING_NAV_ACTIVE_BY_PAGE.get(current or "")
    links: list[str] = []
    for nav_id, label, dest, icon in LEARNING_NAV_ITEMS:
        href = html.escape(_learning_nav_href(rel_path, dest))
        active = nav_id == active_id
        cls = "topnav-link active" if active else "topnav-link"
        cur = ' aria-current="page"' if active else ""
        display_label = learning_nav_label(nav_id, label)
        links.append(
            f'<a class="{cls}" id="{nav_id}" href="{href}"{cur}>{icon}{html.escape(display_label)}</a>'
        )
    return "\n          ".join(links)


def site_page_header(
    rel_path: Path,
    *,
    current: str | None = None,
    breadcrumb_items: list[tuple[str, str | None]] | None = None,
    wide: bool = False,
) -> str:
    """index.html の topnav と同型・同じ学習ナビ（静的ページから SPA へ戻る）。"""
    _ = breadcrumb_items
    nav_html = _learning_nav_links(rel_path, current=current)
    wide_cls = " site-shell-header--wide" if wide else ""
    return f"""<header class="topnav site-shell-header{wide_cls}">
      <div class="topnav-inner">
        {_topnav_logo(rel_path)}
        <nav class="topnav-links" aria-label="メインナビゲーション">
          {nav_html}
        </nav>
      </div>
    </header>"""


def site_shell_footer(
    rel_path: Path,
    *,
    fixed: bool = True,
    include_analytics: bool = True,
    current: str | None = None,
) -> str:
    """index.html の site-footer と同型（画面下固定。site-pages.css で position:fixed）。"""
    _ = fixed
    root = html.escape(footer_href(rel_path, "index.html"))
    title = html.escape(f"{brand_name()}（{exam_name()}対策）トップへ")
    mark = _brand_logo_mark_html(variant="footer")
    links: list[str] = []
    for label, dest, key in SITE_FOOTER_NAV:
        suppress_footer_current = bool(
            current and key == current and key in FOOTER_SUPPRESS_CURRENT_WHEN_HEADER
        )
        is_current = bool(current and key == current and not suppress_footer_current)
        cur = ' aria-current="page"' if is_current else ""
        if dest.startswith("http"):
            href = dest
            links.append(
                f'<a href="{html.escape(href)}" target="_blank" rel="noopener noreferrer"{cur}>'
                f"{html.escape(label)}</a>"
            )
        else:
            href = footer_href(rel_path, dest)
            links.append(
                f'<a href="{html.escape(href)}"{cur}>{html.escape(label)}</a>'
            )
    links_html = "\n          ".join(links)
    footer = f"""<footer class="site-footer" role="contentinfo">
    <div class="site-footer-scroll">
      <div class="site-footer-inner">
        <a class="site-footer-brand" href="{root}" title="{title}">
          {mark}
        </a>
        <span class="site-footer-sep" aria-hidden="true"></span>
        <nav class="site-footer-legal" aria-label="サイト情報・ポリシー">
          {links_html}
        </nav>
        <span class="site-footer-sep" aria-hidden="true"></span>
        <span class="site-footer-copy">{html.escape(SITE_COPYRIGHT)}</span>
      </div>
    </div>
  </footer>"""
    if include_analytics:
        return footer + "\n" + analytics_snippet(rel_path)
    return footer


def site_page_footer(rel_path: Path, *, current: str | None = None, wide: bool = False) -> str:
    """静的ページ用フッター + GA4（site-config の navigation.footer）。"""
    _ = wide
    return site_shell_footer(rel_path, include_analytics=True, current=current)


def site_page_wrap_open() -> str:
    return '<div class="site-page-wrap">'


def site_page_wrap_close() -> str:
    return "</div>"


def q_index_tools_open_html(
    *,
    search_label: str,
    search_placeholder: str,
    hit_text: str,
) -> str:
    """一覧の検索行（ヒット件数を同じ行に）。"""
    return (
        '<div class="past-index-tools" aria-label="絞り込み">'
        '<div class="past-index-tools-primary">'
        f'<label class="past-index-search" for="q-index-q">'
        f'<span class="u-visually-hidden">{html.escape(search_label)}</span>'
        f'<input id="q-index-q" type="search" inputmode="search" autocomplete="off" '
        f'placeholder="{html.escape(search_placeholder)}" '
        f'aria-label="{html.escape(search_label)}">'
        "</label>"
        f'<span id="q-index-hit" class="past-index-hit" aria-live="polite">'
        f"{html.escape(hit_text)}</span>"
        "</div>"
        '<div class="past-index-tools-actions">'
        '<button type="button" class="q-index-reset hide" id="q-index-reset">'
        "条件をクリア</button></div>"
        '<div class="q-index-active-filters hide" id="q-index-active-filters" '
        'aria-live="polite"></div>'
    )


def q_index_tools_close_html() -> str:
    return "</div>"


def q_index_stats_line(*, question_count: int, mode: str, year_count: int = 0, category_count: int = 0) -> str:
    """一覧パネル見出し下の統計（過去問・実践・一問一答で文言を統一）。"""
    n = question_count
    if mode == "practice":
        return f"全{n}問・{category_count}分野"
    if mode == "ichimon":
        return f"全{n}問・{year_count}年度・{category_count}分野"
    return f"全{n}問・{year_count}年度・{category_count}分野"


def q_index_filters_details_html(
    *,
    year_row_label: str,
    year_jump_html: str,
    category_chips_html: str,
    status_chips_html: str,
    show_year_row: bool = True,
    show_category_row: bool = True,
    filters_hint: str = "年度・分野・学習状況",
) -> str:
    """一覧の年度・分野・学習状況チップ（スマホでは details で折りたたみ）。"""
    year_row = ""
    if show_year_row and year_jump_html.strip():
        year_row = (
            f'<div class="q-index-chips-row q-index-year-row" id="q-index-year-row">'
            f'<span class="q-index-chips-label">{html.escape(year_row_label)}</span>'
            f'<nav class="q-index-chips q-index-year-jump" aria-label="{html.escape(year_row_label)}で移動">'
            f"{year_jump_html}</nav></div>"
        )
    category_row = ""
    if show_category_row:
        category_row = (
            '<div class="q-index-chips-row">'
            '<span class="q-index-chips-label" id="q-index-chips-label">分野</span>'
            f'<div class="q-index-chips" aria-labelledby="q-index-chips-label">'
            f"{category_chips_html}</div></div>"
        )
    return (
        '<details class="q-index-filters-more">'
        '<summary class="q-index-filters-more-summary">'
        '<span class="q-index-filters-more-title">絞り込み</span>'
        f'<span class="q-index-filters-more-hint">{html.escape(filters_hint)}</span>'
        "</summary>"
        '<div class="q-index-filters-more-body">'
        f"{year_row}{category_row}"
        '<div class="q-index-chips-row">'
        '<span class="q-index-chips-label">学習状況</span>'
        f'<div class="q-index-chips q-index-status-chips" role="group" aria-label="学習状況（アプリ連携）">'
        f"{status_chips_html}</div></div></div></details>"
    )


def q_hub_links_html(rel_path: Path, *, current: str) -> str:
    """過去問・実践演習・一問一答のモード切替タブ（一覧・個別ページ共通）。"""
    items: list[tuple[str, str, str]] = [
        ("past", "過去問", "q/index.html"),
        ("practice", "実践演習", "q/practice/index.html"),
        ("ichimon", "一問一答", "q/ichimon/index.html"),
    ]
    lis: list[str] = []
    for key, label, target in items:
        if key == current:
            lis.append(
                f'<li class="q-hub-tab is-current">'
                f'<span class="q-hub-tab-label" aria-current="page">{html.escape(label)}</span>'
                f"</li>"
            )
        else:
            href = "/" + target.lstrip("/")
            lis.append(
                f'<li class="q-hub-tab">'
                f'<a class="q-hub-tab-label" href="{html.escape(href)}">{html.escape(label)}</a>'
                f"</li>"
            )
    return (
        '<nav class="q-hub-links q-hub-links--tabs" aria-label="問題タイプ">'
        f'<ul class="q-hub-tabs-list">{"".join(lis)}</ul></nav>'
    )


def breadcrumb_html(rel_path: Path, items: list[tuple[str, str | None]]) -> str:
    """後方互換。新規は site_page_header(..., breadcrumb_items=...) を使用。"""
    return _breadcrumb_ol(rel_path, items)


def static_site_header(*, root_href: str, breadcrumb_items: list[tuple[str, str | None]]) -> str:
    """過去問など従来の q-static ヘッダー（パンくず付き）。"""
    lis: list[str] = []
    for text, href in breadcrumb_items:
        if href:
            lis.append(f'<li><a href="{html.escape(href)}">{html.escape(text)}</a></li>')
        else:
            lis.append(f'<li aria-current="page">{html.escape(text)}</li>')
    crumbs = "\n      ".join(lis)
    return f"""<header class="q-static-header">
  <p class="q-static-brand"><a href="{html.escape(root_href)}">{html.escape(brand_name())}</a>（{html.escape(exam_name())}）</p>
  <nav aria-label="パンくず">
    <ol class="q-breadcrumb">
      {crumbs}
    </ol>
  </nav>
</header>"""


def static_footer_block(rel_path: Path) -> str:
    """過去問など従来の q-static フッター + GA4。"""
    return site_shell_footer(rel_path, include_analytics=True)
