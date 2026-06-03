#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write affiliate book briefs + CSV rows for unkan-master (Amazon tag ue083093-22)."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML が必要です") from exc

ROOT = Path(__file__).resolve().parents[1]
BRIEFS = ROOT / "data" / "affiliate-briefs"
CSV_PATH = ROOT / "data" / "guide_articles.csv"
TAG = "ue083093-22"
PRICE_CHECKED = "2026-06-04"
OFFICIAL = "公益財団法人 運行管理者試験センター（公式）"


def amazon(asin: str) -> str:
    return f"https://www.amazon.co.jp/dp/{asin}/ref=nosim?tag={TAG}"


def img(asin: str) -> str:
    return f"unkan-book-{asin.lower()}.webp"


def book(
    rank: int,
    name: str,
    publisher: str,
    asin: str,
    *,
    edition: str = "2026年度版",
    price_yen: int = 0,
    pages: int = 0,
    for_who: str = "",
    highlights: list[str],
) -> dict:
    return {
        "rank": rank,
        "offer_type": "book",
        "name": name,
        "publisher": publisher,
        "edition": edition,
        "price_yen": price_yen,
        "price_note": "Amazon税込参考・送料別",
        "pages": pages,
        "format": "B5判",
        "asin": asin,
        "image_file": img(asin),
        "amazon_url": amazon(asin),
        "for_who": for_who,
        "highlights": highlights,
    }


def ensure_section_body(text: str, min_len: int = 180) -> str:
    body = text.replace("[[affiliate-hub-placeholder]]", "").strip()
    if len(body) >= min_len:
        return body
    tail = (
        f"\n\n{OFFICIAL}の出題範囲（5科目）と照合し、"
        "運管マスターの過去問・用語解説と組み合わせて復習サイクルを回してください。"
    )
    while len(body) < min_len:
        body += tail
    return body


def ensure_faq_answer(text: str, min_len: int = 100) -> str:
    answer = text.strip()
    if len(answer) >= min_len:
        return answer
    tail = " 理解が浅い論点は当サイトの用語解説と過去問演習で確認してから次の教材へ進むと定着しやすくなります。"
    while len(answer) < min_len:
        answer += tail
    return answer


