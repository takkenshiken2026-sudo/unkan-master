#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate index.html SPA SEO / OGP / Twitter Card / JSON-LD from site-config.json."""

from __future__ import annotations

import html
import json
import re

from tools.brand_assets import theme_ink
from tools.site_config import (
    base_path,
    brand_name,
    clean_origin,
    exam_name,
    fields,
    google_site_verification,
    public_url,
)

INDEX_SEO_MARKER_START = "<!--INDEX_SEO_HEAD-->"
INDEX_SEO_MARKER_END = "<!--/INDEX_SEO_HEAD-->"


def index_home_title() -> str:
    return f"{brand_name()}｜{exam_name()} 過去問・一問一答・用語解説で合格を目指す無料学習サイト"


def index_og_title() -> str:
    return f"{brand_name()}｜{exam_name()} 無料学習プラットフォーム"


def index_site_label() -> str:
    return f"{brand_name()}（{exam_name()}）"


def index_canonical_url() -> str:
    """SPA ホームの canonical / og:url（basePath 対応）。"""
    url = public_url("")
    return url if url.endswith("/") else f"{url}/"


def index_spa_hash_url(hash_frag: str) -> str:
    """JSON-LD 等用の SPA ハッシュ URL（例: https://example.com/fp3#past）。"""
    frag = hash_frag if hash_frag.startswith("#") else f"#{hash_frag}"
    origin = clean_origin()
    bp = base_path()
    if bp:
        return f"{origin}{bp}{frag}"
    return f"{origin}/{frag}"


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
    home_url = index_canonical_url()
    home_id = home_url.rstrip("/")
    alt = f"{exam_name()}対策サイト"
    platform_desc = (
        f"{exam_name()}の過去問・実践演習・一問一答・用語解説を"
        "網羅した無料学習プラットフォーム"
    )
    return [
        {
            "@type": "WebSite",
            "@id": f"{home_id}/#website",
            "url": home_url,
            "name": brand_name(),
            "alternateName": alt,
            "description": platform_desc,
            "inLanguage": "ja",
        },
        {
            "@type": "EducationalApplication",
            "@id": f"{home_id}/#app",
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
                {"@type": "ListItem", "position": 1, "name": "トップ", "item": home_url},
                {"@type": "ListItem", "position": 2, "name": "過去問", "item": index_spa_hash_url("#past")},
                {"@type": "ListItem", "position": 3, "name": "実践演習", "item": index_spa_hash_url("#orig")},
                {"@type": "ListItem", "position": 4, "name": "用語解説", "item": public_url("terms/")},
            ],
        },
    ]


