#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""index.html SPA 部分同期・noscript / FIELDS フォールバックの site-config 化。"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from tools.site_config import brand_name, contact_url, exam_name, fields

INDEX_NOSCRIPT_MARKER_START = "<!--INDEX_NOSCRIPT-->"
INDEX_NOSCRIPT_MARKER_END = "<!--/INDEX_NOSCRIPT-->"
INDEX_FIELDS_FALLBACK_START = "/*INDEX_FIELDS_FALLBACK*/"
INDEX_FIELDS_FALLBACK_END = "/*/INDEX_FIELDS_FALLBACK*/"
INDEX_SPA_PAGE_SEO_START = "/*INDEX_SPA_PAGE_SEO*/"
INDEX_SPA_PAGE_SEO_END = "/*/INDEX_SPA_PAGE_SEO*/"

PATCH_REGIONS: dict[str, tuple[str, str]] = {
    "INDEX_SEO_HEAD": ("<!--INDEX_SEO_HEAD-->", "<!--/INDEX_SEO_HEAD-->"),
    "INDEX_NOSCRIPT": (INDEX_NOSCRIPT_MARKER_START, INDEX_NOSCRIPT_MARKER_END),
    "INDEX_FIELDS_FALLBACK": (INDEX_FIELDS_FALLBACK_START, INDEX_FIELDS_FALLBACK_END),
    "INDEX_SPA_PAGE_SEO": (INDEX_SPA_PAGE_SEO_START, INDEX_SPA_PAGE_SEO_END),
}

_FIELDS_FALLBACK_BLOCK = re.compile(
    rf"{re.escape(INDEX_FIELDS_FALLBACK_START)}[\s\S]*?{re.escape(INDEX_FIELDS_FALLBACK_END)}",
    re.I,
)

_NOSCRIPT_BLOCK = re.compile(
    rf"{re.escape(INDEX_NOSCRIPT_MARKER_START)}[\s\S]*?{re.escape(INDEX_NOSCRIPT_MARKER_END)}",
    re.I,
)

_SITE_CONFIG_SCRIPT = re.compile(
    r'<script\s+src="(?:\./)?site-config\.js"\s*></script>\s*',
    re.I,
)

_FIELDS_BOOTSTRAP = re.compile(
    r"(<!-- CSV 取り込み[\s\S]*?<script>\s*var SITE_CONFIG = window\.SITE_CONFIG \|\| \{\};\s*"
    r"var FIELDS = \(Array\.isArray\(SITE_CONFIG\.fields\) && SITE_CONFIG\.fields\.length\)\s*"
    r"\? SITE_CONFIG\.fields\.map\(function\(f\)\{[\s\S]*?\}\)\s*:\s*)"
    rf"(?:{re.escape(INDEX_FIELDS_FALLBACK_START)}[\s\S]*?{re.escape(INDEX_FIELDS_FALLBACK_END)}|\[[\s\S]*?\])"
    r"(;\s*function getFieldLabel[\s\S]*?</script>)",
    re.I,
)


def _field_noscript_line(field: dict) -> str:
    name = html.escape(str(field.get("name") or field.get("id") or ""))
    aliases = [str(a).strip() for a in (field.get("aliases") or []) if str(a).strip()]
    if len(aliases) >= 2:
        detail = html.escape("・".join(aliases[:3]))
        return f"          <li>{name}（{detail}など）</li>"
    if aliases:
        return f"          <li>{name}（{html.escape(aliases[0])}など）</li>"
    return f"          <li>{name}</li>"


def fields_fallback_js_literal() -> str:
    rows = fields()
    if not rows:
        return f"{INDEX_FIELDS_FALLBACK_START} [] {INDEX_FIELDS_FALLBACK_END}"
    parts: list[str] = []
    for f in rows:
        fid = json.dumps(str(f["id"]), ensure_ascii=False)
        name = json.dumps(str(f.get("name") or f["id"]), ensure_ascii=False)
        aliases = json.dumps(
            [str(a) for a in (f.get("aliases") or [])],
            ensure_ascii=False,
        )
        legacy = json.dumps(
            str(f.get("legacyGlossaryCat") or f["id"]),
            ensure_ascii=False,
        )
        parts.append(
            f"      {{ id: {fid}, name: {name}, aliases: {aliases}, legacyGlossaryCat: {legacy} }}"
        )
    inner = "[\n" + ",\n".join(parts) + "\n    ]"
    return f"{INDEX_FIELDS_FALLBACK_START} {inner} {INDEX_FIELDS_FALLBACK_END}"


