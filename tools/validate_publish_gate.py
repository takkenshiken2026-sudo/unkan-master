#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本番公開前ゲート: 編集品質 strict + ガイド HTML 整合性。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    py = sys.executable
    run([py, "tools/validate_csv.py"])
    run([py, "tools/audit_editorial_quality.py", "--strict"])
    articles = ROOT / "articles"
    if articles.is_dir() and any(articles.iterdir()):
        run([py, "tools/validate_guide_html_coherence.py"])
        run([py, "tools/audit_guide_prose_quality.py", "--root", str(ROOT), "--strict"])
    else:
        print("skip: validate_guide_html_coherence (articles/ not built yet — run build_article_pages first)")
    print("\nOK: publish gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
