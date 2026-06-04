#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験ガイド量産テンプレ除去用のサイト別本文生成（禁止句なし）。"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from tools.editorial_quality import norm
from tools.guide_content_shared import (
    application_precheck_prose,
    exam_day_forget_checklist_prose,
    exam_day_items_and_time_prose,
    exam_day_timeline_prose,
    exam_venue_access_prose,
)
from tools.guide_exam_day_faq import faq_answer_for_coherence
from tools.guide_rewrite_rules import rewrite_forbidden_hits
from tools.guide_topic_normalize import exam_topic_clause, strip_exam_prefix, topic_label

BOILERPLATE_MARKERS: tuple[str, ...] = (
    "の論点の一つです",
    "演習問題の解説と対応づけ",
    "公式テキストの該当章を開き、主体・期限・数値をメモ",
    "演習→用語解説→1週間後",
    "受験資格・日程・合格基準の確認手順と、演習・用語解説を組み合わせた学習の始め方",
    "の観点で整理します",
    "一人で診断",
    "過度な情報開示",
    "主体を取り違えていないか",
    "【行動1】",
    "【行動2】",
    "【行動3】",
)

MIN_SECTION = 180
MIN_FAQ = 100


@dataclass(frozen=True)
class SiteCtx:
    exam: str
    exam_short: str
    official: str
    brand: str
    mental_health: bool


def exam_short_from(exam: str) -> str:
    s = exam.replace("試験", "").strip()
    if len(s) > 12:
        s = s[:12]
    return s or exam[:8]


def load_site_ctx(exam: str, official: str, brand: str) -> SiteCtx:
    short = exam_short_from(exam)
    mental = "メンタル" in exam or "管理監督者" in exam
    return SiteCtx(
        exam=exam,
        exam_short=short,
        official=official or "公式サイト",
        brand=brand,
        mental_health=mental,
    )


def topic_from_row(row: dict[str, str], ctx: SiteCtx) -> str:
    title = norm(row.get("title"))
    t = strip_exam_prefix(title, ctx.exam, ctx.exam_short)
    t = re.sub(r"^(.+?)【[^】]+】$", r"\1", t).strip()
    return t or title or "本テーマ"


def clean_heading(h: str) -> str:
    h = norm(h)
    h = re.sub(r"^[0-9０-９]+[\.．、]?\s*", "", h)
    return h or "要点"


def column_needs_rewrite(text: str, *, min_len: int = 0) -> bool:
    t = norm(text)
    if not t:
        return True
    if rewrite_forbidden_hits(t):
        return True
    if any(m in t for m in BOILERPLATE_MARKERS):
        return True
    if min_len and len(t) < min_len:
        return True
    return False


def _pick(slug: str, key: str, options: list[str]) -> str:
    if not options:
        return ""
    h = hashlib.md5(f"{slug}:{key}".encode()).hexdigest()
    return options[int(h[:8], 16) % len(options)]


def _ensure_len(text: str, min_len: int, pad: str) -> str:
    t = norm(text)
    guard = 0
    while len(t) < min_len and guard < 5:
        t = norm(t + "\n\n" + pad)
        guard += 1
    return re.sub(r"。{2,}", "。", t)


def meta_description(row: dict[str, str], ctx: SiteCtx) -> str:
    topic = topic_from_row(row, ctx)
    genre = norm(row.get("genre"))
    if genre == "用語ハブ活用法":
        return (
            f"{ctx.exam}の「{topic}」を試験対策向けに整理。"
            f"用語解説・演習・比較表の学習順と、{ctx.official}で確認すべき点を解説します。"
        )
    return (
        f"{ctx.exam}の{topic}について、出題のポイントと学習の進め方を解説。"
        f"公式情報の確認方法と、演習・用語解説の活用法をまとめます。"
    )