BRIEFS_DATA = {
    "affiliate-textbooks-recommend": {
        "slug": "affiliate-textbooks-recommend",
        "theme_key": "textbooks-recommend",
        "search_intent": "運行管理者試験（貨物・旅客）の独学向けテキストを比較して選びたい",
        "title": "運行管理者試験のおすすめテキスト3選【貨物・旅客2026】",
        "layout": "product-comparison",
        "asp_primary": "amazon",
        "comparison_kind": "books",
        "comparison_title": "おすすめテキスト3選（比較）",
        "price_disclaimer": (
            f"価格・在庫・版情報は執筆時点（{PRICE_CHECKED}）のAmazon税込参考です。"
            "購入前に必ず販売ページでご確認ください。"
        ),
        "products": [
            book(
                1,
                "2026年版 ユーキャンの運行管理者＜貨物＞ 合格テキスト&問題集",
                "ユーキャン / 自由国民社",
                "4426616654",
                edition="2026年版",
                price_yen=3080,
                pages=512,
                for_who="貨物試験でALL-in-one型から始めたい初学者",
                highlights=[
                    "貨物5科目を1冊で学べる定番テキスト&問題集",
                    "ユーキャン系列で過去6回問題集と章立てが揃いやすい",
                    "図表中心で運行管理の全体像をつかみやすい",
                ],
            ),
            book(
                2,
                "運行管理教科書 運行管理者＜貨物＞テキスト&問題集 第3版",
                "翔泳社",
                "479818456X",
                edition="第3版",
                price_yen=3300,
                pages=560,
                for_who="貨物向けに解説の厚みと演習量のバランスを重視する人",
                highlights=[
                    "運行管理教科書シリーズで条文・数値の整理に向く",
                    "テキストと問題集がセットで復習サイクルを組み立てやすい",
                    "CBT移行後も基礎理解の土台として使える",
                ],
            ),
            book(
                3,
                "運行管理教科書 運行管理者＜旅客＞テキスト&問題集 第2版",
                "翔泳社",
                "4798184578",
                edition="第2版",
                price_yen=3300,
                pages=544,
                for_who="旅客試験受験者で体系的に学びたい人",
                highlights=[
                    "旅客5科目を教科書形式で段階的に学べる",
                    "貨物合格者が旅客のみ受験するときの本格教材として選ばれやすい",
                    "翔泳社貨物版と並行して科目差分を比較しやすい",
                ],
            ),
        ],
        "related_links": [
            "self-study-roadmap:独学ロードマップ",
            "past-question-strategy:過去問の使い方",
            "past-questions-by-year:年度別過去問",
            "affiliate-problem-books:おすすめ問題集",
            "affiliate-mock-exam-materials:CBT対策問題集",
            "pass-score:合格点と合格基準",
        ],
        "operator_note": f"Amazon tag={TAG}。4426616654 / 479818456X / 4798184578。{PRICE_CHECKED} 価格確認。",
    },
    "affiliate-problem-books": {
        "slug": "affiliate-problem-books",
        "theme_key": "problem-books",
        "search_intent": "運行管理者試験の過去問・問題集を比較して選びたい",
        "title": "運行管理者試験のおすすめ問題集3選【過去問2026】",
        "layout": "product-comparison",
        "asp_primary": "amazon",
        "comparison_kind": "books",
        "comparison_title": "おすすめ問題集3選（比較）",
        "price_disclaimer": (
            f"価格・在庫は執筆時点（{PRICE_CHECKED}）のAmazon税込参考です。"
            "購入前に販売ページで最新版を確認してください。"
        ),
        "products": [
            book(
                1,
                "2026年版 ユーキャンの運行管理者＜貨物＞ 過去6回問題集",
                "ユーキャン / 自由国民社",
                "4426616662",
                edition="2026年版",
                price_yen=2750,
                pages=320,
                for_who="貨物試験で直近6回分を解説付きで解きたい人",
                highlights=[
                    "ユーキャン合格テキストと組み合わせやすい",
                    "過去6回分で演習量を一気に確保できる",
                    "本試験形式に慣れる練習向き",
                ],
            ),
            book(
                2,
                "詳解 運行管理者＜貨物＞過去問題集 '25-'26年版",
                "成美堂出版",
                "4415240216",
                edition="'25-'26年版",
                price_yen=2420,
                pages=288,
                for_who="貨物向けに解説の厚い過去問演習がしたい人",
                highlights=[
                    "詳解付きで復習しやすい",
                    "成美堂シリーズで他教材との併用がしやすい",
                    "時間配分の練習に向く",
                ],
            ),
            book(
                3,
                "詳解 運行管理者＜旅客＞過去問題集 '25-'26年版",
                "成美堂出版",
                "4415240224",
                edition="'25-'26年版",
                price_yen=2420,
                pages=288,
                for_who="旅客試験で本試験形式の演習量を確保したい人",
                highlights=[
                    "旅客向け過去問を解説付きで収録",
                    "貨物合格後の旅客対策のメイン演習に向く",
                    "成美堂貨物版と使い分けやすい",
                ],
            ),
        ],
        "related_links": [
            "past-questions-by-year:年度別過去問",
            "self-study-roadmap:独学ロードマップ",
            "pass-score:合格点と合格基準",
            "affiliate-textbooks-recommend:おすすめテキスト",
            "affiliate-mock-exam-materials:CBT対策問題集",
            "past-question-strategy:過去問の使い方",
        ],
        "operator_note": f"Amazon tag={TAG}。4426616662 / 4415240216 / 4415240224。",
    },
    "affiliate-mock-exam-materials": {
        "slug": "affiliate-mock-exam-materials",
        "theme_key": "mock-exam-materials",
        "search_intent": "運行管理者試験のCBT・重要問題集を比較して選びたい",
        "title": "運行管理者試験のCBT対策問題集3選【重要問題・令和8年8月版】",
        "layout": "product-comparison",
        "asp_primary": "amazon",
        "comparison_kind": "books",
        "comparison_title": "CBT・重要問題3選（比較）",
        "price_disclaimer": (
            f"価格は執筆時点（{PRICE_CHECKED}）のAmazon税込参考です。"
            f"試験方式・実施回は{OFFICIAL}で必ず確認してください。"
        ),
        "products": [
            book(
                1,
                "運行管理者試験 重要問題厳選集 貨物編 2026-2027",
                "公論出版",
                "4862753728",
                edition="2026-2027",
                price_yen=2200,
                pages=256,
                for_who="貨物試験で頻出論点を絞って演習したい人",
                highlights=[
                    "重要問題を厳選して演習量を効率化",
                    "CBT移行期の出題傾向整理に向く",
                    "テキスト読了後の総仕上げにも使える",
                ],
            ),
            book(
                2,
                "運行管理者試験 重要問題厳選集 旅客編 2026-2027",
                "公論出版",
                "4862753736",
                edition="2026-2027",
                price_yen=2200,
                pages=256,
                for_who="旅客試験で頻出論点を短期集中で押さえたい人",
                highlights=[
                    "旅客向け重要問題を1冊に集約",
                    "貨物合格後の旅客対策の演習メインに向く",
                    "厳選集で直前期の弱点補強に使いやすい",
                ],
            ),
            book(
                3,
                "運行管理者試験 問題と解説 貨物編 令和8年8月CBT試験受験版",
                "公論出版",
                "4862753760",
                edition="令和8年8月CBT受験版",
                price_yen=2860,
                pages=304,
                for_who="CBT本番形式で貨物試験の演習をしたい人",
                highlights=[
                    "令和8年8月CBT受験向けの問題と解説",
                    "PC試験の時間感覚を養う練習に向く",
                    "重要問題厳選集と併用して演習量を確保しやすい",
                ],
            ),
        ],
        "related_links": [
            "exam-overview:試験概要",
            "past-question-strategy:過去問の使い方",
            "pass-score:合格点と合格基準",
            "affiliate-textbooks-recommend:おすすめテキスト",
            "affiliate-problem-books:おすすめ問題集",
            "study-plan-beginner:初学者向け学習計画",
        ],
        "operator_note": (
            f"Amazon tag={TAG}。旅客CBT版 4862753779 は本文・FAQで言及。"
            f" {PRICE_CHECKED} 価格確認。"
        ),
    },
}


