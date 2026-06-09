#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
past_questions.csv の explanation から選択肢別解説を抽出し、
explanation_choices / explanation_correct を埋める。

使い方:
  python3 tools/enrich_past_explanation_choices.py
  python3 tools/enrich_past_explanation_choices.py --dry-run
  python3 tools/enrich_past_explanation_choices.py --csv path/to/past_questions.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "past_questions.csv"
CIRC = "①②③④⑤"
MIN_WRONG_NOTE_LEN = 36

# 賃貸不動産経営管理士（分野名で explanation_point を付与）
CHINTAIKAN_STUDY_HINTS: dict[str, str] = {
    "賃貸住宅管理業法": (
        "業法は「誰が・何を・どこまで」がセットで問われます。"
        "正答肢の義務主体と手続の流れをメモし、似た制度（登録・重要事項・維持保全）との違いを表に整理してから、"
        "同年・前後年度の過去問で定着を確認してください。"
    ),
    "民法・借地借家法": (
        "借地借家・民法改正の問題は、権利関係の主体と効果の発生時期を一文で説明できるかが要点です。"
        "間違えた肢は「誰に・いつ・どの効果が及ぶか」で正答と対比し、関連用語から解き直してください。"
    ),
    "賃貸借契約": (
        "契約条項・個人情報・原状回復などは、条文の趣旨と実務上の判断基準の両方が問われます。"
        "数字・期限・例外は一覧表にし、他の選択肢との差分を意識して復習してください。"
    ),
    "賃貸借契約実務": (
        "実務問題は「適切な対応か」「義務の範囲か」を区別する設問が多いです。"
        "正答のキーワードを押さえたうえで、誤答肢がどの要件を満たさないかを具体的に書き出すと定着します。"
    ),
    "賃貸不動産経営": (
        "経営・管理の意義や役割の問題は、貸主・借主・管理者の視点の違いがポイントです。"
        "「最も不適切」形式では、一見正しそうな肢こそ正答になりやすいので、設問文の条件を再確認してください。"
    ),
    "管理実務": (
        "管理実務は手続の順序と義務の主体が問われやすいです。"
        "間違えた問題は復習リストに残し、同分野の用語とセットで解き直してください。"
    ),
    "建物・設備": (
        "設備・維持保全は数値基準・点検周期・責任の所在がセットで出題されます。"
        "表や比較で整理し、他選択肢がどの要件（数値・主体・手続）とずれているかを確認してください。"
    ),
    "会計・税金・保険": (
        "税務・会計は計算の前提と課税関係者・時期の取り違えに注意です。"
        "正答の根拠数字をメモし、誤答肢がどの前提を誤っているかを明示して復習してください。"
    ),
    "会計税務": (
        "税務・会計は計算の前提と課税関係者・時期の取り違えに注意です。"
        "正答の根拠数字をメモし、誤答肢がどの前提を誤っているかを明示して復習してください。"
    ),
    "サブリース": (
        "サブリースは貸主・転貸人・借主の関係と契約上の効果の区別が要点です。"
        "各主体の権利義務を図示し、誤答肢がどの関係を取り違えているかを確認してください。"
    ),
    "原状回復": (
        "原状回復は費用負担・範囲・特約の有無が問われやすいです。"
        "正答肢の要件（通常損耗との区別など）を押さえ、他肢との差分を条文・実務の両面で整理してください。"
    ),
    "賃料管理・督促": (
        "賃料・督促は手続の順序と法的効果（催告・解除等）の対応が重要です。"
        "タイムラインで整理し、誤答肢がどの段階・要件を誤っているかを確認してください。"
    ),
    "関連法令": (
        "関連法令は本試験の主たる論点と位置づけの違いが問われます。"
        "根拠法令名と趣旨をセットで覚え、誤答肢の引用法令が設問条件と合うかを照合してください。"
    ),
    "政策課題・社会情勢": (
        "政策・社会情勢は制度の目的と最新の論点の組み合わせが出題されます。"
        "公式の考え方・用語の定義を確認したうえで、他肢が趣旨とずれていないかを見直してください。"
    ),
}

