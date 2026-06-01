#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ロードマップ A→F を順に実行するオーケストレータ。"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SHELL = Path(__file__).resolve().parents[1]
PROJECTS = Path.home() / "Projects"

DEFAULT_SITES = (
    "eisei1shu-master",
    "eisei2shu-master",
    "boiler-master.jp",
    "unkan-master",
    "kikenbutsu-master",
    "mentalhealth-master",
    "mankan-master",
    "kangyou-master",
    "chintaikanrishi-master",
    "takken-master",
)

COMMIT_MSG = """build: ロードマップ完了（ハブ品質・編集WARN・全サイト再ビルド）

- hub_pro_enrich / fix_hub_titles / fix_editorial_auto 適用
- build_all + validate 通過
- gh-pages 同期（該当 repo）
"""


def run(cmd: list[str], *, cwd: Path, check: bool = True, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd))
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, check=check)


def audit_summary(root: Path, tool: str) -> dict:
    if tool == "hub":
        path = root / "reports/hub_audit/summary.json"
    else:
        path = None
    if path and path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def editorial_counts(root: Path, py: str, *, strict: bool = False) -> tuple[int, int, int]:
    cmd = [py, str(SHELL / "tools/audit_editorial_quality.py")]
    if strict:
        cmd.append("--strict")
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    out = proc.stdout + proc.stderr
    m = re.search(r"編集品質: ERROR (\d+) / WARN (\d+)", out)
    err = int(m.group(1)) if m else -1
    warn = int(m.group(2)) if m else -1
    return err, warn, proc.returncode


def sync_template(site: Path) -> None:
    script = SHELL / "tools/sync_from_template.py"
    if not script.is_file():
        return
    run([sys.executable, str(script), "--target", str(site)], cwd=SHELL, check=False)


def phase_b_c(site: Path, py: str) -> bool:
    env = {**dict(__import__("os").environ), "PYTHONPATH": f"{SHELL}:{site}"}
    for tool in (
        "tools/hub_pro_enrich.py",
        "tools/fix_hub_titles.py",
        "tools/fix_editorial_auto.py",
    ):
        path = SHELL / tool
        if path.is_file():
            run([py, str(path), "--root", str(site)], cwd=site, check=True, env=env)
    run([py, "tools/build_all.py"], cwd=site, check=True, env=env)
    run([py, str(SHELL / "tools/audit_hub_quality.py")], cwd=site, check=True, env=env)
    return True


def phase_a_deploy(site: Path, *, push: bool) -> bool:
    if not (site / ".git").is_dir():
        return False
    status = subprocess.run(["git", "status", "--porcelain"], cwd=site, capture_output=True, text=True)
    if not status.stdout.strip():
        print(f"  skip commit (clean): {site.name}")
    else:
        run(["git", "add", "-A"], cwd=site)
        run(["git", "commit", "-m", COMMIT_MSG], cwd=site, check=False)
    if push:
        run(["git", "push", "origin", "HEAD"], cwd=site, check=False)
        gh = site / "tools/sync_gh_pages_branch.sh"
        if gh.is_file():
            run(["bash", str(gh)], cwd=site, check=False)
    return True


def process_site(name: str, *, phases: set[str], push: bool) -> dict:
    site = PROJECTS / name
    py = sys.executable
    report: dict = {"site": name, "ok": True}
    if not site.is_dir():
        return {"site": name, "ok": False, "error": "missing"}

    if "e" in phases:
        sync_template(site)

    if "b" in phases or "c" in phases:
        try:
            phase_b_c(site, py)
        except subprocess.CalledProcessError as exc:
            return {"site": name, "ok": False, "error": str(exc)}

    if "b" in phases:
        report["hub"] = audit_summary(site, "hub")

    if "c" in phases:
        err, warn, rc = editorial_counts(site, py, strict=False)
        _, _, strict_rc = editorial_counts(site, py, strict=True)
        report["editorial"] = {"error": err, "warn": warn, "strict_pass": strict_rc == 0}

    if "a" in phases:
        phase_a_deploy(site, push=push)

    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", action="append")
    parser.add_argument("--phase", action="append", choices=["a", "b", "c", "d", "e", "f"])
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--all-phases", action="store_true")
    args = parser.parse_args()

    phases = set("bcdea") if args.all_phases else set(args.phase or ["b", "c", "a"])
    sites = args.site or list(DEFAULT_SITES)
    reports = [process_site(s, phases=phases, push=args.push) for s in sites]

    print("\n=== summary ===")
    for r in reports:
        print(json.dumps(r, ensure_ascii=False))
    if any(not r.get("ok") for r in reports):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