def index_noscript_inner() -> str:
    bn = html.escape(brand_name())
    en = html.escape(exam_name())
    contact = html.escape(contact_url())
    field_rows = fields()
    practice_names = html.escape("・".join(str(f.get("name") or f.get("id") or "") for f in field_rows[:4]))
    if not practice_names:
        practice_names = "主要分野"
    subject_lines = "\n".join(_field_noscript_line(f) for f in field_rows) or "          <li>主要科目</li>"
    return f"""    <noscript>
      <div style="max-width:860px;margin:40px auto;padding:0 20px;font-family:sans-serif;line-height:1.8">
        <h1>{bn}｜{en} 無料学習プラットフォーム</h1>
        <p>{en}の合格を目指す無料の学習プラットフォームです。本サービスをご利用いただくにはJavaScriptを有効にしてください。</p>
        <h2>主な機能</h2>
        <ul>
          <li><strong>過去問演習</strong>：年度別・科目別に絞り込んで効率的に学習</li>
          <li><strong>実践演習</strong>：{practice_names}の分野別練習（独自問題集）</li>
          <li><strong>用語解説</strong>：重要用語をわかりやすく解説（静的ページ）</li>
          <li><strong>記録・学習分析</strong>：学習日記・バッジ・レベルに加え、正答率や科目別成績で進捗を可視化</li>
        </ul>
        <h2>対応科目</h2>
        <ul>
{subject_lines}
        </ul>
        <p style="margin-top:24px;font-size:14px;line-height:2"><a href="about.html">このサイトについて</a> ・ <a href="q/index.html">過去問一覧</a> ・ <a href="q/practice/index.html">実践演習一覧</a> ・ <a href="q/ichimon/index.html">一問一答一覧</a> ・ <a href="terms/index.html">用語集</a> ・ <a href="articles/index.html">試験ガイド</a> ・ <a href="related-sites.html">関連リンク</a> ・ <a href="privacy.html">プライバシー</a> ・ <a href="{contact}" target="_blank" rel="noopener noreferrer">お問い合わせ</a></p>
      </div>
    </noscript>"""


def inject_index_fields_fallback(text: str) -> str:
    """FIELDS の site-config 未読込時フォールバックを fields から再生成。"""
    fallback = fields_fallback_js_literal()

    def _replace(m: re.Match[str]) -> str:
        return m.group(1) + fallback + m.group(2)

    if INDEX_FIELDS_FALLBACK_START in text:
        text = _FIELDS_BOOTSTRAP.sub(_replace, text, count=1)
    else:
        legacy = re.compile(
            r"(var FIELDS = \(Array\.isArray\(SITE_CONFIG\.fields\) && SITE_CONFIG\.fields\.length\)\s*"
            r"\? SITE_CONFIG\.fields\.map\(function\(f\)\{[\s\S]*?\}\)\s*:\s*)"
            rf"(?:{re.escape(INDEX_FIELDS_FALLBACK_START)}[\s\S]*?{re.escape(INDEX_FIELDS_FALLBACK_END)}|\[[\s\S]*?\])"
            r"(;)",
            re.I,
        )
        text = legacy.sub(rf"\1{fallback}\2", text, count=1)
    return text


_FIELD_BARS_TIP_RE = re.compile(
    r'(<span class="tip-box">)[^<]*(?:法令・制度・契約実務・設備等の各科目ごとの正解率[^<]*)',
    re.I,
)

_TAG_LAW_KS_OLD = (
    "return t.replace(/（((?:民法|法令・制度|宅地建物取引業法|労働衛生法令・制度|借地借家法|区分所有法|"
    "不動産登記法|都市計画法|建築基準法|農地法|国土利用計画法|土地区画整理法|盛土規制法|租税特別措置法|"
    "地方税法|地価公示法)[^）]{1,30}？)）/g,\n"
    "      (_,m)=>`<span class=\"ks-law\">${m}</span>`);"
)
_TAG_LAW_RICH_OLD = (
    "return t.replace(/（((?:民法|法令・制度|宅地建物取引業法|労働衛生法令・制度|借地借家法|区分所有法|"
    "不動産登記法|都市計画法|建築基準法|農地法|国土利用計画法|土地区画整理法|盛土規制法|宅造法|租税特別措置法|"
    "地方税法|地価公示法|住宅品質確保法|住宅金融支援機構法|住宅瑕疵担保履行法)[^）]{1,30}？)）/g,\n"
    "      (_,m)=>`<span class=\"rich-law\">${m}</span>`);"
)

_DAILY_MSGS_BLOCK_RE = re.compile(
    r"// ===== EXAM COUNTDOWN =====\s*"
    r"\(function\(\)\{\s*"
    r"const DAILY_MSGS = \[[\s\S]*?\];\s*"
    r"// 試験日は地域等で異なるため、日数カウント表示は廃止\s*"
    r"\}\)\(\);",
    re.I,
)


def field_bars_tip_text() -> str:
    names = [str(f.get("name") or f.get("id") or "").strip() for f in fields()]
    names = [n for n in names if n]
    if not names:
        return "各分野ごとの正解率。回答済みの科目だけ4段階で表示"
    if len(names) <= 3:
        label = "・".join(names)
    else:
        label = "・".join(names[:3]) + "等"
    return f"{label}の各分野ごとの正解率。回答済みの科目だけ4段階で表示"


