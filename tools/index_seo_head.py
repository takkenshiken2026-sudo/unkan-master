#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate index.html SPA SEO / OGP / Twitter Card / JSON-LD from site-config.json."""

from __future__ import annotations

import html
import json
import re

from tools.brand_assets import theme_ink
from tools.site_config import brand_name, clean_origin, exam_name, fields, public_url

INDEX_SEO_MARKER_START = "<!--INDEX_SEO_HEAD-->"
INDEX_SEO_MARKER_END = "<!--/INDEX_SEO_HEAD-->"


def index_home_title() -> str:
    return f"{brand_name()}｜{exam_name()} 過去問・一問一答・用語解説で合格を目指す無料学習サイト"


def index_og_title() -> str:
    return f"{brand_name()}｜{exam_name()} 無料学習プラットフォーム"


def index_site_label() -> str:
    return f"{brand_name()}（{exam_name()}）"


def index_description() -> str:
    return (
        f"{exam_name()}の合格を目指す無料学習プラットフォーム。"
        "過去問演習・実践演習・一問一答・重要用語解説を網羅。"
        "年度別・分野別に絞った効率学習で合格を目指す。"
    )


def index_description_long() -> str:
    field_names = "・".join(str(f.get("name") or f.get("id") or "") for f in fields()[:4])
    subjects = field_names or "主要分野"
    return (
        f"{exam_name()}の合格を目指す無料学習プラットフォーム。"
        f"過去問演習・実践演習・一問一答・重要用語解説を網羅。"
        f"年度別・科目別（{subjects}）に絞った効率的な学習が可能です。"
    )


def index_keywords() -> str:
    parts = [exam_name(), "過去問", "一問一答", "用語集", "資格学習", "合格"]
    for f in fields()[:3]:
        name = str(f.get("name") or "").strip()
        if name:
            parts.append(name)
    return ",".join(parts)


def index_json_ld_graph() -> list[dict]:
    origin = clean_origin()
    alt = f"{exam_name()}対策サイト"
    platform_desc = (
        f"{exam_name()}の過去問・実践演習・一問一答・用語解説を"
        "網羅した無料学習プラットフォーム"
    )
    return [
        {
            "@type": "WebSite",
            "@id": f"{origin}/#website",
            "url": f"{origin}/",
            "name": brand_name(),
            "alternateName": alt,
            "description": platform_desc,
            "inLanguage": "ja",
        },
        {
            "@type": "EducationalApplication",
            "@id": f"{origin}/#app",
            "name": brand_name(),
            "alternateName": alt,
            "description": platform_desc,
            "applicationCategory": "EducationApplication",
            "operatingSystem": "Web",
            "inLanguage": "ja",
            "educationalLevel": "Professional",
            "teaches": exam_name(),
            "offers": [
                {"@type": "Offer", "name": "無料プラン", "price": "0", "priceCurrency": "JPY"},
                {
                    "@type": "Offer",
                    "name": "プレミアムプラン",
                    "price": "980",
                    "priceCurrency": "JPY",
                    "billingDuration": "P1M",
                },
            ],
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "トップ", "item": f"{origin}/"},
                {"@type": "ListItem", "position": 2, "name": "過去問", "item": f"{origin}/#past"},
                {"@type": "ListItem", "position": 3, "name": "実践演習", "item": f"{origin}/#orig"},
                {"@type": "ListItem", "position": 4, "name": "用語解説", "item": public_url("terms/")},
            ],
        },
    ]