# メンタルヘルスII種など（分野名で explanation_point を付与）
CATEGORY_STUDY_HINTS: dict[str, str] = {
    **CHINTAIKAN_STUDY_HINTS,
    "基礎・役割": (
        "管理監督者の役割・法令の趣旨・ストレスの基礎知識は、用語の定義と"
        "「誰が・何を・どこまで」がセットで出題されます。間違えた肢は正答との"
        "違い（根拠法令・対象範囲・責任の所在）をメモし、関連用語から解き直すと定着します。"
    ),
    "職場環境・配慮": (
        "職場の配慮・リスク要因の問題は、具体策と「誰が担うか」を対にして覚えると得点しやすくなります。"
        "数値基準や手順は表に整理し、同年の過去問で実務イメージを補強してください。"
    ),
    "相談・連携・復職": (
        "面談・医療連携・復職支援は手順と禁止事項（やってはいけないこと）の区別が重要です。"
        "正答肢のキーワードを用語解説で確認してから、同分野の過去問に戻ると理解が深まります。"
    ),
}

LAW_RE = re.compile(
    r"(?:労働[^\s、。]{2,24}法|[^\s、。]{2,12}法|36協定|ストレスチェック|"
    r"メンタルヘルス不調者対応マニュアル|こころの耳)"
)


def norm(s: str | None) -> str:
    return (s or "").strip()


def circ(n: int) -> str:
    return CIRC[n - 1] if 1 <= n <= 5 else str(n)


def circ_to_num(ch: str) -> int | None:
    if ch in CIRC:
        return CIRC.index(ch) + 1
    if ch.isdigit():
        v = int(ch)
        return v if 1 <= v <= 5 else None
    return None


def choice_texts(row: dict) -> dict[int, str]:
    out: dict[int, str] = {}
    for i in range(1, 6):
        t = norm(row.get(f"choice_{i}"))
        if t:
            out[i] = t
    return out


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？])\s*", norm(text))
    return [p.strip() for p in parts if p.strip()]


def find_choice_refs(sentence: str, texts: dict[int, str]) -> set[int]:
    refs: set[int] = set()
    for m in re.finditer(r"[①②③④⑤]", sentence):
        refs.add(CIRC.index(m.group(0)) + 1)
    for m in re.finditer(r"[（(]([1-5])[）)]", sentence):
        refs.add(int(m.group(1)))
    for m in re.finditer(r"選択肢\s*([1-5])", sentence):
        refs.add(int(m.group(1)))
    for m in re.finditer(r"([1-5])\s*番", sentence):
        refs.add(int(m.group(1)))
    for n, txt in texts.items():
        snippet = txt[:18].strip()
        if len(snippet) >= 8 and snippet in sentence:
            refs.add(n)
    return refs


def split_wrong_inline_list(exp: str) -> dict[int, str]:
    """有機溶剤作業主任者の資格（①誤）、区分表示は青色（②誤）… を各肢へ分解。"""
    out: dict[int, str] = {}
    for m in re.finditer(
        r"([^、。；;]{2,56}?)[（(]([①②③④⑤])\s*誤[）)]",
        exp,
    ):
        n = circ_to_num(m.group(2))
        if n:
            reason = norm(m.group(1))
            out[n] = f"{reason}（{circ(n)}誤）。この記述は誤りです。"
    return out


def extract_paren_number_clauses(exp: str) -> dict[int, str]:
    """(1)…、(2)の記述は正しい など、括弧番号付きの短句を各肢へ割り当てる。"""
    out: dict[int, str] = {}
    for m in re.finditer(
        r"[（(]([1-5])[）)]"
        r"([^（(]+?)"
        r"(?=[、。；;]|$|[（(][1-5][）)])",
        exp,
    ):
        n = int(m.group(1))
        body = norm(m.group(2).strip("、。"))
        if len(body) < 2:
            continue
        clause = f"（{n}）{body}"
        if any(k in body for k in ("誤", "なし", "不要", "ない", "できない", "違反", "対象外")):
            if "この記述は" not in clause:
                clause += " この記述は本問の正答ではありません。"
        elif "正しい" in body or "妥当" in body:
            clause += "（単独の記述としては妥当な場合がありますが、設問全体の正答かどうかは他肢と比較して判断してください。）"
        if len(clause) > len(out.get(n, "")):
            out[n] = clause
    return out


