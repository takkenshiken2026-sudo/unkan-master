# -*- coding: utf-8 -*-
"""知識ハブ執筆サンプルページ用の固定データ。"""

from __future__ import annotations

WRITING_SAMPLE_SLUGS = {
    "compare": "c-writing-sample.html",
    "numbers": "n-writing-sample.html",
    "mistakes": "m-writing-sample.html",
    "glossary": "g-writing-sample.html",
    "glossary_diagram": "g-diagram-sample.html",
}

SAMPLE_BANNER_INNER = (
    '<div class="knowledge-hub-sample-banner" role="note">'
    "<p><strong>執筆サンプル</strong>"
    " — 知識ハブ記事の構成・文体・表の書き方の見本です。"
    "CSV 執筆時は {doc_link} とテンプレ CSV をあわせて参照してください。</p>"
    '<p class="knowledge-hub-sample-banner-links">'
    '<a href="{samples_href}">サンプル一覧</a>'
    '<span aria-hidden="true">·</span>'
    '<a href="{type_href}">{type_label}一覧</a>'
    "</p></div>"
)


def sample_banner_html(*, samples_href: str, type_href: str, type_label: str, doc_href: str) -> str:
    doc_link = f'<a href="{doc_href}">執筆ガイド</a>'
    return SAMPLE_BANNER_INNER.format(
        doc_link=doc_link,
        samples_href=samples_href,
        type_href=type_href,
        type_label=type_label,
    )


def sample_robots_meta() -> str:
    return '<meta name="robots" content="noindex, follow">'


COMPARE_WRITING_SAMPLE: dict = {
    "title": "【執筆サンプル】35条説明と37条書面の違い",
    "category": "契約・実務",
    "tags": "宅建業法;書面",
    "summary": "契約前の重要事項説明と契約後の37条書面交付を、時期・目的・担当者の観点で比較します。",
    "col_labels": ["35条説明（重要事項説明）", "37条書面"],
    "compare_rows": [
        {
            "axis": "実施時期",
            "cols": [
                "原則として契約前（自ら売主の場合は2日以内）",
                "原則として契約後5日以内（契約前交付も可）",
            ],
        },
        {
            "axis": "主な目的",
            "cols": [
                "取引内容の重要事項を説明し、判断材料を提供する",
                "契約内容を書面で確定し、交付する",
            ],
        },
        {
            "axis": "担当",
            "cols": [
                "宅地建物取引士が説明（原則）",
                "書面の作成・交付義務（説明担当とは別枠で整理）",
            ],
        },
        {
            "axis": "試験の引っかけ",
            "cols": [
                "「37条も契約前」など時期の取り違え",
                "「35条は契約後」など順序の逆転",
            ],
        },
    ],
    "article_title": "【執筆サンプル】35条説明と37条書面の違い｜比較表の書き方",
    "article_lead": (
        "宅建試験で頻出の「35条と37条」は、契約前後の順序をセットで覚える必要があります。"
        "比較表記事では、時期・目的・担当の3軸を横並びにし、最後に試験の引っかけ行を足すと実用的になります。"
    ),
    "exam_points": "35条=契約前の説明;37条=契約後5日以内の交付;順序を逆にする肢が定番",
    "common_mistakes": "35条と37条を同じタイミングの書面だと思い込むと、時期に関する肢で誤答しやすくなります。",
    "memory_tip": "「前に35・後に37」と契約の流れに沿って覚えると整理しやすいです。",
    "related_terms": "公式情報;試験要項",
    "faq_1_question": "35条説明と37条書面の違いは？",
    "faq_1_answer": (
        "35条説明（重要事項説明）は原則として契約前に行う説明、37条書面は契約後5日以内の交付が基本です。"
        "「いつ・何を」するかが異なるため、比較表では実施時期の行を必ず入れます。"
    ),
    "faq_2_question": "比較表記事では何行書けばよい？",
    "faq_2_answer": (
        "4〜6行が目安です。定義・目的・試験での見方・引っかけの4行構成は、執筆テンプレとして使いやすい型です。"
        "3列比較の場合は col_labels も3件に揃えます。"
    ),
    "faq_3_question": "用語解説との使い分けは？",
    "faq_3_answer": (
        "各語の定義は用語解説、2語の差分整理は比較表に分担します。"
        "比較表末尾の関連用語から用語解説へリンクを張り、相互に読めるようにします。"
    ),
    "faq_4_question": "このサンプルの使い方は？",
    "faq_4_answer": (
        "data/comparisons.csv への追記時に、compare_rows の JSON 構造と FAQ の粒度を参照してください。"
        "scaffold_knowledge_hub_article.py で雛形を出力し、このページと見比べながら編集する流れが効率的です。"
    ),
    "slug_file": WRITING_SAMPLE_SLUGS["compare"],
}

