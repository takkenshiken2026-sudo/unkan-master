#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Download product images (Amazon covers or course LP og:image) into images/affiliate/."""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML が必要です: pip install pyyaml") from exc

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.affiliate_brief import BRIEFS_DIR, IMAGES_DIR, brief_products, load_affiliate_brief, norm  # noqa: E402

ASIN_RE = re.compile(r"(?:/dp/|/gp/product/|/gp/aw/d/|asin=)([A-Z0-9]{10})", re.I)
OG_IMAGE_RE = re.compile(
    r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
    re.I,
)
AMAZON_PLACEHOLDER_IDS = ("01MKUOLsA5L",)
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def extract_asin(value: str) -> str | None:
    text = norm(value)
    if not text:
        return None
    if re.fullmatch(r"[A-Z0-9]{10}", text, re.I):
        return text.upper()
    match = ASIN_RE.search(text)
    return match.group(1).upper() if match else None


def product_source_url(product: dict) -> str:
    for key in ("amazon_url", "affiliate_url", "url", "asin"):
        raw = norm(str(product.get(key) or ""))
        if not raw:
            continue
        asin = extract_asin(raw)
        if asin:
            return f"https://www.amazon.co.jp/dp/{asin}"
        if raw.lower().startswith(("http://", "https://")):
            return raw
    return ""


def _amazon_image_ok(url: str) -> bool:
    text = norm(url)
    if not text or "media-amazon.com" not in text:
        return False
    if text.lower().endswith(".gif"):
        return False
    return not any(token in text for token in AMAZON_PLACEHOLDER_IDS)


def _amazon_hi_res_url(url: str) -> str:
    base = re.sub(r"\._[^.]+\.(jpg|jpeg|webp)$", "", url, flags=re.I)
    if base.endswith((".jpg", ".jpeg", ".webp")):
        return base
    return f"{base}._SL1500_.jpg"


def fetch_amazon_cover_url(product_url: str) -> str | None:
    req = urllib.request.Request(
        product_url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "ja-JP,ja;q=0.9"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    for pattern in (
        r'"landingImageUrl":"(https://[^"]+)"',
        r'"hiRes":"(https://[^"]+)"',
        r'"large":"(https://[^"]+)"',
        r'id="landingImage"[^>]+src="(https://[^"]+)"',
    ):
        match = re.search(pattern, html)
        if not match:
            continue
        url = norm(match.group(1).replace("\\u0026", "&"))
        if _amazon_image_ok(url):
            return _amazon_hi_res_url(url)
    for url in re.findall(
        r"https://m\.media-amazon\.com/images/I/[A-Za-z0-9+._-]+\.(?:jpg|jpeg|webp)",
        html,
        re.I,
    ):
        if _amazon_image_ok(url):
            return _amazon_hi_res_url(url)
    return None


def fetch_og_image_url(product_url: str) -> str | None:
    req = urllib.request.Request(product_url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    match = OG_IMAGE_RE.search(html)
    url = norm(match.group(1)) if match else None
    if url and _amazon_image_ok(url):
        return url
    return None


def download_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def save_as_webp(data: bytes, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        from io import BytesIO

        from PIL import Image

        img = Image.open(BytesIO(data))
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        img.save(dest, format="WEBP", quality=82, method=6)
        return True
    except ImportError:
        # Pillow 無し: 拡張子を og のまま保存
        ext = ".jpg"
        alt = dest.with_suffix(ext)
        alt.write_bytes(data)
        print(f"  Pillow 未導入のため {alt.name} に保存（webp 変換スキップ）", file=sys.stderr)
        return True
    except Exception as exc:
        print(f"  画像変換失敗: {exc}", file=sys.stderr)
        return False


def fetch_product_image(product: dict, *, root: Path, force: bool) -> bool:
    image_file = norm(str(product.get("image_file") or ""))
    if not image_file:
        print(f"  skip: image_file 未設定 ({product.get('name')})")
        return False
    if image_file.lower().startswith(("http://", "https://")):
        print(f"  skip: 外部 URL 指定 ({product.get('name')})")
        return False
    dest = root / "images" / "affiliate" / image_file
    if dest.is_file() and not force:
        print(f"  exists: {dest}")
        return True
    image_url = norm(str(product.get("image_url") or ""))
    if not image_url:
        page_url = product_source_url(product)
        if not page_url:
            print(f"  skip: ASIN/URL なし ({product.get('name')})")
            return False
        try:
            if "amazon.co.jp" in page_url or extract_asin(page_url):
                image_url = fetch_amazon_cover_url(page_url) or ""
            if not image_url:
                image_url = fetch_og_image_url(page_url) or ""
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"  fetch failed ({product.get('name')}): {exc}", file=sys.stderr)
            return False
    if not image_url:
        print(f"  skip: 表紙 URL 未取得 ({product.get('name')})")
        return False
    if not _amazon_image_ok(image_url):
        print(f"  skip: プレースホルダ画像 ({product.get('name')})")
        return False
    try:
        data = download_bytes(image_url)
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"  download failed ({product.get('name')}): {exc}", file=sys.stderr)
        return False
    ok = save_as_webp(data, dest)
    if ok:
        print(f"  saved: {dest}")
    return ok


def fetch_workbook_images(product: dict, *, root: Path, force: bool) -> int:
    if not norm(str(product.get("workbook_image_file") or "")):
        return 0
    workbook = {
        "name": product.get("workbook_name") or "workbook",
        "image_file": product.get("workbook_image_file"),
        "amazon_url": product.get("workbook_amazon_url") or "",
        "image_url": product.get("workbook_image_url") or "",
    }
    return 1 if fetch_product_image(workbook, root=root, force=force) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", help="guide slug（brief のファイル名）")
    parser.add_argument("--brief", type=Path, help="brief YAML パス（--slug より優先）")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--force", action="store_true", help="既存画像を上書き")
    args = parser.parse_args()

    if args.brief:
        brief = yaml.safe_load(args.brief.read_text(encoding="utf-8"))
    elif args.slug:
        brief = load_affiliate_brief(args.slug, root=args.root)
    else:
        parser.error("--slug または --brief が必要です")
    if not isinstance(brief, dict):
        print("invalid brief", file=sys.stderr)
        return 1

    products = brief_products(brief)
    if not products:
        print("products がありません", file=sys.stderr)
        return 1

    saved = 0
    for product in products:
        print(f"product: {product.get('name')}")
        if fetch_product_image(product, root=args.root, force=args.force):
            saved += 1
        saved += fetch_workbook_images(product, root=args.root, force=args.force)

    print(f"done: {saved} image(s) under {args.root / 'images' / 'affiliate'}")
    return 0 if saved else 1


if __name__ == "__main__":
    raise SystemExit(main())