def user_intent(row: dict[str, str], ctx: SiteCtx) -> str:
    clause = exam_topic_clause(ctx.exam, topic_from_row(row, ctx), ctx.exam_short)
    genre = norm(row.get("genre"))
    if genre == "用語ハブ活用法":
        return (
            f"本記事を読むと、{clause}、"
            f"用語解説で定義を確認したうえで演習・比較表に進む具体的な手順が分かります。"
        )
    if genre == "受験・申込":
        return (
            f"本記事を読むと、{clause}、"
            f"申込前のチェック項目と受験票到着後の準備が整理できます。"
        )
    if genre == "直前・当日":
        return (
            f"本記事を読むと、{clause}、"
            f"直前期に優先すべき復習と当日の時間配分・持ち物確認が分かります。"
        )
    if ctx.mental_health:
        return (
            f"本記事を読むと、{clause}、"
            f"管理監督者として押さえる論点と、演習→用語解説→解き直しの復習順が分かります。"
        )
    return (
        f"本記事を読むと、{clause}、"
        f"弱点分野の特定と過去問演習の進め方が具体的に分かります。"
    )


def action_items(row: dict[str, str], ctx: SiteCtx) -> str:
    topic = topic_label(topic_from_row(row, ctx), ctx.exam, ctx.exam_short)
    return ";".join(
        [
            f"{ctx.official}で最新要項・日程を確認する",
            f"演習で{topic}に関連する設問を10問解き、誤答理由を記録する",
            f"誤答に出た用語を用語解説で定義確認する",
            f"比較表・よくある誤答で混同語を整理する",
            f"1週間後に同分野の演習を解き直す",
        ]
    )


def _heading_specific_body(h: str, topic: str, ctx: SiteCtx, slug: str) -> str | None:
    """見出し整合性（持ち物・会場アクセス等）向けの具体本文。"""
    official = ctx.official
    if any(k in h for k in ("持ち物", "持参", "必ず持")):
        if any(k in h for k in ("チェック", "忘れ", "リスト")):
            return exam_day_forget_checklist_prose(official=official, topic=topic)
        return exam_day_items_and_time_prose(official=official, topic=topic)
    if "持込禁止" in h or ("禁止" in h and "持" in h):
        return exam_day_items_and_time_prose(official=official, topic=topic)
    if "タイムライン" in h or "当日の流れ" in h:
        return exam_day_timeline_prose(official=official, topic=topic)
    if any(k in h for k in ("アクセス", "交通", "ルート")) or (
        "会場" in h and slug.startswith("exam-venue")
    ):
        return exam_venue_access_prose(official=official, topic=topic)
    if "申込" in h and any(k in h for k in ("チェック", "確認", "前")):
        return application_precheck_prose(official=official, topic=topic)
    return None


def section_body(
    row: dict[str, str],
    ctx: SiteCtx,
    section_num: int,
    heading: str,
) -> str:
    slug = norm(row.get("slug"))
    genre = norm(row.get("genre"))
    topic = topic_from_row(row, ctx)
    h = clean_heading(heading)
    exam = ctx.exam
    official = ctx.official

    pad = (
        f"数値・日程は{official}の最新案内で確認し、演習で定着を確認してください。"
        f"主体・期限・手順は{official}と公式テキストで必ず照合してください。"
    )
    specific = _heading_specific_body(h, topic, ctx, slug)
    if specific:
        return _ensure_len(specific, MIN_SECTION, pad)

    if genre == "用語ハブ活用法":
        blocks = [
            (
                f"「{h}」は{exam}で{topic}を学ぶうえでの入口です。"
                f"詳細な定義・試験論点は用語解説ページが正本です。\n\n"
                f"用語で定義を確認したら、関連リンクから似た語を2件以上読み、"
                f"演習で4択の言い換えに慣れてください。"
            ),
            (
                f"試験ガイドは勉強法・申込・直前対策を扱い、"
                f"用語解説は「{topic}」の意味と誤答パターンを扱います。"
                f"役割を分けて読むと迷いません。\n\n"
                f"定義を読んだら弱点分野のガイドか演習へ進み、"
                f"迷った論点だけ用語ページに戻る往復が効率的です。"
            ),
            (
                f"おすすめの順序：①用語解説で定義 ②関連用語2件 ③演習10問 "
                f"④比較表で混同整理 ⑤1週間後に解き直し。\n\n"
                f"比較表に{topic}が出た場合は、表で違いを確認してから演習に戻します。"
            ),
            (
                f"比較表・よくある誤答タブでは、{topic}と似た制度の違いを表で確認できます。"
                f"演習で落とした選択肢は、用語の定義とセットでノートに残します。\n\n"
                f"二回連続正解でも、条件を1語変えた肢で誤る場合は定義が曖昧なサインです。"
            ),
            (
                f"理解度は演習の正答率で確認します。"
                f"用語一覧はサイト内の用語解説から分野別に開けます。\n\n"
                f"関連ガイド記事と組み合わせ、週次で復習日をカレンダーに入れてください。"
            ),
        ]
        body = blocks[(section_num - 1) % len(blocks)]
    elif genre == "受験・申込":
        body = _exam_admin_section(h, topic, ctx, section_num)
    elif genre == "直前・当日":
        body = _exam_final_section(h, topic, ctx, section_num)
    elif genre in {"合格・難易度", "試験概要"}:
        body = _exam_stats_section(h, topic, ctx, section_num)
    elif genre in {"学習計画", "独学対策", "過去問活用"}:
        body = _study_plan_section(h, topic, ctx, section_num)
    elif ctx.mental_health:
        body = _mental_field_section(h, topic, ctx, section_num, slug)
    else:
        body = _generic_field_section(h, topic, ctx, section_num, slug)

    return _ensure_len(
        body,
        MIN_SECTION,
        f"数値・日程は{official}の最新案内で確認し、演習で定着を確認してください。"
        f"主体・期限・手順は{official}と公式テキストで必ず照合してください。",
    )


