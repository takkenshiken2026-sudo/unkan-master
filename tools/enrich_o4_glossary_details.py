#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
実践演習・一問一答DBの解説を集約し、glossary_terms.csv の用語詳細記事列を充実させる。

  python3 tools/enrich_o4_glossary_details.py
  python3 tools/enrich_o4_glossary_details.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.site_config import brand_name, exam_name  # noqa: E402

CSV_PATH = ROOT / "data" / "glossary_terms.csv"
PRACTICE = ROOT / "data" / "imported" / "o4_practice_500_source.csv"
ICHIMON = ROOT / "data" / "imported" / "o4_ichimon_500_source.csv"

EXAM = exam_name()
BRAND = brand_name()

KEEP_TERMS = {
    "公式情報",
    "復習",
    "比較表",
    "試験要項",
    "受験資格",
    "合格基準",
    "出題範囲",
    "過去問",
    "一問一答",
    "模擬試験",
    "用語解説",
    "学習記録",
}

# 学習メタ用語（詳細記事の自動生成対象外・ガイド的な短い説明のみ）
META_STUDY_TERMS = frozenset({"ひっかけ対策", "よくある混同論点"})

META_PEER_TERMS = KEEP_TERMS | META_STUDY_TERMS | frozenset({"ひっかけ問題"})

# 用語名と問題DBの topic/unit/本文キーワードの対応
TERM_SEARCH_ALIASES: dict[str, list[str]] = {
    "バックドラフト": ["バックドラフト", "密閉空間", "爆燃"],
    "フラッシュオーバー": ["フラッシュオーバー", "全焼", "急激"],
    "丙種危険物取扱者": ["丙種危険物取扱者", "丙種"],
    "乙種危険物取扱者": ["乙種危険物取扱者", "乙種"],
    "乙種第4類": ["乙種第4類", "乙4", "第4類"],
    "危険物の規制に関する政令": ["危険物の規制に関する政令", "政令", "別表第三"],
    "引火性液体": ["引火性液体", "第4類危険物"],
    "引火性蒸気": ["引火性蒸気", "可燃性蒸気", "蒸気"],
    "消防法別表第二": ["別表第二", "品名", "性状"],
    "消防法施行令": ["消防法施行令", "施行令"],
    "消防署長": ["消防署長"],
    "消防長": ["消防長"],
    "漏えい対策": ["漏えい", "漏洩", "流出"],
    "漏えい防止堤": ["漏えい防止堤", "防止堤"],
    "移動式貯蔵タンク": ["移動タンク貯蔵所", "移動タンク", "タンクローリー"],
    "移動タンク貯蔵所": ["移動タンク貯蔵所", "移動タンク", "タンクローリー"],
    "第2類危険物": ["第2類危険物", "第2類", "酸化性固体"],
    "第3類危険物": ["第3類危険物", "第3類", "自然発火", "禁水性"],
    "第5類危険物": ["第5類危険物", "第5類", "自己反応"],
    "指定数量の倍数": ["指定数量倍数", "倍数", "指定数量"],
    "泡消火": ["泡消火", "泡消火剤", "泡沫"],
    "粉末消火": ["粉末消火", "粉末消火剤"],
    "屋内貯蔵所": ["屋内貯蔵所"],
    "給油取扱所": ["給油取扱所", "ガソリンスタンド"],
    "沸点": ["沸点", "沸騰", "外圧"],
    "注水消火": ["注水", "注水消火", "非水溶性"],
    "水上泡消火": ["水上泡", "泡消火", "泡沫"],
    "密閉空間火災": ["密閉空間", "閉鎖空間", "バックドラフト"],
    "接地": ["接地", "静電気", "アース"],
    "標識": ["標識", "表示板", "危険物の表示"],
    "表示": ["表示", "表示板", "危険物の表示"],
    "消防法別表第二": ["別表第二", "品名", "性状"],
    "消防法施行令": ["施行令", "技術上の基準"],
    "消防署長": ["消防署長", "市町村"],
    "消防長": ["消防長"],
    "漏えい防止堤": ["防止堤", "漏えい防止"],
    "政令": ["危険物の規制に関する政令", "政令"],
    "別表第三": ["別表第三", "政令別表"],
    "品名": ["品名", "別表第一"],
    "性状": ["性状", "別表第二"],
    "類別": ["類別", "第1類", "第4類"],
    "保安員": ["危険物施設保安員", "施設保安員"],
    "動植物油": ["動植物油類"],
    "屋内貯蔵所": ["屋内貯蔵所", "貯蔵所基準"],
    "屋外タンク貯蔵所": ["屋外タンク貯蔵所", "タンク貯蔵所"],
    "給油取扱所": ["給油取扱所", "ガソリンスタンド"],
    "移送取扱所": ["移送取扱所", "移送"],
    "一般取扱所": ["一般取扱所", "取扱所"],
    "販売取扱所": ["販売取扱所", "取扱所"],
    "倍数計算": ["指定数量倍数", "倍数"],
    "設置許可": ["設置許可", "製造所等の設置"],
    "変更許可": ["変更許可", "製造所等の変更"],
    "選任": ["選任", "危険物施設保安員"],
    "譲渡": ["譲渡", "引渡し"],
    "引渡し": ["引渡し", "譲渡"],
    "混載": ["混載", "混載制限"],
    "消火剤": ["消火剤", "泡消火剤", "粉末消火剤"],
    "粉末消火剤": ["粉末消火", "粉末消火剤"],
    "第1石油類": ["第一石油類", "第1石油類"],
    "第2石油類": ["第二石油類", "第2石油類"],
    "第3石油類": ["第三石油類", "第3石油類"],
    "水溶性液体": ["水溶性", "水溶性液体"],
    "非水溶性液体": ["非水溶性", "非水溶性液体"],
    "非水溶性": ["非水溶性液体", "非水溶性"],
    "冷却": ["冷却消火"],
    "窒息": ["窒息消火"],
    "注水": ["注水消火", "注水"],
    "流出": ["漏えい", "流出"],
    "火気": ["火気管理", "火気厳禁"],
    "火気厳禁": ["火気", "裸火"],
    "可燃性": ["可燃性", "引火性"],
    "引火性": ["引火性", "可燃性"],
    "酸化性": ["酸化性固体", "酸化性液体"],
    "酸化性液体": ["酸化性液体", "第6類"],
    "酢酸": ["酢酸", "第二石油類"],
    "一酸化炭素": ["一酸化炭素", "完全燃焼"],
    "酸素": ["酸素", "燃焼の三要素"],
}

