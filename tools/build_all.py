#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-command build for exam-site projects (template and standard production sites)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def ensure_python_deps() -> None:
    """GitHub Actions 等で PyYAML が未導入のとき build を止めない。"""
    py = sys.executable
    try:
        import yaml  # noqa: F401
    except ImportError:
        subprocess.run([py, "-m", "pip", "install", "--quiet", "pyyaml"], check=True)


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    ensure_python_deps()
    py = sys.executable
    run([py, "tools/validate_csv.py"])
    run([py, "tools/validate_question_explanations.py"])
    run([py, "tools/generate_brand_assets.py"])
    run([py, "tools/apply_site_config.py"])
    run([py, "tools/csv_to_exam_site_past_js.py"])
    run([py, "tools/csv_to_exam_site_ichimondou_js.py"])
    run([py, "tools/build_past_question_pages.py"])
    run([py, "tools/build_practice_ichimon_pages.py"])
    run([py, "tools/build_article_pages.py"])
    run([py, "tools/build_glossary_pages.py"])
    run([py, "tools/build_hub_retire_redirects.py"])
    run([py, "tools/build_sitemap.py"])
    run([py, "tools/validate_sitemap.py"])
    run([py, "tools/validate_generated_seo.py"])
    run([py, "tools/validate_site_integration.py"])
    run([py, "tools/validate_internal_links.py"])
    run([py, "tools/validate_public_content.py"])
    run(["bash", "tools/prepare_public_site.sh"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
