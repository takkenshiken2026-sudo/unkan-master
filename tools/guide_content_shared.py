#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全試験サイト guide content lib 共通の prose 生成ヘルパー。"""

from __future__ import annotations

from typing import Callable

from tools.guide_topic_normalize import exam_topic_clause, topic_label


def normalize_topic_from_title(
    title: str,
    *,
    exam: str,
    exam_short: str,
    skip_prefixes: tuple[str, ...] = (),
) -> str:
    from tools.guide_topic_normalize import strip_exam_prefix

    t = (title or "").strip()
    t = __import__("re").sub(r"^(.+?)【[^】]+】$", r"\1", t).strip()
    t = strip_exam_prefix(t, exam, exam_short)
    for prefix in (f"{exam}の", f"{exam}｜", f"{exam_short}の", *skip_prefixes):
        if t.startswith(prefix):
            t = t[len(prefix) :].strip()
    return t


def official_note_single(official: str) -> str:
    return (
        f"数値・日程・合格基準は年度で更新されるため、学習前と申込前には{official}の最新案内を確認してください。"
    )


def keyword_fallback_default(
    heading: str,
    topic: str,
    *,
    exam: str,
    exam_short: str,
    official: str,
    official_note_fn: Callable[[], str],
    practice_note_fn: Callable[[str], str],
    two_paragraphs_fn: Callable[[str, str], str],
) -> str:
    label = topic_label(topic, exam, exam_short)
    if exam and exam not in label:
        subject = f"{exam}の{label}"
    else:
        subject = label
    return two_paragraphs_fn(
        f"「{heading}」に関する{subject}の要点を、{official}の受験要項と受験票で整理します。"
        f"公式テキストの該当章を開きながら読むと、演習問題の解説とも対応づけやすくなります。",
        f"{official_note_fn()} {practice_note_fn(label)}",
    )


def section_body_tail(heading: str, official: str) -> str:
    return f"「{heading}」の詳細は{official}の最新要項と演習解説で照合してください。"


EXAM_DAY_KEYWORD_CHECKS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("持参", "必ず持"), "_heading_試験当日持ち物"),
    (("禁止", "持込", "持ち込み"), "_heading_持込禁止"),
    (("タイムライン",), "_heading_当日タイムライン"),
    (("アクセス", "センター"), "_heading_試験会場アクセス"),
    (("チェックリスト", "忘れ物"), "_heading_最終確認リスト"),
)