# 問題DBに紐づかない核心語の手書き詳細（乙4向け）
CURATED_ARTICLES: dict[str, dict[str, str]] = {
    "移送": {
        "short_def": "移送は、配管・ポンプ等により貯蔵設備間で危険物を移すことで、運搬（車両による事業所外搬送）と区別する。",
        "definition": "まず「移送」は、貯蔵所等から配管・ポンプ等により危険物を他の設備や場所へ移すことをいう。",
        "term_detail_body": "移動タンク貯蔵所による移送や移送取扱所など、設備の種類ごとに基準が異なります。配管の材質・接続、ポンプの接地、漏えい検知、火気・静電気対策が試験の定番です。\n\n運搬は車両等で事業所の外へ運び送ることであり、表示・混載・容器が主な論点です。移送取扱所と移動タンク貯蔵所の役割も別々に整理してください。",
        "exam_points": "配管・ポンプ等による設備間の移動;運搬・譲渡との区別;移送取扱所・移動タンク貯蔵所",
        "common_mistakes": "運搬と混同する;移送取扱所と移動タンク貯蔵所を同一視する",
        "legal_basis": "危険物の規制に関する政令",
    },
    "指定数量": {
        "definition": "まず「指定数量」は、危険物の危険性に応じて政令で定められる基準数量であり、品名・性状ごとに異なる。",
        "term_detail_body": "指定数量は、製造・貯蔵・取扱いの規制区分を決めるための基準値です。ガソリン（第1石油類・非水溶性200 L）やアセトン（水溶性400 L）のように、同じ類でも性状で数量が変わります。\n\n指定数量の倍数は、貯蔵量÷指定数量を品名ごとに求めて合算します。単純にリットル数を足し合わせるのではなく、倍数計算が試験の定番です。",
        "exam_points": "品名・性状ごとに数量が異なる;倍数は貯蔵量÷指定数量の合算;第1石油類は水溶性・非水溶性で数量が違う",
        "common_mistakes": "数量を単純合計する;指定数量と倍数の計算を混同する;水溶性・非水溶性の区分を誤る",
        "legal_basis": "危険物の規制に関する政令",
    },
    "運搬": {
        "short_def": "運搬は、危険物を車両等で事業所外へ運び送ることで、移送（設備間の移動）や譲渡と区別する。",
        "definition": "まず「運搬」は、危険物を事業所外へ車両等で運び送ることをいう。",
        "term_detail_body": "運搬では、車両への表示、混載制限、容器の基準、積載方法・立入禁止などが問われます。タンクローリーやドラム缶の取扱いもこの文脈で出題されます。\n\n移送は配管・ポンプによる設備間の移動、譲渡・引渡しは所有権・占有の移転が中心です。三つを表で対比すると試験で迷いにくくなります。",
        "exam_points": "車両等による事業所外の運搬;表示・混載・容器・積載;移送・譲渡との区別",
        "common_mistakes": "移送と混同する;表示と標識を同一視する",
        "legal_basis": "危険物の規制に関する政令",
    },
    "バックドラフト": {
        "definition": "まず「バックドラフト」は、密閉空間で発生した火災に大量の酸素が一気に供給されたとき、可燃性ガスが急激に燃焼・爆発的に燃え上がる現象をいう。",
        "term_detail_body": "バックドラフトは室内火災の急激な延焼現象です。閉鎖空間では燃焼が不完全になり可燃性ガスが蓄積し、開口部から酸素が流入すると一気に燃焼が進む。\n\n消火活動では、開放前の内部状況確認、換気の段階的実施、自衛消防組織との連携が重要です。",
        "exam_points": "密閉空間＋酸素流入で急燃;開放前の内部確認;換気は段階的に行う",
        "common_mistakes": "通常の延焼と混同する;開口部を一気に全開にする;内部状況未確認で進入する",
        "legal_basis": "消防法",
    },
    "フラッシュオーバー": {
        "definition": "まず「フラッシュオーバー」は、閉鎖空間火災で天井付近の高温ガス層が一気に下方へ伝播し、室内全体が一瞬で燃焼に至る現象をいう。",
        "term_detail_body": "フラッシュオーバーは、火災の成長過程で発生しうる危険な現象です。輻射熱により可燃物表面が一斉に着火し、避難・消火活動の時間的余裕が大きく減ります。\n\n試験ではバックドラフトとの違い（酸素流入型か、輻射熱による一斉着火か）が問われやすいです。",
        "exam_points": "天井付近の高温ガス層が下方へ伝播;室内一斉着火;バックドラフトと区別する",
        "common_mistakes": "バックドラフトと同一視する;単なる延焼とみなす",
        "legal_basis": "消防法",
    },
    "丙種危険物取扱者": {
        "short_def": "丙種危険物取扱者は、丙種の危険物を取り扱える資格者で、乙種第4類とは対象範囲・試験内容が異なる。",
        "definition": "まず「丙種危険物取扱者」は、丙種の危険物を取り扱う資格者で、乙種・甲種とは対象となる危険物の範囲と試験内容が異なる。",
        "term_detail_body": "危険物取扱者免状は甲種・乙種・丙種に区分され、取扱可能な危険物の範囲が異なります。乙種第4類は第4類を中心とした乙種試験であり、丙種とは出題範囲・難易度が別です。\n\n試験では「丙種で扱える危険物」「乙種との違い」が正誤問題になりやすいです。受験資格・実務経験年数の要件も条文とあわせて整理してください。",
        "exam_points": "甲種・乙種・丙種の対象範囲;乙種第4類との出題範囲の違い;免状・受験資格",
        "common_mistakes": "乙種第4類と丙種の出題範囲を同一視する;全類を扱えると誤解する",
        "legal_basis": "消防法",
    },
    "消防法別表第二": {
        "short_def": "消防法別表第二は、危険物の性状区分を定める表で、別表第一の品名と組み合わせて該当性を判断する。",
        "definition": "まず「消防法別表第二」は、危険物の品名と性状を定める表で、別表第一と組み合わせて危険物かどうかを判断する。",
        "term_detail_body": "危険物は、別表第一の品名に該当し、かつ別表第二の区分に応じた性状を有する物品です。例えば引火性液体・可燃性固体・酸化性液体など、性状ごとに取扱い基準が異なります。\n\n試験では品名だけで危険物と決めつける誤答が多いです。別表第三（指定数量）と役割が異なることも混同しないでください。",
        "exam_points": "別表第一の品名＋別表第二の性状;危険物該当性の二段階判断;別表第三との区別",
        "common_mistakes": "別表第一だけで危険物と決めつける;性状区分を品名と混同する",
        "legal_basis": "消防法",
    },
    "消防法施行令": {
        "short_def": "消防法施行令は、消防法の委任に基づき施設の構造設備など技術基準を定める命令である。",
        "article_lead": "消防法・政令・施行令の役割分担と、試験で問われる条文の言い換えを整理します。",
        "definition": "まず「消防法施行令」は、消防法の委任に基づき、製造所等の構造設備や技術上の基準などを定める命令である。",
        "term_detail_body": (
            "法令の階層では、消防法が基本法、危険物の規制に関する政令が危険物の品名・指定数量など、"
            "消防法施行令が施設の構造・設備の技術基準を担います。試験では「政令で定める」と「施行令で定める」の"
            "条文文言の正誤が問われます。\n\n"
            "危険物の規制に関する政令と役割が異なるため、数値・手続・施設基準がどの法令に書かれているかを"
            "表で整理しておくと混同しにくくなります。"
        ),
        "exam_points": "消防法・政令・施行令の三層;施設の構造設備基準;条文文言の正誤",
        "common_mistakes": "政令と施行令の内容を取り違える;指定数量を施行令で定めると誤解する",
        "legal_basis": "消防法;消防法施行令",
    },
    "消防長": {
        "short_def": "消防長は消防本部を置く市町村の消防委員会が選任する消防職員で、消防法上の権限主体の一つである。",
        "definition": "まず「消防長」は、消防本部を置く市町村の消防委員会が選任する消防職員で、消防法上の権限・職務の主体の一つである。",
        "term_detail_body": (
            "消防署長は消防署を置く市町村の長が任命する職員であり、設置主体が消防長と異なります。"
            "命令・監督・検査などの権限が誰に属するかは、条文ごとに確認が必要です。\n\n"
            "都道府県知事の権限（広域の消防行政）と市町村の消防長・消防署長の権限を混同しないよう、"
            "主体（知事／消防長／消防署長／事業者）を表にまとめてください。"
        ),
        "exam_points": "消防長と消防署長の任命主体;知事の権限との区別;命令・監督の主体",
        "common_mistakes": "消防署長と同一とみなす;都道府県知事の権限と混同する",
        "legal_basis": "消防法",
    },
    "政令": {
        "short_def": "政令は、国会の委任に基づく内閣命令で、危険物分野では危険物の規制に関する政令が指定数量・貯蔵基準などの具体規定を定める。",
        "article_lead": "法令・制度の根拠となる政令と、危険物の規制に関する政令の役割を整理します。",
        "definition": "まず「政令」は、国会の委任に基づき内閣が制定する命令であり、危険物分野では主に危険物の規制に関する政令が指定数量・貯蔵方法などの具体基準を定める。",
        "term_detail_body": "乙4でいう政令は、ほぼ「危険物の規制に関する政令」を指します。消防法が大枠、政令が品名ごとの指定数量や貯蔵・取扱いの技術基準、別表第三が品名一覧という役割分担を押さえてください。\n\n指定数量の数値や石油類の区分は政令・別表第三で確認します。試験では「政令で定める」「政令の別表第三に掲げる品名」といった表現の正誤が問われます。",
        "exam_points": "危険物の規制に関する政令が具体基準;指定数量・別表第三は政令で規定;消防法と政令の役割分担",
        "common_mistakes": "政令と消防法本則を混同する;指定数量を消防法だけで定めると誤解する;政令と施行令を取り違える",
        "legal_basis": "危険物の規制に関する政令;消防法",
    },
    "別表第三": {
        "short_def": "別表第三は、危険物の規制に関する政令の別表で、危険物の品名と指定数量などを定める一覧表である。",
        "article_lead": "政令別表第三の意味と、別表第一・第二との違いを整理します。",
        "definition": "まず「別表第三」は、危険物の規制に関する政令に付される表で、危険物の品名を列挙し、指定数量の算定に用いる。",
        "term_detail_body": "危険物かどうかの判断は、消防法別表第一（品名）と別表第二（性状）の組み合わせで行います。別表第三は、すでに危険物とされる物品について、品名ごとの指定数量などを示す表です。\n\n試験では「別表第三に掲げる品名」「指定数量は別表第三に定める」などの文言と、ガソリン・灯油などの具体品名の対応が問われます。",
        "exam_points": "政令別表第三は品名の一覧;指定数量算定に用いる;別表第一・第二との役割の違い",
        "common_mistakes": "別表第三を危険物該当性の判断表と誤解する;別表第一・第二と混同する",
        "legal_basis": "危険物の規制に関する政令",
    },
    "品名": {
        "definition": "まず「品名」は、危険物の規制に関する政令別表第三などに掲げられる物質の名称で、指定数量や区分を品目ごとに定める単位となる。",
        "term_detail_body": "法令上は「ガソリン」「アセトン」などの品名単位で指定数量が定められます。第4類（引火性液体）の中でも、第一石油類・第二石油類などの類と品名の組み合わせで数値が変わります。\n\n製造所等で貯蔵・取扱う危険物の品名を変更する場合は、届出や許可が必要となる場面もあります。品名の変更と数量変更・倍数計算は別の論点として整理してください。",
        "exam_points": "指定数量は品名・性状ごと;石油類は品名で第一〜第三・特殊引火物を区別;品名変更時の手続",
        "common_mistakes": "類名だけで品名を特定する;品名変更と数量変更の手続を混同する",
        "legal_basis": "危険物の規制に関する政令",
    },
    "性状": {
        "definition": "まず「性状」は、危険物が有する化学的・物理的性質の区分であり、消防法別表第二に酸化性固体・引火性液体などとして定められる。",
        "term_detail_body": "危険物該当性は、別表第一の品名に加え、別表第二の性状区分を満たすかで判断します。同じ品名でも性状が異なれば危険物に該当しない場合があります。\n\n乙4では引火性液体（第4類）が中心ですが、他類の性状名（酸化性固体・可燃性固体など）を混同しないよう、類・性状・品名の三層で整理するとよいです。",
        "exam_points": "別表第二が性状区分;品名＋性状で危険物判断;第4類は引火性液体の性状",
        "common_mistakes": "品名だけで危険物と決めつける;類と性状を同一視する",
        "legal_basis": "消防法",
    },
    "類別": {
        "definition": "まず「類別」は、危険物を第1類から第6類までの6区分に分けることで、乙種第4類は第4類（引火性液体）を主に扱う。",
        "term_detail_body": "第1類は酸化性固体、第2類は可燃性固体、第3類は自然発火性・禁水性、第4類は引火性液体、第5類は自己反応性、第6類は酸化性液体です。試験では「第○類に属するものはどれか」「誤っている組合せはどれか」が頻出します。\n\n乙4受験者は第4類の性質と消火・漏えい対策を重点的に学びつつ、他類の代表例を誤り選択肢で排除できる程度に押さえます。",
        "exam_points": "危険物は第1〜6類;乙4は第4類（引火性液体）;各類の代表例を区別",
        "common_mistakes": "第4類を可燃性固体と混同する;第6類と第1類を取り違える",
        "legal_basis": "消防法",
    },
    "一般取扱所": {
        "definition": "まず「一般取扱所」は、危険物の販売・授与・引渡しなどを行う取扱所の一種で、給油取扱所や移送取扱所とは目的・基準が異なる。",
        "term_detail_body": "製造所等は製造所・貯蔵所・取扱所に大別されます。取扱所には一般取扱所・給油取扱所・移送取扱所・販売取扱所などがあり、それぞれ構造設備や保安の基準が異なります。\n\n試験では施設の分類（貯蔵所か取扱所か）と、一般取扱所に該当する行為（販売・授与など）を問う設問が出ます。給油取扱所は自動車等への給油が目的である点が区別の目安です。",
        "exam_points": "取扱所の一種;給油・移送・販売取扱所と区別;貯蔵所ではない",
        "common_mistakes": "一般取扱所を貯蔵所と混同する;給油取扱所と同一視する",
        "legal_basis": "危険物の規制に関する政令;消防法",
    },
    "販売取扱所": {
        "definition": "まず「販売取扱所」は、危険物を販売する取扱所であり、一般取扱所のうち販売を主目的とする施設として整理される。",
        "term_detail_body": "取扱所は危険物の製造以外の授受・取扱いを行う施設です。販売取扱所は名称どおり販売に重点があり、給油取扱所（給油）・移送取扱所（配管移送）とは異なります。\n\n選択肢では「販売取扱所は取扱所である」「屋外タンク貯蔵所は貯蔵所である」といった施設区分の正誤が問われやすいです。",
        "exam_points": "販売を行う取扱所;貯蔵所・製造所と区別;取扱所のサブタイプ",
        "common_mistakes": "販売取扱所を貯蔵所とみなす;一般取扱所と完全同一と考える",
        "legal_basis": "危険物の規制に関する政令",
    },
    "タンク貯蔵所": {
        "short_def": "タンク貯蔵所は、タンクで危険物を貯蔵する貯蔵所の総称で、屋内・屋外・移動タンク貯蔵所などに分かれる。",
        "definition": "まず「タンク貯蔵所」は、タンクにより危険物を貯蔵する貯蔵所の総称で、屋内・屋外・移動タンクなど形態により名称が分かれる。",
        "term_detail_body": "貯蔵所のうちタンクで貯蔵するものをタンク貯蔵所といい、屋内タンク貯蔵所・屋外タンク貯蔵所・移動タンク貯蔵所に細分されます。屋内貯蔵所（タンク以外の貯蔵方法）や取扱所とは構造基準が異なります。\n\n試験では「移動タンク貯蔵所はタンクローリー等の車両タンク」「屋外タンク貯蔵所は屋外設置のタンク」など、形態ごとの定義の正誤が問われます。",
        "exam_points": "タンクによる貯蔵所の総称;屋内・屋外・移動の三分;取扱所・屋内貯蔵所と区別",
        "common_mistakes": "移動タンク貯蔵所だけをタンク貯蔵所とする;屋内貯蔵所と屋内タンク貯蔵所を混同",
        "legal_basis": "危険物の規制に関する政令",
    },
    "屋内貯蔵所": {
        "definition": "まず「屋内貯蔵所」は、建築物内で危険物を貯蔵する貯蔵所であり、屋内タンク貯蔵所や移動タンク貯蔵所とは設置形態が異なる。",
        "term_detail_body": "屋内貯蔵所は建物内の貯蔵施設全般を指す概念として問われ、タンクの有無や構造基準で屋内タンク貯蔵所等と区別されます。名称が似る施設は「何を貯蔵するか」「タンクかどうか」で整理するとよいです。\n\n防火区画・換気・火気管理など、屋内特有の基準が試験の焦点になります。",
        "exam_points": "建築物内の貯蔵所;屋内タンク貯蔵所との違い;取扱所・屋外施設と区別",
        "common_mistakes": "屋内貯蔵所と屋内タンク貯蔵所を同一視する;給油取扱所を貯蔵所とする",
        "legal_basis": "危険物の規制に関する政令",
    },
    "屋外タンク貯蔵所": {
        "definition": "まず「屋外タンク貯蔵所」は、屋外に設置したタンクで危険物を貯蔵する貯蔵所である。",
        "term_detail_body": "屋外タンク貯蔵所は、タンク本体・基礎・囲い・漏えい防止設備など屋外設置ならではの基準が問われます。移動タンク貯蔵所（車両搭載）や屋内タンク貯蔵所と混同しないことが重要です。\n\n保安距離・防火堤・標識表示など、施設ごとの数値・構造要件をセットで覚えると本番で判別しやすくなります。",
        "exam_points": "屋外設置のタンク貯蔵;移動・屋内タンクとの区別;漏えい防止・防火堤",
        "common_mistakes": "屋外貯蔵所（非タンク）と同一視する;移動タンク貯蔵所と混同",
        "legal_basis": "危険物の規制に関する政令",
    },
    "移動タンク貯蔵所": {
        "definition": "まず「移動タンク貯蔵所」は、車両等に固定されたタンクにより危険物を貯蔵・移送する貯蔵所である。",
        "term_detail_body": "タンクローリーに代表される移動タンク貯蔵所では、移送中の漏えい・転倒・静電気・火気管理が試験の定番です。移送取扱所（配管による移送）や運搬（事業所外への輸送）とは区別してください。\n\n設置・変更時の許可・完成検査、運搬時の表示・混載制限など、移動という性質に紐づく論点を関連用語とあわせて確認します。",
        "exam_points": "車両固定タンクによる貯蔵・移送;移送取扱所・運搬との区別;漏えい・火気・静電気対策",
        "common_mistakes": "移送取扱所と同一視する;運搬と混同する",
        "legal_basis": "危険物の規制に関する政令",
    },
    "移送取扱所": {
        "definition": "まず「移送取扱所」は、配管・ポンプ等により危険物を移送する取扱所であり、移動タンク貯蔵所（車両タンク）とは仕組みが異なる。",
        "term_detail_body": "移送は設備間の危険物移動をいい、移送取扱所はその取扱いを行う施設です。移動タンク貯蔵所は車両タンクでの移送、運搬は事業所外への輸送という整理が基本です。\n\n漏えい検知・緊急遮断・火気厳禁・接地など、配管移送に特有の安全対策が問われます。",
        "exam_points": "配管・ポンプによる移送;移動タンク貯蔵所との違い;運搬との区別",
        "common_mistakes": "移動タンク貯蔵所と混同する;運搬・譲渡と混同する",
        "legal_basis": "危険物の規制に関する政令",
    },
    "保安員": {
        "definition": "まず「保安員」は試験文脈では主に危険物施設保安員を指し、一定規模の危険物施設で施設保安の業務に従事する者として選任される。",
        "term_detail_body": "危険物取扱者（免状）、危険物保安監督者・統括管理者（選任 managerial）、危険物施設保安員（施設の保安業務）は役割が異なります。保安員は施設側の保安体制の一部として問われます。\n\n選任要件・業務範囲・取扱者との関係を表にまとめると、主体の取り違えを防げます。",
        "exam_points": "危険物施設保安員の選任;取扱者・監督者との役割分担;施設保安の業務",
        "common_mistakes": "危険物取扱者と同一視する;保安監督者と混同する",
        "legal_basis": "消防法",
    },
    "譲渡": {
        "definition": "まず「譲渡」は、製造所等における危険物施設の権利・義務の承継に関する手続で、施設の引渡しとあわせて届出が必要となる場合がある。",
        "term_detail_body": "製造所等の譲渡・引渡しでは、施設の権利移転と危険物取扱者免状の更新は別手続きです。試験では「譲渡・引渡しがあったときの届出」など手続の正誤が問われます。\n\n廃止届・品名変更・数量変更など、施設ライフサイクルごとの届出・許可を一覧化すると整理しやすくなります。",
        "exam_points": "製造所等の権利承継;引渡しとのセット届出;免状手続きとの区別",
        "common_mistakes": "免状の更新だけで施設届出が不要と誤解する;譲渡と運搬を混同する",
        "legal_basis": "消防法",
    },
    "引渡し": {
        "definition": "まず「引渡し」は、製造所等の施設を他人に引き渡すことで、譲渡とともに法令上の届出・安全確認が問われる。",
        "term_detail_body": "引渡しは施設の実務上の移転を伴い、譲渡は権利義務の承継を伴う概念として整理されます。試験では両者をまとめて「譲渡または引渡しの届出」として問う場合が多いです。\n\n引渡し後も危険物の残存・安全措置・新たな占有者の義務が問題になるため、手続だけでなく保安の継続に注意してください。",
        "exam_points": "施設の引渡し;譲渡・届出との関係;残存危険物の安全",
        "common_mistakes": "譲渡と同義とみなして細部を省略する;運搬・移送と混同する",
        "legal_basis": "消防法",
    },
    "選任": {
        "definition": "まず「選任」は、危険物施設保安員や危険物保安監督者など、法令上必要な者を施設・事業所に就けさせること。",
        "term_detail_body": "選任は「誰を・どの施設に・どの要件で」就けるかが試験の焦点です。危険物取扱者免状の交付・更新とは別の制度として整理してください。\n\n監督者・統括管理者・施設保安員・取扱者の四層を混同しないよう、主体と要件を表にまとめるとよいです。",
        "exam_points": "施設保安員・監督者の選任;免状交付との区別;選任要件の有無",
        "common_mistakes": "選任と免状交付を混同する;施設保安員と取扱者を同一視する",
        "legal_basis": "消防法",
    },
    "混載": {
        "definition": "まず「混載」は、危険物の運搬において性質の異なる危険物や指定の物質を同一車両等に積載することで、制限がある場合が多い。",
        "term_detail_body": "運搬では表示・容器・積載方法に加え、混載制限が重要です。混載が禁止または条件付きとなる組み合わせは、品名・類・性状ごとに整理して覚えます。\n\n表示だけ整えれば任意に混載できるわけではなく、容器基準を満たさない積載は誤りとなります。",
        "exam_points": "運搬時の混載制限;品名・類による組合せ;表示・容器基準とのセット",
        "common_mistakes": "表示があれば混載自由と誤解する;運搬と移送を混同する",
        "legal_basis": "危険物の規制に関する政令",
    },
    "設置許可": {
        "definition": "まず「設置許可」は、指定数量以上の危険物を扱う製造所等を新設するときに、消防法上必要となる許可手続である。",
        "term_detail_body": "製造所等の設置許可は、位置・構造・設備が基準に適合するかを審査する手続です。危険物取扱者免状があっても施設許可が不要になるわけではありません。\n\n設置後の完成検査、変更許可・廃止届との流れを時系列で整理すると、手続問題の得点源になります。",
        "exam_points": "指定数量以上で新設時に必要;免状では代替不可;完成検査との関係",
        "common_mistakes": "免状があれば許可不要と誤解する;変更許可と混同する",
        "legal_basis": "消防法",
    },
    "変更許可": {
        "definition": "まず「変更許可」は、製造所等の位置・構造・設備を変更するときに、法令上必要となる許可手続である。",
        "term_detail_body": "変更許可は新設の設置許可と区別し、既存施設の改築・設備変更・品名・数量の変更が許可・届出の対象かを条文ごとに整理します。取扱者の立会いや標識設置だけでは変更許可が不要になるわけではありません。\n\n品名変更・数量変更は届出で足りる場合と許可が必要な場合があり、試験ではその境界が問われます。",
        "exam_points": "位置・構造・設備の変更;設置許可との違い;品名・数量変更との区別",
        "common_mistakes": "届出で済む変更と許可必要な変更を混同する;標識だけで足りると誤解する",
        "legal_basis": "消防法",
    },
    "濃度": {
        "short_def": "濃度は、溶液中の溶質の相対的な量を表す指標で、試験では質量パーセント濃度の計算が中心となる。",
        "definition": "まず「濃度」は、溶液中の溶質の量を表す指標で、質量パーセント濃度などが物性・化学分野で用いられる。",
        "term_detail_body": "危険物試験では質量パーセント濃度の計算や、濃度と引火点・危険性の関係が問われます。単位（％）と分母（溶液全体か溶媒か）を読み違えると誤答になりやすいです。\n\n関連する用語（質量パーセント濃度・モル濃度など）とあわせて、公式と単位をセットで覚えてください。",
        "exam_points": "質量パーセント濃度の意味;計算と単位;引火点・物性との関係",
        "common_mistakes": "濃度の定義域を取り違える;質量と体積の％を混同する",
        "legal_basis": "",
    },
    "第1類危険物": {
        "short_def": "第1類危険物は酸化性固体に属し、可燃物を燃焼させやすい性質を持つ危険物類である。",
        "definition": "まず「第1類危険物」とは、酸化性固体に属する危険物類で、他の可燃物の燃焼を助長する性質がある。",
        "term_detail_body": (
            "第1類は酸化性固体、第2類は可燃性固体、第3類は自然発火性・禁水性、第4類は引火性液体、"
            "第5類は自己反応性、第6類は酸化性液体です。乙4は第4類が中心ですが、"
            "「第○類に属するものはどれか」の問題で他類の代表例を区別できる必要があります。\n\n"
            "塩素酸カリなど酸化性固体が代表例です。第6類の酸化性液体（過酸化水素など）と混同しないよう、"
            "固体か液体か、類別名をセットで覚えてください。"
        ),
        "exam_points": "酸化性固体;他類の燃焼を助長;第6類酸化性液体との区別",
        "common_mistakes": "第4類引火性液体と混同する;第6類と第1類を取り違える;可燃性固体（第2類）と混同する",
        "legal_basis": "消防法",
    },
    "燃焼の三要素": {
        "short_def": "燃焼の三要素は可燃物・酸素（酸化剤）・着火源で、いずれかを除けば燃焼は成立しない。",
        "definition": "まず「燃焼の三要素」とは、可燃物・酸素などの酸化剤・着火源の三つが揃って初めて燃焼が成立するという考え方を指す。",
        "term_detail_body": (
            "消火は、三要素のいずれかを除去・抑制することで行います。"
            "除去（可燃物の撤去）、冷却（温度低下）、窒息（酸素濃度の低下）、抑制（連鎖反応の抑制）の四方式と対応づけて覚えると、"
            "消火方法の選択肢問題が解きやすくなります。\n\n"
            "酸素は助燃性ガスであり、空気中の酸素濃度低下（窒息消火）や不活性ガスによる置換が関連します。"
            "着火源には明火のほか、静電気放電・摩擦熱なども含まれます。"
        ),
        "exam_points": "可燃物・酸素・着火源;消火四方式との対応;酸素は助燃性",
        "common_mistakes": "水がすべての着火源になると誤解する;窒息と冷却を混同する;三要素のうち一つだけ除けば必ず消火と決めつける",
        "legal_basis": "",
    },
}