def index_seo_head_inner() -> str:
    """SEO block only (og:image は brand_assets の BRAND_ASSET_HEAD が担当)。"""
    home_url = index_canonical_url()
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
    gsc_token = google_site_verification()
    gsc_meta = (
        f'<meta name="google-site-verification" content="{html.escape(gsc_token)}">\n'
        if gsc_token
        else "<!--SITE_VERIFICATION_META_INJECT-->\n"
    )
    return f"""{gsc_meta}<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
<title>{html.escape(home_title)}</title>

<!-- 基本SEO -->
<meta name="description" content="{html.escape(desc_long)}">
<meta name="keywords" content="{html.escape(keywords)}">
<meta name="robots" content="index, follow">
<meta name="application-name" content="{html.escape(site_label)}">
<link rel="canonical" href="{html.escape(home_url)}" id="canonical-link">

<!-- Open Graph (SNS・Slack等でのリッチ表示) -->
<meta property="og:type" content="website">
<meta property="og:url" content="{html.escape(home_url)}">
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

_INDEX_SEO_POLLUTED_REGION = re.compile(
    rf"{re.escape(INDEX_SEO_MARKER_START)}[\s\S]*?"
    rf"{re.escape(INDEX_SEO_MARKER_END)}\s*"
    r"(?:<!-- Open Graph \(SNS・Slack等でのリッチ表示\) -->[\s\S]*?<!--/INDEX_SEO_HEAD-->\s*)*"
    r"(?:\(SNS・Slack等でのリッチ表示\) -->[\s\S]*?<!--/INDEX_SEO_HEAD-->\s*)*"
    r'(?=<meta name="format-detection"|<link rel="preconnect")',
    re.I,
)

_HEAD_BODY_ANCHOR = r'(?=<meta name="format-detection"|<link rel="preconnect")'

_INDEX_SEO_REGION_COLLAPSE = re.compile(
    rf"{re.escape(INDEX_SEO_MARKER_START)}[\s\S]*?{_HEAD_BODY_ANCHOR}",
    re.I,
)

_ORPHAN_SEO_BETWEEN_END_AND_ANCHOR = re.compile(
    rf"{re.escape(INDEX_SEO_MARKER_END)}\s*"
    r"(?:<!--/?INDEX_SEO_HEAD-->[\s\S]*?)*"
    r"(?:<meta name=\"keywords\"[\s\S]*?</script>\s*)*"
    r"(?:<!-- Open Graph[\s\S]*?</script>\s*)*"
    r'(?=<meta name="format-detection"|<link rel="preconnect")',
    re.I,
)

_ORPHAN_SEO_TAIL_RE = re.compile(
    r"(?:(?:<!-- Open Graph )?\(SNS・Slack等でのリッチ表示\) -->[\s\S]*?<!--/INDEX_SEO_HEAD-->\s*)+",
    re.I,
)

_ORPHAN_META_AFTER_SEO_RE = re.compile(
    r"<meta name=\"keywords\"[^>]+>\s*"
    r"<meta name=\"robots\"[^>]+>\s*"
    r"<meta name=\"application-name\"[^>]+>\s*"
    r"<link rel=\"canonical\"[^>]+>\s*",
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
    if m:
        consumed = len(tail) - len(tail.lstrip()) + m.end()
        return text[:tail_start] + tail[consumed:]
    m2 = _ORPHAN_META_AFTER_SEO_RE.match(tail.lstrip())
    if m2:
        consumed = len(tail) - len(tail.lstrip()) + m2.end()
        return text[:tail_start] + tail[consumed:]
    return text


def _strip_orphan_seo_after_index_end(text: str) -> str:
    """INDEX_SEO 終了マーカー直後〜 format-detection 手前の重複 SEO を除去。"""
    while True:
        cleaned = _ORPHAN_SEO_BETWEEN_END_AND_ANCHOR.sub(INDEX_SEO_MARKER_END + "\n", text, count=1)
        if cleaned == text:
            break
        text = cleaned
    return text


def inject_index_seo_head(text: str) -> str:
    """Replace or insert site-config driven SEO head for SPA index.html."""
    block_inner = index_seo_head_inner()
    block = f"{INDEX_SEO_MARKER_START}\n{block_inner}\n{INDEX_SEO_MARKER_END}\n"

    collapsed = _INDEX_SEO_REGION_COLLAPSE.search(text)
    if collapsed:
        text = text[: collapsed.start()] + block + text[collapsed.end() :]
    else:
        polluted = _INDEX_SEO_POLLUTED_REGION.search(text)
        if polluted:
            text = text[: polluted.start()] + block + text[polluted.end() :]
        else:
            while INDEX_SEO_MARKER_START in text and INDEX_SEO_MARKER_END in text:
                text = _INDEX_SEO_BLOCK.sub("", text, count=1)
            text = _ORPHAN_SEO_TAIL_RE.sub("", text)
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

    text = _strip_orphan_seo_after_index_end(text)
    while True:
        cleaned = _strip_duplicate_seo_after_marker(text)
        if cleaned == text:
            break
        text = cleaned
    return text


_OTHER_SITE_HOSTS = (
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
    "fp-master.jp",
)


def migrate_legacy_takken_leaks(text: str) -> str:
    """他サイト fork 残骸を site-config のブランド・ドメインへ置換。"""
    origin = clean_origin()
    bn = brand_name()
    en = exam_name()
    replacements = [
        ("https://takken-master.jp", origin),
        ("宅建マスター", bn),
        ("宅地建物取引士試験対策サイト", f"{en}対策サイト"),
        ("宅地建物取引士試験", en),
        ("マン管マスター", bn),
        ("マンション管理士試験対策サイト", f"{en}対策サイト"),
        ("マンション管理士試験", en),
        ("運管マスター", bn),
        ("運行管理者試験対策サイト", f"{en}対策サイト"),
        ("運行管理者試験", en),
        ("FPマスター", bn),
        ("ファイナンシャル・プランナー試験（FP2級・FP3級）", en),
        ("Sample試験", en),
        ("賃管マスター", bn),
        ("賃貸不動産経営管理士試験", en),
        ("管業マスター", bn),
        ("管理業務主任者試験", en),
    ]
    for src, dst in replacements:
        if src != dst:
            text = text.replace(src, dst)
    host = origin.replace("https://", "").replace("http://", "").strip("/")
    if host:
        for leak in _OTHER_SITE_HOSTS:
            if leak != host:
                text = text.replace(f"https://{leak}", origin)
                text = text.replace(leak, host)
    return text


_SPA_PAGE_SEO_JS = """\
/*INDEX_SPA_PAGE_SEO*/
// ページごとのSEOメタ情報（SITE_CONFIG から組み立て）
function _cfgBrand(){ return (window.SITE_CONFIG && SITE_CONFIG.brandName) || 'Sampleマスター'; }
function _cfgExam(){ return (window.SITE_CONFIG && SITE_CONFIG.examName) || '◯◯試験（プレースホルダー）'; }
function _cfgQuizStartTitle(){ return '「' + _cfgExam() + '」の問題を解く'; }
function _cfgSiteLabel(){ return _cfgBrand() + '（' + _cfgExam() + '）'; }
function _pageTitleFor(id){ return id === 'quiz-start' ? _cfgQuizStartTitle() : (PAGE_TITLES[id] || ''); }
function _cfgSiteSlug(){
  const o=String((window.SITE_CONFIG&&SITE_CONFIG.siteOrigin)||'').replace(/^https?:\\/\\//,'').replace(/\\/.*$/,'');
  if(o) return o.split('.')[0]||'site';
  try{ return (location.hostname||'site').split('.')[0]||'site'; }catch(e){ return 'site'; }
}
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
  'quiz-start': _pageSeo(_cfgQuizStartTitle(), '{exam}の学習モードを選択。実践演習・過去問・一問一答から選んで学習スタート。', '/', ''),
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
    if "_cfgQuizStartTitle" not in text:
        text = text.replace(
            "function _cfgExam(){ return (window.SITE_CONFIG && SITE_CONFIG.examName) || '◯◯試験（プレースホルダー）'; }\n"
            "function _cfgSiteLabel()",
            "function _cfgExam(){ return (window.SITE_CONFIG && SITE_CONFIG.examName) || '◯◯試験（プレースホルダー）'; }\n"
            "function _cfgQuizStartTitle(){ return '「' + _cfgExam() + '」の問題を解く'; }\n"
            "function _cfgSiteLabel()",
        )
        text = text.replace(
            "function _cfgSiteLabel(){ return _cfgBrand() + '（' + _cfgExam() + '）'; }\n"
            "function _pageSeo(",
            "function _cfgSiteLabel(){ return _cfgBrand() + '（' + _cfgExam() + '）'; }\n"
            "function _pageTitleFor(id){ return id === 'quiz-start' ? _cfgQuizStartTitle() : (PAGE_TITLES[id] || ''); }\n"
            "function _pageSeo(",
        )
    text = text.replace(
        "'quiz-start': _pageSeo('問題を解く',",
        "'quiz-start': _pageSeo(_cfgQuizStartTitle(),",
    )
    text = text.replace(
        "const PAGE_TITLES={'quiz-start':'問題を解く',",
        "const PAGE_TITLES={",
    )
    text = text.replace(
        "document.getElementById('topbar-title').textContent=PAGE_TITLES[id]||'';",
        "document.getElementById('topbar-title').textContent=_pageTitleFor(id);",
    )
    return text