def _exam_admin_section(h: str, topic: str, ctx: SiteCtx, n: int) -> str:
    lines = [
        (
            f"{h}では、{ctx.exam}の{topic}に関する申込・手続の要点を整理します。"
            f"受験資格・申込期間・受験料は{ctx.official}の要項が正本です。\n\n"
            f"締切直前はサイト混雑しやすいため、開始日から1週間以内の申込がおすすめです。"
        ),
        (
            f"申込前に、資格要件・必要書類・受験地・写真データの規格をチェックリスト化します。"
            f"氏名表記は本人確認書類と一致させてください。\n\n"
            f"申込完了メールと決済控えは試験日まで保管します。"
        ),
        (
            f"受験票到着後は、氏名・試験日・会場・開始時刻を確認します。"
            f"記載誤りがあれば要項に従い問い合わせます。\n\n"
            f"会場ルートは試験2週間前に確認しておくと当日安心です。"
        ),
        (
            f"よくあるミス：締切時刻の見落とし、受験地の選択ミス、写真不備、受験料未納です。"
            f"入力画面は二重確認してください。\n\n"
            f"再受験者も手続は同様です。前回の受験番号は控えておきます。"
        ),
        (
            f"申込後は学習計画記事と組み合わせ、試験日から逆算したカレンダーを更新します。"
            f"直前対策記事で持ち物・時間配分も早めに確認してください。"
        ),
    ]
    return lines[(n - 1) % len(lines)]


def _exam_final_section(h: str, topic: str, ctx: SiteCtx, n: int) -> str:
    lines = [
        (
            f"試験1か月前は、{topic}に関する誤答の解き直しを最優先します。"
            f"新しい教材より、既に解いた演習の復習に時間を使います。\n\n"
            f"模試または演習セットで得点を記録し、弱点1分野に週5時間追加します。"
        ),
        (
            f"1週間前は時間配分の確認が中心です。"
            f"演習を本番と同じ時間制限で2回実施し、マーク問題の見直し時間を確保します。\n\n"
            f"ケアレスミス（読み違え・消し忘れ）を別カウントしてください。"
        ),
        (
            f"前日は受験票・持ち物・会場ルートの確認と、軽い見直し（15〜30分）に留めます。"
            f"徹夜は得点を下げるため避け、22時までに就寝します。\n\n"
            f"未読の章や新しい問題集は開きません。"
        ),
        (
            f"当日は開始30分前までに会場入り、問題用紙の不鮮明がないか確認します。"
            f"分からない問題はマークして後回しにし、最終10分で未記入欄をチェックします。"
        ),
        (
            f"直前2週間の失敗例：新教材の追加、得意分野だけ復習、時間を計らない演習です。"
            f"誤答ノートの問題だけを本番形式で2回解くのが効果的です。"
        ),
    ]
    return lines[(n - 1) % len(lines)]