from tools.o4_curated_batch50_rest import CURATED_BATCH50_REST  # noqa: E402
from tools.o4_curated_batch_next import CURATED_BATCH_NEXT  # noqa: E402
from tools.o4_curated_study_keep import STUDY_KEEP_ARTICLES  # noqa: E402

CURATED_ARTICLES.update(CURATED_BATCH50_REST)
CURATED_ARTICLES.update(CURATED_BATCH_NEXT)
CURATED_ARTICLES.update(STUDY_KEEP_ARTICLES)

# 問題文の部分一致だけでは別論点の解説が混ざりやすい短語
STRICT_MATCH_TERMS = frozenset(
    {
        "政令",
        "別表第三",
        "品名",
        "性状",
        "類別",
        "選任",
        "譲渡",
        "引渡し",
        "混載",
        "保安員",
        "濃度",
        "対流",
        "酸素",
        "冷却",
        "窒息",
        "火気",
        "非水溶性",
        "倍数計算",
        "酢酸",
        "換気",
        "給油",
        "引火点",
        "ガソリン",
        "水溶性",
        "灯油",
        "漏えい",
    }
)

# --add-terms で追記する用語（問題DB・既存CSVにない短語）
EXTRA_TERMS: list[tuple[str, str]] = [
    ("沸点", "物性・化学"),
    ("質量パーセント濃度", "物性・化学"),
    ("注水消火", "火災・消火・漏えい"),
    ("水上泡消火", "火災・消火・漏えい"),
    ("密閉空間火災", "火災・消火・漏えい"),
    ("タンクローリー", "法令・制度"),
    ("酢酸エチル", "火災・消火・漏えい"),
    ("アセトアルデヒド", "火災・消火・漏えい"),
    ("第4石油類", "火災・消火・漏えい"),
    ("譲渡・引渡し", "法令・制度"),
]

