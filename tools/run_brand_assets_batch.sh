#!/usr/bin/env bash
# 全サイト: 画像生成 → head 注入 → 主要 HTML 再生成
set -euo pipefail

SHELL="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"
SITES=(
  chintaikanrishi-master
  eisei1shu-master
  eisei2shu-master
  kangyou-master
  kikenbutsu-master
  mankan-master
  mentalhealth-master
  unkan-master
  takken-master
  boiler-master.jp
)

cd "$SHELL"
for site in "${SITES[@]}"; do
  target="$HOME/Projects/$site"
  [[ -d "$target/data" || -d "$target/site-config.json" ]] || [[ -f "$target/site-config.json" ]] || { echo "skip $site"; continue; }
  echo "=== $site ==="
  "$PY" tools/sync_from_template.py --target "$target" >/dev/null 2>&1 || true
  (cd "$target" && "$PY" tools/generate_brand_assets.py && "$PY" tools/apply_site_config.py)
  (cd "$target" && "$PY" tools/build_article_pages.py >/dev/null 2>&1 || true)
  (cd "$target" && "$PY" tools/build_glossary_pages.py >/dev/null 2>&1 || true)
done
echo "done."
