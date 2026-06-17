#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply site-config.json to hand-written HTML/JS placeholders."""

from __future__ import annotations

import re
import sys
import csv
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.site_config import (
    base_path,
    brand_logo_lines,
    brand_logo_size_class,
    brand_mark,
    brand_name,
    category_to_field_map,
    clean_origin,
    contact_url,
    copyright_text,
    exam_name,
    external_links,
    ga4_measurement_id,
    learning_nav_label,
    official_organization,
    primary_external_link,
    public_url,
    sync_config_files,
    fields,
)
from tools.html_footer import site_page_footer, site_page_header, site_shell_footer
from tools.brand_assets import inject_brand_head
from tools.build_index_faq_ldjson import inject_index_faq_ldjson
from tools.index_seo_head import (
    INDEX_SEO_MARKER_END,
    INDEX_SEO_MARKER_START,
    inject_index_seo_head,
    migrate_legacy_takken_leaks,
    update_index_spa_seo_js,
)
from tools.index_spa_patch import (
    INDEX_NOSCRIPT_MARKER_END,
    INDEX_NOSCRIPT_MARKER_START,
    ensure_site_config_before_fields,
    inject_index_fields_fallback,
    inject_index_noscript,
    inject_index_spa_ui_leaks,
)


TEXT_TARGETS = [
    ROOT / "index.html",
    ROOT / "about.html",
    ROOT / "privacy.html",
    ROOT / "related-sites.html",
    ROOT / "articles" / "index.html",
    ROOT / "site-analytics.js",
]

STATIC_PAGE_CURRENTS = {
    ROOT / "about.html": "about",
    ROOT / "privacy.html": "privacy",
    ROOT / "related-sites.html": "related",
    ROOT / "articles" / "index.html": "articles",
}

STATIC_PAGE_CANONICAL = {
    ROOT / "about.html": "about.html",
    ROOT / "privacy.html": "privacy.html",
    ROOT / "related-sites.html": "related-sites.html",
}

_STATIC_CANONICAL_RE = re.compile(r'<link rel="canonical" href="[^"]*">', re.I)

_RELATED_OFFICIAL_SECTION_RE = re.compile(
    r'(<section class="site-page-section" aria-labelledby="sec-official">\s*'
    r'<h2 id="sec-official">試験・資格（公式・準公式）</h2>\s*'
    r"<ul>)(.*?)(</ul>\s*</section>)",
    re.S,
)

_MANKAN_OFFICIAL_LINK_RE = re.compile(
    r'<a href="https://www\.mankan\.(?:org|or\.jp)/"[^>]*>試験実施団体</a>'
)
_AUTH_LOGO_BLOCK_RE = re.compile(
    r'<div class="auth-logo-mark" title="[^"]*">[^<]+</div>\s*'
    r"<h1>[^<]+</h1>\s*"
    r'<p class="auth-logo-fullname">[^<]+</p>',
    re.I,
)
_MLIT_OFFICIAL_LINK_RE = re.compile(
    r'<a href="https://www\.mlit\.go\.jp/[^"]*"[^>]*>国土交通省(?:\s*住宅局)?</a>'
)
_JAFP_OFFICIAL_LINK_RE = re.compile(
    r'<a href="[^"]*" target="_blank" rel="noopener" style="color:var\(--text2\);text-decoration:underline">日本FP協会（公式）</a>'
)
_NTA_OFFICIAL_LINK_RE = re.compile(
    r'<a href="[^"]*" target="_blank" rel="noopener" style="color:var\(--text2\);text-decoration:underline">国税庁</a>'
)


_SPA_BREADCRUMB_TOP_RE = re.compile(
    r'(<li class="breadcrumb-item"><a href="/" onclick="event\.preventDefault\(\);gotoPage\(\'quiz-start\'\)" title=")[^"]*(">)[^<]*(</a></li>)',
)
_GA4_INLINE_RE = re.compile(r'window\.__GA4_MEASUREMENT_ID__="[^"]*";')
_GA4_DEFAULT_MID_RE = re.compile(r'var DEFAULT_MID = "[^"]*";')