def extract_choice_verdict_clauses(
    exp: str, correct: int, *, inappropriate: bool
) -> dict[int, str]:
    """「選択肢2は不適切」「○×判定でも選択肢4は不適切」など賃管CSV向け。"""
    out: dict[int, str] = {}
    verdict_re = (
        r"(適切|不適切|誤り|誤っている|誤って|誤|正しい|正しくない|妥当|違反[^、。]{0,12})"
    )
    for m in re.finditer(rf"選択肢\s*([1-5])\s*は\s*{verdict_re}", exp):
        n = int(m.group(1))
        verdict = norm(m.group(2))
        if n == correct:
            continue
        if verdict.startswith(("適切", "正しい", "妥当")):
            if inappropriate:
                out[n] = (
                    f"解説では選択肢{n}は「{verdict}」と整理されています。"
                    f"本問は最も不適切・誤っている記述を選ぶ形式のため、"
                    f"単独では妥当に見える記述でも正答にはなりません。"
                )
        else:
            out[n] = (
                f"解説では選択肢{n}は「{verdict}」と整理されています。"
                f"設問が問う正答（{correct}）と照合し、この記述がなぜ正答でないかを確認してください。"
            )
    for m in re.finditer(
        rf"(?:○×判定|参照用)[^。]*選択肢\s*([1-5])\s*は\s*{verdict_re}",
        exp,
    ):
        n = int(m.group(1))
        verdict = norm(m.group(2))
        if n == correct:
            continue
        if not verdict.startswith(("適切", "正しい", "妥当")):
            out[n] = (
                f"参照用の○×整理では選択肢{n}は「{verdict}」です。"
                f"本問の正答（{correct}）と照らし、記述のどこが設問条件とずれるかを確認してください。"
            )
    return out


def extract_marker_clauses(exp: str) -> dict[int, str]:
    """①誤、②正、③の「…」などの直後・直前の句を拾う。"""
    out: dict[int, str] = split_wrong_inline_list(exp)
    for m in re.finditer(
        r"([^、。；;]{2,48}?)[（(]([①②③④⑤])\s*誤[）)]",
        exp,
    ):
        n = circ_to_num(m.group(2))
        if n:
            reason = norm(m.group(1))
            out[n] = f"{reason}（{circ(n)}誤）。この記述は誤りです。"
    for m in re.finditer(
        r"([①②③④⑤])\s*"
        r"(?:は|の)?\s*"
        r"(?:誤り|誤っている|誤って|誤、|誤は|違反している|違反|正しくない|該当しない|不要|不要である|"
        r"正しい|正|該当|必要|違反していない|含まれない)"
        r"[^。；;]*",
        exp,
    ):
        n = circ_to_num(m.group(1))
        if not n:
            continue
        clause = norm(m.group(0))
        prev = out.get(n, "")
        if prev and "この記述は誤り" in prev:
            continue
        if len(clause) > len(prev):
            out[n] = clause
    for m in re.finditer(r"([①②③④⑤])の[「『]([^」』]{4,})[」』][^。；;]*", exp):
        n = circ_to_num(m.group(1))
        if n:
            out[n] = norm(m.group(0))
    for m in re.finditer(r"([①②③④⑤])[（(]([^）)]{2,})[）)][^。；;]*", exp):
        n = circ_to_num(m.group(1))
        if n:
            clause = norm(m.group(0))
            if len(clause) > len(out.get(n, "")):
                out[n] = clause
    return out


