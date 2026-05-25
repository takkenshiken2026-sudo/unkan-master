#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Temporarily build with long names and many fields, then restore config."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "site-config.json"
BACKUP_TARGETS = [
    "index.html",
    "about.html",
    "privacy.html",
    "related-sites.html",
    "articles/index.html",
    "site-config.js",
    "site-theme.css",
    "CNAME",
    "robots.txt",
    "sitemap.xml",
]


def main() -> int:
    original = json.loads(CONFIG.read_text(encoding="utf-8"))
    backups: dict[Path, str | bytes | None] = {}
    for rel in BACKUP_TARGETS:
        path = ROOT / rel
        backups[path] = path.read_bytes() if path.is_file() else None
    public_backup = ROOT / ".tmp-public-site-backup"
    if public_backup.exists():
        shutil.rmtree(public_backup)
    if (ROOT / "public_site").is_dir():
        shutil.copytree(ROOT / "public_site", public_backup)

    stress = deepcopy(original)
    stress["brandName"] = "長期名称サンプル資格マスター"
    stress["brandMark"] = "長"
    stress["examName"] = "長い正式名称を持つ総合資格試験（実務・法令・設備・会計横断プレースホルダー）"
    stress["theme"] = {
        **(stress.get("theme") or {}),
        "accent": "#1f3a5f",
        "background": "#eef2f7",
    }
    stress["fields"] = [
        {"id": "law", "name": "法令・制度", "aliases": ["法令・制度", "関連法令"], "legacyGlossaryCat": "law"},
        {"id": "rights", "name": "契約・実務", "aliases": ["契約・実務", "実務"], "legacyGlossaryCat": "rights"},
        {"id": "limit", "name": "設備・その他", "aliases": ["設備・その他", "その他"], "legacyGlossaryCat": "limit"},
        {"id": "accounting", "name": "会計・税務", "aliases": ["会計・税務"], "legacyGlossaryCat": "accounting"},
        {"id": "safety", "name": "安全管理", "aliases": ["安全管理"], "legacyGlossaryCat": "safety"},
        {"id": "strategy", "name": "経営・戦略", "aliases": ["経営・戦略"], "legacyGlossaryCat": "strategy"},
    ]

    try:
        CONFIG.write_text(json.dumps(stress, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        subprocess.run([sys.executable, "tools/build_all.py"], cwd=ROOT, check=True)
        print("Stress config build passed")
        return 0
    finally:
        CONFIG.write_text(json.dumps(original, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for path, data in backups.items():
            if data is None:
                if path.exists():
                    path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        public_dir = ROOT / "public_site"
        if public_dir.exists():
            shutil.rmtree(public_dir)
        if public_backup.exists():
            shutil.move(str(public_backup), str(public_dir))


if __name__ == "__main__":
    raise SystemExit(main())