def apply_ga4_measurement_ids(text: str) -> str:
    """site-config の ga4MeasurementId を index / site-analytics へ常に反映する。"""
    mid = ga4_measurement_id()
    text = _GA4_INLINE_RE.sub(f'window.__GA4_MEASUREMENT_ID__="{mid}";', text)
    text = _GA4_DEFAULT_MID_RE.sub(f'var DEFAULT_MID = "{mid}";', text)
    return text


def fix_quiz_start_page_titles(text: str) -> str:
    """トップ（quiz-start）の見出し・パンくずを「試験名」の問題を解くに統一。"""
    title = html.escape(f"「{exam_name()}」の問題を解く")
    for old in (
        '<li class="breadcrumb-item breadcrumb-current" aria-current="page">問題を解く</li>',
        '<li class="breadcrumb-item breadcrumb-current" aria-current="page">「◯◯試験（プレースホルダー）」の問題を解く</li>',
    ):
        text = text.replace(
            old,
            f'<li class="breadcrumb-item breadcrumb-current" aria-current="page">{title}</li>',
        )
    for old in (
        '<h2 class="page-title">問題を解く</h2>',
        '<h2 class="page-title">「◯◯試験（プレースホルダー）」の問題を解く</h2>',
    ):
        text = text.replace(old, f'<h2 class="page-title">{title}</h2>')
    return text


def fix_spa_breadcrumb_top(text: str) -> str:
    """SPA 内パンくず1段目はサイト名ではなく「トップ」に統一する。"""
    return _SPA_BREADCRUMB_TOP_RE.sub(r"\1トップ\2トップ\3", text)


_LEGACY_SPA_PREFIXES = ("/fp3", "/fp2")


def fix_legacy_base_path_hrefs(text: str) -> str:
    """basePath 未設定時に旧多級サブパス（/fp3 等）へのリンク・canonical をルートに揃える。"""
    if base_path():
        return text
    origin = clean_origin()
    for legacy in _LEGACY_SPA_PREFIXES:
        text = text.replace(f'href="{legacy}#', 'href="/#')
        text = text.replace(f"href='{legacy}#", "href='/#")
        text = text.replace(f'href="{legacy}/index.html"', 'href="/index.html"')
        text = text.replace(f"href='{legacy}/index.html'", "href='/index.html'")
        text = text.replace(f'href="{legacy}/"', 'href="/"')
        text = text.replace(f"{origin}{legacy}/", f"{origin}/")
        text = text.replace(f"{origin}{legacy}#", f"{origin}/#")
        text = text.replace(f"{origin}{legacy}\"", f'{origin}/"')
    return text


def replace_all(text: str) -> str:
    origin = clean_origin()
    host = origin.replace("https://", "").replace("http://", "").strip("/")
    official = primary_external_link()
    orig_nav_label = learning_nav_label("tnav-orig", "実践演習")
    replacements = [
        ("© 2026 Sampleマスター学習支援・YOUR-DOMAIN.example", copyright_text()),
        ("Sampleマスター", brand_name()),
        ("◯◯試験（プレースホルダー）", exam_name()),
        ("YOUR-DOMAIN.example", host),
        ("https://YOUR-DOMAIN.example", origin),
        ("https://example.com/contact", contact_url()),
        ("一般社団法人 試験実施団体", official_organization()),
        ("試験実施団体（試験・登録の公式）", official.get("label", official_organization())),
        ("https://example.com/", official.get("url", "https://example.com/")),
    ]
    if orig_nav_label == "実践演習":
        replacements.extend(
            [
                ("オリジナル問題", "実践演習"),
                ("オリジナル演習", "実践演習"),
                ("単元別問題データ", "実践演習データ"),
            ]
        )
    if exam_name() != "◯◯試験（プレースホルダー）":
        replacements.append(("◯◯試験", exam_name()))
    for src, dst in replacements:
        text = text.replace(src, dst)
    text = apply_ga4_measurement_ids(text)

    marker = '<script src="./site-config.js"></script>'
    if "site-config.js" not in text and "site-analytics.js" in text:
        for old, new_block in (
            (
                '<script defer src="./site-analytics.js"></script>',
                marker + '\n<script defer src="./site-analytics.js"></script>',
            ),
            (
                '<script defer src="site-analytics.js"></script>',
                '<script src="site-config.js"></script>\n<script defer src="site-analytics.js"></script>',
            ),
        ):
            if old in text:
                text = text.replace(old, new_block, 1)
                break
    return text