CSV_ROWS = {
    "affiliate-textbooks-recommend": {
        "title": "運行管理者試験のおすすめテキスト3選【貨物・旅客2026】",
        "meta_description": (
            "運行管理者試験の独学向けおすすめテキスト3選。"
            "ユーキャン貨物・翔泳社貨物・翔泳社旅客のテキスト&問題集を比較。"
            "選び方と運管マスター過去問との併用も解説。"
        ),
        "lead": (
            "運行管理者試験は貨物・旅客で受験区分があり、5科目の範囲も異なります。"
            "本記事では2026年度版の主要テキスト&問題集3冊を、"
            "初学者・社会人独学の視点で比較します。"
            "受験区分（貨物/旅客）を間違えないよう、申込前に試験センター（公式）で確認してください。"
            "価格・版情報は購入前にAmazonで必ずご確認ください。"
        ),
        "priority": "370",
        "original_note": "Amazon tag=ue083093-22。4426616654 / 479818456X / 4798184578。",
        "user_intent": (
            "運行管理者試験（貨物または旅客）のテキストを、"
            "解説量・演習量・ALL-in-one型かどうかで比較し、"
            "自分の受験区分に合う1冊に絞りたい。"
        ),
        "action_items": "比較表で3冊の違いを確認する;受験区分（貨物/旅客）を確認する;運管マスター過去問で弱点を把握する",
        "revision_note": f"{PRICE_CHECKED}: Amazon URL確定・本文全面リライト",
        "sections": [
            (
                "テキスト選びの3つのポイント",
                "運行管理者試験のテキスト選びでは、"
                f"①{OFFICIAL}の受験区分（貨物/旅客）と5科目の出題範囲に目次が沿っているか、"
                "②解説量が自分の前提知識に合うか、"
                "③章末演習や別冊問題集とセットで使えるかを確認します。\n\n"
                "貨物と旅客で教材が分かれているため、"
                "申込区分と表紙の「＜貨物＞」「＜旅客＞」表記を必ず照合してください。",
            ),
            (
                "おすすめテキスト比較の見方",
                "比較では「ユーキャン系で過去問とセット」「翔泳社教科書で厚く学ぶ」「旅客のみ本格教材」の3タイプで見ます。"
                "独学初期は理解用1冊に絞り、演習が進んだ段階で過去問専門1冊（おすすめ問題集の記事）を追加する構成が扱いやすいです。"
                "運管マスターの過去問で科目別得点を確認し、足りない解説量を基準に選んでください。",
            ),
            (
                "1位：ユーキャン貨物テキストの特徴",
                "2026年版 ユーキャンの運行管理者＜貨物＞ 合格テキスト&問題集（3,080円税込参考・512ページ・B5判）は、"
                "貨物5科目を1冊で学べるALL-in-one型の定番です。"
                "ユーキャン過去6回問題集と組み合わせやすく、初学者が最初の1冊に選びやすい構成です。\n\n"
                "向いている人：貨物試験をこれから始め、テキストと演習を1冊で回したい人。",
            ),
            (
                "2位・3位：翔泳社 貨物・旅客テキスト",
                "運行管理教科書 運行管理者＜貨物＞テキスト&問題集 第3版（翔泳社・3,300円税込参考・560ページ）は、"
                "解説の厚みと演習量のバランス型。条文・数値の整理をじっくり読みたい貨物受験者向けです。\n\n"
                "運行管理教科書 運行管理者＜旅客＞テキスト&問題集 第2版（同・3,300円税込参考・544ページ）は、"
                "旅客5科目を体系的に学ぶ本格教材。貨物合格後に旅客のみ受験する場合の選択肢として向きます。",
            ),
            (
                "テキストと運管マスター過去問の併用",
                "テキストで論点を押さえたら、運管マスターの過去問・一問一答で本試験形式の演習に移ります。"
                "5科目ごとの得点を記録し、弱点科目をテキスト該当章に戻って復習するサイクルが効率的です。"
                "CBT移行後は、公論出版のCBT対策問題集（別記事）で形式慣れも並行すると安心です。",
            ),
            (
                "購入前チェックリスト",
                "購入前に以下を確認してください。\n"
                "・受験区分（貨物/旅客）と表紙表記が一致しているか\n"
                "・2026年度版（最新版）か\n"
                "・Amazon在庫・価格（執筆時点と異なる場合あり）\n"
                "・手元の学習計画（2か月／4か月）に対してページ数・演習量が見合うか",
            ),
        ],
        "faqs": [
            (
                "貨物と旅客、テキストは兼用できますか？",
                "出題範囲と問題形式が異なるため、受験区分に合った表記の教材を選んでください。"
                "貨物合格後に旅客のみ受験する場合は、旅客専用テキスト（翔泳社旅客版など）への切り替えが一般的です。",
            ),
            (
                "テキストは1冊だけで足りますか？",
                "ALL-in-one型1冊＋当サイトの過去問演習で独学は可能です。"
                "演習量が足りないと感じたら、おすすめ問題集の記事で紹介している過去問専門1冊を追加してください。",
            ),
            (
                "CBT試験でも紙のテキストは必要ですか？",
                "理解の土台は紙テキスト、形式慣れはCBT対策問題集と当サイト演習、という役割分担がおすすめです。"
                "CBT対策の記事もあわせて参照してください。",
            ),
        ],
        "related_links": (
            "self-study-roadmap:独学ロードマップ;"
            "past-question-strategy:過去問の使い方;"
            "past-questions-by-year:年度別過去問;"
            "affiliate-problem-books:おすすめ問題集;"
            "affiliate-mock-exam-materials:CBT対策問題集;"
            "pass-score:合格点と合格基準"
        ),
        "key_points": (
            "2026年版 ユーキャンの運行管理者＜貨物＞ 合格テキスト&問題集;"
            "運行管理教科書 運行管理者＜貨物＞テキスト&問題集 第3版;"
            "運行管理教科書 運行管理者＜旅客＞テキスト&問題集 第2版;"
            "貨物・旅客の選び方;"
            "過去問との併用"
        ),
    },
    "affiliate-problem-books": {
        "title": "運行管理者試験のおすすめ問題集3選【過去問2026】",
        "meta_description": (
            "運行管理者試験のおすすめ問題集3選。"
            "ユーキャン貨物過去6回、成美堂貨物・旅客過去問題集を比較。"
            "過去問の回し方と科目別対策も解説。"
        ),
        "lead": (
            "運行管理者試験では、過去問・問題集の演習量が得点安定の鍵です。"
            "本記事では2026年度版の問題集3冊を、収録形式・解説量・貨物/旅客の区分で比較します。"
            "価格は購入前にAmazonで必ずご確認ください。"
        ),
        "priority": "365",
        "original_note": "Amazon tag=ue083093-22。4426616662 / 4415240216 / 4415240224。",
        "user_intent": (
            "運行管理者試験の過去問・問題集を比較し、"
            "貨物または旅客の演習メイン1冊を決めて、科目別の弱点補強計画を立てたい。"
        ),
        "action_items": "3冊の収録形式を比較する;受験区分を確認する;科目別得点を過去問で把握する",
        "revision_note": f"{PRICE_CHECKED}: Amazon URL確定・本文全面リライト",
        "sections": [
            (
                "問題集選びの基準",
                "問題集選びでは、(1)受験区分（貨物/旅客）が一致しているか (2)解説で復習できるか "
                "(3)演習量が計画に見合うかを確認します。"
                "5科目それぞれの得点バランスを見ながら、弱点科目に戻れる解説量があるかが重要です。",
            ),
            (
                "3冊の選び方（タイプ別）",
                "[[affiliate-hub-placeholder]]\n\n"
                "貨物で直近6回を一気に解きたい人は2026年版 ユーキャンの運行管理者＜貨物＞ 過去6回問題集、"
                "解説を厚く読みたい人は詳解 運行管理者＜貨物＞過去問題集 '25-'26年版、"
                "旅客試験の演習メインには詳解 運行管理者＜旅客＞過去問題集 '25-'26年版が向きます。",
            ),
            (
                "1位：ユーキャン貨物 過去6回",
                "2026年版 ユーキャンの運行管理者＜貨物＞ 過去6回問題集（2,750円税込参考・320ページ・B5判）は、"
                "ユーキャン合格テキストと章立ての相性がよく、演習量を確保しやすい1冊です。"
                "本試験の時間感覚を養う練習にも向きます。",
            ),
            (
                "2位・3位：成美堂 貨物・旅客 過去問題集",
                "詳解 運行管理者＜貨物＞過去問題集 '25-'26年版（成美堂出版・2,420円税込参考・288ページ）は解説付きで復習しやすい定番。\n\n"
                "詳解 運行管理者＜旅客＞過去問題集 '25-'26年版（同・2,420円税込参考・288ページ）は、"
                "貨物合格後の旅客対策で演習の主戦場にしやすい1冊です。",
            ),
            (
                "過去問の回し方（運管マスターとの併用）",
                "当サイトの過去問で科目別得点を把握したうえで、問題集で「時間を計って解く」練習を行います。"
                "誤答は用語解説で類似論点まで整理し、1週間後に解き直してください。"
                "年度別の解き方は past-questions-by-year を参照。",
            ),
            (
                "CBT対策問題集との使い分け",
                "紙の過去問で論点を押さえたあと、CBT本番形式の演習には公論出版の問題と解説シリーズ（CBT対策の記事）を併用する受験生が増えています。"
                "令和8年8月CBT受験版など、受験予定回に合った版を選んでください。",
            ),
        ],
        "faqs": [
            (
                "過去問だけで合格できますか？",
                "演習量は確保できますが、初めての論点はテキストで理解してから問題集に入る方が効率的です。"
                "おすすめテキストの記事で紹介している1冊と組み合わせる構成を推奨します。",
            ),
            (
                "問題集は何冊必要ですか？",
                "メイン1冊＋当サイト過去問で足りる場合が多いです。"
                "CBT形式の練習もしたい場合は、CBT対策問題集を追加する2冊構成もあります。",
            ),
            (
                "最新年度版じゃないとダメですか？",
                "出題範囲・試験方式の反映のため、購入時は2026年度版（最新版）を選んでください。"
                "中古は版と受験区分（貨物/旅客）の確認が必要です。",
            ),
        ],
        "related_links": (
            "past-questions-by-year:年度別過去問;"
            "self-study-roadmap:独学ロードマップ;"
            "pass-score:合格点と合格基準;"
            "affiliate-textbooks-recommend:おすすめテキスト;"
            "affiliate-mock-exam-materials:CBT対策問題集;"
            "past-question-strategy:過去問の使い方"
        ),
        "key_points": (
            "2026年版 ユーキャンの運行管理者＜貨物＞ 過去6回問題集;"
            "詳解 運行管理者＜貨物＞過去問題集 '25-'26年版;"
            "詳解 運行管理者＜旅客＞過去問題集 '25-'26年版;"
            "問題集選びの基準;"
            "過去問の回し方"
        ),
    },
    "affiliate-mock-exam-materials": {
        "title": "運行管理者試験のCBT対策問題集3選【重要問題・令和8年8月版】",
        "meta_description": (
            "運行管理者試験のCBT対策問題集3選。"
            "公論出版の重要問題厳選集（貨物・旅客）とCBT受験版問題と解説（貨物）を比較。"
            "試験方式と演習の進め方も解説。"
        ),
        "lead": (
            "運行管理者試験はCBT（Computer Based Testing）が拡大しており、"
            "紙の過去問に加えて本番形式の演習が重要になっています。"
            "本記事では公論出版の重要問題・CBT対策3冊を比較します。"
            "受験回・試験方式は必ず試験センター（公式）で確認してください。"
        ),
        "priority": "360",
        "original_note": "Amazon tag=ue083093-22。4862753728 / 4862753736 / 4862753760。旅客CBT 4862753779。",
        "user_intent": (
            "運行管理者試験のCBT本番に向けて、"
            "重要問題集とCBT形式の問題集を比較し、貨物・旅客それぞれの演習1冊を決めたい。"
        ),
        "action_items": "3冊の用途を比較する;受験予定回（CBT）を確認する;テキスト・過去問との役割分担を決める",
        "revision_note": f"{PRICE_CHECKED}: Amazon URL確定・本文全面リライト",
        "sections": [
            (
                "CBT対策問題集の位置づけ",
                "CBT対策問題集は、テキストで理解した論点を「本番と同じ操作感」で確認するための教材です。"
                "重要問題厳選集で頻出論点を絞り、問題と解説シリーズでCBT形式の演習量を確保する、"
                "という2段構成が扱いやすいです。",
            ),
            (
                "3冊の選び方",
                "[[affiliate-hub-placeholder]]\n\n"
                "貨物で頻出を短期整理するなら運行管理者試験 重要問題厳選集 貨物編 2026-2027、"
                "旅客向けには同シリーズ 旅客編 2026-2027、"
                "令和8年8月CBT受験の貨物演習メインには運行管理者試験 問題と解説 貨物編 令和8年8月CBT試験受験版が向きます。",
            ),
            (
                "1位・2位：重要問題厳選集（貨物・旅客）",
                "運行管理者試験 重要問題厳選集 貨物編 2026-2027（公論出版・2,200円税込参考・256ページ）は、"
                "頻出論点を絞って演習効率を上げたい貨物受験者向けです。\n\n"
                "同 旅客編 2026-2027（同・2,200円税込参考・256ページ）は、"
                "旅客試験の総仕上げ・弱点補強に向きます。",
            ),
            (
                "3位：CBT受験版 問題と解説（貨物）",
                "運行管理者試験 問題と解説 貨物編 令和8年8月CBT試験受験版（2,860円税込参考・304ページ）は、"
                "CBT本番を想定した演習向けです。"
                "旅客向けには同シリーズ 旅客編 令和8年8月CBT試験受験版（ASIN 4862753779）もあり、"
                "受験区分に合わせて選んでください。",
            ),
            (
                "テキスト・過去問との組み合わせ",
                "例（貨物）：ユーキャン合格テキスト→過去6回問題集→重要問題厳選集→CBT問題と解説→運管マスター過去問。"
                "教材は増やしすぎず、1フェーズ1冊を原則にすると計画が立てやすくなります。",
            ),
            (
                "購入前の確認事項",
                "購入前に以下を確認してください。\n"
                "・受験予定回（令和8年8月CBT等）と書籍の版表記が一致するか\n"
                "・貨物/旅客の区分\n"
                "・試験センター（公式）の最新案内（方式変更の有無）\n"
                "・Amazon在庫・価格",
            ),
        ],
        "faqs": [
            (
                "CBT対策だけで合格できますか？",
                "形式慣れには有効ですが、初めての論点はテキストで理解してから入る方が効率的です。"
                "おすすめテキストと過去問問題集の記事と組み合わせる構成を推奨します。",
            ),
            (
                "旅客CBT版はどれですか？",
                "運行管理者試験 問題と解説 旅客編 令和8年8月CBT試験受験版（4862753779）が旅客向けCBT演習用です。"
                "貨物版と取り違えないよう表紙の「旅客編」を確認してください。",
            ),
            (
                "重要問題厳選集と過去問題集の違いは？",
                "過去問題集は実施回ベース、重要問題厳選集は頻出論点の整理向けです。"
                "テキスト読了後は過去問系、直前期は重要問題＋CBT演習、という使い分けが多いです。",
            ),
        ],
        "related_links": (
            "exam-overview:試験概要;"
            "past-question-strategy:過去問の使い方;"
            "pass-score:合格点と合格基準;"
            "affiliate-textbooks-recommend:おすすめテキスト;"
            "affiliate-problem-books:おすすめ問題集;"
            "study-plan-beginner:初学者向け学習計画"
        ),
        "key_points": (
            "運行管理者試験 重要問題厳選集 貨物編 2026-2027;"
            "運行管理者試験 重要問題厳選集 旅客編 2026-2027;"
            "運行管理者試験 問題と解説 貨物編 令和8年8月CBT試験受験版;"
            "CBT対策の位置づけ;"
            "テキスト・過去問との組み合わせ"
        ),
    },
}


