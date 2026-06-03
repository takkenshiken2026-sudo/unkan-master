#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全試験サイト guide content lib 共通の prose 生成ヘルパー。"""

from __future__ import annotations

import re
from typing import Callable

from tools.guide_topic_normalize import exam_topic_clause, topic_label

_AFFILIATE_PR_SNIPPETS = (
    "【PR・広告】本記事にはアフィリエイトリンクが含まれる場合があります。",
    "※本記事には広告・PR（アフィリエイト）を含みます。",
)


def strip_affiliate_pr_disclaimer(text: str) -> str:
    """アフィリエイト記事の PR 定型文を読者向け本文から除去する。"""
    out = text or ""
    for snippet in _AFFILIATE_PR_SNIPPETS:
        out = out.replace(snippet, "")
    out = re.sub(r"【PR・広告】\s*", "", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    return out.strip()


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
    return two_paragraphs_fn(
        f"「{heading}」は{label}の論点の一つです。"
        f"{official}の受験要項と公式テキストで整理すると、演習問題の解説と対応づけやすくなります。",
        f"{official_note_fn()} {practice_note_fn(label)}",
    )


def section_body_min_filler(heading: str, topic: str, official: str) -> str:
    """180字未満の節を補う具体文（メタ確認だけの1文は使わない）。"""
    label = (topic or heading).strip() or heading
    return (
        f"「{heading}」では、{label}について公式テキストの該当章を開き、"
        f"主体・期限・数値をメモしながら演習問題で定着を確認します。"
        f"数値・日程は{official}の最新要項で必ず照合してください。"
    )


def section_body_tail(heading: str, official: str) -> str:
    """後方互換。ensure_min 用は section_body_min_filler を使う。"""
    return section_body_min_filler(heading, "", official)


def user_intent_prose(
    topic: str,
    exam: str,
    exam_short: str,
    official: str,
    genre: str = "",
) -> str:
    clause = exam_topic_clause(exam, topic, exam_short)
    if genre == "試験概要":
        return (
            f"本記事を読むと、{clause}、"
            f"受験資格・日程・合格基準の確認手順と、演習・用語解説を組み合わせた学習の始め方が分かります。"
        )
    if genre == "受験・申込":
        return (
            f"本記事を読むと、{clause}、"
            f"申込前に要項で確認すべき項目と、受験票到着後の準備までの流れが整理できます。"
        )
    if genre == "用語ハブ活用法":
        return (
            f"本記事を読むと、{clause}、"
            f"用語解説→演習→比較表の往復で弱点を埋める具体的な手順が分かります。"
        )
    return (
        f"本記事を読むと、{clause}、"
        f"公式テキストと{official}で押さえる論点と、演習→用語解説→1週間後の解き直しまでの復習順が具体的に分かります。"
    )


def action_items_prose(
    topic: str,
    exam: str,
    exam_short: str,
    official: str,
    slug: str = "",
    genre: str = "",
) -> str:
    _ = slug, genre
    label = topic_label(topic, exam, exam_short)
    return ";".join(
        [
            f"{official}で{label}の最新要項（日程・合格基準）を確認する",
            f"演習で{label}に関連する設問を10問解き、誤答理由をノートに書く",
            f"誤答に出た用語を用語解説で定義・試験論点まで確認する",
            f"比較表・よくある誤答で{label}の混同しやすい語を整理する",
            f"1週間後に同分野の演習を解き直し、定着を確認する",
        ][:5]
    )


def faq_official_verify_answer(
    question: str,
    topic: str,
    exam: str,
    exam_short: str,
    official: str,
) -> str:
    q = (question or "").strip().rstrip("？?")
    label = topic_label(topic, exam, exam_short)
    return (
        f"「{q}」は{exam}の公式テキスト該当章と{official}で確認するのが確実です。"
        f"{label}では、条文の要件（誰が・いつ・何を）を演習問題とセットで押さえてください。"
    )


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


def exam_venue_access_prose(
    *,
    official: str,
    topic: str = "",
    venue_page_md: str = "",
) -> str:
    """試験会場・センターへのアクセス確認を具体項目まで書き切る。"""
    topic_ref = f"「{topic}」の" if topic else ""
    venue_ref = f"{venue_page_md}および" if venue_page_md else f"{official}の"
    intro = (
        f"試験前日までに、受験票と{venue_ref}会場案内で"
        f"{topic_ref}アクセス情報を確認し、以下をメモまたは印刷しておいてください。"
        f"本人に割り当てられた試験会場の正式名称・住所は受験票の表記が正本です。"
    )
    items = [
        "会場の正式名称と住所（受験票の表記どおり）",
        "最寄り駅・バス停名と、駅から会場までの徒歩ルート（出口・所要時間）",
        "試験当日用の予備ルート（遅延・運休時の電車・バスの組み合わせ）",
        "会場の入口・受付フロア（案内図がある場合は印刷または保存）",
        "駐車場・自転車置場の有無と利用可否（要項・会場案内どおり）",
        "試験開始時刻から逆算した出発時刻（開始30分前到着＋余裕30分）",
        "当日のダイヤ変更・道路工事・イベント規制の有無（前日に再確認）",
        "迷った場合の問い合わせ先（受験票または会場案内の電話番号）",
    ]
    outro = (
        "前日に地図アプリで「自宅→会場」を試験当日と同じ時間帯で検索し、"
        "所要時間の最長見積もりに30分足した時刻を出発目安にします。"
        "初めての会場は、可能であれば前日に最寄り駅から入口までのルートを実際に確認すると安心です。"
    )
    return f"{intro}\n\n{_bullet_block(items)}\n\n{outro}"


def exam_venue_basic_info_prose(
    *,
    topic: str,
    slug: str,
    official: str,
    org: str,
    venue_page_md: str = "",
) -> str:
    """センター記事「基本情報」節。"""
    from tools.exam_venue_official_links import region_for_slug

    region = region_for_slug(slug)
    venue_link = venue_page_md or official
    return (
        f"{topic}は、{org}が地域試験運営の拠点として設置する会場の一つです。"
        f"試験内容は全国共通ですが、申込時に選ぶ受験地によって割り当て会場が変わります。\n\n"
        f"{region}在住の受験者は本センターを受験地として選ぶことが多いため、"
        f"申込前に{venue_link}で会場名・所在地・アクセスマップの最新案内を確認してください。"
        f"出張試験などで会場が異なる場合もあるため、受験票の表記を必ず照合してください。"
    )


def jissh_center_list_prose(*, official: str) -> str:
    """全国センター一覧（shiken-kaijo 等）向け。"""
    from tools.exam_venue_official_links import CENTER_PAGES, EXAM_PORTAL, JISSH_VENUE_HUB, md_link

    hub_md = md_link(*JISSH_VENUE_HUB)
    portal_md = md_link(*EXAM_PORTAL)
    intro = (
        f"第二種衛生管理者試験など{official}が実施する学科試験は、全国の安全衛生技術センターで行われます。"
        f"各センターの所在地・アクセスマップは公式サイトで確認し、本文には住所や交通ルートは載せません。"
        f"本人に割り当てられた会場は受験票の表記が正本です。"
    )
    items = [md_link(label, url) for label, url in CENTER_PAGES.values()]
    outro = (
        f"センター一覧の概要は{hub_md}、試験日程・申込は{portal_md}で確認してください。"
        f"試験地選択前に、最寄りセンターまでの所要時間と当日の交通手段を前日までに確定しておくと安心です。"
    )
    return f"{intro}\n\n{_bullet_block(items)}\n\n{outro}"


def exam_application_venue_prose(
    *,
    official: str,
    topic: str = "",
    official_page_md: str = "",
) -> str:
    """申込・会場選びの手順を具体項目で書き切る。"""
    link = official_page_md or official
    intro = (
        f"申込時に受験地・会場を確定するため、{link}の受験要項で以下を確認します。"
        f"{topic + 'で受験する場合も、' if topic else ''}申込後に変更できない項目がないか要項で確認してください。"
        f"会場の正式名称・所在地・アクセスは{link}の最新案内で確認し、詳細ルートは受験票到着後に確定してください。"
    )
    items = [
        "受験地の選択肢（都市名と会場割当のルール）",
        "申込フォームの入力項目（氏名・住所・連絡先・受験地）",
        "受験票・会場案内の送付方法と届く目安時期",
        "会場変更・キャンセルの可否と手続き",
        "会場周辺の交通概略（詳細ルートは受験票到着後に確定）",
        "申込完了メール・控えの保存",
    ]
    outro = (
        "受験票が届いたら、記載の会場名・住所・アクセスと申込内容が一致しているかを確認し、"
        "不一致があれば要項記載の問い合わせ先へ早めに連絡してください。"
    )
    return f"{intro}\n\n{_bullet_block(items)}\n\n{outro}"

