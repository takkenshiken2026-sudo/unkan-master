#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-command build for the exam-site template."""

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
    run(["bash", "tools/ci_deploy_build.sh"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
