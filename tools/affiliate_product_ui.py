#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Affiliate offer comparison UI: books, courses, and mixed product cards."""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from tools.affiliate_brief import (
    brief_comparison_kind,
    brief_products,
    norm,
    product_affiliate_url,
    product_offer_type,
)
from tools.affiliate_links import is_affiliate_url

EXTERNAL_REL = "nofollow sponsored noopener noreferrer"


def format_yen(value: object) -> str:
    if value is None or value == "":
        return ""
    text = norm(str(value)).replace(",", "").replace("¥", "").replace("円", "")
    if not text:
        return ""
    try:
        amount = int(float(text))
    except ValueError:
        return norm(str(value))
    return f"¥{amount:,}"


def product_highlights(product: dict[str, Any], limit: int = 3) -> list[str]:
    raw = product.get("highlights")
    if isinstance(raw, list):
        return [norm(str(x)) for x in raw if norm(str(x))][:limit]
    if isinstance(raw, str):
        return [norm(x) for x in re.split(r"[;\n]", raw) if norm(x)][:limit]
    for_who = norm(str(product.get("for_who") or ""))
    return [for_who] if for_who else []


def price_display(product: dict[str, Any], offer_type: str) -> str:
    label = norm(str(product.get("price_label") or ""))
    if label:
        return label
    yen = format_yen(product.get("price_yen"))
    if not yen:
        return ""
    if offer_type == "course":
        billing = norm(str(product.get("billing_type") or ""))
        if billing in ("monthly", "月額"):
            return f"月額 {yen}"
        if billing in ("lump", "lump_sum", "買い切り", "一括"):
            return f"{yen}（一括）"
    return yen


def cta_label(offer_type: str) -> str:
    if offer_type == "course":
        return "公式サイトで詳細・料金を見る"
    return "Amazonで詳細・価格を見る"


def image_href(rel_path: Path, image_file: str, *, site_root: Path) -> str | None:
    name = norm(image_file)
    if not name:
        return None
    local = site_root / "images" / "affiliate" / name
    if local.is_file():
        depth = len(rel_path.parent.parts)
        prefix = "/".join([".."] * depth) + "/" if depth else ""
        return f"{prefix}images/affiliate/{html.escape(name, quote=True)}"
    image_url = norm(str(image_file))
    if image_url.lower().startswith(("http://", "https://")):
        return image_url
    return None


def cover_html(
    product: dict[str, Any],
    rel_path: Path,
    *,
    site_root: Path,
    brief: dict[str, Any] | None = None,
) -> str:
    offer_type = product_offer_type(product, brief)
    name = norm(str(product.get("name") or ""))
    brand = norm(
        str(
            product.get("provider")
            or product.get("publisher")
            or product.get("brand")
            or ("講座提供元" if offer_type == "course" else "出版社")
        )
    )
    edition = norm(str(product.get("edition") or product.get("plan_name") or ""))
    image_file = norm(str(product.get("image_file") or ""))
    src = image_href(rel_path, image_file, site_root=site_root)
    course_cls = " affiliate-product-cover--course" if offer_type == "course" else ""
    alt = html.escape(f"{name} {'公式イメージ' if offer_type == 'course' else '表紙'}")
    img_dims = ('width="320" height="180"' if offer_type == "course" else 'width="320" height="448"')
    if src:
        return (
            f'<div class="affiliate-product-cover affiliate-product-cover--photo{course_cls}">'
            f'<img src="{html.escape(src)}" alt="{alt}" {img_dims} loading="lazy" decoding="async">'
            f"</div>"
        )
    ed_html = f'<span class="affiliate-product-cover-edition">{html.escape(edition)}</span>' if edition else ""
    default_title = "講座" if offer_type == "course" else "テキスト"
    return (
        f'<div class="affiliate-product-cover affiliate-product-cover--placeholder{course_cls}" aria-hidden="true">'
        f'<span class="affiliate-product-cover-publisher">{html.escape(brand)}</span>'
        f'<span class="affiliate-product-cover-title">{html.escape(name or default_title)}</span>'
        f"{ed_html}"
        "</div>"
    )