def index_seo_head_inner() -> str:
    """SEO block only (og:image は brand_assets の BRAND_ASSET_HEAD が担当)。"""
    origin = clean_origin()
    og_title = index_og_title()
    home_title = index_home_title()
    desc_short = index_description()
    desc_long = index_description_long()
    site_label = index_site_label()
    keywords = index_keywords()
    theme = html.escape(theme_ink())
    ld_json = json.dumps(
        {"@context": "https://schema.org", "@graph": index_json_ld_graph()},
        ensure_ascii=False,
        indent=2,
    )
    return f"""<!--SITE_VERIFICATION_META_INJECT-->
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
<title>{html.escape(home_title)}</title>

<!-- 基本SEO -->
<meta name="description" content="{html.escape(desc_long)}">
<meta name="keywords" content="{html.escape(keywords)}">
<meta name="robots" content="index, follow">
<meta name="application-name" content="{html.escape(site_label)}">
<link rel="canonical" href="{html.escape(origin)}/" id="canonical-link">

<!-- Open Graph (SNS・Slack等でのリッチ表示) -->
<meta property="og:type" content="website">
<meta property="og:url" content="{html.escape(origin)}/">
<meta property="og:title" content="{html.escape(og_title)}">
<meta property="og:description" content="{html.escape(desc_short)}">
<meta property="og:locale" content="ja_JP">
<meta property="og:site_name" content="{html.escape(site_label)}">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(og_title)}">
<meta name="twitter:description" content="{html.escape(desc_short)}">
<meta name="twitter:image:alt" content="{html.escape(og_title)}">

<!-- Schema.org 構造化データ -->
<script type="application/ld+json">
{ld_json}
</script>"""


_ORPHAN_TWITTER_AFTER_IMAGE = re.compile(
    r'(<meta name="twitter:image" content="[^"]+">)\s*'
    r'(?:<meta name="twitter:(?:image:alt|title|description)"[^>]+>\s*)+',
    re.I,
)

_LEGACY_INDEX_SEO = re.compile(
    r"<!--SITE_VERIFICATION_META_INJECT-->\s*"
    r'(?:<meta name="viewport"[^>]+>\s*)?'
    r"<title>[^<]*</title>\s*"
    r"(?:<!-- 基本SEO -->[\s\S]*?)?"
    r"(?:<!-- Open Graph[\s\S]*?)?"
    r"(?:<!-- Twitter Card[\s\S]*?)?"
    r"(?:<!-- Schema\.org 構造化データ -->[\s\S]*?</script>\s*)?",
    re.I,
)

_INDEX_SEO_BLOCK = re.compile(
    rf"{re.escape(INDEX_SEO_MARKER_START)}[\s\S]*?{re.escape(INDEX_SEO_MARKER_END)}",
    re.I,
)

_ORPHAN_DUP_SEO_AFTER_MARKER = re.compile(
    rf"(?:<meta name=\"theme-color\"[^>]+>\s*)?"
    r"(?:<meta name=\"description\"[^>]+>[\s\S]*?"
    rf"(?:{re.escape(INDEX_SEO_MARKER_END)}\s*)?)+",
    re.I,
)


def _strip_legacy_index_seo(text: str) -> str:
    text = _ORPHAN_TWITTER_AFTER_IMAGE.sub(r"\1\n", text, count=1)
    if INDEX_SEO_MARKER_START in text:
        text = _INDEX_SEO_BLOCK.sub("", text, count=1)
    else:
        text = _LEGACY_INDEX_SEO.sub("", text, count=1)
    return text


def _strip_duplicate_seo_after_marker(text: str) -> str:
    """INDEX_SEO マーカー直後に残った旧 SEO ブロック（他サイト fork 残骸）を除去。"""
    end = text.find(INDEX_SEO_MARKER_END)
    if end < 0:
        return text
    tail_start = end + len(INDEX_SEO_MARKER_END)
    tail = text[tail_start:]
    m = _ORPHAN_DUP_SEO_AFTER_MARKER.match(tail.lstrip())
    if not m:
        return text
    consumed = len(tail) - len(tail.lstrip()) + m.end()
    return text[:tail_start] + tail[consumed:]


