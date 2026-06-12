#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統合契約の機械検証（フッター過去問 URL・q ハブタブ・用語一覧 JSON/JS）。

docs/integration-checklist.md の「一回で揃える」前提が満たされているかを build 後に確認する。
"""

from __future__ import annotations

import csv
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.index_seo_head import (  # noqa: E402
    INDEX_SEO_MARKER_END,
    INDEX_SEO_MARKER_START,
    _OTHER_SITE_HOSTS,
)
from tools.index_spa_patch import (  # noqa: E402
    INDEX_FIELDS_FALLBACK_START,
    INDEX_NOSCRIPT_MARKER_END,
    INDEX_NOSCRIPT_MARKER_START,
)
from tools.site_config import (  # noqa: E402
    base_path,
    clean_origin,
    exam_name,
    ga4_measurement_id,
    load_config,
    public_url,
)


@dataclass
class Issue:
    message: str


def _footer_past_href(cfg: dict) -> Issue | None:
    nav = cfg.get("navigation") or {}
    footer = nav.get("footer") if isinstance(nav, dict) else None
    if not isinstance(footer, list):
        return Issue("site-config.json: navigation.footer がありません")
    past_items = [
        item
        for item in footer
        if isinstance(item, dict) and str(item.get("label") or "").strip() == "過去問一覧"
    ]
    if not past_items:
        return Issue('site-config.json: footer に「過去問一覧」がありません')
    hrefs = {str(i.get("href") or "").strip() for i in past_items}
    if hrefs != {"q/index.html"}:
        return Issue(
            f'site-config.json: 「過去問一覧」の href は q/index.html のみにしてください（現在: {sorted(hrefs)!r}）'
        )
    for item in footer:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        href = str(item.get("href") or "").strip()
        if label in ("実践演習一覧", "一問一答一覧"):
            return Issue(
                f"site-config.json: footer に {label!r} を置かないでください（3モードタブで足ります）"
            )
        if label == "過去問一覧" and "practice" in href:
            return Issue(f"site-config.json: 過去問一覧が実践 URL を指しています: {href!r}")
    return None


def _index_footer(index_path: Path) -> list[Issue]:
    if not index_path.is_file():
        return [Issue(f"{index_path.name} がありません（SPA フッター未検証）")]
    text = index_path.read_text(encoding="utf-8")
    issues: list[Issue] = []
    if "site-pages.css" not in text and "site-theme.css" not in text:
        issues.append(
            Issue(f"{index_path.name}: site-pages.css / site-theme.css が未リンク（apply_site_config を実行）")
        )
    for m in re.finditer(
        r'<a\s+[^>]*href="([^"]+)"[^>]*>\s*過去問一覧\s*</a>',
        text,
        flags=re.I,
    ):
        href = m.group(1)
        if "practice" in href:
            issues.append(
                Issue(f"{index_path.name}: フッター「過去問一覧」が実践 URL {href!r} を指しています")
            )
        elif href not in ("q/index.html", "/q/index.html"):
            issues.append(
                Issue(
                    f"{index_path.name}: フッター「過去問一覧」は q/index.html または /q/index.html にしてください（現在: {href!r}）"
                )
            )
    if "過去問一覧" not in text:
        issues.append(Issue(f"{index_path.name}: フッターに「過去問一覧」リンクがありません"))
    return issues


def _q_index(q_index: Path) -> list[Issue]:
    if not q_index.is_file():
        return [Issue("q/index.html がありません（build_past_question_pages を実行）")]
    text = q_index.read_text(encoding="utf-8")
    issues: list[Issue] = []
    if "q-hub-links" not in text:
        issues.append(Issue("q/index.html: q_hub_links_html（3モードタブ）がありません"))
    if 'aria-current="page">過去問</span>' not in text and "is-current" not in text:
        issues.append(Issue("q/index.html: 過去問タブの current 表示がありません"))
    if (
        "/q/orig/index.html" not in text
        and "/q/practice/index.html" not in text
        and 'href="practice/index.html"' not in text
    ):
        issues.append(Issue("q/index.html: 実践演習タブへのリンクがありません"))
    return issues


def _terms_index(terms_index: Path) -> list[Issue]:
    if not terms_index.is_file():
        return []
    text = terms_index.read_text(encoding="utf-8")
    m = re.search(
        r'<script[^>]+id="terms-index-data"[^>]*>(.*?)</script>',
        text,
        flags=re.S | re.I,
    )
    if not m:
        return [Issue("terms/index.html: #terms-index-data がありません（build_glossary_pages を実行）")]
    try:
        data = json.loads(m.group(1).strip())
    except json.JSONDecodeError as e:
        return [Issue(f"terms/index.html: terms-index-data の JSON が不正: {e}")]
    if not isinstance(data, list):
        return [Issue("terms/index.html: terms-index-data は配列である必要があります")]
    missing: list[str] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        term = str(item.get("term") or "?")
        short_def = str(item.get("shortDef") or "").strip()
        definition = str(item.get("definition") or "").strip()
        if not short_def and not definition:
            missing.append(term)
    if missing:
        preview = ", ".join(missing[:5])
        more = f" 他{len(missing) - 5}件" if len(missing) > 5 else ""
        return [
            Issue(
                f"terms/index.html: shortDef/definition が空の用語があります（{preview}{more}）"
            )
        ]
    return []


def _terms_js(js_path: Path) -> Issue | None:
    if not js_path.is_file():
        return Issue("site-terms-index.js がありません")
    text = js_path.read_text(encoding="utf-8")
    if "shortDef || item.definition" not in text and "item.shortDef || item.definition" not in text:
        return Issue(
            "site-terms-index.js: 定義列は item.shortDef || item.definition で表示してください"
        )
    return None


def _csv_row_count(path: Path, *, skip_invalid: bool = False) -> int:
    if not path.is_file():
        return 0
    rows = list(csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines()))
    if not skip_invalid:
        return len(rows)
    n = 0
    for row in rows:
        if str(row.get("is_invalidated") or "").strip().upper() == "TRUE":
            continue
        n += 1
    return n


def _q_index_data_count(index_html: Path) -> int | None:
    if not index_html.is_file():
        return None
    text = index_html.read_text(encoding="utf-8")
    m = re.search(
        r'<script[^>]+id="q-index-data"[^>]*>(.*?)</script>',
        text,
        flags=re.S | re.I,
    )
    if not m:
        return None
    try:
        data = json.loads(m.group(1).strip())
    except json.JSONDecodeError:
        return None
    return len(data) if isinstance(data, list) else None


def _parse_q_index_config(index_html: Path) -> dict | None:
    if not index_html.is_file():
        return None
    text = index_html.read_text(encoding="utf-8")
    m = re.search(
        r'<script[^>]+id="q-index-config"[^>]*>(.*?)</script>',
        text,
        flags=re.S | re.I,
    )
    if not m:
        return None
    try:
        data = json.loads(m.group(1).strip())
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _mode_index_config(mode: str, index_path: Path) -> list[Issue]:
    """実践・一問一答一覧の INDEX_CONFIG 契約（分野グループ・categoryOrder）。"""
    if not index_path.is_file():
        return []
    cfg = _parse_q_index_config(index_path)
    if cfg is None:
        return [Issue(f"q/{mode}/index.html: #q-index-config がありません")]
    issues: list[Issue] = []
    if cfg.get("variant") != mode:
        issues.append(
            Issue(f"q/{mode}/index.html: variant は {mode!r} である必要があります（現在: {cfg.get('variant')!r}）")
        )
    if cfg.get("groupBy") != "category":
        issues.append(
            Issue(
                f"q/{mode}/index.html: groupBy は 'category' である必要があります"
                f"（現在: {cfg.get('groupBy')!r}。一問一答を年度別にしない）"
            )
        )
    order = cfg.get("categoryOrder")
    if not isinstance(order, list) or not order:
        issues.append(Issue(f"q/{mode}/index.html: categoryOrder が空です（build_practice_ichimon を再実行）"))
    filters = cfg.get("statusFilters")
    if filters != ["wrong", "bookmark"]:
        issues.append(
            Issue(
                f"q/{mode}/index.html: statusFilters は ['wrong', 'bookmark'] にしてください"
                f"（現在: {filters!r}）"
            )
        )
    return issues


def _is_redirect_stub(path: Path) -> bool:
    if not path.is_file():
        return False
    head = path.read_text(encoding="utf-8", errors="replace")[:600]
    return "refresh" in head.lower() and "0;url=" in head.lower()


def _orig_practice_index_ok(path: Path) -> bool:
    """q/orig/index.html は site-q-orig-index.js ベース（#q-index-data 非使用）。"""
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    return "q-orig-index-page" in text and "site-q-orig-index.js" in text