def extract_correct_body(exp: str, correct: int) -> str:
    c = circ(correct)
    patterns = [
        rf"正答は\s*[（(]?{correct}[）)]?",
        rf"正しいのは\s*[（(]?{c}[）)]?",
        rf"該当するのは\s*[（(]?{c}[）)]?",
        rf"誤っているのは\s*[（(]?{c}[）)]?",
        rf"{c}の[^。]+",
    ]
    for pat in patterns:
        m = re.search(pat, exp)
        if m:
            start = m.start()
            chunk = exp[start : start + 420]
            end = chunk.find("。")
            if end > 40:
                return norm(chunk[: end + 1])
            return norm(chunk)
    sents = split_sentences(exp)
    for s in sents[:4]:
        if correct in find_choice_refs(s, {}) or c in s:
            return s
    return ""


def assign_sentences(exp: str, texts: dict[int, str]) -> dict[int, list[str]]:
    buckets: dict[int, list[str]] = {i: [] for i in texts}
    for sent in split_sentences(exp):
        refs = find_choice_refs(sent, texts)
        if not refs:
            continue
        for n in refs:
            if n not in buckets:
                continue
            if sent not in buckets[n]:
                buckets[n].append(sent)
    return buckets


def assign_letter_combo(exp: str, texts: dict[int, str]) -> dict[int, list[str]]:
    """選択肢が A,B / ア,イ 形式のとき、解説中の A（…）・ア（…）を各肢へ割り当てる。"""
    buckets: dict[int, list[str]] = {i: [] for i in texts}
    for sent in split_sentences(exp):
        letters_in_sent = re.findall(r"[A-Eア-オ][（(]", sent)
        if not letters_in_sent:
            continue
        letters = {ch[0] for ch in letters_in_sent}
        for n, txt in texts.items():
            tokens = re.split(r"[,，、\sと]+", txt)
            kana_in_opt = set(re.findall(r"[ア-オ]", txt))
            if letters & set(tokens) or letters & kana_in_opt:
                if sent not in buckets[n]:
                    buckets[n].append(sent)
    return buckets


def extract_kana_letter_clauses(exp: str) -> dict[str, str]:
    """ア（効力なし）… のようにカナラベル付き解説を抽出。"""
    out: dict[str, str] = {}
    for m in re.finditer(
        r"([ア-オ])（([^）]{1,32})）\s*([^。]+。?)",
        norm(exp),
    ):
        letter = m.group(1)
        if letter not in out:
            out[letter] = f"{m.group(2)}　{m.group(3).strip()}"
    return out


def kana_combo_choice_note(
    n: int, opt: str, exp: str, correct: int, correct_opt: str
) -> str:
    """区分所有法など「アとイ」型の組合せ肢向け解説。"""
    letters = re.findall(r"[ア-オ]", opt)
    if len(letters) < 2:
        return ""
    clauses = extract_kana_letter_clauses(exp)
    if not clauses:
        return ""
    bits = [f"{L}：{clauses[L][:110]}" for L in letters if L in clauses]
    summary = ""
    if "これらを踏まえると" in exp:
        summary = exp.split("これらを踏まえると", 1)[1].strip()[:140]
    body = " ".join(bits)
    note = (
        f"（{n}）「{opt}」は正答（{correct}）「{correct_opt}」と異なる組合せです。"
    )
    if body:
        note += f" {body}"
    if summary:
        note += f" {summary}"
    return note.strip()


def is_true_only_marker(note: str) -> bool:
    compact = re.sub(r"\s+", "", note)
    if "誤" in compact:
        return False
    return bool(re.search(r"[①②③④⑤]?正[）)]?", compact)) and len(compact) < 90


def combo_choice_note(n: int, opt: str, exp: str, correct: int, correct_opt: str) -> str:
    letters = re.findall(r"[A-E]", opt)
    if not letters:
        return ""
    hits: list[str] = []
    for sent in split_sentences(exp):
        if any(f"{L}（" in sent or f"{L}(" in sent for L in letters):
            if any(k in sent for k in ("不要", "義務", "必要", "該当", "誤", "ない")):
                hits.append(sent)
    if hits:
        return f"（{n}）の組合せ「{opt}」について：{hits[0]}"
    correct_letters = "".join(re.findall(r"[A-E]", correct_opt))
    return (
        f"（{n}）「{opt}」は、作業主任者の選任が必要な作業の組合せ（{correct_letters}）を"
        f"含んでいません。解説のとおり、該当作業と非該当作業の区別を確認してください。"
    )