def ensure_theme_link(text: str, rel_path: Path) -> str:
    if "site-theme.css" in text:
        return text
    href = "site-theme.css" if rel_path.parent == Path(".") else "../site-theme.css"
    text = text.replace(
        '<link rel="stylesheet" href="./site-pages.css">',
        '<link rel="stylesheet" href="./site-pages.css">\n  <link rel="stylesheet" href="./site-theme.css">',
    )
    text = text.replace(
        '<link rel="stylesheet" href="../site-pages.css">',
        '<link rel="stylesheet" href="../site-pages.css">\n  <link rel="stylesheet" href="../site-theme.css">',
    )
    if "site-theme.css" not in text and "site-pages.css" in text:
        text = re.sub(
            r'(<link rel="stylesheet" href="[^"]*site-pages\.css[^"]*">)',
            rf'\1\n  <link rel="stylesheet" href="{href}">',
            text,
            count=1,
        )
    return text


def fix_wrong_official_urls(text: str) -> str:
    """他試験 fork 由来の公式リンク（mankan.org / 国土交通省 等）を site-config へ差し替え。"""
    official = primary_external_link()
    url = str(official.get("url") or "").strip()
    label = str(official.get("label") or official_organization()).strip()
    links = external_links()
    if url and "jafp.or.jp" not in url and ("jafp.or.jp" in text or "日本FP協会（公式）" in text):
        if label:
            anchor = (
                f'<a href="{html.escape(url)}" target="_blank" rel="noopener" '
                f'style="color:var(--text2);text-decoration:underline">{html.escape(label)}</a>'
            )
            text = _JAFP_OFFICIAL_LINK_RE.sub(anchor, text)
        text = text.replace("https://www.jafp.or.jp/", url)
        if len(links) > 1:
            sec_url = str(links[1].get("url") or "").strip()
            sec_label = str(links[1].get("label") or "").strip()
            sec_short = sec_label.split("（")[0].strip() if sec_label else ""
            if sec_url and sec_short:
                text = text.replace("法令・税制の原文は", "法令・通達の原文は")
                sec_anchor = (
                    f'<a href="{html.escape(sec_url)}" target="_blank" rel="noopener" '
                    f'style="color:var(--text2);text-decoration:underline">{html.escape(sec_short)}</a>'
                )
                text = _NTA_OFFICIAL_LINK_RE.sub(sec_anchor, text)
                text = text.replace("https://www.nta.go.jp/", sec_url)
    if url:
        text = text.replace("https://www.mankan.org/", url)
        text = text.replace("https://www.mankan.or.jp/", url)
        if label:
            text = _MANKAN_OFFICIAL_LINK_RE.sub(
                f'<a href="{html.escape(url)}" target="_blank" rel="noopener noreferrer">{html.escape(label)}</a>',
                text,
            )
            text = _MANKAN_OFFICIAL_LINK_RE.sub(
                f'<a href="{html.escape(url)}" target="_blank" rel="noopener" style="color:var(--text2);text-decoration:underline">{html.escape(label)}</a>',
                text,
            )
            text = text.replace(
                f'href="{html.escape(url)}" target="_blank" rel="noopener" style="color:var(--text2);text-decoration:underline">試験実施団体</a>',
                f'href="{html.escape(url)}" target="_blank" rel="noopener" style="color:var(--text2);text-decoration:underline">{html.escape(label)}</a>',
            )
    if links and "jafp.or.jp" in links[0]["url"]:
        text = text.replace(
            "https://www.mlit.go.jp/jutakukentiku/house/",
            "https://www.nta.go.jp/",
        )
        text = text.replace("https://www.mlit.go.jp/", "https://www.nta.go.jp/")
        text = text.replace("国土交通省 住宅局", "国税庁")
        text = _MLIT_OFFICIAL_LINK_RE.sub(
            '<a href="https://www.nta.go.jp/" target="_blank" rel="noopener" style="color:var(--text2);text-decoration:underline">国税庁</a>',
            text,
        )
        text = _MLIT_OFFICIAL_LINK_RE.sub(
            '<a href="https://www.nta.go.jp/" target="_blank" rel="noopener noreferrer">国税庁</a>',
            text,
        )
        text = text.replace("法令・通達の原文は", "法令・税制の原文は")
        text = text.replace(
            'href="https://www.nta.go.jp/" target="_blank" rel="noopener" style="color:var(--text2);text-decoration:underline">国土交通省</a>',
            'href="https://www.nta.go.jp/" target="_blank" rel="noopener" style="color:var(--text2);text-decoration:underline">国税庁</a>',
        )
    en = exam_name()
    if "FP3級" in en and "FP2" not in en:
        text = text.replace("ファイナンシャル・プランナー試験（FP2級・FP3級）", en)
        text = text.replace("（FP2級・FP3級）", "（FP3級）")
    return text