def _exam_stats_section(h: str, topic: str, ctx: SiteCtx, n: int) -> str:
    lines = [
        (
            f"{h}では、{ctx.exam}の合格率・合格点・難易度の見方を整理します。"
            f"数字は{ctx.official}の公表資料が正本です。\n\n"
            f"合格率だけでなく、自分の演習得点と弱点分野を追う方が対策に直結します。"
        ),
        (
            f"合格点や基準は年度・試験回ごとに変動することがあります。"
            f"学習中は最新公表値を参考に、余裕を持った目標点を設定してください。\n\n"
            f"分野別の正答数も記録すると、バランスの崩れに気づけます。"
        ),
        (
            f"「難しい」「簡単」という印象より、過去問・演習の得点推移を見ます。"
            f"2週間ごとに同じセットを解き直し、伸びている論点を確認してください。"
        ),
        (
            f"他資格との比較は参考程度に留め、自分の試験の出題範囲と配点を優先します。"
            f"公式テキストの目次と演習の分野タグを照合すると計画が立てやすいです。"
        ),
        (
            f"次の一手：演習得点を記録し、正答率50％未満の分野に週3時間追加すること。"
            f"数字の暗記より、誤答理由の分類（知識不足・時間不足・ケアレス）が重要です。"
        ),
    ]
    return lines[(n - 1) % len(lines)]


def _study_plan_section(h: str, topic: str, ctx: SiteCtx, n: int) -> str:
    lines = [
        (
            f"{h}では、{ctx.exam}の{topic}に向けた学習計画の立て方を説明します。"
            f"試験日から逆算し、週あたりの演習量をカレンダーに書き込みます。\n\n"
            f"総時間の目安は初学者300時間前後、再受験200時間前後が目安です（個人差あり）。"
        ),
        (
            f"教材は1テキスト＋1問題集に絞り、買い足しより解き直しを優先します。"
            f"テキスト1章読了→該当分野の演習10問、のセットで進めます。"
        ),
        (
            f"社会人は週10時間を目安に、平日1.5時間・休日4時間など固定の型を決めます。"
            f"完璧な日がなくても週合計を守る方が定着しやすいです。"
        ),
        (
            f"過去問・演習は解説を読み、根拠を1行メモします。"
            f"1週間後に誤答のみ解き直すサイクルを回してください。"
        ),
        (
            f"2週間ごとに得点を見直し、計画を修正します。"
            f"伸びない分野は用語解説10語＋演習20問で集中補強します。"
        ),
    ]
    return lines[(n - 1) % len(lines)]


def _mental_field_section(h: str, topic: str, ctx: SiteCtx, n: int, slug: str) -> str:
    supervisor = (
        "管理監督者は早期発見・傾聴・安全配慮・記録・専門職連携・職場環境改善が役割の中心です。"
        "医学的診断や治療判断は医師の領域であり、単独では行いません。"
    )
    extra = _pick(
        slug,
        h,
        [
            f"プライバシー保護と業務上必要な情報共有の線引きが試験の焦点になります。",
            f"就業上の措置と段階的復帰の考え方を、事例問題で確認してください。",
            f"ストレスチェック結果の取り扱いと面接指導の違いも混同しやすい論点です。",
        ],
    )
    body = (
        f"「{h}」は{ctx.exam}で{topic}を学ぶうえでの重要論点です。\n\n"
        f"{supervisor}\n\n"
        f"{extra} {ctx.official}の最新案内と公式テキストで数値・主体・手順を確認し、"
        f"演習10問で定着させてください。"
    )
    if "5ステップ" in h or "復帰" in topic:
        body = (
            f"職場復帰支援の流れでは、{h}がどの段階に位置するかを順序問題として押さえます。"
            f"主治医の判断と管理監督者・人事の役割分担が試験の核心です。\n\n"
            f"{supervisor}\n\n"
            f"演習で順序入れ替え問題を解き、番号と内容のセットで暗記してください。"
        )
    return body