# 頻出・重要キーワード50件（実践演習・一問一答の出現頻度と乙4出題範囲で選定）
BATCH_50_EXAM_TERMS: list[tuple[str, str]] = [
    ("政令", "法令・制度"),
    ("別表第三", "法令・制度"),
    ("品名", "法令・制度"),
    ("性状", "法令・制度"),
    ("類別", "法令・制度"),
    ("倍数計算", "法令・制度"),
    ("設置許可", "法令・制度"),
    ("変更許可", "法令・制度"),
    ("選任", "法令・制度"),
    ("譲渡", "法令・制度"),
    ("引渡し", "法令・制度"),
    ("混載", "法令・制度"),
    ("屋内貯蔵所", "法令・制度"),
    ("屋外タンク貯蔵所", "法令・制度"),
    ("タンク貯蔵所", "法令・制度"),
    ("移動タンク貯蔵所", "法令・制度"),
    ("給油取扱所", "法令・制度"),
    ("移送取扱所", "法令・制度"),
    ("一般取扱所", "法令・制度"),
    ("販売取扱所", "法令・制度"),
    ("保安員", "法令・制度"),
    ("可燃性", "物性・化学"),
    ("引火性", "物性・化学"),
    ("非水溶性", "物性・化学"),
    ("水溶性液体", "物性・化学"),
    ("非水溶性液体", "物性・化学"),
    ("濃度", "物性・化学"),
    ("蒸発", "物性・化学"),
    ("沸騰", "物性・化学"),
    ("揮発性", "物性・化学"),
    ("中和", "物性・化学"),
    ("対流", "物性・化学"),
    ("酸化性", "物性・化学"),
    ("酸化性液体", "物性・化学"),
    ("酸素", "物性・化学"),
    ("一酸化炭素", "物性・化学"),
    ("火気", "火災・消火・漏えい"),
    ("火気厳禁", "火災・消火・漏えい"),
    ("換気", "火災・消火・漏えい"),
    ("消火剤", "火災・消火・漏えい"),
    ("粉末消火剤", "火災・消火・漏えい"),
    ("冷却", "火災・消火・漏えい"),
    ("窒息", "火災・消火・漏えい"),
    ("注水", "火災・消火・漏えい"),
    ("流出", "火災・消火・漏えい"),
    ("給油", "火災・消火・漏えい"),
    ("第1石油類", "火災・消火・漏えい"),
    ("第2石油類", "火災・消火・漏えい"),
    ("酢酸", "火災・消火・漏えい"),
    ("動植物油", "火災・消火・漏えい"),
]

ADD_TERMS_LIST: list[tuple[str, str]] = [
    *EXTRA_TERMS,
    *BATCH_50_EXAM_TERMS,
]

BLOB_FIELDS = (
    "question",
    "statement",
    "explanation",
    "unit",
    "topic",
    "exam_point",
    "trap_point",
    "source_note",
)

GENERIC_PHRASES = (
    "危険物取扱者試験の出題範囲において重要な概念",
    "選択肢の言い換えや数字のひっかけ",
    "実践演習で誤答した選択肢",
    "公式の定義・試験テキスト",
    "関連用語へ進んでください",
    "繰り返し登場します",
    "混同を防げます",
)