def update_related_sites_official_links(text: str) -> str:
    """related-sites.html の公式リンク一覧を externalLinks から再生成。"""
    links = external_links()
    if not links:
        return text
    items: list[str] = []
    for link in links:
        url = html.escape(link["url"])
        label = html.escape(link["label"])
        desc = html.escape(link.get("description") or "")
        items.append(
            "          <li>\n"
            f'            <a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>\n'
            f"            … {desc}\n"
            "          </li>"
        )
    new_ul = "\n".join(items)

    def repl(match: re.Match[str]) -> str:
        return match.group(1) + "\n" + new_ul + "\n        " + match.group(3)

    return _RELATED_OFFICIAL_SECTION_RE.sub(repl, text, count=1)


def update_static_page_canonical(text: str, path: Path) -> str:
    rel = STATIC_PAGE_CANONICAL.get(path)
    if not rel:
        return text
    url = html.escape(public_url(rel), quote=True)
    return _STATIC_CANONICAL_RE.sub(f'<link rel="canonical" href="{url}">', text, count=1)


def replace_static_chrome(text: str, path: Path) -> str:
    current = STATIC_PAGE_CURRENTS.get(path)
    if not current:
        return text
    rel_path = path.relative_to(ROOT)
    text = re.sub(
        r'\s*<header class="(?:site-page-header(?: site-page-header--wide)?|topnav site-shell-header(?: site-shell-header--wide)?)">.*?</header>',
        "\n" + site_page_header(rel_path, current=current),
        text,
        count=1,
        flags=re.S,
    )
    text = re.sub(
        r'\s*<footer class="(?:site-page-footer(?: site-page-footer--wide)?|site-footer)[^"]*".*?</footer>\s*(?:<!-- GA4:.*?-->\s*)?(?:<script>window\.__GA4_MEASUREMENT_ID__="[^"]*";</script>\s*)?(?:<script defer src="[^"]*site-analytics\.js"></script>\s*)?',
        "\n" + site_page_footer(rel_path, current=current),
        text,
        count=1,
        flags=re.S,
    )
    text = text.replace("</script></div>", "</script>\n  </div>")
    text = re.sub(
        r'(</div>)\s*<!-- GA4:.*?site-analytics\.js"></script>\s*(?=</body>)',
        r"\1\n",
        text,
        count=1,
        flags=re.S,
    )
    return ensure_theme_link(text, rel_path)


