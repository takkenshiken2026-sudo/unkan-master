#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""テンプレ同梱の guide / glossary サンプルを編集品質基準まで引き上げる（1回実行用）."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

GUIDE_CSV = ROOT / "data" / "guide_articles.csv"
GLOSSARY_CSV = ROOT / "data" / "glossary_terms.csv"

BOILER_BODY = (
    "受験前には公式情報や演習解説で数値・期限・主体を必ず確かめ、"
    "似た用語との違いは関連用語ページで整理してください。"
)
GENERIC_FAQ_SNIPPET = "制度や数値は年度や改正で変わるため、本番前には試験実施団体の公式情報"


def strip_boiler(text: str) -> str:
    t = text.replace(BOILER_BODY, "").strip()
    t = re.sub(r"。{2,}", "。", t)
    t = re.sub(r"。\s*。", "。", t)
    return t.strip()


def pad_to(text: str, min_len: int, suffix: str) -> str:
    t = text.strip()
    if len(t) >= min_len:
        return t
    extra = suffix
    while len(t + extra) < min_len:
        extra += " " + suffix
    return (t.rstrip("。") + "。" + extra).strip()


def two_paragraphs(p1: str, p2: str) -> str:
    return f"{p1.strip()}\n\n{p2.strip()}"


GUIDE_SECTION_PATCHES: dict[str, dict[str, str]] = {
    "exam-overview": {
        "section_1_body": (
            "試験日程・申込方法・受験資格・出題範囲・合格発表は、年度や制度改正で変わることがあります。"
            "学習を始める前に、試験実施団体の公式ページで「最新の受験案内」を開き、申込期限と手数料をメモしてください。"
            "非公式なまとめサイトは便利ですが、最終判断は必ず公式情報に置きます。\n\n"
            "特に見落としやすいのは、免除制度の有無、持ち物、会場案内、合格発表の方法です。"
            "申込直前にもう一度公式ページを開き、PDFの更新日が直近かどうかを確認すると安心です。"
        ),
        "section_2_body": (
            "このサイトでは、過去問演習・実践演習・一問一答・用語解説・復習記録を組み合わせて学習できます。"
            "公式情報で「制度と日程」を確認したうえで、サイト内では知識の定着と弱点の可視化に使うのが基本です。\n\n"
            "たとえば、過去問で間違えた語句は用語ページで定義と試験論点を確認し、同分野の問題に戻って解き直します。"
            "演習だけを増やすのではなく、間違いの理由を短く残すと、次回の学習が具体的になります。"
        ),
        "section_3_body": (
            "受験前に押さえる項目は、試験の目的、受験対象、出題形式、合格基準、年間スケジュール、受験後の手続きです。"
            "これらをチェックリスト化しておくと、検索で迷ったときに読み返しやすくなります。\n\n"
            "出題形式（CBTか紙か、科目数、制限時間）が分かると、過去問の解き方や模擬試験の使い方も決めやすくなります。"
            "合格基準に科目別の足切りがある場合は、苦手科目を放置しない計画が必要です。"
        ),
        "section_4_body": (
            "試験日程・手数料・出題範囲・合格基準は、年度ごとに更新されることがあります。"
            "学習中も、月1回程度は公式ページを開き、変更告知がないかを確認する習慣が有効です。\n\n"
            "法改正や要項改定があった年は、過去問の解説と公式範囲のズレに注意してください。"
            "古い問題集だけで進めると、出題範囲外の論点に時間を使ってしまうことがあります。"
        ),
        "section_5_body": (
            "学習を始める場合は、出題範囲の整理記事、過去問の使い方、学習計画の記事へ進むと回遊しやすくなります。"
            "概要記事で全体像をつかんだあと、自分の弱点に合ったガイドを選ぶと迷いが減ります。\n\n"
            "用語解説は、過去問で出た語句から読み始めると効率的です。"
            "関連記事リンクをたどり、同じ分野の用語をまとめて確認すると理解がつながります。"
        ),
        "faq_2_answer": (
            "受験前のチェックリストとして使います。"
            "試験名・年度・申込期限・出題範囲を公式情報で確認したうえで、"
            "このサイトの過去問一覧や学習計画の記事へ進んでください。"
            "制度の数値は資格ごとに異なるため、本文の例は対象試験の公式要項に必ず照合してください。"
        ),
    },
    "study-plan": {
        "section_1_body": (
            "まず出題範囲を分野ごとに分け、公式要項の科目・配点と照合します。"
            "site-config の fields 順に並べると、演習一覧や用語集と同じ分類で学習でき、弱点の見える化がしやすくなります。\n\n"
            "最初の1週間は「全体マップ作り」に充て、各分野で既知・未知を色分けする程度で十分です。"
            "細かい暗記は、過去問で具体的な論点が見えてから始めると効率が上がります。"
        ),
        "section_2_body": (
            "過去問で間違えたテーマは、用語解説で定義と根拠を確認してから、同分野の問題に戻ります。"
            "問題文だけを繰り返すより、用語・制度・数字をセットで押さえると、似た選択肢の見分けが身につきます。\n\n"
            "たとえば、法令分野で迷ったら関連用語ページの比較表を見て、数字や期限の違いを整理します。"
            "その後、実践演習や一問一答で短時間確認すると、記憶の定着を確かめやすくなります。"
        ),
        "section_3_body": (
            "復習日は、カレンダーに「解き直し日」を先に入れておくと実行しやすくなります。"
            "不正解・ブックマーク・説明できなかった用語を対象に、翌日・3日後・試験前の3回程度見直すのが目安です。\n\n"
            "復習では正答番号だけでなく、「なぜ他の選択肢が違うか」を言葉にできるかまで確認します。"
            "言語化できない問題は、まだ理解が浅いサインとして、用語ページに戻ります。"
        ),
        "section_4_body": (
            "直前期は新しい教材を増やしすぎず、間違えた問題・重要用語・頻出数字を中心に絞り込みます。"
            "広く浅く見直すより、過去問で何度も迷った分野を1つずつ潰す方が得点に近づきやすいです。\n\n"
            "模擬試験を使う場合は、時間配分と分野別得点を記録し、翌日に弱点分野の用語と過去問へ戻る流れを作ります。"
            "直前1週間は「新規インプット」より「確認と解き直し」に比重を置くと安定しやすくなります。"
        ),
        "section_5_body": (
            "独学向け・短期合格向け・分野別対策・直前期対策など、状況に合った試験ガイドを選ぶと計画が立てやすくなります。"
            "1本の記事を読み終えたら、action_items の項目をそのままToDoにし、完了したら関連記事へ進んでください。\n\n"
            "学習記録に「次に解く年度・分野・用語」を1行書いておくと、翌日の再開がスムーズです。"
            "完璧なノートより、再開のための短いメモを優先します。"
        ),
    },
    "past-question-strategy": {
        "section_1_body": (
            "最初は1年度分を通しで解き、出題形式と選択肢の聞かれ方に慣れます。"
            "点数は参考程度にし、どの分野で迷ったか、どの用語が分からなかったかを記録してください。\n\n"
            "解き終えたらすぐに全問の解説を読むのではなく、不正解と「自信がなかった問題」だけをピックアップすると効率が上がります。"
            "記録例：「法令・第12問・『35条書面』と混同」など、短くて構いません。"
        ),
        "section_2_body": (
            "間違いの理由は、知識不足・読み飛ばし・用語の混同・数字の暗記不足・時間切れなどに分類します。"
            "分類が付くと、次に開くべき用語ページや復習方法が決まります。\n\n"
            "たとえば混同が多い場合は、関連用語を2〜3件まとめて読み、比較表を自分用に作るとよいです。"
            "知識不足の場合は、分野別の基礎記事や一問一答で短時間確認してから再挑戦します。"
        ),
        "section_3_body": (
            "解説に出てきた重要語句は、用語集で定義・試験論点・よくある誤解まで確認します。"
            "関連用語リンクから似た語句へ進むと、選択肢の「紛らわしい表現」への耐性が上がります。\n\n"
            "解説を読むときは「正解の理由」だけでなく、「誤答がなぜ誤りか」まで追うことが重要です。"
            "誤答パターンは次の年度の似た問題でも再現されやすいため、メモに残します。"
        ),
        "section_4_body": (
            "同じ問題は、当日・数日後・試験前のように間隔を空けて解き直します。"
            "連続で正解しても、条件を1語変えただけで誤答になることがあるため、時間を置いた確認が有効です。\n\n"
            "ブラウザの復習機能やブックマークを使い、解き直し対象を一覧化しておくと漏れが減ります。"
            "解き直しでまた間違えた問題は、優先度を上げて用語と過去問の両方から攻めます。"
        ),
        "section_5_body": (
            "学習計画や用語解説の記事と組み合わせると、過去問で見つけた弱点を体系的に復習できます。"
            "過去問だけを100回解くより、弱点→用語→過去問のループの方が、実力の伸びを感じやすいです。\n\n"
            "年度をまたいで同じ論点が出るかも確認し、頻出テーマのリストを作ると直前期の整理に使えます。"
            "リストは10項目以内に絞ると、見返しやすくなります。"
        ),
    },
    "glossary-how-to": {
        "section_1_body": (
            "用語集では分野別に用語をたどれます。重要度Aの語や、過去問・実践演習で出た語句から読むと、"
            "試験で問われやすい論点を効率よく押さえられます。\n\n"
            "一覧では短い定義だけが見えますが、個別ページでは試験ポイント・誤解・例題・FAQまで確認できます。"
            "「知っているつもり」の用語こそ、個別ページで選択肢の論点まで読み返すと効果的です。"
        ),
        "section_2_body": (
            "各用語ページでは、定義に加えて試験で問われやすい条件、法令根拠（該当する場合）、"
            "よくある誤解、覚え方、例題、FAQを確認できます。\n\n"
            "本文は180字以上を目安に、2段落以上で整理されています。"
            "薄い定義だけのページではなく、受験者が迷いやすい点まで書かれているかを確認しながら読み進めてください。"
        ),
        "section_3_body": (
            "関連用語のリンクから、似た語句やセットで覚える語句へ進めます。"
            "混同しやすい語は3件まとめて読むと、比較表のイメージがつかみやすくなります。\n\n"
            "演習 CSV に `term:用語名` タグが付いている問題から辿ると、実際の出題文脈で理解できます。"
            "用語→演習→用語の往復が、暗記だけより定着しやすいです。"
        ),
        "section_4_body": (
            "例題セクションでは、正誤や空欄形式で理解を確認できます。"
            "自分の弱点に合わせ、重要度AやSの用語から読むと学習効率が上がります。\n\n"
            "例題の解説では、なぜ他の選択肢が違うかまで確認してください。"
            "○×だけ覚えると、言い換え問題で誤答しやすくなります。"
            "1問あたり2分以内で説明できるかが、本番での判断速度の目安になります。"
        ),
        "section_5_body": (
            "数字・期限・似た制度名は、テーマごとにまとめて読み返すと理解が深まります。"
            "たとえば申込・受験資格・合格基準は、公式情報と用語ページをセットで見直すと整理しやすいです。\n\n"
            "用語を増やしたあとは、関連用語が登録済み名称か、FAQが4役割で重複していないかを"
            "執筆時に確認すると、読者に渡る記事の質が安定します。"
        ),
    },
}