def cta_link(url: str, label: str, *, css_class: str = "affiliate-product-cta") -> str:
    if not is_affiliate_url(url):
        return ""
    return (
        f'<a class="{css_class}" href="{html.escape(url)}" target="_blank" rel="{EXTERNAL_REL}">'
        f"{html.escape(label)}</a>"
    )


def product_name_link_html(product: dict[str, Any]) -> str:
    """比較表・要点表紙ラベル用：ASP リンク付き商品名（黒テキスト）。"""
    name = norm(str(product.get("name") or ""))
    if not name:
        return "—"
    url = product_affiliate_url(product)
    if is_affiliate_url(url):
        return (
            f'<a class="affiliate-compare-name-link" href="{html.escape(url)}" '
            f'target="_blank" rel="{EXTERNAL_REL}">{html.escape(name)}</a>'
        )
    return html.escape(name)


def meta_line(product: dict[str, Any], *, brief: dict[str, Any] | None = None) -> str:
    offer_type = product_offer_type(product, brief)
    parts: list[str] = []
    price = price_display(product, offer_type)
    if price:
        parts.append(f"<strong>{html.escape(price)}</strong>")
        note = norm(str(product.get("price_note") or ""))
        if note and offer_type != "book":
            parts.append(f'<span class="affiliate-product-price-note">{html.escape(note)}</span>')
    if offer_type == "course":
        duration = norm(str(product.get("duration") or product.get("study_period") or ""))
        if duration:
            parts.append(html.escape(duration))
        hours = norm(str(product.get("lecture_hours") or ""))
        if hours:
            hours_text = hours if "時間" in hours else f"{hours}時間"
            parts.append(html.escape(hours_text))
        support = norm(str(product.get("support") or ""))
        if support:
            parts.append(html.escape(support))
    if not parts:
        return ""
    return f'<p class="affiliate-product-meta">{" · ".join(parts)}</p>'


def supplement_html(product: dict[str, Any]) -> str:
    """書籍: 問題集 / 講座: 無料体験・特典など。"""
    offer_type = product_offer_type(product)
    if offer_type == "book":
        workbook = norm(str(product.get("workbook_name") or ""))
        workbook_url = norm(str(product.get("workbook_amazon_url") or ""))
        if workbook and is_affiliate_url(workbook_url):
            return (
                f'<p class="affiliate-product-supplement">'
                f"セット問題集: {html.escape(workbook)} "
                f'{cta_link(workbook_url, "問題集を見る", css_class="affiliate-product-supplement-link")}'
                f"</p>"
            )
        return ""
    trial = norm(str(product.get("trial_label") or ""))
    trial_url = norm(str(product.get("trial_url") or product.get("affiliate_url") or ""))
    if trial and is_affiliate_url(trial_url):
        return (
            f'<p class="affiliate-product-supplement">'
            f"{html.escape(trial)} "
            f'{cta_link(trial_url, "体験・詳細を見る", css_class="affiliate-product-supplement-link")}'
            f"</p>"
        )
    return ""


def product_card_html(
    product: dict[str, Any],
    rel_path: Path,
    *,
    site_root: Path,
    brief: dict[str, Any] | None = None,
) -> str:
    offer_type = product_offer_type(product, brief)
    rank = product.get("rank", "")
    try:
        rank_num = int(rank)
    except (TypeError, ValueError):
        rank_num = 0
    rank_label = f"{rank_num}位" if rank_num else ""
    name = norm(str(product.get("name") or ""))
    url = product_affiliate_url(product)
    highlights = product_highlights(product)
    hl_html = ""
    if highlights:
        items = "".join(f"<li>{html.escape(x)}</li>" for x in highlights)
        hl_html = f'<ul class="affiliate-product-highlights">{items}</ul>'
    cta = cta_label(offer_type)
    body = (
        f'<div class="affiliate-product-card-rank">{html.escape(rank_label)}</div>'
        f"{cover_html(product, rel_path, site_root=site_root, brief=brief)}"
        f'<div class="affiliate-product-card-body">'
        f"<h3>{html.escape(name)}</h3>"
        f"{meta_line(product, brief=brief)}"
        f"{hl_html}"
        f'<span class="affiliate-product-cta">{html.escape(cta)}</span>'
        f"</div>"
    )
    aria = f'{name} を{"公式サイト" if offer_type == "course" else "Amazon"}で見る'
    if is_affiliate_url(url):
        hit = (
            f'<a class="affiliate-product-card-hit" href="{html.escape(url)}" target="_blank" '
            f'rel="{EXTERNAL_REL}" aria-label="{html.escape(aria)}">'
            f"{body}</a>"
        )
    else:
        hit = f'<div class="affiliate-product-card-hit affiliate-product-card-hit--static">{body}</div>'
    return (
        f'<article class="affiliate-product-card affiliate-product-card--{offer_type}" '
        f'id="affiliate-product-r{rank_num}">'
        f"{hit}{supplement_html(product)}</article>"
    )