def _mode_index_counts(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    practice_index = root / "q" / "orig" / "index.html"
    if not _orig_practice_index_ok(practice_index):
        practice_index = root / "q" / "practice" / "index.html"
    checks = [
        ("practice", root / "data" / "practice_questions.csv", practice_index, True),
        ("ichimon", root / "data" / "ichimon_questions.csv", root / "q" / "ichimon" / "index.html", False),
    ]
    for mode, csv_path, index_path, skip_invalid in checks:
        csv_n = _csv_row_count(csv_path, skip_invalid=skip_invalid)
        json_n = _q_index_data_count(index_path)
        if csv_n == 0:
            continue
        if mode == "ichimon" and _is_redirect_stub(index_path):
            continue
        if mode == "practice" and _orig_practice_index_ok(index_path):
            continue
        if json_n is None:
            issues.append(Issue(f"q/{mode}/index.html: #q-index-data がありません（build_practice_ichimon を実行）"))
            continue
        if json_n != csv_n:
            issues.append(
                Issue(
                    f"q/{mode}/index.html: 一覧 JSON が {json_n} 件ですが "
                    f"{csv_path.name} は {csv_n} 行です（build_all.py を再実行）"
                )
            )
        issues.extend(_mode_index_config(mode, index_path))
        issues.extend(_mode_index_hub_tabs(mode, index_path))
    return issues


def _site_q_index_js(js_path: Path) -> list[Issue]:
    if not js_path.is_file():
        return [Issue("site-q-index.js がありません")]
    text = js_path.read_text(encoding="utf-8")
    issues: list[Issue] = []
    if "categoryOrderIndex" not in text:
        issues.append(Issue("site-q-index.js: categoryOrderIndex がありません（分野順ソート未実装）"))
    if "q-index-year-link[data-group]" not in text:
        issues.append(Issue("site-q-index.js: ジャンプリンクに data-group 対応がありません"))
    if "ITEMS_RAW" not in text:
        issues.append(Issue("site-q-index.js: ITEMS_RAW による categoryOrder ソートがありません"))
    return issues


def _mode_index_hub_tabs(mode: str, index_path: Path) -> list[Issue]:
    if not index_path.is_file():
        return []
    text = index_path.read_text(encoding="utf-8")
    issues: list[Issue] = []
    if "q-hub-links" not in text:
        issues.append(Issue(f"q/{mode}/index.html: q_hub_links_html（3モードタブ）がありません"))
    for href in ("/q/index.html", "/q/practice/index.html", "/q/ichimon/index.html"):
        if href not in text and href.replace("/q/", "") not in text:
            issues.append(Issue(f"q/{mode}/index.html: タブリンク {href} がありません"))
    return issues


def _build_all_includes_apply(build_all: Path) -> Issue | None:
    if not build_all.is_file():
        return None
    text = build_all.read_text(encoding="utf-8")
    if "apply_site_config.py" not in text:
        return Issue("tools/build_all.py: apply_site_config.py の呼び出しがありません")
    return None


def _ichimon_js_public_paths(root: Path) -> list[Issue]:
    csv_path = root / "data" / "ichimon_questions.csv"
    js_path = root / "exam-site-data-ichimondou.js"
    if not csv_path.is_file() or _csv_row_count(csv_path) == 0:
        return []
    if not js_path.is_file():
        return [Issue("exam-site-data-ichimondou.js がありません（csv_to_exam_site_ichimondou を実行）")]
    text = js_path.read_text(encoding="utf-8")
    if 'publicPath": "ichimon/' in text or "publicPath\": \"ichimon/" in text:
        return [Issue("exam-site-data-ichimondou.js: publicPath が q/ichimon/ で始まっていません")]
    if "q/ichimon/" not in text:
        return [Issue("exam-site-data-ichimondou.js: publicPath に q/ichimon/ が含まれません")]
    return []


def _build_all_includes_practice(build_all: Path) -> Issue | None:
    if not build_all.is_file():
        return Issue("tools/build_all.py がありません")
    text = build_all.read_text(encoding="utf-8")
    if (
        "build_practice_ichimon_pages.py" not in text
        and "build_practice_question_pages.py" not in text
    ):
        return Issue(
            "tools/build_all.py: build_practice_ichimon_pages.py または "
            "build_practice_question_pages.py の呼び出しがありません"
        )
    if "validate_site_integration.py" not in text:
        return Issue("tools/build_all.py: validate_site_integration.py の呼び出しがありません")
    return None


def _html_footer_source(root: Path) -> list[Issue]:
    """tools/html_footer.py の契約（LEARNING_NAV / tnav-past）。"""
    path = root / "tools" / "html_footer.py"
    if not path.is_file():
        return [Issue("tools/html_footer.py がありません")]
    text = path.read_text(encoding="utf-8")
    issues: list[Issue] = []
    if '"q": "tnav-past"' in text or "'q': 'tnav-past'" in text:
        issues.append(
            Issue(
                "html_footer.py: LEARNING_NAV_ACTIVE_BY_PAGE に q → tnav-past を含めないでください（site-chrome.md §3）"
            )
        )
    if '("tnav-past", "過去問", "q/index.html"' in text or "('tnav-past', '過去問', 'q/index.html'" in text:
        issues.append(
            Issue(
                'html_footer.py: LEARNING_NAV_ITEMS の tnav-past は "#past" にしてください（site-chrome.md §3）'
            )
        )
    return issues


def _spa_nav_hash_hrefs() -> dict[str, str]:
    """site-config basePath 付きサイト（fp-master 等）の SPA ハッシュリンク期待値。"""
    bp = base_path()
    hashes = {
        "tnav-ichimondou": "#ichimondou",
        "tnav-orig": "#orig",
        "tnav-past": "#past",
        "tnav-dash": "#dash",
        "tnav-review": "#review",
    }
    if bp:
        return {k: f"{bp}{h}" for k, h in hashes.items()}
    return {k: f"/{h}" for k, h in hashes.items()}


def _spa_home_url() -> str:
    origin = clean_origin().rstrip("/")
    bp = base_path()
    return f"{origin}{bp}" if bp else origin


def _header_learning_nav(root: Path) -> list[Issue]:
    """静的ページの学習ナビ href / q/index の active 状態（site-chrome.md §3, §7）。"""
    spa_hash = _spa_nav_hash_hrefs()
    article_sample = root / "articles" / "field-law-basics" / "index.html"
    if not article_sample.is_file():
        article_sample = root / "articles" / "exam-overview" / "index.html"
    samples: list[tuple[str, Path]] = [
        ("articles sample", article_sample),
        ("terms/index.html", root / "terms" / "index.html"),
        ("about.html", root / "about.html"),
        ("q/index.html", root / "q" / "index.html"),
    ]
    issues: list[Issue] = []
    for label, path in samples:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for nav_id, expected in spa_hash.items():
            m = re.search(rf'id="{re.escape(nav_id)}"\s+href="([^"]+)"', text)
            if not m:
                issues.append(Issue(f"{label}: {nav_id} がありません"))
                continue
            href = m.group(1)
            if href != expected:
                issues.append(
                    Issue(
                        f"{label}: {nav_id} の href は {expected!r} にしてください（現在: {href!r}）"
                    )
                )
            if "q/index.html" in href and nav_id == "tnav-past":
                issues.append(
                    Issue(
                        f"{label}: ヘッダー「過去問」が過去問一覧 q/index.html を指しています（site-chrome.md §3）"
                    )
                )

    q_index = root / "q" / "index.html"
    if q_index.is_file():
        text = q_index.read_text(encoding="utf-8")
        if re.search(r'id="tnav-past"[^>]*\saria-current="page"', text) or 'class="topnav-link active" id="tnav-past"' in text:
            issues.append(
                Issue(
                    "q/index.html: ヘッダー「過去問」に active / aria-current を付けないでください（フッター「過去問一覧」のみ）"
                )
            )
        if not re.search(
            r'<a\s+[^>]*href="[^"]*"[^>]*aria-current="page"[^>]*>\s*過去問一覧\s*</a>',
            text,
            flags=re.I,
        ):
            issues.append(
                Issue("q/index.html: フッター「過去問一覧」に aria-current=\"page\" がありません")
            )
    return issues


VIEWPORT_META_RE = re.compile(
    r'<meta\s+name="viewport"\s+content="width=device-width,\s*initial-scale=1',
    re.I,
)
RESPONSIVE_SECTION_MARKER = "全ページ共通レスポンシブ"
MOBILE_STATIC_MQ = "@media (max-width: 760px)"
MIN_SITE_PAGES_CSS_LINES = 3500


def _responsive_css_source(root: Path) -> list[Issue]:
    """site-pages.css がテンプレ最新（レスポンシブ節あり）か。"""
    css_path = root / "site-pages.css"
    if not css_path.is_file():
        return [Issue("site-pages.css がありません（responsive-layout.md §1）")]
    text = css_path.read_text(encoding="utf-8")
    issues: list[Issue] = []
    line_count = text.count("\n") + (1 if text else 0)
    if RESPONSIVE_SECTION_MARKER not in text:
        issues.append(
            Issue(
                "site-pages.css: 「全ページ共通レスポンシブ」節がありません。"
                "旧版 CSS の可能性 — テンプレから同期してください（docs/responsive-layout.md §0）"
            )
        )
    if MOBILE_STATIC_MQ not in text:
        issues.append(
            Issue(
                "site-pages.css: @media (max-width: 760px) がありません（responsive-layout.md §2）"
            )
        )
    if line_count < MIN_SITE_PAGES_CSS_LINES:
        issues.append(
            Issue(
                f"site-pages.css: 行数が {line_count} 行と少なすぎます（目安 ≥{MIN_SITE_PAGES_CSS_LINES}）。"
                "テンプレ最新版への同期が必要です"
            )
        )
    return issues


def _viewport_and_static_css(root: Path) -> list[Issue]:
    """代表静的 HTML の viewport と site-pages.css リンク。"""
    samples = [
        "about.html",
        "articles/index.html",
        "terms/index.html",
        "q/index.html",
    ]
    issues: list[Issue] = []
    for rel in samples:
        path = root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if not VIEWPORT_META_RE.search(text):
            issues.append(
                Issue(
                    f"{rel}: viewport meta（width=device-width, initial-scale=1）がありません"
                    "（responsive-layout.md §3.1）"
                )
            )
        if "site-pages.css" not in text:
            issues.append(
                Issue(f"{rel}: site-pages.css がリンクされていません（responsive-layout.md §3.1）")
            )
    index = root / "index.html"
    if index.is_file():
        text = index.read_text(encoding="utf-8")
        if not VIEWPORT_META_RE.search(text):
            issues.append(
                Issue("index.html: viewport meta がありません（SPA — responsive-layout.md §4）")
            )
        if INDEX_SEO_MARKER_START not in text or INDEX_SEO_MARKER_END not in text:
            issues.append(
                Issue(
                    "index.html: INDEX_SEO_HEAD マーカーがありません"
                    "（tools/apply_site_config.py を実行してください）"
                )
            )
        elif 'property="og:title"' not in text:
            issues.append(Issue("index.html: og:title がありません（SNSカード用 SEO head 未適用）"))
        else:
            head = text.split("</head>", 1)[0]
            home_url = _spa_home_url()
            og_url_m = re.search(r'property="og:url"\s+content="([^"]+)"', head)
            if og_url_m and og_url_m.group(1).rstrip("/") != home_url:
                issues.append(
                    Issue(
                        f"index.html: og:url が SPA ホーム URL と不一致です"
                        f"（現在: {og_url_m.group(1)!r}、期待: {home_url + '/'}）"
                        " — tools/apply_site_config.py を実行してください"
                    )
                )
            canon_m = re.search(r'id="canonical-link"\s+href="([^"]+)"', head)
            if not canon_m:
                canon_m = re.search(r'rel="canonical"\s+href="([^"]+)"', head)
            if canon_m and canon_m.group(1).rstrip("/") != home_url:
                issues.append(
                    Issue(
                        f"index.html: canonical が SPA ホーム URL と不一致です"
                        f"（現在: {canon_m.group(1)!r}、期待: {home_url + '/'}）"
                        " — tools/apply_site_config.py を実行してください"
                    )
                )
            site_host = clean_origin().replace("https://", "").replace("http://", "").strip("/")
            for leak in (
                "mentalhealth-master.jp",
                "chintaikanrishi-master.jp",
                "mankan-master.jp",
                "kikenbutsu-master.jp",
                "takken-master.jp",
                "eisei1shu-master.jp",
                "eisei2shu-master.jp",
                "kangyou-master.jp",
                "unkan-master.jp",
                "boiler-master.jp",
            ):
                if leak == site_host:
                    continue
                if leak in head:
                    issues.append(
                        Issue(
                            f"index.html: head 内に他サイトのドメイン {leak!r} が残っています"
                            "（apply_site_config を再実行）"
                        )
                    )
                    break
        if INDEX_NOSCRIPT_MARKER_START not in text or INDEX_NOSCRIPT_MARKER_END not in text:
            issues.append(
                Issue(
                    "index.html: INDEX_NOSCRIPT マーカーがありません"
                    "（tools/apply_site_config.py を実行してください）"
                )
            )
        fields_pos = text.find("var FIELDS =")
        cfg_pos = text.find('src="site-config.js"')
        if fields_pos >= 0 and cfg_pos >= 0 and cfg_pos > fields_pos:
            issues.append(
                Issue(
                    "index.html: site-config.js が FIELDS 定義より後にあります"
                    "（apply_site_config / sync_index_spa_from_template を実行）"
                )
            )
        if INDEX_FIELDS_FALLBACK_START not in text:
            issues.append(
                Issue(
                    "index.html: INDEX_FIELDS_FALLBACK マーカーがありません"
                    "（apply_site_config を実行してください）"
                )
            )
        en = exam_name()
        if en != "◯◯試験（プレースホルダー）" and "◯◯試験（プレースホルダー）" in text.split("<noscript>", 1)[-1][:800]:
            issues.append(
                Issue("index.html: noscript 内にテンプレ placeholder の試験名が残っています（apply_site_config）")
            )
        if re.search(r'id="ichi-field-chips">\s*<button', text):
            issues.append(
                Issue(
                    "index.html: 一問一答 #ichi-field-chips に静的 chip が残っています"
                    "（buildIchiFieldChips による FIELDS 動的描画に更新してください）"
                )
            )
        if "function buildIchiFieldChips" not in text:
            issues.append(
                Issue(
                    "index.html: buildIchiFieldChips がありません"
                    "（テンプレ index.html を同期してください）"
                )
            )
    return issues


_GA4_INLINE_RE = re.compile(r'window\.__GA4_MEASUREMENT_ID__="([^"]*)"')
_GA4_DEFAULT_MID_RE = re.compile(r'var DEFAULT_MID = "([^"]*)";')
_GA4_SKIP_PREFIXES = (
    "terms/compare/",
    "terms/numbers/",
    "terms/mistakes/",
    "terms/priority/",
    "terms/samples/",
    "public_site/",
)


def _is_guide_retire_redirect(text: str) -> bool:
    """build_guide_retire_redirects が書く noindex スタブ（GA4 不要）。"""
    return (
        "記事移動中" in text
        and 'content="noindex, follow"' in text
        and "location.replace" in text
    )


def _ga4_page_issues(root: Path, rel: str, *, require_page_view: bool = False) -> list[Issue]:
    """公開 HTML の GA4 スニペット整合性（リダイレクト専用 URL は除外）。"""
    if any(rel.startswith(p) for p in _GA4_SKIP_PREFIXES):
        return []
    path = root / rel
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    if _is_guide_retire_redirect(text):
        return []
    issues: list[Issue] = []
    expected = ga4_measurement_id()
    if "site-analytics.js" not in text:
        issues.append(Issue(f"{rel}: site-analytics.js がありません（GA4 未設置）"))
        return issues
    m = _GA4_INLINE_RE.search(text)
    if expected:
        if not m or m.group(1) != expected:
            got = m.group(1) if m else "(なし)"
            issues.append(Issue(f"{rel}: GA4 測定ID不一致（期待 {expected!r}、実際 {got!r}）"))
    if require_page_view and "ga4PageView" not in text:
        issues.append(Issue(f"{rel}: ga4PageView 呼び出しがありません（SPA 計測漏れ）"))
    return issues


def _ga4_tracking(root: Path) -> list[Issue]:
    """docs/integration-checklist — GA4 測定IDとスニペットの横断検証。"""
    issues: list[Issue] = []
    expected = ga4_measurement_id()

    sa = root / "site-analytics.js"
    if not sa.is_file():
        issues.append(Issue("site-analytics.js がありません"))
    elif expected:
        dm = _GA4_DEFAULT_MID_RE.search(sa.read_text(encoding="utf-8"))
        if not dm or dm.group(1) != expected:
            got = dm.group(1) if dm else "(なし)"
            issues.append(
                Issue(f"site-analytics.js: DEFAULT_MID 不一致（期待 {expected!r}、実際 {got!r}）")
            )

    issues.extend(_ga4_page_issues(root, "index.html", require_page_view=True))
    for rel in ("about.html", "privacy.html", "related-sites.html", "articles/index.html"):
        issues.extend(_ga4_page_issues(root, rel))

    samples: list[str] = []
    for pattern in ("articles/*/index.html", "terms/g-*.html", "q/practice/*/index.html"):
        for path in sorted(root.glob(pattern))[:1]:
            samples.append(str(path.relative_to(root)))
    for rel in samples:
        issues.extend(_ga4_page_issues(root, rel))

    return issues


def _static_chrome(root: Path) -> list[Issue]:
    """docs/site-chrome.md — ヘッダー topnav 統一・旧 q-static-header 禁止。"""
    issues: list[Issue] = []
    samples: list[tuple[str, Path, bool]] = [
        ("about.html", root / "about.html", True),
        ("privacy.html", root / "privacy.html", True),
        ("q/index.html", root / "q" / "index.html", True),
        ("terms/index.html", root / "terms" / "index.html", True),
    ]
    for label, path, require_topnav in samples:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if require_topnav and "topnav site-shell-header" not in text:
            issues.append(
                Issue(f"{label}: site_page_header 由来の topnav site-shell-header がありません（site-chrome.md）")
            )
        if "q-static-header" in text:
            issues.append(Issue(f"{label}: 旧ヘッダー q-static-header が残っています（site-chrome.md）"))

    q_past = root / "q" / "past"
    if q_past.is_dir():
        for html in sorted(q_past.glob("**/index.html"))[:3]:
            text = html.read_text(encoding="utf-8")
            rel = html.relative_to(root)
            if "topnav site-shell-header" not in text:
                issues.append(
                    Issue(f"{rel}: topnav site-shell-header がありません（build_past_question_pages / site-chrome.md）")
                )
            if "q-static-header" in text:
                issues.append(Issue(f"{rel}: q-static-header が残っています"))
    return issues


def _static_page_site_leaks(root: Path) -> list[Issue]:
    """about / privacy / related-sites の他サイトドメイン漏れと canonical を検証。"""
    issues: list[Issue] = []
    site_host = clean_origin().replace("https://", "").replace("http://", "").strip("/")
    static_pages = [
        ("about.html", root / "about.html", public_url("about.html")),
        ("privacy.html", root / "privacy.html", public_url("privacy.html")),
        ("related-sites.html", root / "related-sites.html", public_url("related-sites.html")),
    ]
    for label, path, expected_canonical in static_pages:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for leak in _OTHER_SITE_HOSTS:
            if leak != site_host and leak in text:
                issues.append(
                    Issue(
                        f"{label}: 他サイトのドメイン {leak!r} が残っています"
                        "（tools/apply_site_config.py を実行）"
                    )
                )
                break
        canon_m = re.search(r'<link rel="canonical" href="([^"]+)"', text, re.I)
        if canon_m and canon_m.group(1) != expected_canonical:
            issues.append(
                Issue(
                    f"{label}: canonical が不正です"
                    f"（現在: {canon_m.group(1)!r}、期待: {expected_canonical!r}）"
                    " — tools/apply_site_config.py を実行してください"
                )
            )
    return issues


def main() -> int:
    root = ROOT
    if len(sys.argv) > 1 and sys.argv[1] == "--root":
        root = Path(sys.argv[2]).resolve()
        if not root.is_dir():
            print(f"error: --root is not a directory: {root}", file=sys.stderr)
            return 1

    issues: list[Issue] = []
    cfg_path = root / "site-config.json"
    if cfg_path.is_file():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        err = _footer_past_href(cfg)
        if err:
            issues.append(err)
    else:
        issues.append(Issue("site-config.json がありません"))

    issues.extend(_index_footer(root / "index.html"))
    issues.extend(_q_index(root / "q" / "index.html"))
    issues.extend(_terms_index(root / "terms" / "index.html"))
    err = _terms_js(root / "site-terms-index.js")
    if err:
        issues.append(err)
    err = _build_all_includes_practice(root / "tools" / "build_all.py")
    if err:
        issues.append(err)
    err = _build_all_includes_apply(root / "tools" / "build_all.py")
    if err:
        issues.append(err)
    issues.extend(_mode_index_counts(root))
    issues.extend(_ichimon_js_public_paths(root))
    issues.extend(_site_q_index_js(root / "site-q-index.js"))
    issues.extend(_static_chrome(root))
    issues.extend(_html_footer_source(root))
    issues.extend(_header_learning_nav(root))
    issues.extend(_responsive_css_source(root))
    issues.extend(_viewport_and_static_css(root))
    issues.extend(_ga4_tracking(root))
    issues.extend(_static_page_site_leaks(root))

    if not issues:
        print("validate_site_integration: OK")
        return 0
    for i in issues:
        print(f"error: {i.message}", file=sys.stderr)
    print(f"validate_site_integration: {len(issues)} error(s)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