# テンプレート埋め・文字数稼ぎに使わない定型文（品質監査でも利用）
BOILERPLATE_PHRASES = GENERIC_PHRASES + (
    "条文の言い換えと数値・主体の区別",
    "定義を選択肢に落とし込める",
    "「誤っているものはどれか」形式",
    "本記事では定義・試験ポイント",
    "関連演習へつなげます",
    "一問一答では○×形式",
    "問われやすいです",
    "押さえると理解しやすく",
    "乙種第4類の法令分野では、条文の言い換え",
    "物性・化学分野では、性質の数値",
    "火災・消火分野では、第4類の性質",
    "下の比較の目安として覚え",
    "出題文脈は主に",
    "想定される出題形式の例",
    "試験では特に次の観点が繰り返し",
    "定着を確認してください",
)


def norm(s: str | None) -> str:
    return (s or "").strip()


def norm_term(s: str | None) -> str:
    return re.sub(r"\s+", "", norm(s))


def split_sentences(text: str, limit: int = 6) -> list[str]:
    text = re.sub(r"\s+", " ", norm(text))
    if not text:
        return []
    parts = [p.strip() for p in re.findall(r"[^。！？]+[。！？]?", text) if p.strip()]
    return parts[:limit]


def is_generic_sentence(s: str) -> bool:
    if len(s) < 18:
        return True
    return any(p in s for p in BOILERPLATE_PHRASES)


def is_boilerplate_sentence(s: str) -> bool:
    return is_generic_sentence(s)


def trim_lead_sentence(term: str, sentence: str) -> str:
    s = norm(sentence)
    m = re.search(rf"まず「{re.escape(term)}」は、(.+)", s)
    if m:
        return m.group(1).strip().rstrip("。")
    for prefix in (f"{term}は、", f"{term}とは、", f"{term}は", f"{term}とは"):
        if s.startswith(prefix):
            return s[len(prefix) :].lstrip().rstrip("。")
    return s.rstrip("。")


_EXAM_STEM_MARKERS = (
    "は正しい",
    "は誤",
    "どれか",
    "次の記述",
    "次のうち",
    "正解は選択肢",
    "正しい説明は",
)


def is_exam_stem(sentence: str) -> bool:
    s = norm(sentence)
    if not s:
        return True
    if s.startswith(("誤り", "正しい", "×", "○", "実践演習", "正解は")):
        return True
    return any(m in s for m in _EXAM_STEM_MARKERS)


def _definition_sentence_score(term: str, body: str) -> int:
    score = 0
    if body.startswith(term) or body.startswith(f"{term}は"):
        score += 14
    m = re.match(r"^([^、。]{1,40})は[、]", body)
    if m:
        subj = m.group(1).strip()
        if subj == term or subj.endswith(term):
            score += 10
        elif term in subj and len(subj) > len(term) + 1:
            score -= 12
        elif term in subj:
            score += 4
        else:
            score -= 9
    elif term in body[: min(len(body), 50)]:
        score += 2
    else:
        score -= 5
    return score


def pick_definition_sentence(
    term: str,
    explanations: list[str],
    exam_points: list[str],
) -> str:
    """一覧・リード用に、定義らしい一文を選ぶ（用語名が主語の文を優先）。"""
    best: tuple[int, str] | None = None
    for expl in explanations:
        for sent in split_sentences(expl, 12):
            body = trim_lead_sentence(term, sent)
            if len(body) < 22 or is_exam_stem(body) or is_generic_sentence(body):
                continue
            sc = _definition_sentence_score(term, body)
            if term not in body[:70] and not body.startswith(term):
                sc -= 15
            if best is None or sc > best[0]:
                best = (sc, body)
    if best and best[0] >= 0:
        return best[1]

    for ep in exam_points:
        ep = norm(ep)
        if len(ep) >= 18 and not is_generic_sentence(ep) and not is_exam_stem(ep):
            sc = _definition_sentence_score(term, ep)
            if sc >= 0:
                return ep
    if explanations:
        fallback = trim_lead_sentence(term, explanations[0])
        if len(fallback) >= 18 and not is_exam_stem(fallback):
            return fallback
    return ""


def build_short_def(term: str, lead: str, category: str) -> str:
    if lead:
        line = lead if lead.startswith(term) else f"{term}は、{lead.rstrip('。')}。"
        return line if line.endswith("。") else f"{line}。"
    return (
        f"{term}は、{EXAM}の{category}分野で頻出の用語です。"
        "定義と数値・条件の違いを押さえます。"
    )[:200]


def sentence_key(s: str) -> str:
    return re.sub(r"\s+", "", s)[:120]


def ends_sentence(s: str) -> str:
    t = norm(s)
    if not t:
        return ""
    return t if t.endswith("。") else f"{t}。"


def ensure_sentence(s: str) -> str:
    t = norm(s)
    if not t:
        return ""
    if t.endswith(("。", "！", "？")):
        return t
    return f"{t}。"


def split_semicolon_field(s: str) -> list[str]:
    return [x.strip() for x in (s or "").split(";") if x.strip()]


def format_field_items(items: list[str], *, limit: int = 5) -> str:
    """CSV のセミコロン区切りフィールド向けに、読みやすい短文へ整形する。"""
    out: list[str] = []
    seen: set[str] = set()
    for raw in items:
        chunk = norm(raw)
        if not chunk:
            continue
        parts = [chunk]
        if ";" in chunk and not chunk.endswith("。"):
            parts = [p.strip() for p in chunk.split(";") if p.strip()]
        for part in parts:
            sent = ensure_sentence(part)
            key = sentence_key(sent)
            if key in seen:
                continue
            seen.add(key)
            out.append(sent)
            if len(out) >= limit:
                break
        if len(out) >= limit:
            break
    return ";".join(out)


def append_db_excerpts(
    body: str,
    term: str,
    practice_rows: list[dict[str, str]],
    ichimon_rows: list[dict[str, str]],
) -> str:
    """手書き本文に、問題DB固有の解説だけを重複なく追記する。"""
    seen = {sentence_key(p) for p in re.split(r"\n{2,}", body) if p.strip()}
    extras: list[str] = []
    for insight in extract_choice_insights(practice_rows, limit=3):
        if insight in body or sentence_key(insight) in seen:
            continue
        seen.add(sentence_key(insight))
        extras.append(insight)
    for line in extract_exam_trap_lines(practice_rows, ichimon_rows, limit=2):
        if line in body or sentence_key(line) in seen:
            continue
        seen.add(sentence_key(line))
        extras.append(line)
    if not extras:
        return body
    return body + "\n\n" + "\n\n".join(extras)


def merge_unique_detail_sentences(
    body: str,
    term: str,
    explanations: list[str],
) -> str:
    """既存本文に、問題DB由来の重複しない一文だけを追記する（文字数パディングはしない）。"""
    seen = {sentence_key(p) for p in re.split(r"\n{2,}", body) if p.strip()}
    extras: list[str] = []
    expl_sents: list[str] = []
    for expl in explanations:
        chunk = norm(expl)
        if chunk.startswith(("誤り", "正しい", "誤答", "×", "○")):
            expl_sents.append(chunk)
            continue
        expl_sents.extend(split_sentences(expl, 8))
    for sent in unique_sentences(
        [trim_lead_sentence(term, e) for e in expl_sents if e],
        limit=5,
    ):
        if sent in body:
            continue
        key = sentence_key(sent)
        if key in seen or is_boilerplate_sentence(sent):
            continue
        seen.add(key)
        extras.append(ends_sentence(sent.rstrip("。")))
    if not extras:
        return body
    return body + ("\n\n" if body else "") + "\n\n".join(extras)


def extract_choice_insights(practice_rows: list[dict[str, str]], *, limit: int = 2) -> list[str]:
    """五肢択一の正誤解説から、試験で実際に問われる論点を抜き出す。"""
    out: list[str] = []
    seen: set[str] = set()
    for row in practice_rows[:4]:
        ans = norm(row.get("answer"))
        for i in range(1, 6):
            ex = norm(row.get(f"choice_{i}_explanation"))
            if len(ex) < 28 or is_boilerplate_sentence(ex):
                continue
            if ans and str(i) == ans and not ex.startswith("正"):
                continue
            if not (ex.startswith("誤") or ex.startswith("正") or "誤り" in ex[:12]):
                continue
            key = sentence_key(ex)
            if key in seen:
                continue
            seen.add(key)
            out.append(ex if ex.endswith("。") else f"{ex}。")
            if len(out) >= limit:
                return out
    return out


def extract_exam_trap_lines(
    practice_rows: list[dict[str, str]],
    ichimon_rows: list[dict[str, str]],
    *,
    limit: int = 3,
) -> list[str]:
    lines: list[str] = []
    for row in practice_rows + ichimon_rows:
        for field in ("exam_point", "trap_point"):
            val = norm(row.get(field))
            if len(val) < 12 or is_boilerplate_sentence(val):
                continue
            lines.append(ensure_sentence(val.rstrip("。")))
    return unique_lines(lines, limit=limit)


def unique_sentences(sentences: list[str], *, limit: int = 5) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in sentences:
        s = norm(raw)
        if len(s) < 16 or is_generic_sentence(s) or is_exam_stem(s):
            continue
        key = sentence_key(s)
        if key in seen:
            continue
        if any(len(key) > 24 and (key in o or o in key) for o in seen):
            continue
        seen.add(key)
        out.append(s)
        if len(out) >= limit:
            break
    return out