def inject_index_seo_head(text: str) -> str:
    """Replace or insert site-config driven SEO head for SPA index.html."""
    block_inner = index_seo_head_inner()
    block = f"{INDEX_SEO_MARKER_START}\n{block_inner}\n{INDEX_SEO_MARKER_END}"
    if INDEX_SEO_MARKER_START in text and INDEX_SEO_MARKER_END in text:
        text = _INDEX_SEO_BLOCK.sub(block, text, count=1)
    else:
        text = _strip_legacy_index_seo(text)
        if "<!--SITE_VERIFICATION_META_INJECT-->" in text:
            text = text.replace("<!--SITE_VERIFICATION_META_INJECT-->", block, 1)
        elif _ORPHAN_TWITTER_AFTER_IMAGE.search(text):
            text = _ORPHAN_TWITTER_AFTER_IMAGE.sub(r"\1\n" + block, text, count=1)
        elif "<!--BRAND_ASSET_HEAD-->" in text:
            text = re.sub(
                r"(<!--BRAND_ASSET_HEAD-->[\s\S]*?<link rel=\"apple-touch-icon\"[^>]+>)",
                r"\1\n" + block,
                text,
                count=1,
            )
        else:
            text = re.sub(r'(<meta charset="UTF-8">)', r"\1\n" + block, text, count=1)
    return _strip_duplicate_seo_after_marker(text)


def migrate_legacy_takken_leaks(text: str) -> str:
    """宅建 fork 残骸を site-config のブランド・ドメインへ置換（宅建サイトは除外）。"""
    origin = clean_origin()
    if "takken-master.jp" in origin:
        return text
    bn = brand_name()
    en = exam_name()
    replacements = [
        ("https://takken-master.jp", origin),
        ("宅建マスター", bn),
        ("宅地建物取引士試験対策サイト", f"{en}対策サイト"),
        ("宅地建物取引士試験", en),
    ]
    for src, dst in replacements:
        text = text.replace(src, dst)
    # 他サイト fork からコピーされたドメインを siteOrigin へ
    origin = clean_origin()
    host = origin.replace("https://", "").replace("http://", "").strip("/")
    if host:
        for leak in (
            "chintaikanrishi-master.jp",
            "mankan-master.jp",
            "kangyou-master.jp",
            "eisei1shu-master.jp",
            "eisei2shu-master.jp",
            "mentalhealth-master.jp",
            "kikenbutsu-master.jp",
            "unkan-master.jp",
            "boiler-master.jp",
            "takken-master.jp",
        ):
            if leak != host:
                text = text.replace(f"https://{leak}", origin)
    return text


_SPA_PAGE_SEO_JS = """\
/*INDEX_SPA_PAGE_SEO*/
// ページごとのSEOメタ情報（SITE_CONFIG から組み立て）
function _cfgBrand(){ return (window.SITE_CONFIG && SITE_CONFIG.brandName) || 'Sampleマスター'; }
function _cfgExam(){ return (window.SITE_CONFIG && SITE_CONFIG.examName) || '◯◯試験（プレースホルダー）'; }
function _cfgSiteLabel(){ return _cfgBrand() + '（' + _cfgExam() + '）'; }
function _pageSeo(pageTitle, descTemplate, path, hash) {
  const exam = _cfgExam();
  return {
    title: pageTitle + '｜' + _cfgSiteLabel(),
    desc: String(descTemplate).replace(/\\{exam\\}/g, exam),
    path: path,
    hash: hash || ''
  };
}
const PAGE_SEO = {
  'quiz-start': _pageSeo('問題を解く', '{exam}の学習モードを選択。実践演習・過去問・一問一答から選んで学習スタート。', '/', ''),
  'past-config': _pageSeo('過去問演習', '{exam}の過去問を年度別・分野別に絞り込んで学習。', '/#past', '#past'),
  'orig': _pageSeo('実践演習', '{exam}対策の実践演習問題。分野別データで弱点克服。', '/#orig', '#orig'),
  'dash': _pageSeo('記録・学習分析', '学習日記カレンダー・獲得バッジ・レベルや分野別正答率で、学習の振り返りと弱点把握ができます。', '/#dash', '#dash'),
  'review': _pageSeo('復習', '不正解・未解答の演習問題を分野別にまとめて復習。弱点問題を集中的に解いて定着率を上げる。', '/#review', '#review'),
  'ichimondou': _pageSeo('一問一答', '{exam}の重要知識を一問一答形式で確認。短時間で基礎知識の定着を進められます。', '/#ichimondou', '#ichimondou')
};
/*/INDEX_SPA_PAGE_SEO*/"""

