#!/usr/bin/env bash
# 9サイト試験ガイド品質キャンペーン（段階1: content-lib / 段階2: 手書き batch）
set -uo pipefail

TEMPLATE="${TEMPLATE:-$HOME/Projects/exam-site-shell}"
SITES=(
  mankan-master
  unkan-master
  kikenbutsu-master
  chintaikanrishi-master
  kangyou-master
  mentalhealth-master
  eisei1shu-master
  eisei2shu-master
  boiler-master.jp
)
PY="${PYTHON:-python3}"

for site in "${SITES[@]}"; do
  target="$HOME/Projects/$site"
  echo "========== $site =========="
  [[ -d "$target" ]] || { echo "skip missing"; continue; }
  "$PY" "$TEMPLATE/tools/sync_from_template.py" --target "$target" 2>&1 | tail -2
  (cd "$target" && "$PY" tools/mark_auto_guide_rewrites.py)
  (cd "$target" && "$PY" tools/apply_site_guide_content_lib.py)
  (cd "$target" && "$PY" tools/validate_csv.py) 2>&1 | tail -2 || echo "validate_csv FAILED: $site"
  (cd "$target" && "$PY" tools/build_all.py) 2>&1 | tail -3 || echo "build FAILED: $site"
done

echo "========== campaign summary =========="
"$PY" "$TEMPLATE/tools/guide_rewrite_campaign.py" --all-sites --next 10 --priority A