def build_term_detail_body(
    term: str,
    category: str,
    lead_sentence: str,
    explanations: list[str],
    exam_points: list[str],
    traps: list[str],
    unit: str,
    topic: str,
    q_count: int,
    peers: list[str],
    legal: str,
    practice_rows: list[dict[str, str]],
    ichimon_rows: list[dict[str, str]] | None = None,
    *,
    skip_definition: bool = False,
) -> str:
    ichimon_rows = ichimon_rows or []
    parts: list[str] = []

    def_sents: list[str] = []
    if lead_sentence:
        lead = lead_sentence.rstrip("。")
        if lead.startswith(f"{term}は"):
            def_sents.append(ends_sentence(lead))
        else:
            def_sents.append(ends_sentence(f"{term}は、{lead}"))
    for sent in unique_sentences(
        [trim_lead_sentence(term, e) for e in explanations if e],
        limit=4,
    ):
        if sentence_key(sent) == sentence_key(lead_sentence):
            continue
        if sent.startswith(f"{term}は"):
            def_sents.append(ends_sentence(sent.rstrip("。")))
        elif re.match(rf"^{re.escape(term)}", sent):
            def_sents.append(ends_sentence(sent.rstrip("。")))
        else:
            def_sents.append(ends_sentence(sent.rstrip("。")))
    if def_sents and not skip_definition:
        for sent in def_sents[:4]:
            parts.append(sent)

    choice_insights = extract_choice_insights(practice_rows, limit=2)
    for insight in choice_insights:
        parts.append(insight)

    exam_trap = extract_exam_trap_lines(practice_rows, ichimon_rows, limit=2)
    for line in exam_trap:
        if sentence_key(line) not in {sentence_key(p) for p in parts}:
            parts.append(line)

    if unit and not choice_insights:
        parts.append(
            f"単元「{unit}」の設問では、{term}が条文・数値・主体のいずれかと組み合わされて問われます。"
        )

    if legal:
        basis = legal.replace(";", "・")
        parts.append(
            f"根拠は主に{basis}に関する規定です。数値・手続の最新版は消防試験研究センターのテキストで確認してください。"
        )

    body = "\n\n".join(p for p in parts if p)
    extra_expl = list(explanations) + choice_insights
    return merge_unique_detail_sentences(body, term, extra_expl)


def build_explanation_text(
    term: str,
    category: str,
    traps: list[str],
    exam_questions: list[str],
    practice_rows: list[dict[str, str]],
    ichimon_rows: list[dict[str, str]],
) -> str:
    parts: list[str] = []

    for line in extract_exam_trap_lines(practice_rows, ichimon_rows, limit=2):
        if line not in parts:
            parts.append(line)

    for insight in extract_choice_insights(practice_rows, limit=2):
        if insight not in parts:
            parts.append(insight)

    if traps:
        trap_line = "また、".join(
            ensure_sentence(t.rstrip("。"))
            for t in traps[:2]
            if norm(t) and not is_boilerplate_sentence(t)
        )
        if trap_line:
            parts.append(f"誤答では{trap_line}といった取り違えが選ばれやすいです。")

    if exam_questions:
        preview = exam_questions[0][:100].strip()
        if preview and not is_exam_stem(preview[:40]):
            parts.append(f"実践演習の設問例: 「{preview}…」")

    if ichimon_rows and not practice_rows:
        row = ichimon_rows[0]
        expl = split_sentences(norm(row.get("explanation")), 2)
        for sent in expl:
            if len(sent) >= 20 and not is_boilerplate_sentence(sent):
                parts.append(ends_sentence(trim_lead_sentence(term, sent).rstrip("。")))
                break

    if not parts:
        parts.append(
            f"{term}は{category}分野の用語として、定義と数値・条件の組み合わせで正誤が問われます。"
        )
    return " ".join(parts[:4])


def build_article_lead(
    term: str,
    category: str,
    unit: str,
    lead_sentence: str = "",
) -> str:
    if lead_sentence:
        core = lead_sentence.rstrip("。")
        return f"{category}分野の「{term}」は、{core}。試験では定義の言い換えと数値・主体の区別がセットで問われます。"
    if unit:
        return (
            f"{category}分野の「{unit}」でよく出る用語です。"
            f"下の目次から定義・試験ポイント・例題の順に確認し、演習と往復してください。"
        )
    return (
        f"{category}分野で押さえる用語です。"
        f"定義と試験ポイントを確認したら、関連用語と演習で定着を確認してください。"
    )


def build_memory_tip(term: str, peers: list[str]) -> str:
    tips: list[str] = []
    if peers:
        tips.append(f"「{peers[0]}」と違いを比較表にまとめる。")
    tips.append(
        f"演習で{term}を含む問題を解き、間違えたら"
        "試験ポイント→関連用語→定義の順に見直す。"
    )
    return " ".join(tips)[:300]


def filter_related_peers(
    term: str,
    category: str,
    by_cat: dict[str, list[str]],
    practice_rows: list[dict[str, str]],
    ichimon_rows: list[dict[str, str]],
) -> list[str]:
    """同分野の実義ある用語を関連リンクに選ぶ（メタ用語を除外）。"""
    scores: Counter[str] = Counter()
    for row in practice_rows + ichimon_rows:
        for field in ("topic", "unit"):
            val = norm(row.get(field))
            if not val or val == term or val in META_PEER_TERMS or len(val) > 28:
                continue
            if val != term:
                scores[val] += 3
            for part in re.split(r"[・／/]", val):
                p = norm(part)
                if len(p) >= 3 and p not in META_PEER_TERMS and p != term:
                    scores[p] += 1

    ranked = [t for t, _ in scores.most_common(20) if t not in META_PEER_TERMS]
    if len(ranked) < 2:
        ranked = [
            p
            for p in by_cat.get(category, [])
            if p != term and p not in META_PEER_TERMS and len(p) <= 24
        ]
    return ranked[:3]


META_STUDY_ARTICLES: dict[str, dict[str, str]] = {
    "ひっかけ対策": {
        "short_def": "試験の問い方（正しいもの／誤っているもの）や言い換え、数値の取り違えに注意する学習の視点。",
        "definition": "まず「ひっかけ対策」とは、選択肢の言い換えや「誤っているものはどれか」といった問い方の癖を把握し、定義と条文を照らして判別する学習の仕方を指す。",
        "term_detail_body": (
            "乙4では、正しい説明だけでなく「誤っているものはどれか」が頻出します。"
            "問い方を先に確認し、数字・主体・品名の取り違えを意識して解くことが重要です。\n\n"
            "具体例として、ガソリン（第1石油類）・灯油（第2石油類）・重油（第3石油類）の分類や、"
            "水溶性と非水溶性の違いは、同じような語句で混同されやすいテーマです。\n\n"
            "詳しい学習の進め方は試験ガイド「過去問の使い方」もあわせて確認してください。"
        ),
        "exam_points": "問い方（正しい／誤り）を先に確認;数値・主体・品名の取り違え;類似分類の比較",
        "common_mistakes": "誤り選択肢を正しいと決めつける;数量を単純合計する;水溶性＝安全とみなす",
        "related_terms": "ガソリン;灯油;第4類危険物",
        "explanation": "設問文の冒頭（正しい／誤っている）を線引きし、各選択肢を定義・数値と照合して判断します。",
        "article_lead": "試験特有の問い方と、数値・分類のひっかけに備える学習の視点を整理します。",
    },
    "よくある混同論点": {
        "short_def": "試験で混同されやすい分類・数値・制度を、対比して整理するための論点集。",
        "definition": "まず「よくある混同論点」とは、似た用語や数値の組み合わせを取り違えやすいテーマをまとめ、比較しながら覚えるための整理枠を指す。",
        "term_detail_body": (
            "法令・物性・火災の各分野で、「似ているが違う」組み合わせが繰り返し問われます。"
            "例として、危険物の類と品名、指定数量と倍数、消火方法と危険物の性質などです。\n\n"
            "1つの論点を押さえたら、関連する用語ページと実践演習でセット復習すると定着しやすくなります。"
        ),
        "exam_points": "類似語の対比;指定数量と倍数;消火方法と危険物分類",
        "common_mistakes": "名称だけで分類を判断する;単位や主体を読み飛ばす;例外規定を一般化する",
        "related_terms": "指定数量;第4類危険物;泡消火",
        "explanation": "比較表や一覧で「同じ点・違う点」だけを書き出し、選択肢ごとに当てはめて確認します。",
        "article_lead": "混同しやすいテーマを対比表で整理する考え方を説明します。",
    },
}


def apply_study_keep_full(row: dict[str, str], curated: dict[str, str]) -> None:
    """学習メタ用語：手書きテンプレを一括反映（演習DBの上書きなし）。"""
    apply_curated(row, curated)
    apply_curated_overrides(row, curated)
    term = norm(row.get("term"))
    category = norm(row.get("category"))
    if norm(curated.get("explanation")):
        row["explanation"] = norm(curated["explanation"])
    row["article_title"] = (
        norm(curated.get("article_title"))
        or f"{term}とは？{EXAM}の学習で押さえるポイント"
    )
    if norm(curated.get("related_terms")):
        row["related_terms"] = norm(curated["related_terms"])
    row["faq_1_question"] = f"{term}とは何ですか？"
    row["faq_1_answer"] = norm(row.get("short_def")) or norm(curated.get("definition"))
    row["faq_2_question"] = f"{term}の使い方でよくある誤りは？"
    mistakes = split_semicolon_field(norm(curated.get("common_mistakes")))
    row["faq_2_answer"] = (
        "また、".join(ensure_sentence(m) for m in mistakes[:2])
        if mistakes
        else f"{category}分野では、手順を飛ばして暗記だけに偏りやすいです。"
    )
    row["faq_3_question"] = f"{term}は試験でどう問われますか？"
    exam_pts = split_semicolon_field(norm(curated.get("exam_points") or row.get("exam_points")))
    row["faq_3_answer"] = (
        ensure_sentence(exam_pts[0])
        if exam_pts
        else f"{category}分野では、定義の言い換えや例外条件が選択肢で問われやすいです。"
    )
    row["faq_4_question"] = f"{term}を学んだあとに何を確認しますか？"
    row["faq_4_answer"] = (
        "関連用語ページで似た語との違いを確認し、過去問演習で理解を確かめてください。"
        "数値や期限は公式情報で最新内容を必ず確認してください。"
    )
    tags = [t for t in parse_tags(norm(row.get("tags"))) if t != "詳細記事"]
    if "学習法" not in tags:
        tags.append("学習法")
    row["tags"] = ";".join(dict.fromkeys(tags))


