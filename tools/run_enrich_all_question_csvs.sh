#!/usr/bin/env bash
# 全サイトの past / practice CSV に explanation_choices 等を充填（空行のみ）
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

for site in "${SITES[@]}"; do
  target="$HOME/Projects/$site"
  [[ -f "$target/site-config.json" ]] || continue
  echo "=== $site ==="
  (
    cd "$target"
    if [[ -f data/past_questions.csv ]]; then
      "$PY" tools/enrich_past_explanation_choices.py --only-empty --refresh-boilerplate
    fi
    if [[ -f data/practice_questions.csv ]]; then
      "$PY" tools/enrich_past_explanation_choices.py --csv data/practice_questions.csv --only-empty --refresh-boilerplate
    fi
    if [[ -f tools/validate_question_explanations.py ]]; then
      if ! "$PY" tools/validate_question_explanations.py; then
        echo "  warn: validate_question_explanations failed for $site" >&2
      fi
    fi
  )
done

echo "=== mankan full re-enrich (kana combo) ==="
(
  cd "$HOME/Projects/mankan-master"
  "$PY" tools/enrich_past_explanation_choices.py
  "$PY" tools/enrich_past_explanation_choices.py --csv data/practice_questions.csv
)
echo "done."