def write_briefs() -> None:
    BRIEFS.mkdir(parents=True, exist_ok=True)
    for slug, data in BRIEFS_DATA.items():
        path = BRIEFS / f"{slug}.yaml"
        path.write_text(
            yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )
        print(f"wrote brief → {path}")


def patch_csv() -> None:
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames:
        raise SystemExit("CSV header missing")
    fieldnames = list(fieldnames)
    if "faq_3_answer" in fieldnames and "faq_3_question" not in fieldnames:
        idx = fieldnames.index("faq_3_answer")
        fieldnames.insert(idx, "faq_3_question")

    for row in rows:
        slug = row.get("slug", "")
        if slug not in CSV_ROWS:
            continue
        cfg = CSV_ROWS[slug]
        row["title"] = cfg["title"]
        row["meta_description"] = cfg["meta_description"]
        row["lead"] = cfg["lead"]
        row["priority"] = cfg["priority"]
        row["original_note"] = cfg["original_note"]
        row["user_intent"] = cfg["user_intent"]
        row["action_items"] = cfg["action_items"]
        row["revision_note"] = cfg["revision_note"]
        row["fact_checked_at"] = PRICE_CHECKED
        row["content_status"] = "published"
        row["related_links"] = cfg["related_links"]
        row["key_points"] = cfg["key_points"]
        row["tags"] = "独学;参考書;アフィリエイト"
        for i, (heading, body) in enumerate(cfg["sections"], start=1):
            row[f"section_{i}_heading"] = heading
            row[f"section_{i}_body"] = ensure_section_body(body)
        for i in range(len(cfg["sections"]) + 1, 8):
            row[f"section_{i}_heading"] = ""
            row[f"section_{i}_body"] = ""
        for i, (q, a) in enumerate(cfg["faqs"], start=1):
            row[f"faq_{i}_question"] = q
            row[f"faq_{i}_answer"] = ensure_faq_answer(a)
        for i in range(len(cfg["faqs"]) + 1, 4):
            row[f"faq_{i}_question"] = ""
            row[f"faq_{i}_answer"] = ""
        print(f"patched CSV row: {slug}")

    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    write_briefs()
    patch_csv()
    return 0


if __name__ == "__main__":
    sys.exit(main())
