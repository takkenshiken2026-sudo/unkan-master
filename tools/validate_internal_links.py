#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate that every internal href in generated HTML resolves to an existing target."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlparse

ROOT = Path(__file__).resolve().parents[1]

# index.html SPA: hash routes are handled by JS (see gotoPage / boot routing).
INDEX_HASH_WHITELIST = frozenset(
    {
        "past",
        "past-config",
        "orig",
        "ichimondou",
        "dash",
        "review",
        "quiz-start",
        "quiz",
        "score",
        "analytics",
    }
)

HREF_RE = re.compile(r"""href\s*=\s*(["'])(.*?)\1""", re.IGNORECASE | re.DOTALL)
ID_RE = re.compile(r"""\bid\s*=\s*(["'])([A-Za-z][\w:.-]*)\1""")


@dataclass
class Issue:
    level: str
    path: Path
    message: str

    def format(self) -> str:
        return f"[{self.level}] {self.path.relative_to(ROOT)} - {self.message}"


class InternalLinkValidator:
    def __init__(self) -> None:
        self.issues: list[Issue] = []
        self.html_files: list[Path] = []
        self.existing: set[Path] = set()

    def error(self, path: Path, message: str) -> None:
        self.issues.append(Issue("ERROR", path, message))

    def warn(self, path: Path, message: str) -> None:
        self.issues.append(Issue("WARN", path, message))

    def discover_html(self) -> None:
        roots = [
            ROOT / "index.html",
            ROOT / "about.html",
            ROOT / "privacy.html",
            ROOT / "privacy-terms.html",
            ROOT / "related-sites.html",
        ]
        for base in roots:
            if base.is_file():
                self.html_files.append(base)
        for pattern in ("articles/**/*.html", "terms/**/*.html", "q/**/*.html"):
            self.html_files.extend(sorted(ROOT.glob(pattern)))
        self.existing = {p.resolve() for p in self.html_files}

    @staticmethod
    def extract_ids(text: str) -> set[str]:
        return {m.group(2) for m in ID_RE.finditer(text)}

    @staticmethod
    def is_external(href: str) -> bool:
        lowered = href.lower()
        return lowered.startswith(
            ("http://", "https://", "mailto:", "tel:", "javascript:", "data:")
        )

    def resolve_target(self, page: Path, href: str) -> tuple[Path | None, str]:
        href = unquote(href.strip())
        if not href or href == "#":
            return None, ""
        path_part, fragment = urldefrag(href)
        if self.is_external(path_part or href):
            return None, fragment
        if path_part in ("/", ""):
            target = (ROOT / "index.html").resolve()
        elif path_part.startswith("/"):
            target = (ROOT / path_part.lstrip("/")).resolve()
        elif path_part:
            target = (page.parent / path_part).resolve()
        else:
            target = page.resolve()
        if target.suffix == "" and target.exists() and target.is_dir():
            target = (target / "index.html").resolve()
        elif target.suffix == "" and not target.exists():
            index_candidate = Path(str(target) + ".html")
            if index_candidate.is_file():
                target = index_candidate.resolve()
            else:
                index_in_dir = (target / "index.html").resolve()
                if index_in_dir.is_file():
                    target = index_in_dir
        return target, fragment

    def fragment_ok(self, target: Path, fragment: str, page: Path) -> bool:
        if not fragment:
            return True
        if target.name == "index.html" and target.parent == ROOT.resolve():
            return fragment in INDEX_HASH_WHITELIST
        text = target.read_text(encoding="utf-8")
        ids = self.extract_ids(text)
        if fragment in ids:
            return True
        # aria-labelledby / headers often mirror ids without duplicate id=
        if f'id="{fragment}"' in text or f"id='{fragment}'" in text:
            return True
        self.error(page, f"アンカー #{fragment} が {target.relative_to(ROOT)} に存在しません")
        return False

    @staticmethod
    def skip_href(href: str) -> bool:
        if "${" in href or "#{" in href:
            return True
        return False

    @staticmethod
    def path_without_query(path_part: str) -> str:
        return path_part.split("?", 1)[0].split("#", 1)[0]

    def validate_href(self, page: Path, href: str) -> None:
        if self.skip_href(href):
            return
        if not href or href.startswith("#"):
            if href.startswith("#") and len(href) > 1:
                frag = href[1:]
                if frag not in self.extract_ids(page.read_text(encoding="utf-8")):
                    if not (page.name == "index.html" and frag in INDEX_HASH_WHITELIST):
                        self.error(page, f"ページ内アンカー {href} が存在しません")
            return
        if self.is_external(href):
            return
        path_part, fragment = urldefrag(href.strip())
        if path_part:
            path_part = self.path_without_query(path_part)
            href = f"{path_part}#{fragment}" if fragment else path_part
        target, fragment = self.resolve_target(page, href)
        if target is None:
            return
        if not target.is_file():
            self.error(
                page,
                f"リンク切れ: href={href!r} → {target.relative_to(ROOT)} が見つかりません",
            )
            return
        if target.resolve() not in self.existing:
            try:
                target.relative_to(ROOT)
            except ValueError:
                self.error(page, f"リンク切れ: href={href!r} がサイト外を指しています")
                return
        self.fragment_ok(target, fragment, page)

    def validate_page(self, page: Path) -> None:
        text = page.read_text(encoding="utf-8")
        for match in HREF_RE.finditer(text):
            self.validate_href(page, match.group(2))

    def run(self) -> int:
        self.discover_html()
        if not self.html_files:
            self.error(ROOT, "検証対象の HTML がありません")
        for path in self.html_files:
            self.validate_page(path)

        for issue in self.issues:
            print(issue.format(), file=sys.stderr if issue.level == "ERROR" else sys.stdout)

        errors = [i for i in self.issues if i.level == "ERROR"]
        warnings = [i for i in self.issues if i.level == "WARN"]
        if errors:
            print(
                f"Internal link validation failed: {len(errors)} error(s), {len(warnings)} warning(s)",
                file=sys.stderr,
            )
            return 1
        print(
            f"Internal link validation passed: {len(self.html_files)} file(s), "
            f"{warnings and str(len(warnings)) + ' warning(s)' or 'no broken links'}",
        )
        return 0


def main() -> int:
    return InternalLinkValidator().run()


if __name__ == "__main__":
    raise SystemExit(main())