NUMBERS_WRITING_SAMPLE: dict = {
    "title": "【執筆サンプル】契約前後の説明・交付期限",
    "category": "契約・実務",
    "tags": "期限;宅建業法",
    "summary": "35条説明・37条書面・クーリング・オフなど、契約関連の代表数字を早見表にまとめた例です。",
    "highlight": "35条8日 / 37条5日 / CO 8日",
    "detail_rows": [
        {
            "item": "重要事項説明（35条）",
            "value": "原則8日以内",
            "note": "契約前。自ら売主は2日以内",
        },
        {
            "item": "37条書面の交付",
            "value": "原則5日以内",
            "note": "契約後。契約前交付も可",
        },
        {
            "item": "クーリング・オフ",
            "value": "8日以内",
            "note": "書面交付を受けた日から（対象取引）",
        },
        {
            "item": "手付金の上限",
            "value": "代金の20%以内",
            "note": "売買契約。超過部分は無効",
        },
    ],
    "article_title": "【執筆サンプル】契約前後の説明・交付期限｜早見表の書き方",
    "article_lead": (
        "数値・期限早見表は、1ページに関連する数字を3〜8行に集約します。"
        "value 列は短く、note 列に例外・条文・条件を書くと、一覧でも詳細でも読みやすくなります。"
    ),
    "exam_points": "数字と条件（誰が・いつ）をセットで覚える;highlight 列で一覧の3列目を要約する",
    "common_mistakes": "8日と5日を入れ替えて暗記すると、時期問題で即不正解になります。",
    "memory_tip": "「前8・後5・CO8・手付20%」と契約フロー順に並べると記憶しやすいです。",
    "related_terms": "公式情報;試験要項",
    "faq_1_question": "早見表と比較表の違いは？",
    "faq_1_answer": (
        "早見表は同一テーマの数字を縦に並べ、比較表は2〜3項目の差分を横に並べます。"
        "35条と37条の「違い」は比較表、関連する期限数字の一覧は早見表が向いています。"
    ),
    "faq_2_question": "highlight 列は何を書く？",
    "faq_2_answer": (
        "一覧ページ3列目に出る代表値です。「35条8日 / 37条5日」のように、"
        "記事の核心となる数字をスラッシュ区切りで短くまとめます。"
    ),
    "faq_3_question": "item_rows は何行必要？",
    "faq_3_answer": (
        "3〜8行が目安です。少なすぎるとページが薄く、多すぎると1記事の焦点がぼやけます。"
        "テーマを「契約前後の期限」「報酬・手付金」など1つに絞ります。"
    ),
    "faq_4_question": "このサンプルの使い方は？",
    "faq_4_answer": (
        "data/numbers.csv の item_rows JSON を参照し、scaffold --type numbers で雛形を生成してください。"
        "資格固有の数字は必ず公式テキストで裏取りしてから公開します。"
    ),
    "slug_file": WRITING_SAMPLE_SLUGS["numbers"],
}

MISTAKES_WRITING_SAMPLE: dict = {
    "title": "【執筆サンプル】35条説明と37条書面の取り違え",
    "category": "契約・実務",
    "tags": "誤答;宅建業法",
    "summary": "契約前後の説明・交付を逆にする典型肢を、誤答例と正解の対比で整理した例です。",
    "confusion_point": "契約前後の順序",
    "detail_rows": [
        {
            "topic": "実施時期",
            "wrong": "37条書面は契約前に交付しなければならない",
            "correct": "35条説明は契約前、37条書面は原則契約後5日以内",
            "trap": "説明と交付の順序",
        },
        {
            "topic": "35条の位置づけ",
            "wrong": "35条説明は契約後でもよい",
            "correct": "35条説明は原則契約前（自ら売主は2日以内）",
            "trap": "35条を契約後とする肢",
        },
        {
            "topic": "宅建士の関与",
            "wrong": "37条書面の交付も宅建士が説明する",
            "correct": "35条説明は宅建士が説明。37条は書面交付義務",
            "trap": "説明義務と交付義務の混同",
        },
    ],
    "article_title": "【執筆サンプル】35条説明と37条書面の取り違え｜誤答パターンの書き方",
    "article_lead": (
        "誤答パターン記事は、過去問で実際に引っかかる肢に近い文言を wrong 列に書きます。"
        "correct 列は短く整理し、trap 列で「何に引っかかるか」を一言で示すのがコツです。"
    ),
    "exam_points": "wrong は肢に近い言い回しにする;trap 列で引っかけの型を明示する",
    "common_mistakes": "比較表と内容が重複する場合、誤答記事は「肢の言い回し」に焦点を当てると差別化できます。",
    "memory_tip": "過去問で間違えた肢をそのまま wrong 列に転記すると、復習資料としても使えます。",
    "related_terms": "公式情報;試験要項",
    "faq_1_question": "誤答パターン記事の書き方は？",
    "faq_1_answer": (
        "pattern_rows の wrong / correct / trap の3列を埋めます。"
        "wrong は「正しそうに見える誤り」、trap は試験作成者の意図を短く書きます。"
    ),
    "faq_2_question": "比較表と何が違う？",
    "faq_2_answer": (
        "比較表は制度の差分整理、誤答パターンは選択肢レベルの引っかけ整理です。"
        "同じテーマでも両方用意すると、理解と演習対策の両方に使えます。"
    ),
    "faq_3_question": "confusion_point 列は？",
    "faq_3_answer": (
        "一覧3列目に出る混同ポイントの一言です。"
        "検索と一覧で「何が似ているか」が伝わる短いフレーズにします。"
    ),
    "faq_4_question": "このサンプルの使い方は？",
    "faq_4_answer": (
        "data/mistakes.csv への追記時に pattern_rows の JSON 構造を参照してください。"
        "演習で間違えた問題があれば、その肢を wrong 列に追加する運用も有効です。"
    ),
    "slug_file": WRITING_SAMPLE_SLUGS["mistakes"],
}

