#!/usr/bin/env bash
# GitHub Actions 用: ロゴ・ファビコン・静的ページを public_site/ に配置（audit 省略）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"

"$PY" tools/generate_brand_assets.py
"$PY" tools/apply_site_config.py
bash tools/prepare_public_site.sh