_PAGE_SEO_LEGACY_RE = re.compile(
    r"/\*INDEX_SPA_PAGE_SEO\*/[\s\S]*?/\*/INDEX_SPA_PAGE_SEO\*/|"
    r"// ページごとのSEOメタ情報(?:（SITE_CONFIG から組み立て）)?[\s\S]*?const PAGE_SEO = \{[\s\S]*?\};",
)

_UPDATE_PAGE_META_OG_ONLY = re.compile(
    r"  // OGP(?:も更新| / Twitter Card も更新（SNS再共有・ブラウザタブ用）)[\s\S]*?"
    r"  if \(ogDesc\)  ogDesc\.content  = seo\.desc;\n",
)

_UPDATE_PAGE_META_FULL = """\
  // OGP / Twitter Card も更新（SNS再共有・ブラウザタブ用）
  const ogTitle = document.querySelector('meta[property="og:title"]');
  const ogDesc  = document.querySelector('meta[property="og:description"]');
  const ogUrl   = document.querySelector('meta[property="og:url"]');
  const twTitle = document.querySelector('meta[name="twitter:title"]');
  const twDesc  = document.querySelector('meta[name="twitter:description"]');
  const twAlt   = document.querySelector('meta[name="twitter:image:alt"]');
  if (ogTitle) ogTitle.content = seo.title;
  if (ogDesc)  ogDesc.content  = seo.desc;
  if (ogUrl)   ogUrl.content   = publicCanonicalUrl(seo.path);
  if (twTitle) twTitle.content = seo.title;
  if (twDesc)  twDesc.content  = seo.desc;
  if (twAlt)   twAlt.content   = seo.title;
"""


def update_index_spa_seo_js(text: str) -> str:
    """PAGE_SEO と _updatePageMeta を SITE_CONFIG 連動版に統一。"""
    if "_pageSeo(" not in text:
        text = _PAGE_SEO_LEGACY_RE.sub(_SPA_PAGE_SEO_JS, text, count=1)
    if 'meta[name="twitter:title"]' not in text.split("function _updatePageMeta", 1)[-1][:1200]:
        text = _UPDATE_PAGE_META_OG_ONLY.sub(_UPDATE_PAGE_META_FULL, text, count=1)
    text = text.replace(
        "function getSiteShareLabel(){\n"
        "  return `${SITE_CONFIG.brandName||'Sampleマスター'}（${SITE_CONFIG.examName||'◯◯試験（プレースホルダー）'}）`;\n"
        "}",
        "function getSiteShareLabel(){\n  return _cfgSiteLabel();\n}",
    )
    for old, new in (
        (
            "if(!data) return 'Sampleマスター（◯◯試験（プレースホルダー））で問題演習をしました。';",
            "if(!data) return getSiteShareLabel() + 'で問題演習をしました。';",
        ),
        (
            "return `Sampleマスター（◯◯試験（プレースホルダー））で${modeLabel}を解きました。",
            "return getSiteShareLabel() + `で${modeLabel}を解きました。",
        ),
        (
            "return `Sampleマスター（◯◯試験（プレースホルダー））で「${badge.name}」バッジを獲得しました。",
            "return getSiteShareLabel() + `で「${badge.name}」バッジを獲得しました。",
        ),
        (
            "openTwitterShareIntent(`Sampleマスター（◯◯試験（プレースホルダー））で一問一答を解きました。",
            "openTwitterShareIntent(getSiteShareLabel() + `で一問一答を解きました。",
        ),
        (
            "return `Sampleマスター（◯◯試験（プレースホルダー））でレベルアップしました！",
            "return getSiteShareLabel() + `でレベルアップしました！",
        ),
        (
            "lines.push(`【Sampleマスター｜◯◯試験（プレースホルダー）｜この日の記録（${isoKey}）】`);",
            "lines.push(`【${_cfgBrand()}｜${_cfgExam()}｜この日の記録（${isoKey}）】`);",
        ),
    ):
        text = text.replace(old, new)
    return text
