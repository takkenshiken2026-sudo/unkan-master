#!/usr/bin/env bash
# 全サイト: テンプレ同期 → ブランド画像 → 全 HTML 再生成 → public_site 配置
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

build_if() {
  local script="$1"
  if [[ -f "tools/$script" ]]; then
    "$PY" "tools/$script" || echo "  warn: $script"
  fi
}

cd "$SHELL"
for site in "${SITES[@]}"; do
  target="$HOME/Projects/$site"
  if [[ ! -f "$target/site-config.json" ]]; then
    echo "skip $site (no site-config.json)"
    continue
  fi
  echo "=== $site ==="
  "$PY" tools/sync_from_template.py --target "$target" >/dev/null 2>&1 || true
  (
    cd "$target"
    "$PY" tools/generate_brand_assets.py
    "$PY" tools/apply_site_config.py
    if [[ -f data/guide_articles.csv ]]; then
      "$PY" tools/fix_exam_venue_hub_articles.py --target "$(pwd)" 2>/dev/null || true
      "$PY" tools/fix_exam_venue_guide_articles.py --target "$(pwd)" 2>/dev/null || true
    fi
    build_if build_article_pages.py
    build_if build_glossary_pages.py
    if [[ -f data/past_questions.csv ]]; then
      build_if build_past_question_pages.py
    fi
    if [[ -f data/practice_questions.csv ]] || [[ -f data/ichimon_questions.csv ]]; then
      build_if build_practice_ichimon_pages.py
    fi
    if [[ -f tools/prepare_public_site.sh ]]; then
      bash tools/prepare_public_site.sh >/dev/null
    fi
  )
  echo "  ok"
done
echo "done."
