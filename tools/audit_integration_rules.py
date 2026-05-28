#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統合ルールの厳密監査（テンプレ正本 + 任意で本番サイト）。

docs/integration-checklist.md の契約が、マニフェスト・build_all・Cursor ルール・
validate_site_integration で揃っているかを一覧する。

  python3 tools/audit_integration_rules.py              # テンプレのみ
  python3 tools/audit_integration_rules.py --target /path/to/site
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# integration-checklist.md §1.4 / §1.5 で「同期対象」とされる共通エンジン
REQUIRED_MANIFEST_PATHS = [
    "site-q-index.js",
    "site-terms-index.js",
    "tools/html_footer.py",
    "tools/apply_site_config.py",
    "tools/build_past_question_pages.py",
    "tools/build_practice_ichimon_pages.py",
    "tools/csv_to_exam_site_past_js.py",
    "tools/csv_to_exam_site_ichimondou_js.py",
    "tools/import_orig_questions_to_practice_csv.py",
    "tools/import_base_questions_to_ichimon_csv.py",
    "tools/validate_site_integration.py",
    "tools/build_glossary_pages.py",
    "tools/term_diagram.py",
    "docs/integration-checklist.md",
    "docs/question-static-pages.md",
    "docs/term-diagrams.md",
    "docs/site-chrome.md",
    ".cursor/rules/site-integration.mdc",
    ".cursor/rules/practice-ichimon-static.mdc",
    ".cursor/rules/term-diagrams.mdc",
]

REQUIRED_BUILD_ALL_SNIPPETS = [
    "validate_csv.py",
    "apply_site_config.py",
    "build_past_question_pages.py",
    "build_practice_ichimon_pages.py",
    "validate_site_integration.py",
    "validate_internal_links.py",
]

REQUIRED_DOCS = [
    "docs/integration-checklist.md",
    "docs/question-static-pages.md",
    "docs/term-diagrams.md",
    "docs/multi-site-workflow.md",
    "docs/README.md",
    "data/README.md",
    "sites/README.md",
    "sites/_example/SITE.md",
    "sites/takken-master/SITE.md",
    "sites/takken-master/manifest-phase1.txt",
    "sites/takken-master/manifest-phase3.txt",
]


@dataclass
class Finding:
    level: str  # OK | WARN | ERROR
    area: str
    message: str