def _bullet_block(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def exam_day_forget_checklist_prose(*, official: str, topic: str) -> str:
    """試験前日・当日の忘れ物チェックリスト（箇条書きまで書き切る）。"""
    topic_ref = (topic or "試験当日").strip()
    intro = (
        f"試験前日までに、{official}の受験要項と受験票で{topic_ref}の内容を最終確認し、"
        f"忘れ物がないよう前日のうちに以下をチェックしてください。"
    )
    items = [
        "受験票（印刷したもの、または要項で認められた表示方法）",
        "HB程度の黒い鉛筆を2本以上（予備含む。シャープペンシル可否は要項で確認）",
        "消しゴム（汚れ・欠けがないもの）",
        "受験票に「身分証明書持参」とある場合は、有効期限内の写真付き身分証",
        "会場名・住所・最寄り駅・会場入口（受験票の案内どおり）",
        "試験開始時刻と受付開始時刻（多くの会場は開始30分前までに着席）",
        "当日の交通手段・所要時間・予備経路（遅延時の連絡先も控える）",
        "腕時計の持込可否（禁止の場合は会場の時計のみ使用）",
        "スマートフォン・タブレット・参考書・電卓・ノート・辞書など禁止物品を持ち込まない",
        "前日就寝時刻・当日の起床時刻・朝食（体調管理）",
    ]
    outro = (
        "学習面では新しい教材を増やさず、直近1週間の誤答ノートと頻出用語だけを30分以内で見直します。"
        "当日朝は持ち物をリスト通りにカバンへ入れ、出発前にもう一度中身を確認してください。"
    )
    return f"{intro}\n\n{_bullet_block(items)}\n\n{outro}"


def exam_day_timeline_prose(*, official: str, topic: str = "") -> str:
    """試験当日の流れを時系列で書き切る。"""
    topic = (topic or "").strip()
    if topic and "試験当日" in topic:
        intro = (
            f"{topic}は、起床から退場までの流れを想定して行動します。"
            f"時刻は受験票どおりに調整してください。"
        )
    elif topic:
        intro = (
            f"{topic}の試験当日は、起床から退場までの流れを想定して行動します。"
            f"時刻は受験票どおりに調整してください。"
        )
    else:
        intro = (
            "試験当日は、起床から退場までの流れを想定して行動します。"
            "時刻は受験票どおりに調整してください。"
        )
    items = [
        "前日：持ち物をカバンに入れ、会場ルートと所要時間を最終確認。就寝は普段より早めに",
        "当日朝：リストどおり持ち物を再確認し、禁止物品（スマホ等）を自宅に置く",
        "出発：開始時刻の60〜90分前を目安に家を出る（交通状況に応じて前倒し）",
        "会場到着：開始30分前までに受付・着席（要項・会場案内の指示に従う）",
        "受付〜着席：受験票・身分証の提示、座席確認、筆記用具の準備",
        "試験開始：問題冊を開封し、まず全体をざっと確認して時間配分を決める",
        "解答中：演習で慣れたペースを維持し、見直し用に5〜10分を確保",
        "終了〜退場：係員の指示どおり解答用紙を提出し、持ち帰り禁止物を確認して退場",
    ]
    outro = (
        "開始直前は長時間の暗記より、深呼吸で落ち着き、問題文を最後まで読む習慣を意識します。"
        f"解答時間の目安は{official}の要項と演習記録で確認してください。"
    )
    return f"{intro}\n\n{_bullet_block(items)}\n\n{outro}"


def exam_day_items_and_time_prose(*, official: str, topic: str = "") -> str:
    """持ち物と時間配分を具体項目で書き切る。"""
    intro = (
        f"受験票・要項に記載された持ち物と解答時間を、{official}で確認したうえで前日に準備します。"
    )
    items = [
        "持参：HB程度の黒い鉛筆2本以上、消しゴム、受験票、要項で求められる身分証",
        "予備：鉛筆芯の予備、ティッシュ（要項で認められる範囲）",
        "禁止：スマートフォン、参考書、電卓、辞書、ノートなど（要項の禁止リストどおり）",
        "時間配分：演習で記録した1問あたりの目安時間を維持し、最後に5〜10分の見直しを確保",
        "長文問題：設問文の条件（主体・期間・人数など）を下線メモする程度に留める",
    ]
    outro = (
        f"「{topic}」の解答時間は{official}の要項で必ず再確認し、"
        f"本番前に同じ問題数・時間で模擬演習するとペース感が定着しやすくなります。"
        if topic
        else f"解答時間は{official}の要項で必ず再確認し、本番前に同じ問題数・時間で模擬演習するとペース感が定着しやすくなります。"
    )
    return f"{intro}\n\n{_bullet_block(items)}\n\n{outro}"


def application_precheck_prose(*, official: str, topic: str) -> str:
    """申込前チェックリストを具体項目で書き切る。"""
    intro = (
        f"申込前に、{official}の受験要項で以下を確認してください。"
        f"{topic}について不明点があれば、申込前に解消します。"
    )
    items = [
        "受験資格：自分が該当する区分・要件（実務・研修・選任歴など）を要項どおり確認",
        "申込期間：締切日時と申込方法（Web・郵送など）",
        "受験料：金額・支払方法・支払期限",
        "受験地・会場：受験票に記載される会場の都市と交通",
        "必要書類：写真データ・証明書など、要項で求められる提出物",
        "学習進捗：公式テキストの主要章と演習での弱点分野の把握",
    ]
    outro = (
        "申込直後は、試験日までの週次計画を試験ガイドの学習計画記事を参考に立て直すと、"
        "残り期間を無駄なく使えます。"
    )
    return f"{intro}\n\n{_bullet_block(items)}\n\n{outro}"