def finalize_wrong_note(
    note: str,
    n: int,
    opt: str,
    correct: int,
    correct_opt: str,
    exp: str,
    stem: str,
) -> str:
    note = norm(note)
    if len(note) >= MIN_WRONG_NOTE_LEN and re.search(
        r"効力|組合せ|区分所有|解説では|⇒|→|第\d+条",
        note,
    ):
        return note
    opt_short = opt[:80] + ("…" if len(opt) > 80 else "")
    correct_short = correct_opt[:80] + ("…" if len(correct_opt) > 80 else "")

    if len(re.findall(r"[①②③④⑤]", note)) >= 2:
        return (
            f"（{n}）「{opt_short}」は、単独の記述としては法令上妥当な場合がありますが、"
            f"本問で選ぶべき正答は（{correct}）「{correct_short}」です。"
            f"問題文の条件と照らし、設問が問う論点に合う肢を選び直してください。"
        )

    if is_true_only_marker(note) or re.fullmatch(r"[①②③④⑤\s、,正）)（(・]+", note.replace(" ", "")):
        return (
            f"（{n}）「{opt_short}」は、単独の記述としては法令上妥当な場合がありますが、"
            f"本問で選ぶべき正答は（{correct}）「{correct_short}」です。"
            f"問題文の条件（{stem[:48]}…）と照らし、設問が問う論点に合う肢を選び直してください。"
        )

    # 他肢の正誤が混在する長い文から、当該肢を含む文だけ残す
    if note.count("正") > 2 and circ(n) not in note[:12]:
        for sent in split_sentences(note):
            if circ(n) in sent or f"（{n}）" in sent:
                note = sent
                break

    note = re.sub(r"\s+", " ", note).strip()
    return note


def shared_wrong_clause(exp: str, wrong_nums: list[int], correct: int) -> str:
    """②③④⑤は〜しません などの一括記述を各肢に展開する。"""
    joined = "".join(circ(n) for n in wrong_nums)
    m = re.search(
        rf"[{''.join(CIRC)}]{{2,}}[^。]*(?:しません|ない|誤り|該当しません|対象外|不要)[^。]*。",
        exp,
    )
    if m:
        return norm(m.group(0))
    m = re.search(
        rf"(?:他の選択肢|その他)[^。]*(?:{joined}|など)[^。]*。",
        exp,
    )
    if m:
        return norm(m.group(0))
    return ""


def polish_note(note: str, n: int, opt: str, correct: int, category: str) -> str:
    note = norm(note)
    if "この記述は誤り" in note:
        opt_short = opt[:56] + ("…" if len(opt) > 56 else "")
        enriched = f"{note} 対象の記述は「{opt_short}」。"
        return enriched if len(enriched) >= MIN_WRONG_NOTE_LEN else enriched
    if len(note) >= MIN_WRONG_NOTE_LEN:
        return note
    opt_short = opt[:72] + ("…" if len(opt) > 72 else "")
    if note:
        return f"{note} 選択肢（{n}）「{opt_short}」は本問の正答（{correct}）とは異なるため不適です。"
    cat = category.split("（")[0] if category else "本試験"
    tail = (
        "解説の根拠・用語の定義と照らして正答を確認してください。"
        if category in CATEGORY_STUDY_HINTS
        else "記述内容と法令・制度の要件の対応を確認してください。"
    )
    return (
        f"選択肢（{n}）「{opt_short}」は、{cat}の出題趣旨・問題文の条件に照らすと正答（{correct}）ではありません。"
        f"{tail}"
    )


def stem_asks_inappropriate(stem: str) -> bool:
    return "不適切" in stem and "適切" in stem


def law_terms(text: str) -> list[str]:
    return list(dict.fromkeys(LAW_RE.findall(norm(text))))