def ensure_index_theme(text: str) -> str:
    if "site-theme.css" in text:
        return text
    theme_link = '<link rel="stylesheet" href="site-theme.css">'
    for needle, repl in (
        ('<script src="site-config.js"></script>', theme_link + '\n<script src="site-config.js"></script>'),
        ('<script src="./site-config.js"></script>', theme_link + '\n  <script src="./site-config.js"></script>'),
        ('<script defer src="site-analytics.js"></script>', theme_link + '\n<script defer src="site-analytics.js"></script>'),
        (
            '<script defer src="./site-analytics.js"></script>',
            theme_link + '\n<script defer src="./site-analytics.js"></script>',
        ),
    ):
        if needle in text:
            return text.replace(needle, repl, 1)
    if "</head>" in text:
        return text.replace("</head>", f"  {theme_link}\n</head>", 1)
    return text


def update_index_shell_footer(text: str) -> str:
    """SPA フッターを site-config の navigation.footer と同型に揃える。"""
    block = site_shell_footer(Path("index.html"), fixed=True, include_analytics=False)
    indented = "\n".join(("  " + line) if line else line for line in block.splitlines())
    return re.sub(
        r'\n  <footer class="site-footer[^"]*" role="contentinfo">.*?</footer>',
        "\n" + indented,
        text,
        count=1,
        flags=re.S,
    )


def _index_logo_mark_html() -> str:
    top, bottom = brand_logo_lines()
    size_cls = brand_logo_size_class(top)
    cls = "topnav-logo-mark" + (f" {size_cls}" if size_cls else "")
    return (
        f'<div class="{cls}" aria-hidden="true">'
        f'<span class="logo-mark-line">{html.escape(top)}</span>'
        f'<span class="logo-mark-line logo-mark-line--sub">{html.escape(bottom)}</span>'
        f"</div>"
    )



_TOPNAV_LOGO_MARK_RE = re.compile(
    r'<div class="[^"]*\btopnav-logo-mark\b[^"]*"[^>]*>.*?</div>',
    re.S,
)


def _ensure_topnav_logo_stack(text: str) -> str:
    """ヘッダー横に site-config のサイト名・試験名を必ず入れる。"""
    name = html.escape(brand_name())
    exam = html.escape(exam_name())
    stack = (
        f'<span class="topnav-logo-stack">\n'
        f'          <span class="topnav-logo-text">{name}</span>\n'
        f'          <span class="topnav-logo-sub">{exam}</span>\n'
        f"        </span>"
    )
    stack_re = re.compile(
        r'<span class="topnav-logo-stack">.*?</span>\s*(?=</a>|</div>\s*</div>|</header>)',
        re.S,
    )
    if stack_re.search(text):
        return stack_re.sub(stack, text, count=1)
    return re.sub(
        r'(</div>\s*)(<span class="topnav-logo-stack">)',
        r"\1" + stack,
        text,
        count=1,
    )


def update_index_auth_modal(text: str) -> str:
    mark = html.escape(brand_mark())
    bn = html.escape(brand_name())
    en = html.escape(exam_name())
    replacement = (
        f'<div class="auth-logo-mark" title="{bn}">{mark}</div>\n'
        f"      <h1>{bn}</h1>\n"
        f'      <p class="auth-logo-fullname">{en}対策サイト</p>'
    )
    return _AUTH_LOGO_BLOCK_RE.sub(replacement, text, count=1)


def update_index_brand_mark(text: str) -> str:
    mark = _index_logo_mark_html()

    text = _TOPNAV_LOGO_MARK_RE.sub(mark, text, count=1)
    text = _ensure_topnav_logo_stack(text)
    # 旧 update の残骸（二重 </span>）を除去
    text = re.sub(
        r'(</span></span>)\s*<span class="logo-mark-line logo-mark-line--sub">[^<]+</span></span>',
        r"\1",
        text,
    )
    return text


