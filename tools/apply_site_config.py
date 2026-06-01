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
    brand_logo_lines,
    brand_logo_size_class,
    brand_mark,
    brand_name,
    category_to_field_map,
    clean_origin,
    contact_url,
    copyright_text,
    exam_name,
    ga4_measurement_id,
    learning_nav_label,
    official_organization,
    primary_external_link,
    sync_config_files,
    fields,
)
from tools.html_footer import site_page_footer, site_page_header, site_shell_footer
from tools.brand_assets import inject_brand_head


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
        ("window.__GA4_MEASUREMENT_ID__=\"\"", f'window.__GA4_MEASUREMENT_ID__="{ga4_measurement_id()}"'),
        ('var DEFAULT_MID = "";', f'var DEFAULT_MID = "{ga4_measurement_id()}";'),
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



def update_index_brand_mark(text: str) -> str:
    mark = _index_logo_mark_html()

    text = re.sub(
        r'<div class="topnav-logo-mark"[^>]*>.*?</div>',
        mark,
        text,
        count=1,
        flags=re.S,
    )
    name = html.escape(brand_name())
    if 'class="topnav-logo-text"' in text:
        text = re.sub(
            r'(<span class="topnav-logo-text">)[^<]*(</span>)',
            lambda m: f"{m.group(1)}{name}{m.group(2)}",
            text,
            count=1,
        )
    else:
        insert = f'<span class="topnav-logo-text">{name}</span>\n          '
        text = re.sub(
            r'(<span class="topnav-logo-stack">\s*)',
            lambda m: m.group(1) + insert,
            text,
            count=1,
        )
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
.topnav-logo-mark .logo-mark-line--sub,.site-footer-logo-mark .logo-mark-line--sub{font-size:11px;letter-spacing:.04em}
.site-footer-logo-mark{min-width:46px;min-height:30px;padding:4px 8px 3px;border-radius:3px}
.site-footer-logo-mark .logo-mark-line{font-size:10px}
.site-footer-logo-mark .logo-mark-line--sub{font-size:9px}"""


def update_index_logo_styles(text: str) -> str:
    if ".logo-mark-line" in text and INDEX_LOGO_MARK_CSS.splitlines()[0] in text:
        return text
    text = re.sub(
        r"\.topnav-logo-mark\{width:28px;height:28px[^}]+\}",
        INDEX_LOGO_MARK_CSS,
        text,
        count=1,
    )
    text = re.sub(
        r"\.site-footer-logo-mark\{width:22px;height:22px[^}]+\}\n?",
        "",
        text,
        count=1,
    )
    text = re.sub(
        r"  \.topnav-logo-mark\{width:26px;height:26px;font-size:11px\}",
        "  .topnav-logo-mark{min-width:48px;min-height:32px;padding:5px 8px 4px}"
        "  .topnav-logo-mark .logo-mark-line{font-size:11px}"
        "  .topnav-logo-mark .logo-mark-line--sub{font-size:10px}",
        text,
        count=1,
    )
    text = re.sub(
        r"  \.site-footer-logo-mark\{width:20px;height:20px[^}]+\}\n?",
        "",
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
        new = replace_static_chrome(replace_all(old), path)
        rel = path.relative_to(ROOT)
        if path.suffix == ".html":
            new = inject_brand_head(new, rel, site_root=ROOT)
        if path == ROOT / "index.html":
            new = ensure_index_theme(new)
            new = update_index_shell_footer(new)
            new = update_index_brand_mark(new)
            new = update_index_logo_styles(new)
            new = update_index_glossary_excerpt(new)
        if new != old:
            path.write_text(new, encoding="utf-8")
            print(f"Updated {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