def infer_contrast_note(
    n: int,
    opt: str,
    correct: int,
    correct_opt: str,
    exp: str,
    stem: str,
) -> str:
    """解説が短く肢番号を含まない場合、正答・解説と誤答肢の記述を突き合わせる。"""
    opt_short = opt[:64] + ("…" if len(opt) > 64 else "")
    correct_short = correct_opt[:56] + ("…" if len(correct_opt) > 56 else "")
    reasons: list[str] = []

    if stem_asks_inappropriate(stem):
        return (
            f"（{n}）「{opt_short}」は、設問の趣旨では適切な記述・対応に当たることが多いです。"
            f"本問は「最も不適切なもの」を選ぶ形式のため、正答は（{correct}）「{correct_short}」です。"
            f"解説のポイント：{exp[:120]}{'…' if len(exp) > 120 else ''}"
        )

    exp_laws = law_terms(exp)
    opt_laws = law_terms(opt)
    wrong_laws = [l for l in opt_laws if l not in exp_laws and not any(l in e or e in l for e in exp_laws)]
    if wrong_laws and exp_laws:
        reasons.append(
            f"根拠の記述が異なります。解説では「{exp_laws[0]}」が根拠ですが、"
            f"（{n}）は「{wrong_laws[0]}」を根拠とする内容です。"
        )

    if re.search(r"刑事罰|罰則|処罰", opt) and not re.search(r"刑事|罰則|処罰", exp):
        reasons.append(
            f"（{n}）は刑事罰・処罰を前提としていますが、本問の解説は制度の趣旨・"
            f"配慮義務の内容を問うもので、刑事罰が直ちに科される趣旨ではありません。"
        )

    if re.search(r"のみ|だけ|必ず|すべて|いつでも|発生しない|ない$|しない$", opt):
        if re.search(r"個人|管理監督者|双方|精神|メンタル|及ぶ|ある|問われる|あり得る", exp):
            if re.search(r"のみ|だけ", opt) and re.search(r"個人|管理監督者|双方", exp):
                reasons.append(
                    "「のみ」「だけ」などの限定表現が解説の内容（責任主体・対象範囲の広さ）と一致しません。"
                )
            if "発生しない" in opt and re.search(r"ないわけではない|あり得る|減額", exp):
                reasons.append(
                    "「発生しない」と断定していますが、解説では過失相殺等を踏まえ賠償がゼロとは限らない趣旨です。"
                )

    if re.search(r"心療内科", opt) and "精神科" in exp and "心身症" in exp:
        reasons.append(
            "心療内科と精神科の診療範囲の区別が解説と異なります。精神科は精神疾患全般、"
            "心療内科は心身症が中心という整理が本問のポイントです。"
        )
    if re.search(r"精神科", opt) and "心療内科" in exp and "心身症" in exp and "すべて" in opt:
        reasons.append("診療科の対象範囲の言い過ぎ・取り違えがある可能性があります。")

    for sent in split_sentences(exp):
        if len(sent) < 12:
            continue
        key = sent[:24]
        if key in opt:
            continue
        if any(
            tok in opt
            for tok in ("ない", "しない", "のみ", "誤", "対象外", "不要", "含まれない")
        ) and any(tok in sent for tok in ("及ぶ", "ある", "必要", "実施", "有効", "適切")):
            if len(sent) <= 100:
                reasons.append(f"解説では「{sent}」とある一方、（{n}）の記述はそれと矛盾します。")
                break

    if not reasons:
        reasons.append(
            f"（{n}）の内容は、正答（{correct}）「{correct_short}」が示す論点とずれています。"
        )

    lead = " ".join(reasons[:2])
    return (
        f"{lead} 解説の要点：{exp[:140]}{'…' if len(exp) > 140 else ''} "
        f"正答（{correct}）との違いを確認し直してください。"
    )


def synthesize_wrong_note(
    n: int,
    opt: str,
    correct: int,
    correct_opt: str,
    exp: str,
    category: str,
    buckets: dict[int, list[str]],
) -> str:
    if buckets.get(n):
        return polish_note("".join(buckets[n]), n, opt, correct, category)
    # 正答説明との対比
    correct_sents = buckets.get(correct) or []
    lead = correct_sents[0] if correct_sents else extract_correct_body(exp, correct)
    if lead:
        return polish_note(
            f"本問の正答は（{correct}）です。{lead} したがって（{n}）の記述は正答ではありません。",
            n,
            opt,
            correct,
            category,
        )
    return polish_note("", n, opt, correct, category)


