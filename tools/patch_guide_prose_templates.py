#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""archive/*_guide_content_lib.py の user_intent / action_items / section tail / FAQ を具体化。"""

from __future__ import annotations

import re
from pathlib import Path

ARCHIVE = Path(__file__).resolve().parent / "archive"
LIBS = sorted(ARCHIVE.glob("*_guide_content_lib.py"))

USER_INTENT_OLD = re.compile(
    r"    return \(\n"
    r"        f\"本記事を読むと、\{exam_topic_clause\(EXAM, topic, EXAM_SHORT\)\}、\"\n"
    r"        f\"公式テキスト・\{OFFICIAL\}で確認すべき点と、演習・用語解説を使った復習の進め方が分かります。\"\n"
    r"        f\"読了後は行動チェックリストに沿って演習と用語確認まで進められる状態を目指します。\"\n"
    r"    \)",
    re.MULTILINE,
)

USER_INTENT_NEW = """    from tools.guide_content_shared import user_intent_prose

    return user_intent_prose(topic, EXAM, EXAM_SHORT, OFFICIAL, genre)"""

ACTION_OLD = re.compile(
    r"def action_items_for\(topic: str, slug: str, genre: str\) -> str:\n"
    r"    from tools\.guide_topic_normalize import topic_label\n\n"
    r"    label = topic_label\(topic, EXAM, EXAM_SHORT\)\n"
    r"    return \";\"\.join\(\n.*?\n    \)\n",
    re.DOTALL,
)

ACTION_NEW = """def action_items_for(topic: str, slug: str, genre: str) -> str:
    from tools.guide_content_shared import action_items_prose

    return action_items_prose(topic, EXAM, EXAM_SHORT, OFFICIAL, slug, genre)
"""

SECTION_TAIL_A = re.compile(
    r"    from tools\.guide_content_shared import section_body_tail\n\n"
    r"    tail = section_body_tail\(heading, OFFICIAL\)\n"
    r"    return ensure_min\(body, 180, tail\)",
)

SECTION_TAIL_B = re.compile(
    r"    tail = f\"「\{heading\}」の詳細は\{OFFICIAL\}の最新要項と演習解説で照合してください。\"\n"
    r"    return ensure_min\(body, 180, tail\)",
)

SECTION_TAIL_NEW = """    from tools.guide_content_shared import section_body_min_filler

    return ensure_min(body, 180, section_body_min_filler(heading, topic, OFFICIAL))"""

FAQ_SUBJECT_OLD = re.compile(
    r"            text = \(\n"
    r"                f\"「\{q\}」の答えは、\{EXAM\}の公式テキスト該当章と\{OFFICIAL\}で確認するのが確実です。\"\n"
    r"                f\"\{topic\}では、条文や指針の主体（[^\"]+）をセットで押さえてください。\"\n"
    r"            \)",
    re.MULTILINE,
)

FAQ_SUBJECT_NEW = """            from tools.guide_content_shared import faq_official_verify_answer

            text = faq_official_verify_answer(q, topic, EXAM, EXAM_SHORT, OFFICIAL)"""


def patch_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    orig = text
    text = USER_INTENT_OLD.sub(USER_INTENT_NEW, text)
    text = ACTION_OLD.sub(ACTION_NEW, text)
    text = SECTION_TAIL_A.sub(SECTION_TAIL_NEW, text)
    text = SECTION_TAIL_B.sub(SECTION_TAIL_NEW, text)
    text = FAQ_SUBJECT_OLD.sub(FAQ_SUBJECT_NEW, text)
    if text != orig:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> int:
    changed = 0
    for path in LIBS:
        if patch_file(path):
            print("patched:", path.name)
            changed += 1
        else:
            print("skip:", path.name)
    print(f"done: {changed}/{len(LIBS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