def _read_manifest(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(line.rstrip("/"))
    return out


def audit_template(root: Path) -> list[Finding]:
    findings: list[Finding] = []

    manifest = root / "tools/template_sync_manifest.txt"
    manifest_paths = _read_manifest(manifest)
    if not manifest_paths:
        findings.append(Finding("ERROR", "manifest", f"{manifest} がありません"))
    else:
        for req in REQUIRED_MANIFEST_PATHS:
            if req.startswith(".cursor/rules/"):
                if ".cursor/rules" in manifest_paths or ".cursor/rules/" in manifest_paths:
                    findings.append(Finding("OK", "manifest", "登録済み: .cursor/rules/"))
                else:
                    findings.append(Finding("ERROR", "manifest", "template_sync_manifest に .cursor/rules/ がありません"))
                continue
            if req in manifest_paths:
                findings.append(Finding("OK", "manifest", f"登録済み: {req}"))
            else:
                findings.append(Finding("ERROR", "manifest", f"template_sync_manifest に未登録: {req}"))

    build_all = root / "tools/build_all.py"
    if build_all.is_file():
        text = build_all.read_text(encoding="utf-8")
        for snip in REQUIRED_BUILD_ALL_SNIPPETS:
            if snip in text:
                findings.append(Finding("OK", "build_all", f"含む: {snip}"))
            else:
                findings.append(Finding("ERROR", "build_all", f"不足: {snip}"))
    else:
        findings.append(Finding("ERROR", "build_all", "tools/build_all.py がありません"))

    for doc in REQUIRED_DOCS:
        p = root / doc
        if p.is_file():
            findings.append(Finding("OK", "docs", f"存在: {doc}"))
        else:
            findings.append(Finding("ERROR", "docs", f"欠落: {doc}"))

    # ドキュメント内の旧誤情報が残っていないか
    ic = root / "docs/integration-checklist.md"
    if ic.is_file():
        if "FOOTER_ROOT_HREFS" in ic.read_text(encoding="utf-8"):
            findings.append(Finding("OK", "docs", "FOOTER_ROOT_HREFS 否定記載あり"))
        if "groupBy: category" in ic.read_text(encoding="utf-8"):
            findings.append(Finding("OK", "docs", "一問一答 groupBy: category 契約あり"))

    rule = root / ".cursor/rules/practice-ichimon-static.mdc"
    if rule.is_file():
        rt = rule.read_text(encoding="utf-8")
        if "§1.5, §7" in rt and "§1.5, §6" not in rt:
            findings.append(Finding("ERROR", "cursor", "practice-ichimon-static.mdc: §7 参照誤り（§6 が展開手順）"))
        elif "§1.5, §6" in rt:
            findings.append(Finding("OK", "cursor", "practice-ichimon-static.mdc: 正しい節参照"))

    # INDEX_CONFIG ソース契約
    bp = root / "tools/build_practice_ichimon_pages.py"
    if bp.is_file():
        bt = bp.read_text(encoding="utf-8")
        for mode in ("practice", "ichimon"):
            m = re.search(rf'"{mode}":\s*\{{[^}}]*"groupBy":\s*"category"', bt, re.S)
            if m:
                findings.append(Finding("OK", "generator", f'INDEX_CONFIG[{mode}].groupBy = category'))
            else:
                findings.append(Finding("ERROR", "generator", f'INDEX_CONFIG[{mode}] が groupBy: category ではない'))

    return findings


def audit_target_site(site: Path) -> list[Finding]:
    findings: list[Finding] = []

    validate = site / "tools/validate_site_integration.py"
    if validate.is_file():
        proc = subprocess.run(
            [sys.executable, str(validate), "--root", str(site)],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            findings.append(Finding("OK", "site", "validate_site_integration: OK"))
        else:
            for line in (proc.stderr or proc.stdout).splitlines():
                if line.strip():
                    findings.append(Finding("ERROR", "site", line.strip()))
    else:
        findings.append(Finding("WARN", "site", "validate_site_integration.py 未導入（統合未完了）"))

    build_all = site / "tools/build_all.py"
    if build_all.is_file():
        text = build_all.read_text(encoding="utf-8")
        for snip in ("build_practice_ichimon_pages.py", "validate_site_integration.py", "apply_site_config.py"):
            if snip in text:
                findings.append(Finding("OK", "site-build_all", f"含む: {snip}"))
            else:
                findings.append(Finding("WARN", "site-build_all", f"不足: {snip}"))
    else:
        findings.append(Finding("ERROR", "site", "tools/build_all.py なし"))

    site_md = ROOT / "sites" / f"{site.name}/SITE.md"
    if not site_md.is_file():
        # パス名が site id と一致しない場合もある
        findings.append(Finding("WARN", "site", f"sites/{site.name}/SITE.md がテンプレに無い（手順の正本を要確認）"))
    else:
        findings.append(Finding("OK", "site", f"テンプレに SITE.md あり: sites/{site.name}/SITE.md"))

    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="統合ルール監査")
    ap.add_argument("--root", type=Path, default=ROOT, help="テンプレ root")
    ap.add_argument("--target", type=Path, default=None, help="本番サイト root（任意）")
    args = ap.parse_args()

    template_root = args.root.resolve()
    all_findings = audit_template(template_root)

    if args.target:
        all_findings.extend(audit_target_site(args.target.resolve()))

    errors = [f for f in all_findings if f.level == "ERROR"]
    warns = [f for f in all_findings if f.level == "WARN"]
    oks = [f for f in all_findings if f.level == "OK"]

    print(f"=== 統合ルール監査 ===")
    print(f"テンプレ: {template_root}")
    if args.target:
        print(f"本番:     {args.target.resolve()}")
    print(f"OK: {len(oks)}  WARN: {len(warns)}  ERROR: {len(errors)}")
    print()

    if errors:
        print("## ERROR")
        for f in errors:
            print(f"  [{f.area}] {f.message}")
        print()
    if warns:
        print("## WARN")
        for f in warns:
            print(f"  [{f.area}] {f.message}")
        print()

    if not errors and not warns:
        print("監査結果: テンプレの統合ルールは整備済みです。")
        return 0
    if errors:
        print("監査結果: ERROR あり — 上記を修正してください。")
        return 1
    print("監査結果: WARN のみ — 未移行サイト等の可能性があります。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