INDEX_LOGO_MARK_CSS = """\
.topnav-logo-mark,.site-footer-logo-mark{min-width:54px;min-height:36px;padding:6px 10px 5px;border-radius:4px;background:var(--ink);display:inline-flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;flex-shrink:0;font-family:var(--font);color:var(--bg2);box-sizing:border-box}
.topnav-logo-mark .logo-mark-line,.site-footer-logo-mark .logo-mark-line{display:block;font-size:12px;font-weight:700;line-height:1.05;text-align:center;white-space:nowrap;letter-spacing:.02em}
.topnav-logo-mark .logo-mark-line--sub,.site-footer-logo-mark .logo-mark-line--sub{font-size:11px;letter-spacing:.04em}"""

INDEX_LOGO_MOBILE_CSS = (
    "  .topnav-logo-mark,.site-footer-logo-mark{min-width:48px;min-height:32px;padding:5px 8px 4px}"
    "  .topnav-logo-mark .logo-mark-line,.site-footer-logo-mark .logo-mark-line{font-size:11px}"
    "  .topnav-logo-mark .logo-mark-line--sub,.site-footer-logo-mark .logo-mark-line--sub{font-size:10px}"
)

_LEGACY_FOOTER_LOGO_CSS_RES = (
    re.compile(r"\.site-footer-logo-mark\{width:22px;height:22px[^}]+\}\n?", re.S),
    re.compile(r"  \.site-footer-logo-mark\{width:20px;height:20px[^}]+\}\n?", re.S),
    re.compile(r"  \.site-footer-logo-mark\{width:28px;height:20px[^}]+\}\n?", re.S),
    re.compile(
        r"\.site-footer-logo-mark\{min-width:46px;min-height:30px[^}]+\}\n?"
        r"\.site-footer-logo-mark \.logo-mark-line\{font-size:10px\}\n?"
        r"\.site-footer-logo-mark \.logo-mark-line--sub\{font-size:9px\}\n?",
        re.S,
    ),
)


def _strip_legacy_footer_logo_css(text: str) -> str:
    for pattern in _LEGACY_FOOTER_LOGO_CSS_RES:
        text = pattern.sub("", text)
    return text


def _normalize_index_logo_mark_css(text: str) -> str:
    return re.sub(
        r"(\.topnav-logo-mark \.logo-mark-line--sub,\.site-footer-logo-mark \.logo-mark-line--sub\{font-size:11px;letter-spacing:\.04em\})\n"
        r"\.site-footer-logo-mark\{min-width:46px[^}]+\}\n"
        r"\.site-footer-logo-mark \.logo-mark-line\{font-size:10px\}\n"
        r"\.site-footer-logo-mark \.logo-mark-line--sub\{font-size:9px\}",
        r"\1",
        text,
        count=1,
    )


def update_index_logo_styles(text: str) -> str:
    text = _strip_legacy_footer_logo_css(text)
    text = _normalize_index_logo_mark_css(text)
    if ".logo-mark-line" not in text or INDEX_LOGO_MARK_CSS.splitlines()[0] not in text:
        text = re.sub(
            r"\.topnav-logo-mark\{width:28px;height:28px[^}]+\}",
            INDEX_LOGO_MARK_CSS,
            text,
            count=1,
        )
    text = re.sub(
        r"  \.topnav-logo-mark\{width:26px;height:26px;font-size:11px\}",
        INDEX_LOGO_MOBILE_CSS,
        text,
        count=1,
    )
    text = re.sub(
        r"  \.topnav-logo-mark\{min-width:48px;min-height:32px;padding:5px 8px 4px\}"
        r"  \.topnav-logo-mark \.logo-mark-line\{font-size:11px\}"
        r"  \.topnav-logo-mark \.logo-mark-line--sub\{font-size:10px\}",
        INDEX_LOGO_MOBILE_CSS,
        text,
        count=1,
    )
    text = re.sub(
        r"  \.topnav-logo-mark\{width:32px;height:26px[^}]+\}\n?"
        r"  \.site-footer-logo-mark\{width:28px;height:20px[^}]+\}\n?",
        "",
        text,
        count=1,
    )
    return text


