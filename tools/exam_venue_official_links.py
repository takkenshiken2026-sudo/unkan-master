#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験会場ガイド向けの公式会場案内 URL（JISSH センター・各試験の公式ハブ）。"""

from __future__ import annotations

import json
from pathlib import Path

JISSH_TOP = ("安全衛生技術試験協会（公式）", "https://www.jissh.or.jp/")
EXAM_PORTAL = ("安全衛生技術試験協会 試験案内（公式）", "https://www.exam.or.jp/")
JISSH_VENUE_HUB = ("安全衛生技術試験協会 試験実施場所（公式）", "https://www.exam.or.jp/h_aramashi/")

# slug -> (リンクラベル, センター公式ページ URL)
CENTER_PAGES: dict[str, tuple[str, str]] = {
    "hokkaido-center": ("北海道安全衛生技術センター（公式・会場案内）", "https://www.exam.or.jp/center_hokkaido/"),
    "tohoku-center": ("東北安全衛生技術センター（公式・会場案内）", "https://www.exam.or.jp/center_tohoku/"),
    "kanto-center": ("関東安全衛生技術センター（公式・会場案内）", "https://www.exam.or.jp/center_kanto/"),
    "chubu-center": ("中部安全衛生技術センター（公式・会場案内）", "https://www.exam.or.jp/center_chubu/"),
    "kinki-center": ("近畿安全衛生技術センター（公式・会場案内）", "https://www.exam.or.jp/center_kinki/"),
    "chushikoku-center": ("中国四国安全衛生技術センター（公式・会場案内）", "https://www.exam.or.jp/center_chushi/"),
    "kyushu-center": ("九州安全衛生技術センター（公式・会場案内）", "https://www.exam.or.jp/center_kyushu/"),
}

CENTER_REGION: dict[str, str] = {
    "hokkaido-center": "北海道",
    "tohoku-center": "東北",
    "kanto-center": "関東",
    "chubu-center": "中部",
    "kinki-center": "近畿",
    "chushikoku-center": "中国・四国",
    "kyushu-center": "九州",
}

HUB_SLUGS = frozenset({"exam-venue-and-region", "shiken-kaijo"})

JISSH_EXAM_KEYWORDS = ("第二種衛生", "第一種衛生", "ボイラー", "衛生管理者")


def md_link(label: str, url: str) -> str:
    return f"[{label}]({url})"


def is_exam_center_slug(slug: str) -> bool:
    return slug.endswith("-center") and slug in CENTER_PAGES


def is_venue_guide_slug(slug: str) -> bool:
    if is_exam_center_slug(slug):
        return True
    if slug in HUB_SLUGS:
        return True
    return slug.startswith("exam-venue")


def venue_page_for_slug(slug: str) -> tuple[str, str] | None:
    return CENTER_PAGES.get(slug)


def region_for_slug(slug: str) -> str:
    return CENTER_REGION.get(slug, "該当地域")


def load_site_external_links(site_root: Path) -> list[tuple[str, str]]:
    cfg_path = site_root / "site-config.json"
    if not cfg_path.is_file():
        return []
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    out: list[tuple[str, str]] = []
    for item in cfg.get("externalLinks") or []:
        url = str(item.get("url") or "").strip()
        label = str(item.get("label") or url).strip()
        if url.startswith(("http://", "https://")):
            out.append((label, url))
    return out


def is_jissh_exam_site(site_root: Path) -> bool:
    cfg_path = site_root / "site-config.json"
    if not cfg_path.is_file():
        return False
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    exam = str(cfg.get("examName") or "")
    org = str(cfg.get("officialOrganization") or "")
    blob = exam + org
    return any(k in blob for k in JISSH_EXAM_KEYWORDS) or "安全衛生技術試験協会" in org


def primary_official_link(site_root: Path) -> tuple[str, str]:
    links = load_site_external_links(site_root)
    if links:
        return links[0]
    if is_jissh_exam_site(site_root):
        return EXAM_PORTAL
    return ("公式サイト", "https://www.example.com/")


def venue_official_md(site_root: Path) -> str:
    if is_jissh_exam_site(site_root):
        return md_link(*EXAM_PORTAL)
    label, url = primary_official_link(site_root)
    return md_link(label, url)


def primary_sources_for_venue(slug: str, site_root: Path | None = None) -> str:
    parts: list[str] = []
    if site_root and is_jissh_exam_site(site_root):
        parts.append(f"{JISSH_TOP[0]}|{JISSH_TOP[1]}")
        parts.append(f"{EXAM_PORTAL[0]}|{EXAM_PORTAL[1]}")
    elif site_root:
        for label, url in load_site_external_links(site_root)[:2]:
            parts.append(f"{label}|{url}")
    page = venue_page_for_slug(slug)
    if page:
        parts.append(f"{page[0]}|{page[1]}")
    if not parts and site_root:
        label, url = primary_official_link(site_root)
        parts.append(f"{label}|{url}")
    return ";".join(parts)


def primary_sources_for_hub(slug: str, site_root: Path) -> str:
    parts: list[str] = []
    if is_jissh_exam_site(site_root):
        parts.extend(
            [
                f"{JISSH_TOP[0]}|{JISSH_TOP[1]}",
                f"{EXAM_PORTAL[0]}|{EXAM_PORTAL[1]}",
                f"{JISSH_VENUE_HUB[0]}|{JISSH_VENUE_HUB[1]}",
            ]
        )
    else:
        for label, url in load_site_external_links(site_root)[:3]:
            parts.append(f"{label}|{url}")
    if slug == "shiken-kaijo":
        for label, url in CENTER_PAGES.values():
            parts.append(f"{label}|{url}")
    if not parts:
        label, url = primary_official_link(site_root)
        parts.append(f"{label}|{url}")
    # 重複 URL を除く
    seen: set[str] = set()
    uniq: list[str] = []
    for item in parts:
        url = item.split("|", 1)[-1]
        if url in seen:
            continue
        seen.add(url)
        uniq.append(item)
    return ";".join(uniq)


def primary_sources_for_slug(slug: str, site_root: Path) -> str:
    if is_exam_center_slug(slug):
        return primary_sources_for_venue(slug, site_root)
    if slug in HUB_SLUGS or slug.startswith("exam-venue"):
        return primary_sources_for_hub(slug, site_root)
    return primary_sources_for_venue(slug, site_root)


def official_page_md_for_exam(exam: str, official_label: str) -> str:
    """guide lib 内から exam 名だけで公式会場ページの Markdown リンクを返す。"""
    blob = (exam or "") + (official_label or "")
    if any(k in blob for k in JISSH_EXAM_KEYWORDS) or "安全衛生技術試験協会" in blob:
        return md_link(*EXAM_PORTAL)
    return ""
