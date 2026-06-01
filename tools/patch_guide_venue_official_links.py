#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""archive/*_guide_content_lib.py の会場関連見出しに公式リンク対応を入れる。"""

from __future__ import annotations

import re
from pathlib import Path

ARCHIVE = Path(__file__).resolve().parent / "archive"
LIBS = sorted(ARCHIVE.glob("*_guide_content_lib.py"))

ACCESS_FN = '''def _heading_試験会場アクセス(topic: str, slug: str, _genre: str, _ctx: dict) -> str:
    from tools.exam_venue_official_links import md_link, venue_page_for_slug
    from tools.guide_content_shared import exam_venue_access_prose

    page = venue_page_for_slug(slug)
    venue_page_md = md_link(*page) if page else ""
    return exam_venue_access_prose(official=OFFICIAL, topic=topic, venue_page_md=venue_page_md)


'''

ACCESS_OLD = re.compile(
    r"def _heading_試験会場アクセス\(topic: str, _slug: str, _genre: str, _ctx: dict\) -> str:\n"
    r"    from tools\.guide_content_shared import exam_venue_access_prose\n\n"
    r"    return exam_venue_access_prose\(official=OFFICIAL, topic=topic\)\n",
    re.MULTILINE,
)

VENUE_FN = '''def _heading_申込手順会場(topic: str, slug: str, _genre: str, _ctx: dict) -> str:
    from tools.guide_content_shared import exam_application_venue_prose
    from tools.exam_venue_official_links import official_page_md_for_exam

    return exam_application_venue_prose(
        official=OFFICIAL,
        topic=topic,
        official_page_md=official_page_md_for_exam(EXAM, OFFICIAL),
    )


'''

VENUE_OLD = re.compile(
    r"def _heading_申込手順会場\(topic: str, _slug: str, _genre: str, _ctx: dict\) -> str:\n"
    r"    return two_paragraphs\(\n"
    r"        f\"「\{topic\}」では、申込フォームの氏名・受験地・連絡先を正確に入力します。\"\n"
    r"        f\"会場は都市ごとに設定されるため、交通手段と試験当日の所要時間を前もって確認してください。\",\n"
    r"        f\"受験票に記載される持ち物（筆記用具、身分証など）は要項どおりに準備し、\"\n"
    r"        f\"前日にカバンに入れておくと当日のミスを減らせます。\"\n"
    r"        f\"\{topic\}に関する申込・会場情報は\{OFFICIAL\}で最新版を確認してください。\",\n"
    r"    \)\n",
    re.MULTILINE,
)

VENUE_OLD_B = re.compile(
    r"def _heading_申込手順会場\(topic: str, slug: str, _genre: str, _ctx: dict\) -> str:\n"
    r"    from tools\.guide_content_shared import exam_application_venue_prose\n\n"
    r"    return exam_application_venue_prose\(official=OFFICIAL, topic=topic\)\n",
    re.MULTILINE,
)

BASIC_FN = '''def _heading_試験会場基本情報(topic: str, slug: str, _genre: str, _ctx: dict) -> str:
    from tools.exam_venue_official_links import md_link, venue_page_for_slug
    from tools.guide_content_shared import exam_venue_basic_info_prose

    page = venue_page_for_slug(slug)
    venue_page_md = md_link(*page) if page else ""
    return exam_venue_basic_info_prose(
        topic=topic,
        slug=slug,
        official=OFFICIAL,
        org=ORG,
        venue_page_md=venue_page_md,
    )


'''


def patch_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    changes: list[str] = []
    new = text

    if ACCESS_OLD.search(new):
        new = ACCESS_OLD.sub(ACCESS_FN, new, count=1)
        changes.append("access_fn")

    if VENUE_OLD_B.search(new):
        new = VENUE_OLD_B.sub(VENUE_FN, new, count=1)
        changes.append("venue_fn")
    elif VENUE_OLD.search(new):
        new = VENUE_OLD.sub(VENUE_FN, new, count=1)
        changes.append("venue_fn")

    if path.name == "eisei2shu_guide_content_lib.py":
        old_basic = re.search(
            r"def _heading_試験会場基本情報\(topic: str, slug: str, _genre: str, _ctx: dict\) -> str:.*?"
            r"        venue_page_md=venue_page_md,\n"
            r"    \)\n",
            new,
            re.DOTALL,
        )
        if not old_basic:
            old_basic = re.search(
                r"def _heading_試験会場基本情報\(topic: str, slug: str, _genre: str, _ctx: dict\) -> str:.*?"
                r"出張試験などで会場が異なる場合もあるため、受験票の表記を必ず照合してください。\",\n"
                r"    \)\n",
                new,
                re.DOTALL,
            )
        if old_basic:
            new = new[: old_basic.start()] + BASIC_FN + new[old_basic.end() :]
            changes.append("basic_fn")

    if "_heading_試験会場アクセス" not in new and "_heading_試験会場基本情報" in new:
        anchor = new.find("def _heading_試験日程確認")
        if anchor != -1:
            new = new[:anchor] + ACCESS_FN + new[anchor:]
            changes.append("access_fn_restore")

    if new != text:
        path.write_text(new, encoding="utf-8")
    return changes


def main() -> int:
    for path in LIBS:
        ch = patch_file(path)
        print(f"{path.name}: {ch or 'unchanged'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
