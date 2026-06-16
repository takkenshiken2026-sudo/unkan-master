#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Load affiliate article brief YAML (data/affiliate-briefs/{slug}.yaml)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML が必要です: pip install pyyaml") from exc

ROOT = Path(__file__).resolve().parents[1]
BRIEFS_DIR = ROOT / "data" / "affiliate-briefs"
IMAGES_DIR = ROOT / "images" / "affiliate"


def norm(value: str | None) -> str:
    return (value or "").strip()


def load_affiliate_brief(slug: str, *, root: Path | None = None) -> dict[str, Any] | None:
    base = root or ROOT
    path = base / "data" / "affiliate-briefs" / f"{slug}.yaml"
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    return data


def _product_rank_key(product: dict[str, Any]) -> tuple[int, int | str]:
    raw = product.get("rank")
    if raw is None or raw == "":
        return (1, 999)
    try:
        return (0, int(raw))
    except (TypeError, ValueError):
        return (0, str(raw))


def brief_products(brief: dict[str, Any]) -> list[dict[str, Any]]:
    products = brief.get("products") or []
    if not isinstance(products, list):
        return []
    out: list[dict[str, Any]] = []
    for item in products:
        if isinstance(item, dict) and norm(str(item.get("name") or "")):
            out.append(item)
    return sorted(out, key=_product_rank_key)


def brief_has_product_comparison(brief: dict[str, Any] | None) -> bool:
    if not brief:
        return False
    layout = norm(str(brief.get("layout") or ""))
    if layout != "product-comparison":
        return False
    return bool(brief_products(brief))


def brief_comparison_kind(brief: dict[str, Any] | None) -> str:
    """books | courses — 比較表・見出し・CTA の既定値。"""
    if not brief:
        return "books"
    kind = norm(str(brief.get("comparison_kind") or "")).lower()
    if kind in ("course", "courses", "lecture", "lectures", "講座"):
        return "courses"
    return "books"


def product_offer_type(product: dict[str, Any], brief: dict[str, Any] | None = None) -> str:
    """book | course。商品ごとに offer_type があれば優先。"""
    raw = norm(str(product.get("offer_type") or "")).lower()
    if raw in ("book", "books", "textbook", "material"):
        return "book"
    if raw in ("course", "courses", "lecture", "school"):
        return "course"
    if brief_comparison_kind(brief) == "courses":
        return "course"
    return "book"


def product_affiliate_url(product: dict[str, Any]) -> str:
    for key in ("amazon_url", "affiliate_url", "a8_url", "afb_url", "url"):
        url = norm(str(product.get(key) or ""))
        if url:
            from tools.affiliate_links import is_trackable_asp_url

            if is_trackable_asp_url(url):
                return url
    return ""


def brief_link_config(brief: dict[str, Any]) -> dict[str, Any]:
    """Shape brief for affiliate_links helpers (related / asp keys)."""
    related = brief.get("related_links") or brief.get("related") or []
    if isinstance(related, list):
        related_str = ";".join(norm(str(x)) for x in related if norm(str(x)))
    else:
        related_str = norm(str(related))
    return {
        **brief,
        "related": related_str,
        "asp": norm(str(brief.get("asp_primary") or brief.get("asp") or "")),
    }