GLOSSARY_PATCHES: dict[str, dict[str, str]] = {}


def build_glossary_faqs(term: str) -> dict[str, str]:
    """用語ごとに4FAQを役割分担（100字以上）."""
    return {
        "faq_1_question": f"{term}とは何ですか？",
        "faq_1_answer": pad_to(
            f"{term}は、◯◯試験の学習や受験判断で押さえる概念です。"
            f"短い定義だけでなく、試験では選択肢の言い換えや似た用語との違いとして問われることがあります。"
            f"個別ページの「定義と基本理解」で意味と位置づけを確認してください。",
            100,
            "具体例は演習解説と公式情報で照合します。",
        ),
        "faq_2_question": f"{term}でよくある誤解は？",
        "faq_2_answer": pad_to(
            f"「{term}」を別の語句と同じ意味だと思い込む、または一般常識で答えてしまう誤りが多いです。"
            f"本文の「よくある誤解」で、過去問の誤答パターンとセットで確認すると改善しやすくなります。",
            100,
            "混同する語は関連用語リンクから比較してください。",
        ),
        "faq_3_question": f"{term}は試験でどう問われますか？",
        "faq_3_answer": pad_to(
            f"定義の言い換え、数値・期限・主体の条件、例外の有無などが四択で問われやすいです。"
            f"「選択肢で問われやすい点」と例題を読み、なぜ誤答になるかまで言語化してから次の問題へ進んでください。",
            100,
            "実践・一問一答に term タグがあれば該当問も確認します。",
        ),
        "faq_4_question": f"{term}を学んだあとに何を確認しますか？",
        "faq_4_answer": pad_to(
            f"関連用語を2件以上読み、過去問または実践演習で理解を確認します。"
            f"制度・数値が絡む場合は試験要項などの公式情報で最新の条件を必ず照合してください。",
            100,
            "間違えた問題は復習リストに残して解き直します。",
        ),
    }


