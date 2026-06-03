#!/usr/bin/env bash
# GitHub Actions 用: validate → 生成 → 検証 → public_site/ 配置
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"
if ! "$PY" -c "import yaml" 2>/dev/null; then
  "$PY" -m pip install --quiet pyyaml
fi
exec "$PY" tools/build_all.py