GLOSSARY_WRITING_SAMPLE: dict = {
    "term": "【執筆サンプル】重要事項説明",
    "category": "法令・制度",
    "tags": "宅建業法;書面",
    "short_def": "宅建士が契約前に行う、取引内容の重要事項の説明。",
    "definition": (
        "宅地建物取引業法35条に基づき、宅地建物取引士が、売買・交換・賃貸借等の契約前に、"
        "相手方に対して重要事項を説明する制度。書面または電磁的方法で行う。"
    ),
    "related_terms": "公式情報;試験要項;比較表",
    "legal_basis": "宅地建物取引業法第35条",
    "importance": "A",
    "explanation": (
        "35条説明が出る問題では、実施時期（契約前）、説明者（宅建士）、"
        "説明方法（書面・電磁的方法）の3点が選択肢で問われやすいです。"
        "37条書面との順序の取り違えにも注意します。"
    ),
    "article_title": "【執筆サンプル】重要事項説明とは？用語解説の書き方",
    "article_lead": (
        "用語解説は1語1ページで、定義・試験論点・FAQまで含む詳細記事です。"
        "このサンプルは、term_detail_body の段落構成と exam_points の書き方の見本として使えます。"
    ),
    "term_detail_body": (
        "重要事項説明（35条説明）は、宅地建物取引士試験で最頻出の手続のひとつです。"
        "契約の前に、相手方が判断に必要な情報を説明する制度であり、"
        "宅建士が関与する点が試験の要点になります。\n\n"
        "説明は原則として契約前8日以内（自ら売主の場合は2日以内）に行います。"
        "37条書面が契約後の交付であるのに対し、35条説明は「契約前」に位置づけられるため、"
        "両者の順序をセットで覚える必要があります。比較表・早見表・誤答パターン記事とあわせて読むと理解が定着しやすくなります。"
    ),
    "exam_points": "契約前8日（自ら売主2日）;宅建士が説明;37条書面との順序",
    "common_mistakes": "37条書面と同じタイミングだと思い込む。口頭のみで足りると誤解する。",
    "memory_tip": "「前に35・宅建士・8日」とセットで覚える。",
    "example_question": "重要事項説明は、原則として契約後5日以内に行う。",
    "example_answer": "×。35条説明は原則契約前8日以内。5日は37条書面の交付期限の典型値。",
    "faq_1_question": "重要事項説明（35条説明）とは？",
    "faq_1_answer": (
        "宅建士が契約前に行う重要事項の説明制度です。"
        "取引内容の判断に必要な情報を、書面または電磁的方法で提供します。"
        "試験では実施時期と37条書面との違いが頻出です。"
    ),
    "faq_2_question": "用語解説記事で厚く書く列は？",
    "faq_2_answer": (
        "term_detail_body（180字以上・2段落以上）と FAQ 4件（各100字以上）が必須です。"
        "glossary-term-template.md の必須列一覧に沿って執筆してください。"
    ),
    "faq_3_question": "関連用語は何件必要？",
    "faq_3_answer": (
        "related_terms は登録済み用語2件以上が目安です。"
        "混同しやすい語がある場合は比較表記事も別途用意すると内部リンクが強化されます。"
    ),
    "faq_4_question": "このサンプルの使い方は？",
    "faq_4_answer": (
        "scaffold_glossary_term.py で雛形を生成し、glossary_terms.csv に追記する流れが基本です。"
        "このページの見出し順・情報量を参考に、資格固有の内容へ差し替えてください。"
    ),
    "slug_file": WRITING_SAMPLE_SLUGS["glossary"],
    "field_hub": "",
}