def update_index_glossary_excerpt(text: str) -> str:
    csv_path = ROOT / "data" / "glossary_terms.csv"
    if not csv_path.is_file() or '<section class="glos-static-section"' not in text:
        return text
    rows = list(csv.DictReader(csv_path.read_text(encoding="utf-8-sig").splitlines()))
    cat_map = category_to_field_map()
    by_field: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        fid = cat_map.get(str(row.get("category") or "").strip())
        if not fid:
            continue
        by_field.setdefault(fid, []).append(row)

    blocks: list[str] = []
    for f in fields():
        fid = str(f["id"])
        items = by_field.get(fid, [])[:2]
        if not items:
            continue
        legacy = str(f.get("legacyGlossaryCat") or fid)
        articles = []
        for item in items:
            term = html.escape(str(item.get("term") or "").strip())
            desc = html.escape(str(item.get("short_def") or item.get("definition") or "").strip())
            articles.append(
                '<article class="glos-static-card" itemscope itemtype="https://schema.org/DefinedTerm">\n'
                f'  <h4 class="glos-static-term" itemprop="name">{term}</h4>\n'
                f'  <p class="glos-static-desc" itemprop="description">{desc}</p>\n'
                "</article>"
            )
        blocks.append(
            f'<div class="glos-cat-section" data-cat="{html.escape(legacy)}">\n'
            f'<h3 class="glos-cat-heading">{html.escape(str(f.get("name") or fid))}</h3>\n'
            + "\n".join(articles)
            + "\n</div>"
        )
    if not blocks:
        return text

    start = text.find('<section class="glos-static-section"')
    first_block = text.find('<div class="glos-cat-section"', start)
    end = text.find("</section>", first_block)
    if start < 0 or first_block < 0 or end < 0:
        return text
    intro = text[start:first_block]
    replacement = intro + "\n".join(blocks) + "\n</section>"
    return text[:start] + replacement + text[end + len("</section>") :]


def main() -> int:
    sync_config_files()
    for path in TEXT_TARGETS:
        if not path.is_file():
            continue
        old = path.read_text(encoding="utf-8")
        new = replace_all(old)
        if path.suffix == ".html":
            new = fix_legacy_base_path_hrefs(new)
            new = migrate_legacy_takken_leaks(new)
            new = fix_wrong_official_urls(new)
            new = update_static_page_canonical(new, path)
            if path == ROOT / "related-sites.html":
                new = update_related_sites_official_links(new)
        new = replace_static_chrome(new, path)
        rel = path.relative_to(ROOT)
        if path.suffix == ".html":
            new = inject_brand_head(new, rel, site_root=ROOT)
        if path == ROOT / "index.html":
            new = ensure_site_config_before_fields(new)
            new = inject_index_seo_head(new)
            new = inject_index_faq_ldjson(new)
            new = inject_index_noscript(new)
            new = inject_index_fields_fallback(new)
            new = inject_index_spa_ui_leaks(new)
            new = update_index_spa_seo_js(new)
            new = fix_quiz_start_page_titles(new)
            new = fix_spa_breadcrumb_top(new)
            new = ensure_index_theme(new)
            new = update_index_shell_footer(new)
            new = update_index_brand_mark(new)
            new = update_index_auth_modal(new)
            new = update_index_logo_styles(new)
            new = update_index_glossary_excerpt(new)
        if new != old:
            path.write_text(new, encoding="utf-8")
            print(f"Updated {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
