#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""テンプレ同期の共通処理（sync_from_template / check_template_drift）。"""

from __future__ import annotations

import filecmp
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "tools" / "template_sync_manifest.txt"
DEFAULT_SITE_ONLY = ROOT / "tools" / "template_site_only.paths"


def load_path_list(path: Path) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(path)
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def is_site_only(rel: str, site_only_prefixes: list[str]) -> bool:
    rel = rel.rstrip("/")
    for prefix in site_only_prefixes:
        p = prefix.rstrip("/")
        if rel == p or rel.startswith(p + "/"):
            return True
    return False


def iter_manifest_entries(template_root: Path, manifest: list[str]) -> list[Path]:
    entries: list[Path] = []
    for rel in manifest:
        src = template_root / rel
        if not src.exists():
            continue
        if src.is_dir():
            for f in sorted(src.rglob("*")):
                if f.is_file():
                    entries.append(f.relative_to(template_root))
        else:
            entries.append(Path(rel))
    return entries


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sync_to_target(
    template_root: Path,
    target_root: Path,
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    site_only_path: Path = DEFAULT_SITE_ONLY,
    dry_run: bool = False,
) -> tuple[int, int, list[str]]:
    """テンプレ → target に manifest のファイルをコピー。戻り値: (copied, skipped, warnings)。"""
    manifest = load_path_list(manifest_path)
    site_only = load_path_list(site_only_path)
    copied = 0
    skipped = 0
    warnings: list[str] = []

    for rel in iter_manifest_entries(template_root, manifest):
        rel_s = rel.as_posix()
        if is_site_only(rel_s, site_only):
            skipped += 1
            continue
        src = template_root / rel
        dst = target_root / rel
        if not src.is_file():
            warnings.append(f"missing in template: {rel_s}")
            continue
        if dst.exists() and filecmp.cmp(src, dst, shallow=False):
            skipped += 1
            continue
        if dry_run:
            print(f"would copy: {rel_s}")
            copied += 1
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"copied: {rel_s}")
        copied += 1
    return copied, skipped, warnings


def collect_drift(
    template_root: Path,
    target_root: Path,
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
) -> list[tuple[str, str]]:
    """(rel_path, status) status: missing | different | ok"""
    manifest = load_path_list(manifest_path)
    rows: list[tuple[str, str]] = []
    for rel in iter_manifest_entries(template_root, manifest):
        rel_s = rel.as_posix()
        src = template_root / rel
        dst = target_root / rel
        if not dst.is_file():
            rows.append((rel_s, "missing"))
        elif not src.is_file():
            rows.append((rel_s, "template_missing"))
        elif file_digest(src) != file_digest(dst):
            rows.append((rel_s, "different"))
        else:
            rows.append((rel_s, "ok"))
    return rows