def finalize_glossary_row(row: dict[str, str]) -> None:
    """全用語に共通の整形（句読点・重複除去のみ。文字数の水増しはしない）。"""
    term = norm(row.get("term"))
    for field in ("common_mistakes", "exam_points"):
        raw = norm(row.get(field))
        if raw:
            row[field] = format_field_items(split_semicolon_field(raw), limit=8)
    if term in KEEP_TERMS | META_STUDY_TERMS:
        faq2 = norm(row.get("faq_2_answer"))
        if faq2 and ";" in faq2:
            parts = split_semicolon_field(format_field_items(split_semicolon_field(faq2), limit=3))
            row["faq_2_answer"] = "また、".join(parts) if parts else ensure_sentence(faq2)
        return
    body = norm(row.get("term_detail_body"))
    if len(body) < 80:
        body = body or norm(row.get("definition")) or norm(row.get("explanation"))
        expl = [norm(row.get("definition")), norm(row.get("explanation"))]
        row["term_detail_body"] = merge_unique_detail_sentences(
            body, term, [x for x in expl if x]
        )
    faq2 = norm(row.get("faq_2_answer"))
    if faq2:
        if ";" in faq2:
            parts = split_semicolon_field(format_field_items(split_semicolon_field(faq2), limit=3))
            row["faq_2_answer"] = "また、".join(parts) if parts else ensure_sentence(faq2)
        elif not faq2.endswith(("。", "！", "？")):
            row["faq_2_answer"] = ensure_sentence(faq2)


def apply_meta_study_term(row: dict[str, str]) -> None:
    term = norm(row.get("term"))
    curated = META_STUDY_ARTICLES.get(term, {})
    if curated:
        apply_curated(row, curated)
    tags = [t for t in parse_tags(norm(row.get("tags"))) if t != "詳細記事"]
    for drop in ("実践演習連動", "一問一答連動"):
        if drop in tags:
            tags.remove(drop)
    if "学習法" not in tags:
        tags.append("学習法")
    row["tags"] = ";".join(dict.fromkeys(tags))
    row["article_title"] = f"{term}とは？{EXAM}の学習で押さえる整理の仕方"
    row["memory_tip"] = (
        f"混同しやすいテーマは比較表にし、演習で間違えた論点だけを表に追記する。"
    )[:300]