GLOSSARY_DIAGRAM_SAMPLE: dict = {
    "term": "【執筆サンプル】建ぺい率と容積率",
    "category": "法令・制度",
    "tags": "都市計画;建築基準",
    "short_def": "建ぺい率は1階の広がり、容積率は全階の床面積合計を敷地面積で割った割合。",
    "definition": (
        "建ぺい率は建築面積を敷地面積で割った割合（％）で、土地の上に建物がどれだけ広がっているかを示す。"
        "容積率は延床面積を敷地面積で割った割合（％）で、建物全体の床面積の大きさを示す。"
        "都市計画法・建築基準法の分野で頻出の対比用語です。"
    ),
    "related_terms": "公式情報;試験要項;比較表",
    "legal_basis": "都市計画法;建築基準法",
    "importance": "A",
    "explanation": (
        "建ぺい率は「真上から見た1階の広がり」、容積率は「全階の床面積の合計」と覚えると整理しやすい。"
        "敷地面積200㎡・建築面積100㎡・延床面積240㎡なら、建ぺい率50％・容積率120％になる典型例がよく出ます。"
        "分子（建築面積か延床面積か）の取り違えが定番の引っかけです。"
    ),
    "article_title": "【執筆サンプル】建ぺい率と容積率｜用語解説への図解差し込み",
    "article_lead": (
        "図解が必要な用語記事では、CSV の diagram_id 列に JSON の ID を指定します。"
        "このサンプルは compare_dual 型の2項目比較図解を「定義と基本理解」の直後に挿入した見本です。"
    ),
    "term_detail_body": (
        "建ぺい率と容積率は、どちらも敷地面積を分母にする割合ですが、分子が異なります。"
        "建ぺい率は建築面積（原則1階の建築面積）を使い、土地の上に建物がどれだけ広がっているかを表します。"
        "容積率は延床面積（各階の床面積の合計）を使い、建物全体の規模を表します。\n\n"
        "試験では数値例とセットで問われることが多く、"
        "「建築面積÷敷地面積」と「延床面積÷敷地面積」を混同しないことが重要です。"
        "下の図解ブロックは data/term_diagrams/kenpei-yoseki.json から自動生成されます。"
    ),
    "exam_points": "建ぺい率=建築面積÷敷地面積;容積率=延床面積÷敷地面積;分子の取り違えに注意",
    "common_mistakes": "建ぺい率に延床面積を使う。容積率に建築面積を使う。全階合計と1階のみの見方を逆にする。",
    "memory_tip": "建ぺい=真上から1階、容積=全階の床を足す。",
    "example_question": "敷地面積200㎡、建築面積100㎡、延床面積240㎡のとき、建ぺい率と容積率は？",
    "example_answer": "建ぺい率50％（100÷200）、容積率120％（240÷200）。",
    "faq_1_question": "建ぺい率と容積率の違いは？",
    "faq_1_answer": (
        "建ぺい率は建築面積を敷地面積で割った割合で、1階の広がりを表します。"
        "容積率は延床面積を敷地面積で割った割合で、全階の床面積合計を表します。"
        "どちらも％表示ですが、見る対象が異なります。"
    ),
    "faq_2_question": "用語記事に図解を差し込む方法は？",
    "faq_2_answer": (
        "glossary_terms.csv に diagram_id 列を追加し、data/term_diagrams/ 内の JSON ID を指定します。"
        "例: diagram_id=kenpei-yoseki。図解は定義セクションの直後に「図解で理解する」として挿入されます。"
        "図解データは tools/term_diagram.py がビルド時に HTML 化します。"
    ),
    "faq_3_question": "compare_dual 型とは？",
    "faq_3_answer": (
        "2項目を左右に並べ、それぞれに図解・計算式・例・メモを載せるテンプレートです。"
        "left/right に label, catch, formula, example, memo, visual（land または floors）を書きます。"
        "試験の覚え方と一問一答ブロックも JSON で指定できます。"
    ),
    "faq_4_question": "このサンプルの使い方は？",
    "faq_4_answer": (
        "terms/diagram-samples/ で図解単体を確認し、g-diagram-sample.html で記事内配置を確認してください。"
        "新規図解は kenpei-yoseki.json をコピーして編集し、必要な用語行の diagram_id に ID を設定します。"
    ),
    "diagram_id": "kenpei-yoseki",
    "slug_file": WRITING_SAMPLE_SLUGS["glossary_diagram"],
    "field_hub": "",
}
