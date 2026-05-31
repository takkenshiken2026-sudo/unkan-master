#!/usr/bin/env bash
# GitHub Pages 用: SPA（index.html）＋生成済みデータ・静的ページを public_site/ に配置する。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/public_site"
rm -rf "$OUT"
mkdir -p "$OUT"
cd "$ROOT"
for f in \
  index.html \
  about.html \
  privacy.html \
  related-sites.html \
  site-config.json \
  site-config.js \
  site-pages.css \
  site-theme.css \
  seo-editorial.css \
  site-q-index.js \
  site-terms-index.js \
  site-compare-index.js \
  site-knowledge-hub-index.js \
  site-priority-index.js \
  site-analytics.js \
  CNAME \
  robots.txt \
  sitemap.xml \
  .nojekyll \
  exam-site-data-past.js \
  exam-site-data-practice.js \
  exam-site-data-ichimondou.js
do
  if [[ ! -e "$f" ]]; then
    echo "prepare_public_site.sh: 必須ファイルがありません: $f" >&2
    echo "先に python3 tools/csv_to_exam_site_past_js.py と各生成スクリプトを実行してください。" >&2
    exit 1
  fi
  cp "$f" "$OUT/"
done
for d in articles q terms; do
  if [[ -d "$ROOT/$d" ]]; then
    cp -R "$ROOT/$d" "$OUT/"
  fi
done
# サイト固有 SPA データ（eisei1 / eisei2 など）。無ければスキップ。
for f in eisei1-*.js eisei2-*.js; do
  if [[ -f "$ROOT/$f" ]]; then
    cp "$ROOT/$f" "$OUT/"
  fi
done
if [[ -f "$ROOT/privacy-terms.html" ]]; then
  cp "$ROOT/privacy-terms.html" "$OUT/"
fi
# SPA トップ（index.html）用。CSS/JS を index から分離したサイト向け。
for f in site-spa.css site-spa-fields.js site-app.css; do
  if [[ -f "$ROOT/$f" ]]; then
    cp "$ROOT/$f" "$OUT/"
  fi
done
if [[ -f "$ROOT/docs/glossary-article-slugs.json" ]]; then
  mkdir -p "$OUT/docs"
  cp "$ROOT/docs/glossary-article-slugs.json" "$OUT/docs/"
fi
n="$(find "$OUT" -type f | wc -l | tr -d ' ')"
if grep -q 'site-spa.css' "$OUT/index.html" 2>/dev/null && [[ ! -f "$OUT/site-spa.css" ]]; then
  echo "prepare_public_site.sh: index.html が site-spa.css を参照していますが public_site にありません。" >&2
  exit 1
fi
if grep -q 'site-spa-fields.js' "$OUT/index.html" 2>/dev/null && [[ ! -f "$OUT/site-spa-fields.js" ]]; then
  echo "prepare_public_site.sh: index.html が site-spa-fields.js を参照していますが public_site にありません。" >&2
  exit 1
fi
if grep -q 'site-app.css' "$OUT/index.html" 2>/dev/null && [[ ! -f "$OUT/site-app.css" ]]; then
  echo "prepare_public_site.sh: index.html が site-app.css を参照していますが public_site にありません。" >&2
  exit 1
fi
if grep -rq 'seo-editorial.css' "$OUT/terms" "$OUT/articles" 2>/dev/null && [[ ! -f "$OUT/seo-editorial.css" ]]; then
  echo "prepare_public_site.sh: 用語・ガイドが seo-editorial.css を参照していますが public_site にありません。" >&2
  exit 1
fi
echo "prepare_public_site.sh: $OUT に $n ファイルを配置しました。"
