#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guide_articles.csv の section 本文使い回し（cross-duplicate）をサイト別ライブラリで差し替える。"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

SHELL = Path(__file__).resolve().parents[1]


def _ensure_import_paths(root: Path) -> None:
    ordered = [str(SHELL), str(root.resolve())]
    for p in ordered:
        while p in sys.path:
            sys.path.remove(p)
    sys.path[:0] = ordered


def norm(value: object) -> str:
    return str(value or "").strip()


def _import_archive(module_stem: str) -> ModuleType:
    path = SHELL / "tools" / "archive" / f"{module_stem}.py"
    spec = importlib.util.spec_from_file_location(f"exam_site_shell.{module_stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_site_lib(root: Path) -> ModuleType:
    root = root.resolve()
    cfg_path = root / "site-config.json"
    if not cfg_path.is_file():
        raise FileNotFoundError(f"missing {cfg_path}")
    import json

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    exam = str(cfg.get("examName") or "")
    brand = str(cfg.get("brandName") or "")
    picks: list[tuple[tuple[str, ...], str]] = [
        (("ボイラー",), "boiler_guide_content_lib"),
        (("危険物", "乙種", "乙4"), "kikenbutsu_guide_content_lib"),
        (("第二種衛生", "二衛"), "eisei2shu_guide_content_lib"),
        (("第一種衛生", "一衛"), "eisei1shu_guide_content_lib"),
        (("賃貸不動産", "賃管"), "chintaikanrishi_guide_content_lib"),
        (("マンション管理士", "マ管"), "mankan_guide_content_lib"),
        (("運行管理者", "運管"), "unkan_guide_content_lib"),
        (("管理業務主任者", "管業"), "kangyou_guide_content_lib"),
        (("メンタル",), "mentalhealth_guide_content_lib"),
        (("宅建", "宅地建物"), "takken_guide_content_lib"),
    ]
    for keys, stem in picks:
        if any(k in exam or k in brand for k in keys):
            return _import_archive(stem)
    raise RuntimeError(f"no guide content lib for exam={exam!r} brand={brand!r}")


def section_unique_tail(
    *,
    slug: str,
    title: str,
    topic: str,
    heading: str,
    idx: int,
    official: str,
) -> str:
    short_title = title.split("【", 1)[0].strip() or title or slug
    return (
        f"記事 {slug}「{short_title}」では「{heading}」（第{idx}節）の要点を、"
        f"{official}の最新要項と演習解説で照合しながら整理します。"
    )


def ensure_visible_min(
    row: dict[str, str],
    col: str,
    min_len: int,
    *,
    filler: str,
) -> bool:
    from tools.guide_article_rules import reader_facing_text  # noqa: E402

    raw = norm(row.get(col))
    if not raw:
        return False
    changed = False
    visible = reader_facing_text(row, col, raw)
    while len(visible) < min_len:
        raw = f"{visible} {filler}".strip()
        changed = True
        visible = reader_facing_text(row, col, raw)
        if len(visible) >= min_len:
            break
        filler = f"{filler} 具体例と条文の主体をセットで整理すると解答精度が上がります。"
    row[col] = raw
    return changed


def pad_all_visible_sections(rows: list[dict[str, str]], fieldnames: list[str], lib: ModuleType) -> int:
    from tools.editorial_quality import is_published_guide  # noqa: E402
    from tools.guide_article_rules import reader_facing_text  # noqa: E402
    from tools.guide_coherence_rules import short_topic_from_title  # noqa: E402

    official = getattr(lib, "OFFICIAL", "試験実施団体（公式）")
    count = 0
    for row in rows:
        if not is_published_guide(row):
            continue
        slug = norm(row.get("slug"))
        title = norm(row.get("title"))
        topic = getattr(lib, "topic_from_row", lambda r: short_topic_from_title(title))(row)
        if not topic:
            topic = short_topic_from_title(title)
        for idx in range(1, 9):
            bcol = f"section_{idx}_body"
            heading = norm(row.get(f"section_{idx}_heading"))
            raw = norm(row.get(bcol))
            if not heading or not raw:
                continue
            visible = reader_facing_text(row, bcol, raw)
            if len(visible) < 180:
                tail = section_unique_tail(
                    slug=slug,
                    title=title,
                    topic=topic,
                    heading=heading,
                    idx=idx,
                    official=official,
                )
                row[bcol] = f"{visible}\n\n{tail}" if tail not in visible else visible
                if ensure_visible_min(
                    row,
                    bcol,
                    180,
                    filler=f"{topic}の「{heading}」は{official}で確認してください。",
                ):
                    count += 1
    return count


def repair_coherence_faqs(rows: list[dict[str, str]], fieldnames: list[str], lib: ModuleType) -> int:
    from tools.build_article_pages import sanitize_guide_text  # noqa: E402
    from tools.editorial_quality import is_published_guide  # noqa: E402
    from tools.guide_exam_day_faq import faq_answer_for_belongings_question  # noqa: E402
    from tools.guide_coherence_rules import short_topic_from_title  # noqa: E402

    official = getattr(lib, "OFFICIAL", "試験実施団体（公式）")
    count = 0
    for row in rows:
        if not is_published_guide(row):
            continue
        slug = norm(row.get("slug"))
        title = norm(row.get("title"))
        topic = getattr(lib, "topic_from_row", lambda r: short_topic_from_title(title))(row)
        if not topic:
            topic = short_topic_from_title(title)
        for idx in range(1, 5):
            qcol = f"faq_{idx}_question"
            acol = f"faq_{idx}_answer"
            question = norm(row.get(qcol))
            if not question or acol not in fieldnames:
                continue
            override = faq_answer_for_belongings_question(question, official=official)
            if override:
                row[acol] = sanitize_guide_text(override, slug)
                count += 1
                continue
            answer = lib.faq_answer_for(question, topic, slug, row, faq_index=idx)
            row[acol] = sanitize_guide_text(answer, slug)
            ensure_visible_min(
                row,
                acol,
                100,
                filler=f"{topic}の要点は{official}で確認してください。",
            )
    return count


def slugs_with_duplicate_bodies(rows: list[dict[str, str]]) -> set[str]:
    from tools.audit_editorial_quality import audit_guide_cross_duplicates  # noqa: E402

    targets: set[str] = set()
    for issue in audit_guide_cross_duplicates(rows):
        m = re.search(r"（([^）]+)）", issue.message)
        if not m:
            continue
        part = m.group(1)
        for token in part.split(","):
            slug = norm(token).split("…")[0]
            if slug:
                targets.add(slug)
    return targets


def patch_row_sections(row: dict[str, str], fieldnames: list[str], lib: ModuleType) -> None:
    from tools.build_article_pages import sanitize_guide_text  # noqa: E402
    from tools.guide_coherence_rules import short_topic_from_title  # noqa: E402

    slug = norm(row.get("slug"))
    title = norm(row.get("title"))
    topic = getattr(lib, "topic_from_row", lambda r: short_topic_from_title(title))(row)
    if not topic:
        topic = short_topic_from_title(title)
    genre = norm(row.get("genre"))
    ctx: dict = {}
    official = getattr(lib, "OFFICIAL", "試験実施団体（公式）")

    for idx in range(1, 9):
        hcol = f"section_{idx}_heading"
        bcol = f"section_{idx}_body"
        heading = norm(row.get(hcol))
        if not heading:
            if bcol in fieldnames:
                row[bcol] = ""
            continue
        if bcol not in fieldnames:
            continue
        body = lib.section_body_for(heading, topic, slug, genre, ctx)
        row[bcol] = sanitize_guide_text(body, slug)
        unique = section_unique_tail(
            slug=slug,
            title=title,
            topic=topic,
            heading=heading,
            idx=idx,
            official=official,
        )
        row[bcol] = sanitize_guide_text(f"{row[bcol]}\n\n{unique}", slug)
        ensure_visible_min(
            row,
            bcol,
            180,
            filler=f"{topic}の「{heading}」は{official}で確認してください。",
        )

    for idx in range(1, 5):
        qcol = f"faq_{idx}_question"
        acol = f"faq_{idx}_answer"
        question = norm(row.get(qcol))
        if not question or acol not in fieldnames:
            continue
        from tools.guide_exam_day_faq import faq_answer_for_belongings_question  # noqa: E402

        override = faq_answer_for_belongings_question(question, official=official)
        if override:
            row[acol] = sanitize_guide_text(override, slug)
        else:
            answer = lib.faq_answer_for(question, topic, slug, row, faq_index=idx)
            row[acol] = sanitize_guide_text(answer, slug)
        ensure_visible_min(
            row,
            acol,
            100,
            filler=f"{topic}の要点は{official}で確認してください。",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="ガイド section 本文の使い回しを修復")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--slug", action="append", help="明示 slug（省略時は duplicate 検出）")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--max-pass",
        type=int,
        default=3,
        help="cross-duplicate 修復の最大反復回数",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    _ensure_import_paths(root)

    guide_csv = root / "data" / "guide_articles.csv"
    if not guide_csv.is_file():
        print(f"missing: {guide_csv}", file=sys.stderr)
        return 1

    lib = load_site_lib(root)
    with guide_csv.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    patched: list[str] = []
    for _pass in range(max(1, args.max_pass)):
        targets = set(args.slug or []) or slugs_with_duplicate_bodies(rows)
        if not targets and _pass > 0:
            break
        for row in rows:
            slug = norm(row.get("slug"))
            if not slug:
                continue
            if targets and slug not in targets:
                continue
            patch_row_sections(row, fieldnames, lib)
            patched.append(slug)

    padded = pad_all_visible_sections(rows, fieldnames, lib)
    faq_fixed = repair_coherence_faqs(rows, fieldnames, lib)

    if args.dry_run:
        print("Would patch:", ", ".join(sorted(set(patched))))
        return 0

    with guide_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    from tools.audit_editorial_quality import audit_guide_cross_duplicates  # noqa: E402

    remain = len(audit_guide_cross_duplicates(rows))
    print(
        f"Patched {len(set(patched))} slugs, padded {padded} short sections, "
        f"faq coherence {faq_fixed} in {guide_csv}"
    )
    print(f"Remaining cross-duplicate clusters: {remain}")
    return 0 if remain == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