def unique_lines(items: list[str], limit: int = 5) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        s = norm(raw)
        if not s or s in seen or is_generic_sentence(s):
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= limit:
            break
    return out


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build_question_index(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    by_term: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen_ids: dict[str, set[str]] = defaultdict(set)

    def attach(term_key: str, row: dict[str, str]) -> None:
        rid = norm(row.get("id"))
        if rid and rid in seen_ids[term_key]:
            return
        if rid:
            seen_ids[term_key].add(rid)
        by_term[term_key].append(row)

    for row in rows:
        keys: set[str] = set()
        for field in ("topic", "unit"):
            t = norm_term(row.get(field))
            if len(t) >= 2:
                keys.add(t)
        topic = norm_term(row.get("topic"))
        for part in re.split(r"[・／/]", topic):
            p = norm_term(part)
            if len(p) >= 3:
                keys.add(p)
        for key in keys:
            attach(key, row)
    return by_term


def search_keys_for(term: str) -> list[str]:
    keys = [norm_term(term)]
    keys.extend(norm_term(a) for a in TERM_SEARCH_ALIASES.get(term, []) if norm(a))
    out: list[str] = []
    seen: set[str] = set()
    for k in keys:
        if len(k) >= 2 and k not in seen:
            seen.add(k)
            out.append(k)
    return sorted(out, key=len, reverse=True)


def row_blob(row: dict[str, str]) -> str:
    return norm_term("".join(row.get(f, "") for f in BLOB_FIELDS))


def row_score(term: str, key: str, row: dict[str, str]) -> int:
    score = 0
    nt = norm_term(term)
    nk = norm_term(key)
    for field in ("topic", "unit"):
        val = norm_term(row.get(field))
        if nt and nt in val:
            score += 12
        elif nk and nk in val:
            score += 8
    if nk and nk in row_blob(row):
        score += 2
    return score


def is_ichimon_row(row: dict[str, str]) -> bool:
    rid = norm(row.get("id"))
    return rid.startswith("TF-") or (norm(row.get("statement")) and not norm(row.get("question")))


def find_question_rows(
    term: str,
    exact_idx: dict[str, list[dict[str, str]]],
    all_rows: list[dict[str, str]],
    *,
    max_rows: int = 48,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    keys = search_keys_for(term)
    seen_ids: set[str] = set()
    scored: list[tuple[int, dict[str, str]]] = []

    def add_row(row: dict[str, str], base: int) -> None:
        rid = norm(row.get("id"))
        if rid and rid in seen_ids:
            return
        if rid:
            seen_ids.add(rid)
        best = max((row_score(term, k, row) for k in keys), default=0)
        scored.append((base + best, row))

    for key in keys:
        for row in exact_idx.get(key, []):
            add_row(row, 20)

    if len(scored) < 4 and term not in STRICT_MATCH_TERMS:
        for row in all_rows:
            blob = row_blob(row)
            for key in keys:
                nk = norm_term(key)
                if len(nk) >= 2 and nk in blob:
                    add_row(row, 5)
                    break
    elif len(scored) < 4 and term in STRICT_MATCH_TERMS:
        for row in all_rows:
            if row_score(term, term, row) >= 12:
                add_row(row, 8)

    scored.sort(key=lambda x: x[0], reverse=True)
    picked = [row for _, row in scored[:max_rows]]
    practice = [r for r in picked if not is_ichimon_row(r)]
    ichimon = [r for r in picked if is_ichimon_row(r)]
    return practice, ichimon


def most_common_unit(rows: list[dict[str, str]]) -> str:
    units = [norm(r.get("unit")) for r in rows if norm(r.get("unit"))]
    if not units:
        return ""
    return Counter(units).most_common(1)[0][0]


def extract_legal_basis(rows: list[dict[str, str]]) -> str:
    found: list[str] = []
    for row in rows:
        note = norm(row.get("source_note"))
        if not note:
            continue
        for label in ("消防法", "危険物の規制に関する政令", "消防法施行令", "保安規程"):
            if label in note and label not in found:
                found.append(label)
    return ";".join(found[:4])


def pick_example(
    term: str, practice_rows: list[dict[str, str]], ichimon_rows: list[dict[str, str]]
) -> tuple[str, str]:
    if ichimon_rows:
        row = ichimon_rows[0]
        q = norm(row.get("statement"))
        if len(q) > 220:
            q = q[:217] + "…"
        ans = norm(row.get("answer_text")) or ("○" if norm(row.get("answer")).lower() == "true" else "×")
        expl = split_sentences(norm(row.get("explanation")), 1)
        detail = expl[0] if expl else ""
        return q, f"{ans}。{detail}" if detail else ans
    if practice_rows:
        row = practice_rows[0]
        q = norm(row.get("question"))
        if len(q) > 220:
            q = q[:217] + "…"
        ans_num = norm(row.get("answer"))
        labels = ("ア", "イ", "ウ", "エ", "オ")
        try:
            idx = int(ans_num) - 1
            label = labels[idx] if 0 <= idx < 5 else ans_num
        except ValueError:
            label = ans_num
        expl = split_sentences(norm(row.get("explanation")), 1)
        detail = expl[0] if expl else ""
        return q, f"正解は選択肢{label}。{detail}" if detail else f"正解は選択肢{label}。"
    return (
        f"{term}について正しい説明はどれか。",
        "公式の定義・試験テキストの説明と一致する選択肢を選ぶ。",
    )


def apply_curated(row: dict[str, str], curated: dict[str, str]) -> None:
    for key, value in curated.items():
        if norm(value):
            row[key] = value


def apply_curated_overrides(row: dict[str, str], curated: dict[str, str] | None) -> None:
    """手書きテンプレを最終反映（自動生成フィールドの上書きを防ぐ）。"""
    if not curated:
        return
    for key in (
        "short_def",
        "definition",
        "term_detail_body",
        "article_lead",
        "exam_points",
        "common_mistakes",
        "legal_basis",
    ):
        if norm(curated.get(key)):
            row[key] = norm(curated[key])
    if norm(curated.get("faq_1_answer")):
        row["faq_1_answer"] = norm(curated["faq_1_answer"])
    elif norm(row.get("short_def")):
        row["faq_1_answer"] = norm(row["short_def"])
    mistakes_curated = split_sentences(curated.get("common_mistakes", ""), 3)
    if mistakes_curated:
        row["faq_2_answer"] = mistakes_curated[0]


def enrich_row(
    row: dict[str, str],
    practice_rows: list[dict[str, str]],
    ichimon_rows: list[dict[str, str]],
    by_cat: dict[str, list[str]],
    *,
    curated: dict[str, str] | None = None,
) -> bool:
    term = norm(row.get("term"))
    category = norm(row.get("category"))
    if curated:
        apply_curated(row, curated)
    if not practice_rows and not ichimon_rows:
        return bool(curated)

    all_rows = (practice_rows + ichimon_rows) or []
    unit = most_common_unit(all_rows)
    topic = norm(all_rows[0].get("topic")) if all_rows else ""

    expl_sources = practice_rows + ichimon_rows
    if term in STRICT_MATCH_TERMS:
        expl_sources = [
            r
            for r in expl_sources
            if row_score(term, term, r) >= 8 or row_score(term, norm_term(term), r) >= 12
        ] or expl_sources[:6]
    explanations = unique_lines(
        [norm(r.get("explanation")) for r in expl_sources],
        limit=5,
    )
    if not explanations and curated:
        explanations = unique_lines(
            [curated.get("definition", ""), curated.get("term_detail_body", "")],
            limit=3,
        )
    if curated and norm(curated.get("exam_points")):
        exam_points = [p.strip() for p in curated.get("exam_points", "").split(";") if p.strip()]
    else:
        exam_points = unique_lines(
            [norm(r.get("exam_point")) for r in practice_rows + ichimon_rows],
            limit=8,
        )
    if curated and norm(curated.get("common_mistakes")):
        traps = split_semicolon_field(curated.get("common_mistakes", ""))
    else:
        traps = unique_lines(
            [norm(r.get("trap_point")) for r in practice_rows + ichimon_rows],
            limit=5,
        )

    curated_lead_locked = bool(curated and norm(curated.get("definition")))

    lead_sentence = ""
    if curated_lead_locked:
        curated_def = split_sentences(curated.get("definition", ""), 1)
        if curated_def:
            lead_sentence = trim_lead_sentence(term, curated_def[0])
    if not lead_sentence:
        lead_sentence = pick_definition_sentence(term, explanations, exam_points)
    if not lead_sentence:
        lead_sentence = trim_lead_sentence(term, norm(row.get("short_def")))

    if (
        not curated_lead_locked
        and lead_sentence
        and _definition_sentence_score(term, lead_sentence) < 8
    ):
        best_alt: tuple[int, str] | None = None
        for alt in unique_sentences(
            [trim_lead_sentence(term, e) for e in explanations if e],
            limit=8,
        ):
            sc = _definition_sentence_score(term, alt)
            if term not in alt[:70] and not alt.startswith(term):
                sc -= 15
            if best_alt is None or sc > best_alt[0]:
                best_alt = (sc, alt)
        if best_alt and best_alt[0] >= 8:
            lead_sentence = best_alt[1]

    if curated and norm(curated.get("short_def")):
        short_def = norm(curated["short_def"])
        if not short_def.endswith("。"):
            short_def += "。"
    else:
        short_def = build_short_def(term, lead_sentence, category)

    if curated_lead_locked:
        definition = norm(curated.get("definition"))
    elif lead_sentence:
        definition = f"まず「{term}」は、{lead_sentence.rstrip('。')}。"
    else:
        definition = norm(row.get("definition"))
    if not curated_lead_locked and len(explanations) > 1:
        second = trim_lead_sentence(term, explanations[1])
        if second and second != lead_sentence:
            definition += f" {second}" + ("" if second.endswith("。") else "。")
    if unit and not curated_lead_locked:
        definition += f" {category}では「{unit}」の文脈で繰り返し問われます。"

    q_count = len(practice_rows) + len(ichimon_rows)
    ex_q, ex_a = pick_example(term, practice_rows, ichimon_rows)
    legal = extract_legal_basis(all_rows) or norm(row.get("legal_basis"))
    peers = filter_related_peers(term, category, by_cat, practice_rows, ichimon_rows)

    if curated and norm(curated.get("term_detail_body")):
        term_detail_body = norm(curated["term_detail_body"])
    else:
        term_detail_body = build_term_detail_body(
            term,
            category,
            lead_sentence,
            explanations,
            exam_points,
            traps,
            unit,
            topic,
            q_count,
            peers,
            legal,
            practice_rows,
            ichimon_rows,
        )
    term_detail_body = append_db_excerpts(
        term_detail_body, term, practice_rows, ichimon_rows
    )
    if not practice_rows and not ichimon_rows:
        term_detail_body = merge_unique_detail_sentences(
            term_detail_body, term, explanations
        )

    exam_section = unique_lines(
        [norm(r.get("question")) for r in practice_rows[:3]],
        limit=2,
    )
    explanation = build_explanation_text(
        term,
        category,
        traps,
        exam_section,
        practice_rows,
        ichimon_rows,
    )

    if traps:
        mistakes = format_field_items(traps, limit=5)
    else:
        mistakes = format_field_items(
            split_semicolon_field(norm(row.get("common_mistakes"))),
            limit=5,
        )

    memory = build_memory_tip(term, peers)

    tags = parse_tags(norm(row.get("tags")))
    if "詳細記事" not in tags:
        tags.append("詳細記事")
    if practice_rows:
        tags.append("実践演習連動")
    if ichimon_rows:
        tags.append("一問一答連動")

    row.update(
        {
            "short_def": short_def,
            "definition": definition,
            "explanation": explanation,
            "article_title": f"{term}とは？{EXAM}で押さえる意味・試験ポイント",
            "article_lead": (
                norm(curated.get("article_lead"))
                if curated and norm(curated.get("article_lead"))
                else build_article_lead(
                    term,
                    category,
                    "" if curated_lead_locked else unit,
                    lead_sentence,
                )
            ),
            "term_detail_body": term_detail_body,
            "exam_points": format_field_items(exam_points, limit=8)
            if exam_points
            else norm(row.get("exam_points")),
            "common_mistakes": mistakes,
            "memory_tip": memory[:300],
            "example_question": ex_q,
            "example_answer": ex_a,
            "legal_basis": legal,
            "faq_1_question": f"{term}の試験での意味は？",
            "faq_1_answer": (
                short_def
                if short_def
                else (
                    (lead_sentence.rstrip("。") + "。")
                    if lead_sentence
                    else (
                        explanations[0]
                        if explanations
                        else norm(row.get("faq_1_answer"))
                    )
                )
            ),
            "faq_2_question": f"{term}でよくある誤りは？",
            "faq_2_answer": (
                ensure_sentence(traps[0])
                if traps
                else (
                    f"{category}分野では似た用語や数値と混同しやすいです。"
                    "演習で誤った選択肢をメモし、関連用語と対比して復習してください。"
                )
            ),
            "faq_3_question": f"{term}は試験でどう問われますか？",
            "faq_3_answer": (
                ensure_sentence(exam_points[0])
                if exam_points
                else (
                    f"{category}分野では、{term}の定義や条件の言い換えが選択肢で問われやすいです。"
                    "演習の解説で、正解と誤答の違いを確認してください。"
                )
            ),
            "faq_4_question": f"{term}を学んだあとに何を確認しますか？",
            "faq_4_answer": (
                "関連用語ページで似た語との違いを整理し、過去問演習で理解を確かめてください。"
                "制度や数値は公式情報で最新内容を確認してください。"
            ),
            "tags": ";".join(dict.fromkeys(tags)),
        }
    )
    if peers:
        row["related_terms"] = ";".join(peers)

    return True


def parse_tags(raw: str) -> list[str]:
    return [t.strip() for t in re.split(r"[;,、]", raw) if t.strip()]


def append_extra_terms(rows: list[dict[str, str]], fieldnames: list[str]) -> int:
    from tools.populate_o4_glossary_terms import build_row  # noqa: E402

    existing = {norm(r.get("term")) for r in rows}
    added = 0
    for term, category in ADD_TERMS_LIST:
        if term in existing:
            continue
        row = build_row(term, category)
        for col in fieldnames:
            row.setdefault(col, "")
        rows.append(row)
        existing.add(term)
        added += 1
    return added


def main() -> int:
    ap = argparse.ArgumentParser(description="乙4用語詳細記事の本文を問題DBから充実")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--add-terms",
        action="store_true",
        help="頻出の試験用語（BATCH_50 含む）を glossary_terms.csv に追記してから充実する",
    )
    args = ap.parse_args()

    if not CSV_PATH.is_file():
        print(f"入力がありません: {CSV_PATH}", file=sys.stderr)
        return 1

    practice_rows_src = load_csv_rows(PRACTICE)
    ichimon_rows_src = load_csv_rows(ICHIMON)
    all_q_rows = practice_rows_src + ichimon_rows_src
    exact_idx = build_question_index(all_q_rows)

    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    added_terms = 0
    if args.add_terms and not args.dry_run:
        added_terms = append_extra_terms(rows, fieldnames)
        if added_terms:
            print(f"新規用語を {added_terms} 件追加しました")
    elif args.add_terms and args.dry_run:
        existing = {norm(r.get("term")) for r in rows}
        added_terms = sum(1 for t, _ in ADD_TERMS_LIST if t not in existing)
        if added_terms:
            print(f"（dry-run）新規用語を {added_terms} 件追加予定")

    by_cat: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        t = norm(row.get("term"))
        if t:
            by_cat[norm(row.get("category"))].append(t)

    enriched = 0
    skipped_keep = 0
    meta_study = 0
    curated_only = 0
    no_source = 0

    for row in rows:
        term = norm(row.get("term"))
        if not term:
            continue
        if term in KEEP_TERMS:
            curated_keep = STUDY_KEEP_ARTICLES.get(term) or CURATED_ARTICLES.get(term)
            if curated_keep:
                apply_study_keep_full(row, curated_keep)
            skipped_keep += 1
            continue
        if term in META_STUDY_TERMS:
            apply_meta_study_term(row)
            meta_study += 1
            continue

        practice_rows, ichimon_rows = find_question_rows(term, exact_idx, all_q_rows)
        curated = CURATED_ARTICLES.get(term)
        if not practice_rows and not ichimon_rows and not curated:
            no_source += 1
            continue

        if enrich_row(row, practice_rows, ichimon_rows, by_cat, curated=curated):
            enriched += 1
            if curated and not practice_rows and not ichimon_rows:
                curated_only += 1
        elif curated:
            enriched += 1
            curated_only += 1
        if curated:
            apply_curated_overrides(row, curated)
        if practice_rows or ichimon_rows:
            row["term_detail_body"] = append_db_excerpts(
                norm(row.get("term_detail_body")),
                term,
                practice_rows,
                ichimon_rows,
            )

    for row in rows:
        if norm(row.get("term")):
            finalize_glossary_row(row)

    print(
        f"用語 {len(rows)} 件 — 詳細充実 {enriched} 件"
        f"（手書きテンプレ {curated_only} 件）、学習メタ {meta_study} 件、"
        f"手書き維持 {skipped_keep} 件、未対応 {no_source} 件"
    )

    if args.dry_run:
        return 0

    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {CSV_PATH}")
    print("Next: python3 tools/build_all.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
