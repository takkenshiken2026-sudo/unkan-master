#!/usr/bin/env python3
"""試験ガイド・用語・過去問一覧などに共通のおすすめ講座・教材カード HTML。"""

from __future__ import annotations

import html
import re
from pathlib import Path

from tools.site_config import brand_name, exam_name, guide_index_picks

GUIDE_INDEX_PICK_LAYOUTS = frozenset({"grid-3", "grid-2", "strip", "compact", "text"})


def apply_vars(value: str) -> str:
    text = (value or "").strip()
    return (
        text.replace("Sampleマスター", brand_name())
        .replace("◯◯試験（プレースホルダー）", exam_name())
        .replace("◯◯試験", exam_name())
    )


def guide_index_pick_href(href: str, rel_path: Path) -> str:
    raw = (href or "").strip()
    if not raw:
        return ""
    if raw.startswith(("http://", "https://", "/")):
        return raw
    if raw.startswith("../"):
        return raw
    hub = rel_path.parent.name if rel_path.parent != Path(".") else ""
    if hub == "articles":
        return raw.lstrip("/")
    article_href = raw.lstrip("/")
    if not article_href.startswith("articles/"):
        article_href = f"articles/{article_href}"
    return f"../{article_href}"


def guide_index_pick_image_src(image: str, rel_path: Path) -> str:
    raw = (image or "").strip()
    if not raw:
        return ""
    if raw.startswith(("http://", "https://", "/")):
        return raw
    if raw.startswith("../"):
        return raw
    depth = len(rel_path.parent.parts)
    prefix = "/".join([".."] * depth) + "/" if depth else ""
    return f"{prefix}{raw.lstrip('/')}"


def _link_attrs(href: str) -> tuple[str, str]:
    external = href.startswith("http://") or href.startswith("https://")
    rel_attr = ' rel="noopener noreferrer"' if external else ""
    target_attr = ' target="_blank"' if external else ""
    return target_attr, rel_attr


def build_guide_index_pick_image_html(
    item: dict[str, str],
    *,
    title: str,
    rel_path: Path,
    layout: str,
) -> str:
    image = (item.get("image") or "").strip()
    if not image or layout == "text":
        return ""
    src = guide_index_pick_image_src(image, rel_path)
    alt = (item.get("imageAlt") or title or "おすすめ教材").strip()
    kind = (item.get("kind") or "textbook").strip()
    media_kind = "course" if kind == "course" else "book"
    bleed_cls = " hub-promo-card__media--bleed" if layout in {"grid-3", "grid-2", "compact"} else ""
    if media_kind == "course":
        size_attrs = 'width="320" height="180"'
    else:
        size_attrs = 'width="160" height="220"'
    return (
        f'<div class="hub-promo-card__media hub-promo-card__media--{media_kind}'
        f' article-index-pick-media article-index-pick-media--{media_kind}{bleed_cls}">'
        f'<img src="{html.escape(src, quote=True)}" alt="{html.escape(alt)}" '
        f'{size_attrs} loading="lazy" decoding="async">'
        f"</div>"
    )


def _card_body(
    *,
    title: str,
    description: str,
    kind_label: str,
    cta: str,
    layout: str,
) -> str:
    desc_html = ""
    if description and layout not in {"compact"}:
        desc_html = f'<p class="hub-promo-card__desc article-index-pick-desc">{html.escape(description)}</p>'
    elif description and layout == "compact":
        desc_html = (
            f'<p class="hub-promo-card__desc hub-promo-card__desc--compact article-index-pick-desc">'
            f"{html.escape(description)}</p>"
        )
    cta_class = "hub-promo-card__cta article-index-pick-cta"
    if layout == "text":
        cta_class += " hub-promo-card__cta--text"
    foot = (
        '<div class="hub-promo-card__foot article-index-pick-foot">'
        f'<span class="{cta_class}">{cta}</span>'
        f'<span class="hub-promo-card__kind article-index-pick-kind">{kind_label}</span>'
        "</div>"
    )
    if layout == "strip":
        return (
            '<div class="hub-promo-card__body">'
            f'<span class="hub-promo-card__kind hub-promo-card__kind--strip article-index-pick-kind">{kind_label}</span>'
            f"<h3>{html.escape(title)}</h3>"
            f"{desc_html}"
            f'<span class="{cta_class}">{cta}</span>'
            "</div>"
        )
    return (
        '<div class="hub-promo-card__body">'
        f"<h3>{html.escape(title)}</h3>"
        f"{desc_html}"
        f"{foot}"
        "</div>"
    )


