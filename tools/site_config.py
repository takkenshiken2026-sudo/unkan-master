# -*- coding: utf-8 -*-
"""Central site configuration helpers for the exam-site template."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


def resolve_site_root() -> Path:
    """Prefer cwd (or EXAM_SITE_ROOT) so cross-repo PYTHONPATH still validates the right site."""
    env_root = os.environ.get("EXAM_SITE_ROOT", "").strip()
    if env_root:
        p = Path(env_root).resolve()
        if (p / "site-config.json").is_file():
            return p
    cwd = Path.cwd().resolve()
    if (cwd / "site-config.json").is_file():
        return cwd
    return Path(__file__).resolve().parents[1]


ROOT = resolve_site_root()
CONFIG_PATH = ROOT / "site-config.json"


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(f"site-config.json が見つかりません: {CONFIG_PATH}")
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(cfg, dict):
        raise ValueError("site-config.json は JSON object にしてください")
    return cfg


CONFIG = load_config()


def clean_origin() -> str:
    return str(CONFIG.get("siteOrigin") or "").rstrip("/")


def brand_name() -> str:
    return str(CONFIG.get("brandName") or "Sampleマスター")


def brand_mark() -> str:
    return str(CONFIG.get("brandMark") or brand_name()[:1] or "S")


def brand_logo_lines() -> tuple[str, str]:
    """長方形ロゴ（2行）の上段・下段。brandLogoTop/Bottom > brandLogoText > brandName から自動分割。"""
    top = str(CONFIG.get("brandLogoTop") or "").strip()
    bottom = str(CONFIG.get("brandLogoBottom") or "").strip()
    if top and bottom:
        return top, bottom
    logo_text = str(CONFIG.get("brandLogoText") or "").strip()
    if logo_text:
        return logo_text, "マスター"
    name = brand_name()
    if name.endswith("マスター"):
        return name[: -len("マスター")], "マスター"
    return brand_mark(), name


def brand_logo_size_class(top_line: str) -> str:
    n = len(top_line)
    if n >= 7:
        return "logo-mark--compact"
    if n >= 5:
        return "logo-mark--narrow"
    return ""


def exam_name() -> str:
    return str(CONFIG.get("examName") or "◯◯試験")


def extended_correct_answers() -> bool:
    """past/practice の correct が multi・combination 等を許容するサイト。"""
    return bool(CONFIG.get("extendedCorrectAnswers"))


def is_template_site() -> bool:
    """exam-site-shell サンプル（プレースホルダー運用）かどうか。"""
    origin = clean_origin().lower()
    brand = brand_name()
    if "your-domain" in origin or origin.endswith(".example"):
        return True
    if brand in {"Sampleマスター", "サンプルマスター"}:
        return True
    exam = exam_name()
    return "プレースホルダ" in exam or exam.startswith("◯◯")


def excluded_past_exam_years() -> set[str]:
    """静的過去問から除外する exam_year（site-config.json の excludePastExamYears）。"""
    raw = CONFIG.get("excludePastExamYears") or CONFIG.get("excludedPastExamYears") or []
    if isinstance(raw, str):
        return {raw.strip()} if raw.strip() else set()
    return {str(x).strip() for x in raw if str(x).strip()}


def contact_url() -> str:
    return str(CONFIG.get("contactUrl") or "#")


def base_path() -> str:
    """SPA のサブパス（例: /fp3）。未設定なら空。"""
    raw = str(CONFIG.get("basePath") or "").strip().rstrip("/")
    if not raw:
        return ""
    return raw if raw.startswith("/") else f"/{raw}"


def exam_grade() -> str:
    return str(CONFIG.get("examGrade") or "").strip()


def grade_portal_href() -> str:
    """級選択ポータルへのリンク（FP 等の multi-grade サイト用）。"""
    return str(CONFIG.get("gradePortalHref") or "").strip()


def google_site_verification() -> str:
    """Google Search Console の HTML タグ確認用トークン（未設定なら空）。"""
    return str(CONFIG.get("googleSiteVerification") or "").strip()


def ga4_measurement_id() -> str:
    return str(CONFIG.get("ga4MeasurementId") or "").strip()


def copyright_text() -> str:
    configured = str(CONFIG.get("copyright") or "").strip()
    if configured:
        return configured
    host = clean_origin().replace("https://", "").replace("http://", "").strip("/")
    suffix = f"・{host}" if host else ""
    return f"© 2026 {brand_name()}学習支援{suffix}"


def footer_disclaimer() -> str:
    return str(CONFIG.get("footerDisclaimer") or "")


def learning_nav_label_overrides() -> dict[str, str]:
    """SPA 学習ナビの表示ラベル上書き（例: tnav-orig → オリジナル問題）。"""
    raw = CONFIG.get("learningNavLabelOverrides") or {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items() if v}


def learning_nav_label(nav_id: str, default: str) -> str:
    return learning_nav_label_overrides().get(nav_id, default)


def official_organization() -> str:
    return str(CONFIG.get("officialOrganization") or "試験実施団体")


def external_links() -> list[dict[str, str]]:
    raw = CONFIG.get("externalLinks") or []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        label = str(item.get("label") or "").strip()
        if url and label:
            out.append(
                {
                    "url": url,
                    "label": label,
                    "description": str(item.get("description") or "").strip(),
                }
            )
    return out


def primary_external_link() -> dict[str, str]:
    links = external_links()
    if links:
        return links[0]
    return {
        "url": "https://example.com/",
        "label": official_organization(),
        "description": "試験日程・要項・合格発表などの公式情報を確認してください。",
    }


DEFAULT_HEADER_NAV = [
    {"label": "トップ", "href": "index.html", "key": "top"},
    {"label": "このサイトについて", "href": "about.html", "key": "about"},
    {"label": "過去問一覧", "href": "q/index.html", "key": "q"},
    {"label": "用語集", "href": "terms/index.html", "key": "terms"},
    {"label": "試験ガイド", "href": "articles/index.html", "key": "articles"},
    {"label": "関連リンク", "href": "related-sites.html", "key": "related"},
    {"label": "プライバシー", "href": "privacy.html", "key": "privacy"},
]

DEFAULT_FOOTER_NAV = [
    *DEFAULT_HEADER_NAV,
    {"label": "お問い合わせ", "href": "__CONTACT__", "key": "contact"},
]


def navigation_items(section: str) -> list[tuple[str, str, str]]:
    nav = CONFIG.get("navigation") or {}
    raw = nav.get(section) if isinstance(nav, dict) else None
    if not isinstance(raw, list) or not raw:
        raw = DEFAULT_FOOTER_NAV if section == "footer" else DEFAULT_HEADER_NAV
    out: list[tuple[str, str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        href = str(item.get("href") or "").strip()
        key = str(item.get("key") or "").strip()
        if href == "__CONTACT__":
            href = contact_url()
        if label and href:
            out.append((label, href, key or label))
    return out


def theme() -> dict[str, str]:
    raw = CONFIG.get("theme") or {}
    if not isinstance(raw, dict):
        raw = {}
    defaults = {
        "accent": "#333333",
        "accentText": "#ffffff",
        "background": "#f0f0f1",
        "surface": "#ffffff",
        "surfaceAlt": "#f4f4f5",
        "text": "#111111",
        "textMuted": "#555555",
        "border": "rgba(0, 0, 0, 0.09)",
        "radius": "10px",
        "navWidth": "1080px",
        "contentWidth": "1080px",
    }
    return {k: str(raw.get(k) or v) for k, v in defaults.items()}


def write_site_theme_css() -> None:
    t = theme()
    accent = t["accent"]
    css = f""":root {{
  --sel: {accent};
  --accent: {accent};
  --accent-text: {t["accentText"]};
  --accent-soft: color-mix(in srgb, {accent} 11%, #ffffff);
  --accent-soft-mid: color-mix(in srgb, {accent} 18%, #ffffff);
  --accent-border: color-mix(in srgb, {accent} 26%, #ffffff);
  --accent-emphasis: color-mix(in srgb, {accent} 42%, #333333);
  --accent-hover-surface: color-mix(in srgb, {accent} 7%, #ffffff);
  --accent-hover-border: color-mix(in srgb, {accent} 30%, #e4e4e6);
  --accent-shadow: color-mix(in srgb, {accent} 12%, transparent);
  --bg: {t["surface"]};
  --bg2: {t["surfaceAlt"]};
  --page-bg: {t["background"]};
  --text: {t["text"]};
  --text2: {t["textMuted"]};
  --border: {t["border"]};
  --r2: {t["radius"]};
  --site-nav-w: {t["navWidth"]};
  --site-content-w: {t["contentWidth"]};
  --site-readable-w: min(860px, {t["contentWidth"]});
}}
body {{
  background: var(--page-bg);
}}
.site-page-mark {{
  background: var(--accent);
  color: var(--accent-text);
}}
.terms-idx-chip.on,
.gcat-btn.active {{
  background: var(--accent-soft);
  border-color: var(--accent-border);
  color: var(--accent-emphasis);
}}
"""
    (ROOT / "site-theme.css").write_text(css, encoding="utf-8")


DEFAULT_GUIDE_ARTICLE_GENRES: list[dict[str, str]] = [
    {"id": "overview", "label": "試験概要", "phase": "制度を知る", "style": "overview", "hint": ""},
    {"id": "application", "label": "受験・申込", "phase": "制度を知る", "style": "institution", "hint": ""},
    {"id": "pass-stats", "label": "合格・難易度", "phase": "制度を知る", "style": "institution", "hint": ""},
    {"id": "exam-scope", "label": "出題・形式", "phase": "制度を知る", "style": "institution", "hint": ""},
    {"id": "study-plan", "label": "学習計画", "phase": "学習を設計する", "style": "study", "hint": ""},
    {"id": "self-study", "label": "独学対策", "phase": "学習を設計する", "style": "study", "hint": ""},
    {"id": "past-questions", "label": "過去問活用", "phase": "演習と定着", "style": "practice", "hint": ""},
    {"id": "field-study", "label": "分野別対策", "phase": "演習と定着", "style": "practice", "hint": ""},
    {"id": "glossary-study", "label": "用語整理", "phase": "演習と定着", "style": "practice", "hint": ""},
    {"id": "review-weak", "label": "復習・苦手克服", "phase": "演習と定着", "style": "practice", "hint": ""},
    {"id": "final-prep", "label": "直前・当日", "phase": "直前と当日", "style": "final", "hint": ""},
    {"id": "cautions", "label": "注意点・更新", "phase": "横断", "style": "meta", "hint": ""},
]


def guide_article_genres() -> list[dict[str, str]]:
    raw = CONFIG.get("guideArticleGenres")
    if not isinstance(raw, list) or not raw:
        return [dict(g) for g in DEFAULT_GUIDE_ARTICLE_GENRES]
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        out.append(
            {
                "id": str(item.get("id") or label),
                "label": label,
                "phase": str(item.get("phase") or "").strip(),
                "style": str(item.get("style") or "meta").strip() or "meta",
                "hint": str(item.get("hint") or "").strip(),
            }
        )
    return out or [dict(g) for g in DEFAULT_GUIDE_ARTICLE_GENRES]


def guide_genre_labels() -> list[str]:
    return [g["label"] for g in guide_article_genres()]


def guide_genre_order_index() -> dict[str, int]:
    return {label: i for i, label in enumerate(guide_genre_labels())}


def guide_genre_style_by_label() -> dict[str, str]:
    return {g["label"]: g["style"] for g in guide_article_genres()}


def fields() -> list[dict[str, Any]]:
    out = CONFIG.get("fields") or []
    if not isinstance(out, list) or not out:
        raise ValueError("site-config.json の fields は1件以上の配列にしてください")
    return out


def field_ids() -> list[str]:
    return [str(f["id"]) for f in fields()]


def field_labels() -> dict[str, str]:
    return {str(f["id"]): str(f.get("name") or f["id"]) for f in fields()}


def category_to_field_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for f in fields():
        fid = str(f["id"])
        names = [f.get("name"), *(f.get("aliases") or [])]
        for name in names:
            if name:
                mapping[str(name)] = fid
    return mapping


def category_order() -> list[str]:
    out: list[str] = []
    for f in fields():
        for name in [f.get("name"), *(f.get("aliases") or [])]:
            if name and str(name) not in out:
                out.append(str(name))
    return out


def legacy_glossary_cat(category: str) -> str:
    fid = category_to_field_map().get(category)
    if not fid:
        return "limit"
    for f in fields():
        if str(f["id"]) == fid:
            return str(f.get("legacyGlossaryCat") or fid)
    return fid


def css_safe_field_id(field_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", field_id).strip("-")
    return safe or "field"


def public_url(rel_path: str) -> str:
    rel = rel_path.lstrip("/")
    origin = clean_origin()
    bp = base_path()
    if bp and not rel.startswith(bp.lstrip("/")):
        prefix = bp.lstrip("/")
        if rel:
            rel = f"{prefix}/{rel}"
        else:
            rel = prefix
    return f"{origin}/{rel}" if rel else origin


GUIDE_INDEX_PICK_KIND_LABELS: dict[str, str] = {
    "course": "講座",
    "textbook": "テキスト",
    "problem-book": "問題集",
    "mock": "模試",
}

GUIDE_INDEX_PICK_LAYOUTS = frozenset({"grid-3", "grid-2", "strip", "compact", "text"})


def guide_index_picks() -> dict[str, Any] | None:
    """ハブ一覧（articles/terms/q index）のおすすめ講座・教材カード。最大4件。"""
    raw = CONFIG.get("guideIndexPicks")
    if not isinstance(raw, dict):
        return None
    items_raw = raw.get("items")
    if not isinstance(items_raw, list):
        return None
    layout = str(raw.get("layout") or "grid-3").strip().lower()
    if layout not in GUIDE_INDEX_PICK_LAYOUTS:
        layout = "grid-3"
    max_items = 4 if layout == "grid-2" else 3
    items: list[dict[str, str]] = []
    for item in items_raw[:max_items]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        href = str(item.get("href") or "").strip()
        if not title or not href:
            continue
        kind = str(item.get("kind") or "textbook").strip() or "textbook"
        kind_label = str(item.get("kindLabel") or "").strip() or GUIDE_INDEX_PICK_KIND_LABELS.get(kind, "教材")
        description = str(item.get("description") or "").strip()
        cta = str(item.get("cta") or "記事を読む").strip() or "記事を読む"
        image = str(item.get("image") or "").strip()
        image_alt = str(item.get("imageAlt") or "").strip()
        pick: dict[str, str] = {
            "kind": kind,
            "kindLabel": kind_label,
            "title": title,
            "description": description,
            "href": href,
            "cta": cta,
        }
        if image:
            pick["image"] = image
        if image_alt:
            pick["imageAlt"] = image_alt
        items.append(pick)
    if not items:
        return None
    leads_by_hub_raw = raw.get("leadsByHub")
    leads_by_hub: dict[str, str] = {}
    if isinstance(leads_by_hub_raw, dict):
        for key, value in leads_by_hub_raw.items():
            text = str(value or "").strip()
            if text:
                leads_by_hub[str(key)] = text
    return {
        "title": str(raw.get("title") or "おすすめの講座・教材").strip() or "おすすめの講座・教材",
        "lead": str(raw.get("lead") or "").strip(),
        "leadsByHub": leads_by_hub,
        "layout": layout,
        "items": items,
    }


def paid_mock_exam() -> dict[str, str] | None:
    raw = CONFIG.get("paidMockExam")
    if not isinstance(raw, dict):
        return None
    url = str(raw.get("url") or "").strip()
    if not url:
        return None
    out: dict[str, str] = {"url": url}
    for key in (
        "modeTitle",
        "modePurpose",
        "priceLabel",
        "scoreMeta",
        "scoreLead",
    ):
        val = raw.get(key)
        if val is not None and str(val).strip():
            out[key] = str(val).strip()
    return out


def write_site_config_js() -> None:
    payload = {
        "brandName": brand_name(),
        "brandMark": brand_mark(),
        "examName": exam_name(),
        "siteOrigin": clean_origin(),
        "contactUrl": contact_url(),
        "ga4MeasurementId": ga4_measurement_id(),
        "theme": theme(),
        "navigation": {
            "header": [
                {"label": label, "href": href, "key": key}
                for label, href, key in navigation_items("header")
            ],
            "footer": [
                {"label": label, "href": href, "key": key}
                for label, href, key in navigation_items("footer")
            ],
        },
        "fields": [
            {
                "id": str(f["id"]),
                "name": str(f.get("name") or f["id"]),
                "aliases": [str(a) for a in (f.get("aliases") or [])],
                "legacyGlossaryCat": str(f.get("legacyGlossaryCat") or f["id"]),
            }
            for f in fields()
        ],
    }
    pm = paid_mock_exam()
    if pm:
        payload["paidMockExam"] = pm
    (ROOT / "site-config.js").write_text(
        "window.SITE_CONFIG = "
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + ";\n",
        encoding="utf-8",
    )


def write_crawler_files() -> None:
    origin = clean_origin()
    host = origin.replace("https://", "").replace("http://", "").strip("/")
    (ROOT / "CNAME").write_text(host + "\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n\n"
        f"Sitemap: {origin}/sitemap.xml\n",
        encoding="utf-8",
    )


def sync_config_files() -> None:
    write_site_config_js()
    write_site_theme_css()
    write_crawler_files()


if __name__ == "__main__":
    sync_config_files()
    print("Synced site-config.js, CNAME, robots.txt from site-config.json")