def tag_law_js_body(class_name: str) -> str:
    return (
        "return t.replace(/（((?:[^）]{1,34}(?:法|令|規則|条例|省令|告示|規程))[^）]{0,16}?)）/g,"
        f'(_,m)=>`<span class="{class_name}">${{m}}</span>`);'
    )


def inject_index_spa_ui_leaks(text: str) -> str:
    """他試験 fork 由来の SPA UI 文言（分野ツールチップ・法令ハイライト・未使用メッセージ）を site-config へ合わせる。"""
    tip = html.escape(field_bars_tip_text(), quote=False)
    text = _FIELD_BARS_TIP_RE.sub(rf"\1{tip}", text, count=1)
    text = _DAILY_MSGS_BLOCK_RE.sub(
        "// 試験日は地域等で異なるため、日数カウント表示は廃止（旧 DAILY_MSGS は削除）",
        text,
        count=1,
    )
    if _TAG_LAW_KS_OLD in text:
        text = text.replace(_TAG_LAW_KS_OLD, tag_law_js_body("ks-law"), 1)
    if _TAG_LAW_RICH_OLD in text:
        text = text.replace(_TAG_LAW_RICH_OLD, tag_law_js_body("rich-law"), 1)
    return text


def inject_index_noscript(text: str) -> str:
    block = f"{INDEX_NOSCRIPT_MARKER_START}\n{index_noscript_inner()}\n    {INDEX_NOSCRIPT_MARKER_END}"
    if INDEX_NOSCRIPT_MARKER_START in text and INDEX_NOSCRIPT_MARKER_END in text:
        return _NOSCRIPT_BLOCK.sub(block, text, count=1)
    legacy = re.compile(
        r"<!-- JS無効時のフォールバック \(SEOクローラー向け静的コンテンツ\) -->\s*<noscript>[\s\S]*?</noscript>",
        re.I,
    )
    if legacy.search(text):
        return legacy.sub(block, text, count=1)
    return text.replace(
        "    <!-- JS無効時のフォールバック (SEOクローラー向け静的コンテンツ) -->",
        f"    <!-- JS無効時のフォールバック (SEOクローラー向け静的コンテンツ) -->\n{INDEX_NOSCRIPT_MARKER_START}\n"
        + index_noscript_inner()
        + f"\n    {INDEX_NOSCRIPT_MARKER_END}",
        1,
    )


def ensure_site_config_before_fields(text: str) -> str:
    """site-config.js を FIELDS 定義より前に読み込む（二重読込は除去）。"""
    fields_pos = text.find("var FIELDS =")
    if fields_pos < 0:
        return text
    first_cfg = _SITE_CONFIG_SCRIPT.search(text)
    if not first_cfg or first_cfg.start() < fields_pos:
        return text

    cfg_tag = first_cfg.group(0)
    text = text[: first_cfg.start()] + text[first_cfg.end() :]

    theme_link = '<link rel="stylesheet" href="site-theme.css">'
    bootstrap_marker = "<!-- CSV 取り込みデータを QUESTIONS 等へ反映する（exam-site-data-past.js の末尾から呼ばれる） -->"
    insert = f"{theme_link}\n{cfg_tag}{bootstrap_marker}"
    if bootstrap_marker in text:
        return text.replace(bootstrap_marker, insert, 1)
    return text.replace(
        "<script>\nvar SITE_CONFIG = window.SITE_CONFIG || {};\nvar FIELDS =",
        f"{theme_link}\n{cfg_tag}\n<script>\nvar SITE_CONFIG = window.SITE_CONFIG || {{}};\nvar FIELDS =",
        1,
    )


def extract_marker_region(text: str, start: str, end: str) -> str | None:
    pattern = re.compile(rf"{re.escape(start)}[\s\S]*?{re.escape(end)}", re.I)
    m = pattern.search(text)
    return m.group(0) if m else None


def replace_marker_region(text: str, start: str, end: str, replacement: str) -> str:
    pattern = re.compile(rf"{re.escape(start)}[\s\S]*?{re.escape(end)}", re.I)
    if not pattern.search(text):
        return text
    return pattern.sub(replacement, text, count=1)


def sync_index_spa_regions(template_text: str, target_text: str, region_names: list[str]) -> tuple[str, list[str]]:
    """テンプレ index.html のマーカー領域を本番 index.html へコピー。"""
    updated: list[str] = []
    out = target_text
    for name in region_names:
        key = name.strip()
        if not key or key.startswith("#"):
            continue
        markers = PATCH_REGIONS.get(key)
        if not markers:
            continue
        start, end = markers
        region = extract_marker_region(template_text, start, end)
        if not region:
            continue
        if start not in out or end not in out:
            continue
        new_out = replace_marker_region(out, start, end, region)
        if new_out != out:
            updated.append(key)
            out = new_out
    return out, updated


def load_patch_region_names(manifest_path: Path) -> list[str]:
    if not manifest_path.is_file():
        return list(PATCH_REGIONS.keys())
    names: list[str] = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            names.append(line)
    return names