def build_guide_index_pick_card_html(
    item: dict[str, str],
    *,
    rel_path: Path,
    layout: str,
) -> str:
    href = guide_index_pick_href(apply_vars(item["href"]), rel_path)
    title = apply_vars(item["title"])
    description = apply_vars(item.get("description") or "")
    kind = html.escape(item.get("kind") or "textbook", quote=True)
    kind_label = html.escape(apply_vars(item.get("kindLabel") or "教材"))
    cta = html.escape(apply_vars(item.get("cta") or "記事を読む"))
    target_attr, rel_attr = _link_attrs(href)
    image_html = build_guide_index_pick_image_html(item, title=title, rel_path=rel_path, layout=layout)
    link_extra = ""
    if layout == "strip":
        link_extra = " hub-promo-card__link--strip"
    elif layout == "text":
        link_extra = " hub-promo-card__link--text"
    elif layout == "compact":
        link_extra = " hub-promo-card__link--compact"
    body_html = _card_body(
        title=title,
        description=description,
        kind_label=kind_label,
        cta=cta,
        layout=layout,
    )
    inner = image_html + body_html
    if layout in {"grid-3", "grid-2", "compact"} and image_html:
        return (
            f'<article class="hub-promo-card article-index-pick" data-pick-kind="{kind}">'
            f'<a class="hub-promo-card__link article-index-pick-link{link_extra}" '
            f'href="{html.escape(href, quote=True)}"{target_attr}{rel_attr}>'
            f"{inner}"
            f"</a></article>"
        )
    return (
        f'<article class="hub-promo-card article-index-pick" data-pick-kind="{kind}">'
        f'<a class="hub-promo-card__link article-index-pick-link{link_extra}" '
        f'href="{html.escape(href, quote=True)}"{target_attr}{rel_attr}>'
        f"{inner}"
        f"</a></article>"
    )


def normalize_guide_index_pick_layout(layout: str) -> str:
    key = re.sub(r"[^a-z0-9-]", "", (layout or "grid-3").strip().lower())
    return key if key in GUIDE_INDEX_PICK_LAYOUTS else "grid-3"


def build_guide_index_picks_html(rel_path: Path) -> str:
    picks = guide_index_picks()
    if not picks:
        return ""
    layout = normalize_guide_index_pick_layout(str(picks.get("layout") or "grid-3"))
    items = picks["items"]
    cards = [
        build_guide_index_pick_card_html(item, rel_path=rel_path, layout=layout)
        for item in items
    ]
    hub = rel_path.parent.name if rel_path.parent != Path(".") else ""
    leads_by_hub = picks.get("leadsByHub") or {}
    lead = ""
    if isinstance(leads_by_hub, dict) and hub in leads_by_hub:
        lead = str(leads_by_hub.get(hub) or "").strip()
    if not lead:
        lead = str(picks.get("lead") or "").strip()
    lead = apply_vars(lead)
    lead_html = f'<p class="hub-promo__lead">{html.escape(lead)}</p>' if lead else ""
    return (
        f'<section class="hub-promo hub-promo--{html.escape(layout, quote=True)} article-index-picks" '
        'aria-labelledby="article-index-picks-heading">'
        '<div class="hub-promo__head article-index-picks-head">'
        f'<h2 id="article-index-picks-heading">{html.escape(apply_vars(picks["title"]))}</h2>'
        f"{lead_html}"
        "</div>"
        f'<div class="hub-promo__grid article-index-picks-grid">{"".join(cards)}</div>'
        "</section>"
    )