def build_row_fields(row: dict) -> tuple[str, str, str]:
    texts = choice_texts(row)
    if not texts:
        cat = norm(row.get("category"))
        pt = norm(row.get("explanation_point")) or CATEGORY_STUDY_HINTS.get(cat, "")
        return "", "", norm(row.get("explanation_summary")), pt
    try:
        correct = int(row["correct"])
    except (TypeError, ValueError):
        cat = norm(row.get("category"))
        pt = norm(row.get("explanation_point")) or CATEGORY_STUDY_HINTS.get(cat, "")
        return "", "", norm(row.get("explanation_summary")), pt

    exp = norm(row.get("explanation"))
    if not exp:
        cat = norm(row.get("category"))
        return "", "", "", CATEGORY_STUDY_HINTS.get(cat, "")

    stem = norm(row.get("stem"))
    inappropriate = stem_asks_inappropriate(stem)
    markers = extract_marker_clauses(exp)
    for n, clause in extract_choice_verdict_clauses(
        exp, correct, inappropriate=inappropriate
    ).items():
        if clause and (n not in markers or len(clause) > len(markers.get(n, ""))):
            markers[n] = clause
    paren_markers = extract_paren_number_clauses(exp)
    for n, clause in paren_markers.items():
        if clause and (n not in markers or len(clause) > len(markers.get(n, ""))):
            markers[n] = clause
    buckets = assign_sentences(exp, texts)
    letter_buckets = assign_letter_combo(exp, texts)
    for n, sents in letter_buckets.items():
        for s in sents:
            if s not in buckets.setdefault(n, []):
                buckets[n].append(s)
    for n, clause in markers.items():
        if n in texts and clause:
            if clause not in buckets.get(n, []):
                buckets.setdefault(n, []).insert(0, clause)

    wrong_nums = [n for n in texts if n != correct]
    shared = shared_wrong_clause(exp, wrong_nums, correct)
    if shared:
        for n in wrong_nums:
            if not buckets.get(n):
                per = shared
                for other in wrong_nums:
                    if other != n:
                        per = per.replace(circ(other), "")
                per = re.sub(r"[①②③④⑤]{2,}", circ(n), per)
                buckets[n] = [
                    f"（{n}）「{texts[n][:48]}…」について：{per}"
                    if len(texts[n]) > 10
                    else per
                ]

    wrong_map: dict[int, str] = {}
    correct_opt = texts.get(correct, "")
    for n in wrong_nums:
        parts: list[str] = []
        if re.search(r"[ア-オ]", texts[n]):
            combo = kana_combo_choice_note(n, texts[n], exp, correct, correct_opt)
            if combo:
                parts.append(combo)
        elif re.match(r"^[A-E]", texts[n].strip()):
            combo = combo_choice_note(n, texts[n], exp, correct, correct_opt)
            if combo:
                parts.append(combo)
        if markers.get(n) and "この記述は誤り" in markers[n]:
            parts = [markers[n]]
        else:
            if markers.get(n):
                parts.append(markers[n])
            for s in buckets.get(n, []):
                if s in parts:
                    continue
                if circ(n) in s or f"（{n}）" in s or f"（{n}誤）" in s:
                    parts.append(s)
                elif len(parts) == 0 and len(s) > 40:
                    parts.append(s)
        note = finalize_wrong_note(
            " ".join(parts[:2]),
            n,
            texts[n],
            correct,
            correct_opt,
            exp,
            stem,
        )
        wrong_map[n] = polish_note(
            note, n, texts[n], correct, norm(row.get("category"))
        )

    category = norm(row.get("category"))

    for n in wrong_nums:
        if len(wrong_map[n]) < MIN_WRONG_NOTE_LEN:
            wrong_map[n] = synthesize_wrong_note(
                n,
                texts[n],
                correct,
                correct_opt,
                exp,
                category,
                buckets,
            )
        wrong_map[n] = finalize_wrong_note(
            wrong_map[n], n, texts[n], correct, correct_opt, exp, stem
        )
        if len(wrong_map[n]) < MIN_WRONG_NOTE_LEN or wrong_map[n] == polish_note(
            "", n, texts[n], correct, category
        ):
            wrong_map[n] = infer_contrast_note(
                n, texts[n], correct, correct_opt, exp, stem
            )
        wrong_map[n] = polish_note(
            wrong_map[n], n, texts[n], correct, category
        )

    if len(wrong_nums) >= 2:
        notes = [wrong_map[n] for n in wrong_nums]
        if len(set(notes)) == 1:
            for n in wrong_nums:
                m = re.search(rf"\({n}\)\s*([^。]+。?)", exp)
                if m:
                    wrong_map[n] = polish_note(
                        m.group(1).strip(), n, texts[n], correct, category
                    )
                else:
                    wrong_map[n] = infer_contrast_note(
                        n, texts[n], correct, correct_opt, exp, stem
                    )

    correct_body = norm(row.get("explanation_correct"))
    if not correct_body:
        parts = []
        if markers.get(correct):
            parts.append(markers[correct])
        parts.extend(buckets.get(correct, []))
        correct_body = " ".join(dict.fromkeys(parts)) or extract_correct_body(exp, correct)
        if not correct_body:
            correct_body = exp[:500]
    for bad in (
        " この記述は本問の正答ではありません。",
        "本問の正答ではありません",
        "正答ではありません",
    ):
        correct_body = correct_body.replace(bad, "")
    correct_body = re.sub(r"\s{2,}", " ", correct_body).strip()

    summary = norm(row.get("explanation_summary"))
    if not summary or summary == exp[:200]:
        lead = extract_correct_body(exp, correct) or exp[:180]
        summary = lead[:220]

    choices_field = ";".join(f"{n}:{wrong_map[n]}" for n in sorted(wrong_map))
    point = norm(row.get("explanation_point")) or CATEGORY_STUDY_HINTS.get(category, "")
    return choices_field, correct_body, summary, point


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--only-empty",
        action="store_true",
        help="explanation_choices が既に入っている行は上書きしない",
    )
    args = ap.parse_args()
    path = args.csv.resolve()
    if not path.is_file():
        print(f"error: CSV not found: {path}", file=sys.stderr)
        return 1

    text = path.read_text(encoding="utf-8-sig")
    rows = list(csv.DictReader(text.splitlines()))
    if not rows:
        print("error: empty CSV", file=sys.stderr)
        return 1
    fieldnames = list(rows[0].keys())
    for col in (
        "explanation_choices",
        "explanation_correct",
        "explanation_summary",
        "explanation_point",
    ):
        if col not in fieldnames:
            fieldnames.append(col)

    short = 0
    skipped = 0
    for row in rows:
        if args.only_empty and norm(row.get("explanation_choices")):
            skipped += 1
            continue
        choices_field, correct_body, summary, point = build_row_fields(row)
        if choices_field:
            note_lens = [
                len(p.split(":", 1)[1])
                for p in choices_field.split(";")
                if ":" in p
            ]
            if note_lens:
                avg = sum(note_lens) / len(note_lens)
                if avg < MIN_WRONG_NOTE_LEN:
                    short += 1
        if not args.dry_run:
            row["explanation_choices"] = choices_field
            row["explanation_correct"] = correct_body
            row["explanation_summary"] = summary
            if point:
                row["explanation_point"] = point

    filled = sum(1 for r in rows if norm(r.get("explanation_choices")))
    print(f"rows={len(rows)} explanation_choices filled={filled}")
    if skipped:
        print(f"skipped (only-empty): {skipped}")
    if short:
        print(f"warning: {short} rows with short average wrong-note length")

    if args.dry_run:
        sample = rows[0]
        print("sample q1 choices:", sample.get("explanation_choices", "")[:200])
        return 0

    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