def comparison_table_html(brief: dict[str, Any], products: list[dict[str, Any]]) -> str:
    if len(products) < 2:
        return ""
    kind = brief_comparison_kind(brief)
    if kind == "courses":
        headers = ["順位", "講座名", "料金（参考）", "学習期間", "向いている人"]
        label = "講座比較表"
    else:
        headers = ["順位", "商品名", "価格（税込参考）", "ページ数", "向いている人"]
        label = "教材比較表"
    rows: list[str] = []
    for product in products:
        offer_type = product_offer_type(product, brief)
        rank = norm(str(product.get("rank") or ""))
        price = price_display(product, offer_type) or "—"
        if kind == "courses":
            spec = norm(str(product.get("duration") or product.get("study_period") or "")) or "—"
        else:
            spec = norm(str(product.get("pages") or "")) or "—"
        for_who = norm(str(product.get("for_who") or "")) or "—"
        name_cell = product_name_link_html(product)
        rows.append(
            "<tr>"
            f'<th scope="row">{html.escape(rank)}</th>'
            f"<td>{name_cell}</td>"
            f"<td>{html.escape(price)}</td>"
            f"<td>{html.escape(spec)}</td>"
            f"<td>{html.escape(for_who)}</td>"
            "</tr>"
        )
    head = "".join(f'<th scope="col">{html.escape(h)}</th>' for h in headers)
    body = "".join(rows)
    return (
        f'<div class="affiliate-compare-table-wrap" aria-label="{html.escape(label)}">'
        '<table class="affiliate-compare-table">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )


def hub_title(brief: dict[str, Any]) -> str:
    custom = norm(str(brief.get("comparison_title") or ""))
    if custom:
        return custom
    n = len(brief_products(brief))
    if brief_comparison_kind(brief) == "courses":
        return f"おすすめ講座{n}選（比較）" if n else "おすすめ講座比較"
    return f"おすすめテキスト{n}選（比較）" if n else "おすすめ教材比較"


def default_price_disclaimer(brief: dict[str, Any]) -> str:
    custom = norm(str(brief.get("price_disclaimer") or ""))
    if custom:
        return custom
    if brief_comparison_kind(brief) == "courses":
        return (
            "料金・キャンペーン・受講期間は執筆時点の公式参考です。"
            "申込前に必ず各講座の公式ページで最新条件を確認してください。"
        )
    return (
        "価格・在庫・版情報は執筆時点のAmazon参考です。"
        "購入前に必ず販売ページでご確認ください。"
    )


def affiliate_product_hub_html(
    brief: dict[str, Any],
    rel_path: Path,
    *,
    site_root: Path,
) -> str:
    products = brief_products(brief)
    if not products:
        return ""
    title = hub_title(brief)
    cards = "".join(
        product_card_html(product, rel_path, site_root=site_root, brief=brief)
        for product in products
    )
    table = comparison_table_html(brief, products)
    return (
        '<section class="seo-article-section affiliate-product-hub" '
        f'data-comparison-kind="{html.escape(brief_comparison_kind(brief), quote=True)}" '
        'id="affiliate-products" aria-labelledby="affiliate-products-title">'
        f'<h2 id="affiliate-products-title">{html.escape(title)}</h2>'
        f'<p class="affiliate-price-disclaimer">{html.escape(default_price_disclaimer(brief))}</p>'
        f"{table}"
        f'<div class="affiliate-product-grid" data-product-count="{len(products)}">{cards}</div>'
        "</section>"
    )


def affiliate_hub_toc_item(brief: dict[str, Any] | None) -> tuple[str, str] | None:
    if not brief or not brief_has_product_comparison_ui(brief):
        return None
    return ("affiliate-products", hub_title(brief))


def key_points_aside_cover_html(
    product: dict[str, Any],
    rel_path: Path,
    *,
    site_root: Path,
    brief: dict[str, Any] | None = None,
) -> str:
    """要点ボックス右端用：1位商品の表紙のみ。"""
    offer_type = product_offer_type(product, brief)
    name = norm(str(product.get("name") or ""))
    image_file = norm(str(product.get("image_file") or ""))
    src = image_href(rel_path, image_file, site_root=site_root)
    course_cls = " seo-key-points-aside-cover--course" if offer_type == "course" else ""
    alt = html.escape(f"{name} {'公式イメージ' if offer_type == 'course' else '表紙'}")
    if src:
        aside_dims = ('width="88" height="50"' if offer_type == "course" else 'width="88" height="124"')
        inner = (
            f'<img src="{html.escape(src)}" alt="{alt}" {aside_dims} '
            f'loading="lazy" decoding="async">'
        )
    else:
        brand = norm(
            str(
                product.get("provider")
                or product.get("publisher")
                or product.get("brand")
                or ("講座" if offer_type == "course" else "書籍")
            )
        )
        short = html.escape(name[:16] + ("…" if len(name) > 16 else ""))
        inner = (
            f'<span class="seo-key-points-aside-placeholder-brand">{html.escape(brand[:10])}</span>'
            f'<span class="seo-key-points-aside-placeholder-title">{short}</span>'
        )
        course_cls += " seo-key-points-aside-cover--placeholder"
    url = product_affiliate_url(product)
    cover = f'<span class="seo-key-points-aside-cover{course_cls}">{inner}</span>'
    label_html = ""
    if name:
        label_html = f'<span class="seo-key-points-aside-label">{html.escape(name)}</span>'
    stack = f'<span class="seo-key-points-aside-stack">{cover}{label_html}</span>'
    if is_affiliate_url(url):
        return (
            f'<a class="seo-key-points-aside-link" href="{html.escape(url)}" '
            f'target="_blank" rel="{EXTERNAL_REL}">{stack}</a>'
        )
    return stack


def affiliate_key_points_box_html(
    *,
    intro: str,
    items: list[str],
    highlight_product: dict[str, Any] | None,
    rel_path: Path,
    site_root: Path,
    brief: dict[str, Any] | None = None,
    article: dict[str, str] | None = None,
    title: str = "この記事の要点",
    heading_id: str = "key-points-title",
) -> str:
    """商品比較アフィリエイト記事向け：要点はテキストリスト、右端に代表表紙1枚。"""
    intro_text = intro.strip()
    cleaned_items = [item.strip() for item in items if item and item.strip()]
    if article:
        from tools.affiliate_body_links import affiliate_name_labels, wrap_affiliate_names_in_quotes

        name_labels = affiliate_name_labels(brief, article)
        cleaned_items = [wrap_affiliate_names_in_quotes(item, name_labels) for item in cleaned_items]
    if not cleaned_items and not intro_text and not highlight_product:
        return ""

    intro_html = f"<p>{html.escape(intro_text)}</p>" if intro_text else ""
    list_html = ""
    if cleaned_items:
        lis = "".join(f"<li>{html.escape(item)}</li>" for item in cleaned_items[:5])
        list_html = f'<ul class="seo-key-points-list">{lis}</ul>'

    aside_html = ""
    if highlight_product:
        cover = key_points_aside_cover_html(
            highlight_product, rel_path, site_root=site_root, brief=brief
        )
        aside_html = f'<aside class="seo-key-points-aside" aria-label="代表商品">{cover}</aside>'

    body_html = (
        f'<div class="seo-key-points-body">{aside_html}'
        f'<div class="seo-key-points-main">{intro_html}{list_html}</div></div>'
    )
    modifier = " seo-key-points-box--affiliate" if highlight_product else ""
    return (
        f'<section class="seo-key-points-box{modifier}" aria-labelledby="{html.escape(heading_id)}">'
        f'<h2 id="{html.escape(heading_id)}">{html.escape(title)}</h2>'
        f"{body_html}"
        "</section>"
    )


def brief_has_product_comparison_ui(brief: dict[str, Any] | None) -> bool:
    from tools.affiliate_brief import brief_has_product_comparison

    return brief_has_product_comparison(brief)