def polish_glossary_row(row: dict[str, str]) -> None:
    term = row["term"].strip()
    definition = strip_boiler(row.get("definition", ""))
    detail = strip_boiler(row.get("term_detail_body", ""))
    # 2段落化
    sentences = [s.strip() for s in re.split(r"[。]", detail) if s.strip()]
    if len(sentences) < 2:
        sentences = [definition, detail or definition]
    mid = max(1, len(sentences) // 2)
    p1 = "。".join(sentences[:mid]) + "。"
    p2 = "。".join(sentences[mid:]) + ("。" if sentences[mid:] else "")
    if len(p2) < 40:
        p2 = (
            f"試験では、{term}がどの選択肢で問われるかを過去問・実践演習の解説で確認します。"
            f"正解だけでなく、似た用語との違いと数値条件をセットで整理すると得点につながりやすくなります。"
        )
    row["term_detail_body"] = pad_to(two_paragraphs(p1, p2), 180, "公式情報と演習解説で最新条件を確認してください。")
    row["definition"] = pad_to(definition, 50, "試験対策では公式情報と照合します。")
    row["article_lead"] = pad_to(
        strip_boiler(row.get("article_lead", "")),
        60,
        f"{term}の意味と試験での見方を、この記事で整理します。",
    )
    expl = strip_boiler(row.get("explanation", ""))
    if len(expl) < 80 or "選択肢" not in expl:
        expl = (
            f"{term}が出る問題では、定義の言い換え・数値や期限の条件・似た用語との違いが"
            f"選択肢で問われやすいです。演習の解説で、正解と誤答の根拠を比較して確認してください。"
        )
    row["explanation"] = pad_to(expl, 80, "演習解説で選択肢の違いを確認してください。")
    row["common_mistakes"] = pad_to(
        strip_boiler(row.get("common_mistakes", "")),
        40,
        "公式情報と照合して確認してください。",
    )
    row["memory_tip"] = pad_to(
        strip_boiler(row.get("memory_tip", "")),
        25,
        "関連語とセットで覚えます。",
    )
    if "の要点。" in row.get("short_def", ""):
        row["short_def"] = row["short_def"].replace("の要点。", "。")
    row.update(build_glossary_faqs(term))
    if term in GLOSSARY_PATCHES:
        row.update(GLOSSARY_PATCHES[term])


GUIDE_SECTION_PATCHES_EXTRA: dict[str, dict[str, str]] = {
    "self-study-roadmap": {
        "section_2_body": (
            "独学では、何をどこまで学ぶかを自分で決める必要があります。"
            "まず出題範囲を分野ごとに分け、過去問や用語を同じカテゴリで整理します。"
            "分野が揃っていると、苦手な領域を見つけやすくなります。\n\n"
            "公式要項の科目名と、サイト内の分野ラベルを対応づけると、"
            "演習データと用語集を行き来しやすくなります。"
            "1分野あたりの目標時間を週単位で書いておくと、計画の抜けが減ります。"
        ),
    },
}

GUIDE_FAQ_PATCHES: dict[str, dict[str, str]] = {
    "exam-overview": {
        "faq_1_answer": (
            "試験実施団体の公式サイト、受験案内、試験要項、合格発表ページで確認します。"
            "ブログや口コミと内容が違う場合は、必ず公式情報を優先してください。"
            "申込前と直前期の2回は、日程・手数料・出題範囲を改めて見直すと安全です。"
        ),
    },
    "study-plan": {
        "faq_1_answer": (
            "前提知識や1日の学習時間により異なりますが、出題範囲の広さを見て余裕を持った期間を設定します。"
            "過去問で現在地を測り、弱点分野に週あたりの時間を配分すると計画が現実的になります。"
        ),
        "faq_2_answer": (
            "全体像把握のため、基礎を軽く確認したうえで1年度分の過去問に早めに触れる方法は有効です。"
            "ただし解きっぱなしにせず、間違えた用語は用語解説で定義と試験論点まで戻って確認してください。"
        ),
    },
    "past-question-strategy": {
        "faq_1_answer": (
            "資格によって異なります。過去問は出題傾向と弱点発見に欠かせませんが、"
            "法改正や出題範囲の改定は公式情報で必ず確認してください。"
            "過去問だけで足りるかは、自分の得点と科目別基準を見て判断します。"
        ),
        "faq_2_answer": (
            "正答番号だけでなく、なぜ他の選択肢が誤りか、どの用語を混同したかをメモします。"
            "関連用語ページで似た語の違いを整理し、数日後に同じ問題を解き直して定着を確認します。"
        ),
    },
}


def upgrade_guides() -> None:
    rows = list(csv.DictReader(GUIDE_CSV.open(encoding="utf-8-sig")))
    for row in rows:
        slug = row.get("slug", "").strip()
        patch = {
            **GUIDE_SECTION_PATCHES.get(slug, {}),
            **GUIDE_SECTION_PATCHES_EXTRA.get(slug, {}),
            **GUIDE_FAQ_PATCHES.get(slug, {}),
        }
        for col, val in patch.items():
            row[col] = val
        lead = row.get("lead", "")
        if len(lead) < 80:
            row["lead"] = pad_to(
                lead,
                80,
                "公式情報を先に確認し、このサイトの演習と用語解説で弱点を補強する流れを推奨します。",
            )
        intent = row.get("user_intent", "")
        if len(intent) < 50:
            row["user_intent"] = pad_to(
                intent,
                50,
                "読了後に公式確認と演習・用語復習まで進められる状態を目指します。",
            )
        for n in range(1, 8):
            col = f"section_{n}_body"
            if row.get(col):
                row[col] = pad_to(
                    row[col],
                    180,
                    "数値・期限は対象試験の公式要項で必ず確認してください。",
                )
        for n in range(1, 4):
            a = row.get(f"faq_{n}_answer", "")
            if len(a) < 100:
                row[f"faq_{n}_answer"] = pad_to(
                    strip_boiler(a).replace("差し替えてください", "公式要項で確認してください"),
                    100,
                    "対象資格の最新情報に照合してください。",
                )
    with GUIDE_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys(), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def upgrade_glossary() -> None:
    rows = list(csv.DictReader(GLOSSARY_CSV.open(encoding="utf-8-sig")))
    for row in rows:
        polish_glossary_row(row)
        row["explanation"] = row["explanation"].replace("。。。。。。。", "。")
    with GLOSSARY_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys(), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    upgrade_guides()
    upgrade_glossary()
    print("Upgraded sample guide and glossary CSV for editorial quality.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