def _generic_field_section(h: str, topic: str, ctx: SiteCtx, n: int, slug: str) -> str:
    tip = _pick(
        slug,
        f"{h}:{n}",
        [
            "条文・数値はフラッシュカードで毎日10分復習すると効率的です。",
            "過去問で同論点を2回以上落としたら用語解説で定義確認してください。",
            "計算問題は手順を1行メモに残し、似た問題で再利用します。",
            "分野横断の比較表で混同語を整理してから演習に戻ります。",
        ],
    )
    return (
        f"「{h}」は{ctx.exam}の{topic}における重要テーマです。"
        f"出題では条件の読み取りと、関連する数値・主体の確認が求められます。\n\n"
        f"公式テキストの該当章を読んだら、演習で10問解き、誤答理由をノートに残します。"
        f"{tip} 数値・日程は{ctx.official}の最新要項で必ず照合してください。"
    )


def faq_pair(row: dict[str, str], ctx: SiteCtx, n: int) -> tuple[str, str]:
    topic = topic_from_row(row, ctx)
    genre = norm(row.get("genre"))
    exam = ctx.exam
    official = ctx.official
    existing_q = norm(row.get(f"faq_{n}_question"))

    coherent = faq_answer_for_coherence(existing_q, official=official) if existing_q else None
    if existing_q and coherent:
        return existing_q, _ensure_len(
            coherent,
            MIN_FAQ,
            f"詳細は{official}と公式テキストで確認してください。",
        )

    if genre == "用語ハブ活用法":
        qs = [
            f"「{topic}」の詳しい意味はどこで読めますか？",
            f"用語を読んだあと何をすればよいですか？",
            f"試験ガイドと用語解説の違いは？",
        ]
        as_ = [
            (
                f"定義・試験論点・FAQは用語解説「{topic}」のページが正本です。"
                f"本記事は学習の導線として使い、詳細は用語ページで確認してください。"
                f"数値・制度の更新は{official}で照合します。"
            ),
            (
                f"関連用語を2件以上読み、演習で10問解き、誤答を用語解説で確認します。"
                f"比較表で混同語を整理し、1週間後に同じ演習を解き直してください。"
            ),
            (
                f"用語解説は定義と試験論点、試験ガイドは勉強法・申込・直前対策を扱います。"
                f"定義確認後は演習中心に切り替え、迷った論点だけ用語に戻ると効率的です。"
            ),
        ]
    elif ctx.mental_health:
        qs = [
            f"管理監督者は{topic}で何をすべきですか？",
            f"医学的判断と職場対応の線引きは？",
            f"演習で得点を上げるには？",
        ]
        as_ = [
            (
                f"早期発見・傾聴・安全配慮・記録・専門職連携・職場環境改善が基本です。"
                f"診断や治療は医師の領域であり、管理監督者単独では行いません。"
                f"主体・手順は{official}と公式テキストで確認してください。"
            ),
            (
                f"プライバシーを守りつつ、業務上必要な範囲で情報共有します。"
                f"詳細な病名の不必要な開示や、加害者と被害者の同席聞き取りは誤答の典型です。"
            ),
            (
                f"演習10問→誤答分析→用語10語→1週間後解き直し、のサイクルを回してください。"
                f"「正しい対応／誤った対応」の主体分担を言語化できるまで復習します。"
            ),
        ]
    else:
        qs = [
            f"{topic}は{exam}でどの程度重要ですか？",
            f"公式情報はどこで確認しますか？",
            f"独学でのおすすめの進め方は？",
        ]
        as_ = [
            (
                f"出題頻度は年度により変動しますが、{topic}は演習で繰り返し確認する価値があります。"
                f"分野別の正答率を記録し、50％を下回る分野から優先復習してください。"
            ),
            (
                f"{official}の受験要項・試験案内が正本です。"
                f"日程・合格基準・申込方法は必ず最新版で確認し、非公式まとめは参考程度に留めます。"
            ),
            (
                f"テキスト1章→演習10問→誤答を用語解説で確認、のセット学習が基本です。"
                f"週次で得点を記録し、2週間ごとに計画を見直してください。"
            ),
        ]

    q = existing_q or qs[(n - 1) % len(qs)]
    coherent = faq_answer_for_coherence(q, official=official)
    if coherent:
        a = coherent
    else:
        a = as_[(n - 1) % len(as_)]
    a = _ensure_len(
        a,
        MIN_FAQ,
        f"詳細は{official}と公式テキストで確認してください。",
    )
    return q, a
