# -*- coding: utf-8 -*-
"""過去問・実践演習・一問一答の解説 HTML（正解の理由・他肢コメント）。"""

from __future__ import annotations

import html
import re

from tools.q_content_quality import (
    clean_ichimon_correct_body,
    dedupe_prose,
    ichimon_body_already_states_truth,
    strip_four_choice_leak,
)


def norm(value: object) -> str:
    return (value or "").strip() if value is not None else ""


_FW_DIGIT_TRANS = str.maketrans("０１２３４５６７８９", "0123456789")


def _parse_choice_num(raw: str) -> int | None:
    s = norm(raw).translate(_FW_DIGIT_TRANS)
    return int(s) if s.isdigit() else None


def correct_choice_indices(correct: object) -> set[int]:
    """page['correct'] から正答肢番号の集合（multi は 1,4 → {1,4}）。"""
    if correct is None:
        return set()
    if isinstance(correct, int):
        return {correct}
    raw = norm(correct)
    if not raw:
        return set()
    if raw.isdigit():
        return {int(raw)}
    if "," in raw and all(part.strip().isdigit() for part in raw.split(",") if part.strip()):
        return {int(part.strip()) for part in raw.split(",") if part.strip()}
    return set()


def _correct_choice_index(correct: object) -> int | None:
    """page['correct'] が int または multi の '1,3' 等のとき、先頭肢番号を返す。"""
    indices = correct_choice_indices(correct)
    return min(indices) if indices else None


def parse_numbered_choice_notes(text: str) -> dict[int, str]:
    """「１．…２．…」形式（運管過去問解説など）の肢別メモを抽出。"""
    out: dict[int, str] = {}
    if not text:
        return out
    section_re = (
        r"(?:^|(?<=[。．\n]))"
        r"(?:([０-９]+)[．.]|(\d{1,2})[．.](?![0-9]))\s*"
        r"(.+?)"
        r"(?=(?:^|(?<=[。．\n]))(?:[０-９]+[．.]|\d{1,2}[．.](?![0-9]))|$)"
    )
    for m in re.finditer(section_re, text, flags=re.DOTALL):
        num = _parse_choice_num(m.group(1) or m.group(2))
        note = norm(m.group(3))
        if num is not None and note:
            out[num] = note
    return out


def text_to_html(text: str) -> str:
    if not text:
        return ""
    return html.escape(text).replace("\n", "<br>\n")


def parse_explanation_choices(raw: str) -> dict[int, str]:
    """選択肢別解説。形式: 「2:理由;3:理由」または改行区切り「（2）理由」。"""
    out: dict[int, str] = {}
    if not raw:
        return out
    for chunk in re.split(r"[\n;]+", raw):
        chunk = norm(chunk)
        if not chunk:
            continue
        m = re.match(r"^[（(]?(\d+)[）)]?\s*[:：]?\s*(.+)$", chunk)
        if m:
            out[int(m.group(1))] = m.group(2).strip()
    return out


def question_ask_mode(stem: str) -> str:
    """設問の求め方: most_correct / least_appropriate / truefalse_mark / unknown。"""
    s = norm(stem)
    if re.search(r"「適」を.*「不適」|適切なものには.*不適|不適」を記入", s):
        return "truefalse_mark"
    if re.search(r"適切でない|誤っている|誤りである|正しくない|不適切なもの", s):
        return "least_appropriate"
    if re.search(r"正しい|妥当|適切である|適切なもの", s):
        return "most_correct"
    return "unknown"


def _choice_sounds_positive(text: str) -> bool:
    t = norm(text)
    if not t:
        return False
    positive = (
        r"確認する|整理する|復習|見直|用語|過去問|頻出|公式|記録|学習に役立|効率|押さえ|"
        r"組み合わせ|たどる|ブックマーク|振り返|比較表|一覧"
    )
    negative = r"しない方が|不要|優先する|削除|送信される|連携できない|役立たない|変わらない|固定"
    if re.search(negative, t):
        return False
    return bool(re.search(positive, t))


def _snippet(text: str, max_len: int = 36) -> str:
    t = norm(text)
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _normalize_for_compare(text: str) -> str:
    return re.sub(r"\s+", "", norm(text))


def _parrots_stem(stem: str, body: str) -> bool:
    """正解理由が設問文の言い換え・丸写しに近いか。"""
    s = _normalize_for_compare(stem)
    b = _normalize_for_compare(body)
    if not s or not b:
        return False
    if len(s) >= 24 and s in b:
        return True
    if len(s) >= 16 and b in s and len(b) >= int(len(s) * 0.85):
        return True
    return False


def _ichimon_judgment_clause(statement: str) -> str:
    m = re.search(r"「([^」]+)」", norm(statement))
    if m:
        return m.group(1)
    return norm(statement)


_MIN_CHOICE_NOTE_LEN = 72


def _strip_summary_overlap(summary: str, body: str) -> str:
    sm = dedupe_prose(summary)
    bd = dedupe_prose(body)
    if not sm or not bd:
        return bd
    if sm == bd:
        return ""
    sm_core = sm.rstrip("。")
    if bd.startswith(sm_core):
        rest = bd[len(sm_core) :].lstrip("。、 \n")
        if len(re.sub(r"\s+", "", rest)) < 48:
            return ""
        return rest
    if sm.startswith(bd.rstrip("。")):
        return ""
    sm_first = re.split(r"(?<=[。！？!?])\s*", sm)[0].strip()
    if sm_first and len(sm_first) >= 16 and sm_first in bd:
        rest = bd.replace(sm_first, "", 1).lstrip("。、 \n")
        if len(re.sub(r"\s+", "", rest)) < 48:
            return ""
        return rest
    return bd


_WRONG_NOTE_BOILER_RE = re.compile(
    r"解説の要点[：「][^。]*[。]?|解説の要点は「[^」]*」[^。]*[。]?|"
    r"との違いを、?解説の要点[^。]*[。]?|との違いを確認し直してください[。]?|"
    r"[^。]*が示す論点と一致しません[。]?|"
    r"解説では「[^」]{8,}」とある一方、（\d+）の記述はそれと矛盾します[。]?"
)


def _strip_wrong_note_boilerplate(note: str, *, context: str = "") -> str:
    """enrich テンプレや正解解説の丸写しを他肢解説から除去する。"""
    n = norm(note)
    if not n:
        return n
    n = _WRONG_NOTE_BOILER_RE.sub("", n)
    n = re.sub(r"\s*正解の要点:\s*", "", n)
    if context:
        ctx_keys = {
            re.sub(r"\s+", "", s)
            for s in re.split(r"(?<=[。！？!?])\s*", dedupe_prose(context))
            if len(re.sub(r"\s+", "", s)) >= 16
        }
        kept: list[str] = []
        for sent in re.split(r"(?<=[。！？!?])\s*", n):
            s = sent.strip()
            if not s:
                continue
            if re.sub(r"\s+", "", s) in ctx_keys:
                continue
            kept.append(s if s.endswith("。") else s + "。")
        n = "".join(kept)
    return dedupe_prose(n.strip(" 。、"))


def _is_enrich_boilerplate_note(note: str) -> bool:
    n = norm(note)
    if not n:
        return False
    if not re.search(
        r"解説の要点[：「]|解説の要点は「|が示す論点と一致しません|"
        r"との違いを、?解説の要点|との違いを確認し直してください",
        n,
    ):
        return False
    cleaned = _strip_wrong_note_boilerplate(n)
    return len(cleaned) < _MIN_CHOICE_NOTE_LEN


def _ensure_correct_body(page: dict, row: dict, summary: str, correct_body: str) -> tuple[str, str]:
    """要約との重複除去・設問丸写し時は正答肢ベースで理由を組み立てる。"""
    stem = norm(page.get("stem_plain") or page.get("stem") or "")
    summary = dedupe_prose(summary)
    correct_body = _strip_summary_overlap(summary, dedupe_prose(correct_body))
    if summary and correct_body and dedupe_prose(summary) == dedupe_prose(correct_body):
        correct_body = ""
    correct = page.get("correct")
    cor_idx = _correct_choice_index(correct)
    opts = page.get("opts") or []
    opt_text = opts[cor_idx - 1] if cor_idx and 1 <= cor_idx <= len(opts) else ""
    correct_indices = correct_choice_indices(correct)
    numbered = parse_numbered_choice_notes(
        norm(row.get("explanation")) or correct_body
    )
    if len(correct_indices) > 1 and numbered:
        correct_notes = [
            numbered[i] for i in sorted(correct_indices) if i in numbered
        ]
        if correct_notes:
            correct_body = dedupe_prose(" ".join(correct_notes))
        return summary, correct_body

    if correct_body and not _parrots_stem(stem, correct_body):
        return summary, correct_body
    mode = question_ask_mode(stem)
    parts: list[str] = []
    if correct is not None:
        if mode == "least_appropriate":
            parts.append(
                f"正答（{correct}）は、"
                "設問が問う「最も適切でないもの」に該当します。"
            )
        elif not summary or _is_thin_enrich_summary(summary):
            parts.append(f"正答は（{correct}）です。")
    for src in (
        norm(row.get("explanation_correct")),
        norm(row.get("explanation")),
    ):
        if src and not _parrots_stem(stem, src):
            for sent in re.split(r"(?<=[。！？!?])\s*", src):
                s = sent.strip()
                if not s or _is_thin_enrich_summary(s):
                    continue
                if re.fullmatch(r"正答は\d+[。]?", s):
                    continue
                if s.startswith("正答は") and len(s) < 20:
                    continue
                if len(s) >= 16 and not re.match(r"^（\d+）", s):
                    parts.append(s if s.endswith("。") else s + "。")
                    break
            if len(parts) > (0 if mode == "least_appropriate" else 1):
                break
    rebuilt = dedupe_prose("\n\n".join(parts))
    return summary, rebuilt or correct_body


def _is_substantive_choice_note(note: str) -> bool:
    """短くても試験解説として有用（⇒対比・条文・誤り理由など）。"""
    n = norm(note)
    if not n:
        return False
    if len(n) >= _MIN_CHOICE_NOTE_LEN:
        return True
    if _is_enrich_boilerplate_note(n):
        return False
    if re.search(
        r"⇒|→|第\d+条|誤り|誤っ|正しく|届出|認可|不適|適\.|「.+」|解説では|効力なし|効力あり|組合せ",
        n,
    ):
        return True
    return False


def _is_redundant_answer_lead(summary: str, correct: object) -> bool:
    """ページ上部の正答欄と同文のリードを省く。"""
    s = norm(summary)
    if not s or correct is None:
        return False
    cor = norm(str(correct))
    return bool(
        re.fullmatch(rf"正答は[（(]{re.escape(cor)}[）)]です[。]?", s)
        or re.fullmatch(rf"正答は\s*[（(]{re.escape(cor)}[）)]\s*です[。]?", s)
    )


def parse_inline_paren_choice_reasons(text: str) -> dict[int, str]:
    """本文中の (2)理由、(3)理由 形式を肢番号ごとに抽出。"""
    out: dict[int, str] = {}
    if not text:
        return out
    for chunk in re.split(r"(?<=[、,。])\s*(?=[（(]\d+[）)])|(?=^[（(]\d+[）)])", text):
        chunk = norm(chunk).lstrip("、,")
        m = re.match(r"^[（(](\d+)[）)](.+)$", chunk)
        if not m:
            continue
        num = int(m.group(1))
        note = norm(m.group(2)).strip("、。；; ")
        if note:
            out[num] = note
    return out


def _inline_wrong_notes(row: dict) -> dict[int, str]:
    merged = " ".join(
        norm(row.get(k))
        for k in ("explanation", "explanation_correct", "explanation_summary")
        if norm(row.get(k))
    )
    return parse_inline_paren_choice_reasons(merged)


def _is_thin_enrich_summary(text: str) -> bool:
    n = norm(text)
    if not n:
        return True
    if re.search(r"単独の記述としては妥当|設問全体の正答かどうかは他肢と比較", n):
        return len(n) < 160
    return False


def _substantive_explanation_lead(row: dict) -> str:
    for key in ("explanation", "explanation_correct"):
        src = norm(row.get(key))
        if not src:
            continue
        m = re.search(r"正答は[^。]+。", src)
        if m and len(m.group(0)) >= 20:
            return m.group(0)
        for sent in re.split(r"(?<=[。！？!?])\s*", src):
            s = sent.strip()
            if len(s) >= 24 and not _is_thin_enrich_summary(s):
                return s if s.endswith("。") else s + "。"
    return ""


def _keyword_tokens(text: str) -> set[str]:
    return set(
        re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{2,}", _normalize_for_compare(text))
    )


def _keyword_overlap_ratio(a: str, b: str) -> float:
    ta, tb = _keyword_tokens(a), _keyword_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def _overlaps_correct_choice_text(text: str, page: dict) -> bool:
    cor_idx = _correct_choice_index(page.get("correct"))
    opts = page.get("opts") or []
    if not cor_idx or not text or not (1 <= cor_idx <= len(opts)):
        return False
    opt = opts[cor_idx - 1]
    if _keyword_overlap_ratio(text, opt) >= 0.5:
        return True
    nt, no = _normalize_for_compare(text), _normalize_for_compare(opt)
    return len(nt) >= 24 and len(no) >= 24 and (nt in no or no in nt)


def _compact_wrong_note_vs_choice(choice_text: str, note: str) -> str:
    """他肢解説が選択肢全文と酷似する場合、対比だけに短縮する。"""
    opt, n = norm(choice_text), norm(note)
    if not opt or not n or _keyword_overlap_ratio(n, opt) < 0.5:
        return note
    flips = (
        (r"小さい", r"大きい"),
        (r"低い", r"高い"),
        (r"少ない", r"多い"),
    )
    for wpat, rpat in flips:
        wm = re.search(wpat, opt)
        rm = re.search(rpat, n)
        if wm and rm:
            return f"「{wm.group(0)}」とあるが、正しくは「{rm.group(0)}」の関係です。"
    if re.search(r"反映する|適している|最も適", opt) and re.search(r"反映しない", n):
        return (
            "RMRは動的筋作業向けの指標であり、"
            "精神的・静的作業の負担は正確に反映されません。"
        )
    if re.search(r"全く無関係|常に一定", opt):
        return "基礎代謝量は体格・性別・年齢等の影響を受けます（「全く一定」は誤り）。"
    return note


def _pick_explanation_lead(page: dict, row: dict, summary: str) -> str:
    """正答肢と重複するリードは出さない。"""
    candidates: list[str] = []
    if summary and not _is_thin_enrich_summary(summary):
        candidates.append(summary)
    lead = _substantive_explanation_lead(row)
    if lead:
        candidates.append(lead)
    for cand in candidates:
        if cand and not _overlaps_correct_choice_text(cand, page):
            return cand
    return ""


def _strip_choice_echo(note: str, choice_text: str, choice_num: int) -> str:
    """選択肢見出しと重複する引用・肢番号付きリードを除去。"""
    n = norm(note)
    if not n:
        return n
    if re.match(rf"^（{choice_num}）(?:の内容は|は)", n):
        return n
    snip = _snippet(choice_text, 48)
    patterns = [
        rf"^（{choice_num}）「{re.escape(snip)}[^」]*」は、?",
        rf"^（{choice_num}）「[^」]+」は、?",
    ]
    for pat in patterns:
        n2 = re.sub(pat, "", n).strip()
        if n2 != n:
            n = n2
            break
    if snip and snip in n and len(n) < len(note) * 0.85:
        # 見出しと同じ長文引用が本文に残る場合は、対比以降だけ残す
        m = re.search(r"(⇒|→).+", n)
        if m:
            n = m.group(0).strip()
    return n.strip(" 。、")


def _is_thin_choice_note(note: str, mode: str) -> bool:
    """CSV の選択肢別解説が形式的・短すぎるか（読み手向けの価値が低い）。"""
    n = norm(note)
    if not n:
        return True
    if _is_substantive_choice_note(n):
        return False
    if len(n) < _MIN_CHOICE_NOTE_LEN:
        return True
    if mode == "least_appropriate":
        if re.search(r"本肢.*妥当|正しい学習|推奨される学習", n) and len(n) < 140:
            if not re.search(
                r"最も適切でない|正答は[（(]?\d|学習効果.*損|有害|放棄|誤った記述",
                n,
            ):
                return True
        if re.search(r"設問形式の読み違えに注意", n) and len(n) < 100:
            return True
    if mode == "most_correct" and re.search(r"本肢を選ぶ場合は、設問が", n):
        return True
    if re.search(r"本問で選ぶべき正答は[（(]?\d", n):
        return len(n) < _MIN_CHOICE_NOTE_LEN
    if re.search(r"単独の記述としては法令上妥当", n):
        return True
    if re.search(r"が示す論点とずれています", n) and len(n) < 200:
        return True
    if re.search(r"基準と照らすと正答になりません", n):
        return True
    return False


def _choice_specific_lead(
    choice_num: int,
    opt: str,
    *,
    mode: str,
    correct: object,
    correct_text: str,
    category: str,
) -> str:
    """肢ごとに異なる冒頭文（同一テンプレ連発を防ぐ）。"""
    snip = _snippet(opt, 36)
    if mode == "least_appropriate" and _choice_sounds_positive(opt):
        return (
            f"（{choice_num}）「{snip}」は単体では妥当な学習法・対応に当たります。"
            "「最も適切でないもの」として選ぶ正答にはなりません。"
        )
    if mode == "least_appropriate":
        return (
            f"（{choice_num}）「{snip}」は一見もっともらしいですが、"
            f"正答（{correct}）「{_snippet(correct_text, 40)}」ほど"
            "学習・制度・実務の観点で問題がある記述ではありません。"
        )
    if mode == "most_correct":
        return (
            f"（{choice_num}）「{snip}」は、"
            f"{category or '本分野'}の基準と照らすと正答になりません。"
        )
    return (
        f"（{choice_num}）「{snip}」は、設問の求め方と照らすと正答になりません。"
    )


def infer_wrong_choice_note(
    page: dict,
    choice_num: int,
    choice_text: str,
    row: dict,
) -> str:
    """CSV に explanation_choices が無いとき、選択肢文から読み手向けの解説を組み立てる。"""
    stem = norm(page.get("stem_plain") or page.get("stem") or "")
    mode = question_ask_mode(stem)
    opt = norm(choice_text)
    correct = page.get("correct")
    numbered = parse_numbered_choice_notes(norm(row.get("explanation")))
    if choice_num in numbered and _is_substantive_choice_note(numbered[choice_num]):
        return dedupe_prose(numbered[choice_num])

    multi_pick = len(correct_choice_indices(correct)) > 1
    if multi_pick and mode == "most_correct":
        if numbered.get(choice_num):
            return dedupe_prose(numbered[choice_num])
        return dedupe_prose(
            f"（{choice_num}）は正答（{correct}）に含まれないため、この設問の正解の組合せにはなりません。"
            "届出・認可・期限・主体など、正答肢と異なる要件がないか確認してください。"
        )

    correct_text = ""
    cor_idx = _correct_choice_index(correct)
    opts = page.get("opts") or []
    if cor_idx is not None and 1 <= cor_idx <= len(opts):
        correct_text = opts[cor_idx - 1]
    correct_body = norm(row.get("explanation_correct")) or norm(row.get("explanation")) or ""
    category = norm(page.get("category") or "")

    parts: list[str] = [_choice_specific_lead(
        choice_num,
        opt,
        mode=mode,
        correct=correct,
        correct_text=correct_text,
        category=category,
    )]

    if mode == "least_appropriate" and _choice_sounds_positive(opt):
        parts.append(
            f"「{opt}」は、単体では適切な学習法・正しい対応に当たります。"
            "したがって「最も適切でないもの」として選ぶ正答にはなりません。"
        )
        if correct and correct_text:
            parts.append(
                f"本問の正答は（{correct}）「{_snippet(correct_text, 56)}」です。"
                "この記述は、学習効果を著しく損ねる・明らかに誤った方針であり、"
                "他の肢より「最も不適切」と言えます。"
            )
        parts.append(
            "よくある誤解は、「正しい学習法か」で各肢を判断してしまい、"
            "（4）のような明らかに有害な記述を見落とすことです。"
            "設問文の「最も適切でない」を先に線引きし、四肢を比較して選んでください。"
        )
    elif mode == "least_appropriate":
        parts.append(
            "「最も適切でない」形式では、正しそうな肢が複数あることがあります。"
            "各肢の主語・客体・数字・期限・手続の順序が設問条件と合うかを確認し、"
            "最も不適切な一つだけを選びます。"
        )
    elif mode == "most_correct":
        if not multi_pick and correct and correct_text:
            parts.append(
                f"正答（{correct}）「{_snippet(correct_text, 56)}」は、"
                "制度・手続・学習法のいずれかの観点で適切な内容です。"
            )
    else:
        parts.append(
            "設問文の「正しいもの／誤っているもの／最も適切でないもの」を"
            "先に確認してから、各肢を読み直してください。"
        )

    rules: list[tuple[str, str]] = [
        (
            r"口コミ|SNS|ブログ|噂",
            "受験制度・出題範囲・合格基準の正誤は、実施団体の公式発表が基準です。"
            "口コミは参考程度にとどめ、日程・範囲・申込方法は必ず公式サイトや受験案内で確認してください。",
        ),
        (
            r"毎年|常に|固定|変わらない|前年と同じ",
            "試験日程・出題範囲・申込方法は改定されることがあります。"
            "「一度確認すれば十分」と決めつけると、変更の見落としや学習範囲のズレにつながります。",
        ),
        (
            r"生成済み|直接編集|手編集|JSだけ",
            "公開用データは CSV とビルドスクリプトを正本にすると、再生成・検証・本番同期が一貫します。"
            "生成物だけを手修正すると、次回ビルドで上書きされたり、テンプレと本番の差分が残りやすくなります。",
        ),
        (
            r"列名は自由|列名.*変え",
            "CSV 列名はツールの検証・変換と対応しています。"
            "任意の列名に変えると、ビルドやリンク検証が失敗し、静的ページとアプリ用データの整合が崩れます。",
        ),
        (
            r"ドメイン.*不要|設定は不要",
            "canonical・サイトマップ・OGP には正しいドメイン（siteOrigin）が必要です。"
            "プレースホルダーのままでは検索エンジンと SNS プレビューで URL が誤って扱われます。",
        ),
        (
            r"削除される|送信される|連携できない",
            "本テンプレートでは、学習履歴はブラウザ内保存を基本とし、復習・ブックマーク・用語解説へつなげる設計です。"
            "この肢の断定は、実際の仕様（ローカル保存・関連ページ）と一致しません。",
        ),
        (
            r"図表|比較.*役立たない",
            "関連制度の違いや数値・期限は、表や比較で整理すると混同が減ります。"
            "特に設備・税務・手続き分野では、一覧表を自作して見直すと得点しやすくなります。",
        ),
        (
            r"記録しない|参照しない",
            "苦手分野や混同しやすい用語を記録しておくと、復習の優先順位がつけられます。"
            "用語の定義を飛ばすと、設問の前提（誰が・何を・どこまで）を取り違えやすくなります。",
        ),
        (
            r"二度と見直さない|見直さない",
            "誤答した問題を放置すると、同じパターンのミスが本番まで残ります。"
            "復習リストや間隔を空けた解き直しで、弱点を可視化することが重要です。",
        ),
    ]
    for pattern, msg in rules:
        if re.search(pattern, opt):
            if not any(re.search(pattern, p) for p in parts):
                parts.append(msg)
            break

    if mode == "most_correct" and correct_text and len(parts) < 4 and not multi_pick:
        parts.append(
            f"特に「{_snippet(opt, 32)}」の部分は、"
            f"正答「{_snippet(correct_text, 32)}」と両立しない限定語・主体・手順がないか確認してください。"
        )

    if correct_body and len(parts) < 3:
        hint = _snippet(correct_body, 56)
        if hint and hint not in "".join(parts) and len(hint) >= 20:
            parts.append(
                f"正答の論点（{hint}）と両立しない限定語・主体・手順がないか確認してください。"
            )

    if len(parts) < 2:
        parts.append(
            f"正答（{correct}）との差分を一行メモに残し、同分野の過去問・実践演習で解き直すと定着しやすくなります。"
        )

    return dedupe_prose("\n\n".join(parts))


def _wrong_note_context(page: dict, row: dict) -> str:
    parts = [
        norm(row.get("explanation_summary")),
        norm(row.get("explanation_correct")),
        norm(row.get("explanation")),
    ]
    return dedupe_prose(" ".join(p for p in parts if p))


def _brief_wrong_note_from_choice(choice_text: str) -> str:
    opt = norm(choice_text)
    if not opt:
        return ""
    if re.search(r"全く無関係|常に一定|必ず.*同じ|影響は少ない|影響はない", opt):
        return (
            "「全く無関係」「常に一定」などの限定が実態と異なります。"
            "数値・主体・条件の取り違えがないか確認してください。"
        )
    if re.search(r"小さい|低い|少ない|不要|しない", opt):
        m = re.search(r"(小さい|低い|少ない)", opt)
        if m:
            return (
                f"「{m.group(1)}」という方向が実際と逆、または限定が強すぎる記述です。"
                "正答の論点と数値・程度の関係を照合してください。"
            )
    return ""


def resolve_wrong_choice_note(
    page: dict,
    choice_num: int,
    choice_text: str,
    row: dict,
    *,
    csv_note: str = "",
) -> str:
    """CSV 優先。薄い解説は推論で置き換え、未記入は推論で補完。"""
    stem = norm(page.get("stem_plain") or page.get("stem") or "")
    mode = question_ask_mode(stem)
    context = _wrong_note_context(page, row)
    inline = _inline_wrong_notes(row)
    if choice_num in inline and len(inline[choice_num]) >= 8:
        return dedupe_prose(
            _compact_wrong_note_vs_choice(choice_text, inline[choice_num])
        )
    brief = _brief_wrong_note_from_choice(choice_text)
    note = norm(csv_note)
    if note and _is_generic_wrong_note(note):
        note = ""
    if note and re.search(r"が示す論点とずれています", note):
        note = ""
    if note and _is_substantive_choice_note(note):
        cleaned = _strip_wrong_note_boilerplate(
            _strip_choice_echo(note, choice_text, choice_num),
            context=context,
        )
        if cleaned and not _is_thin_choice_note(cleaned, mode):
            return dedupe_prose(_compact_wrong_note_vs_choice(choice_text, cleaned))
    if brief and (not note or _is_thin_choice_note(note, mode) or _is_generic_wrong_note(note)):
        return brief
    inferred = infer_wrong_choice_note(page, choice_num, choice_text, row)
    compact = lambda t: dedupe_prose(_compact_wrong_note_vs_choice(choice_text, t))
    if not note:
        return compact(
            _strip_wrong_note_boilerplate(
                _strip_choice_echo(inferred, choice_text, choice_num),
                context=context,
            )
        )
    if _is_thin_choice_note(note, mode) or _is_enrich_boilerplate_note(note):
        return compact(
            _strip_wrong_note_boilerplate(
                _strip_choice_echo(inferred, choice_text, choice_num),
                context=context,
            )
        )
    return compact(
        _strip_wrong_note_boilerplate(
            _strip_choice_echo(note, choice_text, choice_num),
            context=context,
        )
    )


CATEGORY_STUDY_HINTS: dict[str, str] = {
    "法令・制度": (
        "試験制度・受験要件は年度ごとに見直されることがあります。"
        "受験要項・実施要領・合格発表の公式ページをブックマークし、改定年度は出題範囲表と学習計画を更新してください。"
        "用語解説で「受験資格」「試験要項」「公式情報」などの定義を押さえたうえで、"
        "同年・前後年度の過去問で出題パターンを確認すると、制度問題と実務問題のつながりが整理できます。"
        "模試・実践演習の前には、最新の公式情報を再確認する習慣を入れておくと安心です。"
    ),
    "契約・実務": (
        "実務・学習法の問題は、「誰が・何を・どこまで」が適切か、または「最も適切でないもの」かを"
        "設問文で切り替えて読むことが重要です。間違えた問題は復習リストに残し、"
        "正答・誤答それぞれについて「どの条件を満たさないか」を一文で書き出してください。"
        "関連ガイド（学習計画・過去問の進め方）と用語解説を往復すると、"
        "単発の暗記ではなく判断基準として定着しやすくなります。"
    ),
    "設備・その他": (
        "数値・期限・例外規定は、暗記だけでは混同しやすいです。"
        "自分用の比較表（単位・条件・責任者・手続の順序）を作り、週次で見直してください。"
        "分野別の用語一覧から関連語をたどり、過去問一覧で出題傾向を確認する流れが効率的です。"
        "実践演習で時間配分を測ったあと、間違えた設問だけ過去問の同分野に戻ると弱点がはっきりします。"
    ),
    "基礎・役割": (
        "管理監督者の役割・法令の趣旨・ストレスの基礎は、用語の定義と"
        "「誰が・何を・どこまで」がセットで出題されます。"
        "間違えた肢ごとに、正答との差分（根拠法令・対象範囲・責任の所在）をメモし、"
        "関連用語から同分野の過去問・実践演習を解き直してください。"
    ),
    "職場環境・配慮": (
        "職場の配慮・リスク要因は、具体策と「誰が担うか」を対にして覚えると得点しやすくなります。"
        "数値基準や手順は表に整理し、同年の過去問で実務イメージを補強してください。"
        "一問一答で用語の定義を確認してから、記述式に近い過去問に戻ると理解が深まります。"
    ),
    "相談・連携・復職": (
        "面談・医療連携・復職支援は、手順と禁止事項（やってはいけないこと）の区別が重要です。"
        "正答肢のキーワードを用語解説で確認し、同分野の過去問でケースのパターンを増やしてください。"
        "「最も不適切」形式では、一見正しそうな肢に惑わされないよう、設問文を先にマークする習慣をつけましょう。"
    ),
    "関係法令": (
        "法令・制度は条文の趣旨と数字・期限をセットで覚えると得点しやすくなります。"
        "関連用語を用語解説で押さえ、同年の過去問で「例外」「罰則」「手続」の組み合わせを確認してください。"
        "公式情報の更新時期は学習カレンダーに入れておくと、直前期の取りこぼしを防げます。"
    ),
    "労働衛生": (
        "衛生・安全は用語の定義と数値基準の組み合わせが多いです。"
        "間違えた問題は復習リストに残し、用語解説で意味を確認しながら解き直してください。"
        "図や表で「基準値・測定・記録義務」を一覧化すると、本番直前の確認が短くなります。"
    ),
    "労働生理": (
        "生理・人体は図解と用語の対応づけが有効です。"
        "分野別の用語一覧から関連語をたどり、過去問で「原因・対策・禁忌」のセットで復習してください。"
    ),
    "賃貸住宅管理業法": (
        "業法は「誰が・何を・どこまで」がセットで問われます。"
        "正答肢の義務主体と手続の流れをメモし、似た制度との違いを表に整理してから、"
        "同年・前後年度の過去問で定着を確認してください。"
    ),
    "民法・借地借家法": (
        "借地借家・民法改正は、権利関係の主体と効果の発生時期を一文で説明できるかが要点です。"
        "間違えた肢は正答と「誰に・いつ・どの効果が及ぶか」で対比してください。"
    ),
    "賃貸借契約": (
        "契約条項・個人情報・原状回復は、条文の趣旨と実務上の判断基準の両方が問われます。"
        "数字・期限・例外は一覧表にし、他の選択肢との差分を意識して復習してください。"
    ),
    "賃貸借契約実務": (
        "実務問題は「適切な対応か」「義務の範囲か」を区別する設問が多いです。"
        "誤答肢がどの要件を満たさないかを具体的に書き出すと定着します。"
    ),
    "賃貸不動産経営": (
        "経営・管理では、貸主・借主・管理者の視点の違いがポイントです。"
        "「最も不適切」形式では、一見正しそうな肢こそ見落としやすいので、設問文を再確認してください。"
    ),
    "管理実務": (
        "管理実務は手続の順序と義務の主体が問われやすいです。"
        "間違えた問題は復習リストに残し、同分野の用語とセットで解き直してください。"
    ),
    "建物・設備": (
        "設備・維持保全は数値基準・点検周期・責任の所在がセットで出題されます。"
        "他選択肢がどの要件（数値・主体・手続）とずれているかを確認してください。"
    ),
    "会計・税金・保険": (
        "税務・会計は計算の前提と課税関係者・時期の取り違えに注意です。"
        "誤答肢がどの前提を誤っているかを明示して復習してください。"
    ),
    "会計税務": (
        "税務・会計は計算の前提と課税関係者・時期の取り違えに注意です。"
        "誤答肢がどの前提を誤っているかを明示して復習してください。"
    ),
    "サブリース": (
        "サブリースは貸主・転貸人・借主の関係と契約上の効果の区別が要点です。"
        "誤答肢がどの関係を取り違えているかを確認してください。"
    ),
    "原状回復": (
        "原状回復は費用負担・範囲・特約の有無が問われやすいです。"
        "正答肢の要件を押さえ、他肢との差分を整理してください。"
    ),
    "賃料管理・督促": (
        "賃料・督促は手続の順序と法的効果の対応が重要です。"
        "誤答肢がどの段階・要件を誤っているかを確認してください。"
    ),
    "関連法令": (
        "関連法令は本試験の主たる論点と位置づけの違いが問われます。"
        "根拠法令名と趣旨をセットで覚えてください。"
    ),
    "政策課題・社会情勢": (
        "政策・社会情勢は制度の目的と論点の組み合わせが出題されます。"
        "公式の考え方・用語の定義を確認したうえで復習してください。"
    ),
}

DEFAULT_STUDY_HINT = (
    "この問題で間違えた場合は、設問文の求め方（「正しいもの」「誤っているもの」「最も適切でないもの」）を"
    "最初に線引きしてください。正答・誤答それぞれについて、用語の定義と制度の前提を用語解説で確認し、"
    "復習リストや実践演習・一問一答と組み合わせて、同分野の過去問を解き直すと定着しやすくなります。"
)


def _is_template_study_hint(text: str) -> bool:
    t = dedupe_prose(text)
    if not t:
        return True
    if t == DEFAULT_STUDY_HINT:
        return True
    return t in CATEGORY_STUDY_HINTS.values()


def _hint_should_skip_explanation_tail(page: dict, row: dict) -> bool:
    """各肢解説・組合せ解説に explanation が既出なら、ヒントへ同文を足さない。"""
    mode = _extended_question_mode(page, row)
    if mode in {"truefalse_group", "combination", "multi"}:
        return True
    exp = norm(row.get("explanation"))
    if exp and parse_numbered_choice_notes(exp):
        return True
    return False


def build_study_hint(page: dict, row: dict) -> str:
    point = norm(row.get("explanation_point"))
    if point and not _is_template_study_hint(point):
        return dedupe_prose(point)

    stem = norm(
        page.get("stem_plain")
        or page.get("stem")
        or page.get("statement")
        or row.get("question")
        or ""
    )
    category = norm(page.get("category") or "")
    parts: list[str] = []
    if category:
        parts.append(f"分野「{category}」の問題です。")

    mode = question_ask_mode(stem)
    if mode == "least_appropriate":
        parts.append(
            "「最も適切でないもの」を問う設問では、四肢を比較して最も問題のある一つを選びます。"
        )
    elif mode == "truefalse_mark":
        parts.append(
            "各記述を「適」「否」で判定します。⇒ の対比表現や限定語の取り違えに注意してください。"
        )
    elif mode == "most_correct":
        parts.append("正しいものを問う設問では、限定語・主体・手続の条件を順に確認します。")

    if page.get("statement") is not None or row.get("question"):
        clause = _ichimon_judgment_clause(stem)
        ans = "○" if page.get("correct_answer") else "×"
        parts.append(f"判断対象は「{_snippet(clause, 40)}」。正答は {ans} です。")
    elif page.get("correct") is not None:
        parts.append(
            "誤った肢は、どの条件・主体・数字がずれているかを一行メモしてください。"
        )

    for src in (norm(row.get("explanation_correct")), norm(row.get("explanation"))):
        if _hint_should_skip_explanation_tail(page, row):
            break
        if not src:
            continue
        for sent in re.split(r"(?<=[。！？!?])\s*", src):
            s = sent.strip()
            if len(s) >= 18 and not _parrots_stem(stem, s):
                parts.append(s if s.endswith("。") else s + "。")
                break
        if len(parts) >= 3:
            break

    if len(parts) >= 2:
        return dedupe_prose("".join(parts))

    cat_hint = CATEGORY_STUDY_HINTS.get(category)
    if cat_hint:
        return dedupe_prose(_snippet(cat_hint, 180))

    return dedupe_prose("".join(parts)) if parts else DEFAULT_STUDY_HINT


def split_legacy_explanation(exp: str) -> tuple[str, str]:
    m = re.match(r"^正解は\s*(\d+)\s*です[。.]?\s*(.*)$", exp, re.DOTALL)
    if m:
        body = norm(m.group(2)) or exp
        summary = f"正答は（{m.group(1)}）です。"
        return summary, body
    return "", exp


def parse_combination_slots(raw: str) -> dict[str, int]:
    """A-8;B-3;C-4;D-7 → {'A': 8, 'B': 3, ...}"""
    out: dict[str, int] = {}
    for part in norm(raw).split(";"):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^([A-Za-zア-オ甲乙①-⑫])-(\d+)$", part)
        if m:
            out[m.group(1).upper()] = int(m.group(2))
    return out


def parse_truefalse_group_labels(raw: str) -> dict[str, set[int]]:
    """適-2,3;不適-1 → {'適': {2,3}, '不適': {1}}"""
    out: dict[str, set[int]] = {}
    for part in norm(raw).split(";"):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^([^-]+)-(.+)$", part)
        if not m:
            continue
        label = norm(m.group(1))
        nums: set[int] = set()
        for chunk in m.group(2).split(","):
            n = _parse_choice_num(chunk)
            if n is not None:
                nums.add(n)
        if label and nums:
            out[label] = nums
    return out


def _truefalse_display_label(raw_label: str) -> str:
    if raw_label in {"適", "正"}:
        return "適"
    if raw_label in {"不適", "否", "誤"}:
        return "否"
    return raw_label


def _extended_question_mode(page: dict, row: dict) -> str:
    typ = norm(page.get("type"))
    if typ in {"combination", "truefalse_group", "multi"}:
        return typ
    cor = norm(row.get("correct")) or norm(str(page.get("correct") or ""))
    from tools.correct_answer_format import detect_correct_format

    fmt = detect_correct_format(cor)
    if fmt in {"combination", "truefalse_group", "multi"}:
        return fmt
    return "single"


def build_combination_explanation_html(page: dict, row: dict) -> str:
    """穴埋め組合せ — 語句バンク（１～８）を他肢として並べない。"""
    base = norm(row.get("explanation")) or "（解説は未入力です。）"
    correct_raw = norm(str(page.get("correct") or row.get("correct") or ""))
    slots = parse_combination_slots(correct_raw)
    opts = page.get("opts") or []
    parts: list[str] = ['<div class="q-exp">']

    parts.append(
        '<section class="q-exp-section" aria-labelledby="q-exp-correct-h">'
        '<h3 id="q-exp-correct-h" class="q-exp-h3">正解の組合せ</h3>'
    )
    if slots:
        lis = []
        for slot in sorted(slots.keys()):
            num = slots[slot]
            word = opts[num - 1] if 1 <= num <= len(opts) else ""
            lis.append(
                f'<li class="q-exp-choice-item">'
                f'<p><strong>{html.escape(slot)}</strong> '
                f"→ <strong>（{num}）</strong> {html.escape(word)}</p></li>"
            )
        parts.append(f'<ul class="q-exp-choice-list">{"".join(lis)}</ul>')
    summary = norm(row.get("explanation_summary")) or norm(row.get("explanation_correct"))
    body = summary or base
    parts.append(f"<p>{text_to_html(body)}</p></section>")

    parts.append("</div>")
    return "\n    ".join(parts)


def build_truefalse_group_explanation_html(page: dict, row: dict) -> str:
    """適/否を記入する記述群 — 各肢ごとに判定と解説を示す。"""
    base = norm(row.get("explanation")) or "（解説は未入力です。）"
    correct_raw = norm(str(page.get("correct") or row.get("correct") or ""))
    labels = parse_truefalse_group_labels(correct_raw)
    numbered = parse_numbered_choice_notes(base)
    opts = page.get("opts") or []

    idx_to_label: dict[int, str] = {}
    for raw_label, nums in labels.items():
        disp = _truefalse_display_label(raw_label)
        for n in nums:
            idx_to_label[n] = disp

    parts: list[str] = ['<div class="q-exp">']

    parts.append(
        '<section class="q-exp-section" aria-labelledby="q-exp-stmts-h">'
        '<h3 id="q-exp-stmts-h" class="q-exp-h3">各記述の解説</h3>'
        '<ul class="q-exp-choice-list">'
    )
    for i, _opt in enumerate(opts, start=1):
        verdict = idx_to_label.get(i, "")
        note = numbered.get(i) or ""
        if not note and verdict == "適":
            continue
        badge = (
            f'<span class="q-marubatsu q-tf-verdict">{html.escape(verdict)}</span> '
            if verdict
            else ""
        )
        parts.append(
            f'<li class="q-exp-choice-item">'
            f'<p class="q-exp-choice-head">'
            f'<span class="q-exp-choice-num">（{i}）</span> {badge}</p>'
        )
        if note:
            parts.append(f'<p class="q-exp-choice-note">{text_to_html(note)}</p>')
        parts.append("</li>")
    parts.append("</ul></section>")

    parts.append("</div>")
    return "\n    ".join(parts)


def _wrong_note_dedupe_key(note: str) -> str:
    """肢番号・長い選択肢引用を除いた比較用キー。"""
    n = norm(note)
    if re.search(r"正しくは「|の関係です", n) and len(n) < 80:
        return _normalize_for_compare(n)
    n = re.sub(r"（\d+）", "", n)
    n = re.sub(r"「[^」]{20,}」", "", n)
    return _normalize_for_compare(n)


def _is_generic_wrong_note(note: str) -> bool:
    n = norm(note)
    if not n or len(n) < 48:
        return True
    if _is_enrich_boilerplate_note(n):
        return True
    generic_markers = (
        r"一見もっともらしい",
        r"学習・制度・実務の観点",
        r"記述自体としては正しい",
        r"最も適切でない.*形式では、正しそうな肢",
        r"正答の論点（.+）と両立しない",
        r"が示す論点とずれています",
        r"単体では適切な学習法・正しい対応",
        r"設問形式の読み違え",
        r"単独の記述としては法令上妥当",
        r"本問で選ぶべき正答は",
        r"問題文の条件（",
    )
    return any(re.search(p, n) for p in generic_markers)


def _consolidated_wrong_choices_note(
    page: dict, row: dict, wrong_nums: list[int]
) -> str:
    stem = norm(page.get("stem_plain") or page.get("stem") or "")
    mode = question_ask_mode(stem)
    correct = page.get("correct")
    if mode == "least_appropriate":
        return (
            "いずれも、単体では適切な記述に当たります。"
            f"本問は「最も適切でないもの」を選ぶ形式のため、正答は（{correct}）です。"
            "四肢を比較し、最も不適切な一つだけを選びます。"
        )
    return (
        f"いずれも、正答（{correct}）とは異なる論点です。"
        "設問の条件と照らし、正答に最も合う肢を選び直してください。"
    )


def collapse_wrong_choice_items(
    page: dict, row: dict, items: list[tuple[int, str, str]]
) -> list[tuple[str, str]]:
    """同一解説文の肢をまとめ、汎用テンプレの連打を防ぐ。"""
    if not items:
        return []
    groups: list[dict] = []
    index: dict[str, int] = {}
    for num, _opt, note in items:
        key = _wrong_note_dedupe_key(note)
        if key not in index:
            index[key] = len(groups)
            groups.append({"nums": [num], "note": note})
        else:
            groups[index[key]]["nums"].append(num)
    collapsed: list[tuple[str, str]] = []
    for group in groups:
        nums = sorted(group["nums"])
        label = "、".join(str(n) for n in nums)
        note = group["note"]
        if len(nums) > 1 and _is_generic_wrong_note(note):
            note = _consolidated_wrong_choices_note(page, row, nums)
        collapsed.append((label, note))
    return collapsed


def build_choice_commentary(page: dict, row: dict) -> list[tuple[int, str, str]]:
    mode = _extended_question_mode(page, row)
    if mode in {"combination", "truefalse_group"}:
        return []
    parsed = parse_explanation_choices(norm(row.get("explanation_choices")))
    numbered = parse_numbered_choice_notes(norm(row.get("explanation")))
    correct = page.get("correct")
    correct_indices = correct_choice_indices(correct)
    items: list[tuple[int, str, str]] = []
    for i, opt in enumerate(page["opts"], start=1):
        if page.get("is_invalidated") or correct is None:
            continue
        if i in correct_indices:
            continue
        csv_note = parsed.get(i) or numbered.get(i) or ""
        note = resolve_wrong_choice_note(
            page, i, opt, row, csv_note=csv_note
        )
        items.append((i, opt, note))
    return items


def build_explanation_html(page: dict, row: dict) -> str:
    base = norm(row.get("explanation")) or "（解説は未入力です。）"
    if page.get("is_invalidated") or page.get("correct") is None:
        return f'<div class="q-exp"><p>{text_to_html(base)}</p></div>'

    mode = _extended_question_mode(page, row)
    if mode == "combination":
        return build_combination_explanation_html(page, row)
    if mode == "truefalse_group":
        return build_truefalse_group_explanation_html(page, row)

    summary = norm(row.get("explanation_summary"))
    correct_body = norm(row.get("explanation_correct"))
    point = norm(row.get("explanation_point"))

    if not summary and not correct_body and not point:
        leg_summary, leg_body = split_legacy_explanation(base)
        summary = summary or leg_summary
        correct_body = correct_body or leg_body

    summary, correct_body = _ensure_correct_body(page, row, summary, correct_body)
    summary = _pick_explanation_lead(page, row, summary)
    if summary and correct_body and _normalize_for_compare(summary) == _normalize_for_compare(
        correct_body
    ):
        correct_body = ""
    elif correct_body and _is_thin_enrich_summary(correct_body):
        cb = _substantive_explanation_lead(row) or correct_body
        correct_body = "" if _overlaps_correct_choice_text(cb, page) else cb
    elif correct_body and _overlaps_correct_choice_text(correct_body, page):
        correct_body = ""
    if summary and correct_body:
        sm = _normalize_for_compare(summary)
        kept: list[str] = []
        for part in re.split(r"\n\n+", correct_body):
            p = norm(part)
            if not p:
                continue
            pn = _normalize_for_compare(p)
            if pn == sm or pn in sm or sm in pn:
                continue
            if re.fullmatch(r"正答は[（(]?\d+[）)]?です[。]?", p):
                continue
            kept.append(p if p.endswith("。") else p + "。")
        correct_body = dedupe_prose("\n\n".join(kept))

    parts: list[str] = ['<div class="q-exp">']
    correct = page.get("correct")
    if correct and not page.get("is_invalidated"):
        correct_indices = correct_choice_indices(correct)
        numbered = parse_numbered_choice_notes(norm(row.get("explanation")))
        correct_inner: list[str] = []
        if len(correct_indices) > 1:
            if correct_body and not numbered:
                correct_inner.append(f"<p>{text_to_html(correct_body)}</p>")
            for idx in sorted(correct_indices):
                note = numbered.get(idx) or ""
                if note:
                    correct_inner.append(
                        f'<p class="q-exp-correct-opt"><strong>（{idx}）</strong> '
                        f"{text_to_html(note)}</p>"
                    )
        elif correct_body:
            correct_inner.append(f"<p>{text_to_html(correct_body)}</p>")
        if correct_inner:
            parts.append(
                '<section class="q-exp-section" aria-labelledby="q-exp-correct-h">'
                '<h3 id="q-exp-correct-h" class="q-exp-h3">正解の理由</h3>'
            )
            parts.extend(correct_inner)
            parts.append("</section>")

        wrong_items = collapse_wrong_choice_items(
            page, row, build_choice_commentary(page, row)
        )
        if wrong_items:
            lis = "".join(
                f'<li class="q-exp-choice-item">'
                f'<p class="q-exp-choice-head">'
                f'<span class="q-exp-choice-num">（{nums}）</span></p>'
                f'<p class="q-exp-choice-note">{text_to_html(note)}</p></li>'
                for nums, note in wrong_items
            )
            parts.append(
                '<section class="q-exp-section" aria-labelledby="q-exp-wrong-h">'
                '<h3 id="q-exp-wrong-h" class="q-exp-h3">他の選択肢</h3>'
                f'<ul class="q-exp-choice-list">{lis}</ul></section>'
            )

    parts.append("</div>")
    return "\n    ".join(parts)


def _ichimon_answer_is_true(page: dict) -> bool:
    return bool(page.get("correct_answer"))


def split_legacy_ichimon_explanation(
    exp: str, *, is_true: bool, statement: str
) -> tuple[str, str]:
    """1 段落の explanation から要約と正解理由のたたき台を作る。"""
    body = norm(exp) or "（解説は未入力です。）"
    if is_true:
        summary = (
            "この記述は正しい内容です。"
            "○ が正答になります。"
        )
    else:
        summary = (
            "この記述は誤りです。"
            "× が正答になります。"
        )
    if len(body) <= 120:
        return summary, dedupe_prose(body)
    first = re.split(r"[。.]\s*", body, maxsplit=1)[0]
    if first and len(first) >= 20:
        summary = first + ("。" if not first.endswith("。") else "")
    return summary, dedupe_prose(body)


def infer_ichimon_opposite_note(page: dict, row: dict) -> str:
    """○/× のもう一方を選びそうになる理由（CSV 未記入時）。"""
    statement = norm(page.get("statement") or row.get("question"))
    clause = _ichimon_judgment_clause(statement)
    is_true = _ichimon_answer_is_true(page)
    category = norm(page.get("category") or "")
    wrong = "×" if is_true else "○"
    parts: list[str] = []

    if is_true:
        parts.append(
            f"「{_snippet(clause, 44)}」は正しい記述です。"
            f"それでも {wrong} を選ぶ場合は、"
            "一般論と設問の限定語（必要・毎年・常に・しなくてもよい等）を取り違えている可能性があります。"
        )
    else:
        parts.append(
            f"「{_snippet(clause, 44)}」は誤った記述です。"
            f"それでも {wrong} を選ぶ場合は、"
            "一見もっともらしい表現に引っ張られ、判断対象の一文だけを精査していない可能性があります。"
        )

    exp = strip_four_choice_leak(norm(row.get("explanation_correct") or row.get("explanation")))
    if exp:
        for sent in re.split(r"(?<=[。！？!?])\s*", exp):
            s = sent.strip()
            if len(s) >= 16 and (clause[: min(8, len(clause))] in s or (not is_true and "誤" in s)):
                parts.append(s if s.endswith("。") else s + "。")
                break
            if len(s) >= 20 and not _parrots_stem(statement, s):
                parts.append(s if s.endswith("。") else s + "。")
                break

    if re.search(r"第\d+類|危険物|石油類|引火|消火|漏えい", statement + category):
        parts.append(
            "危険物の類別・性質は、政令別表と用語定義の組み合わせで判断します。"
            "類似名称（動植物油類・石油類・特殊引火物など）の違いを用語解説で確認してください。"
        )
    elif re.search(r"復習|見直|定着", statement):
        parts.append(
            "誤答記録と間隔を空けた解き直しは学習の基本です。"
            "「見直さない」「記録しない」系の記述は × になりやすい点に注意してください。"
        )
    elif re.search(r"公式|受験案内|出題範囲|毎年|制度", statement):
        parts.append(
            "制度・数値・期限の正誤は公式情報が基準です。"
            "記憶や一般論だけで ○/× を決めないようにしてください。"
        )
    elif category:
        parts.append(
            f"分野「{category}」では、用語定義と制度の前提を確認し、"
            "同分野の過去問・実践演習で判断基準を固めてください。"
        )

    return dedupe_prose("\n\n".join(parts))


def build_ichimon_explanation_html(page: dict, row: dict) -> str:
    """一問一答 — 正解の理由・もう一方の記号のみ。"""
    statement = norm(page.get("statement") or row.get("question"))
    is_true = _ichimon_answer_is_true(page)
    ans = "○" if is_true else "×"
    wrong = "×" if is_true else "○"

    summary = norm(row.get("explanation_summary"))
    correct_body = strip_four_choice_leak(norm(row.get("explanation_correct")))
    opposite = norm(row.get("explanation_opposite"))
    point = norm(row.get("explanation_point"))
    base = strip_four_choice_leak(norm(row.get("explanation")) or "（解説は未入力です。）")

    if not summary and not correct_body and not point:
        leg_summary, leg_body = split_legacy_ichimon_explanation(
            base, is_true=is_true, statement=statement
        )
        summary = summary or leg_summary
        correct_body = correct_body or leg_body

    summary = dedupe_prose(summary)
    correct_body = clean_ichimon_correct_body(
        correct_body,
        summary=summary,
        is_true=is_true,
    )
    opposite = dedupe_prose(opposite)
    if not opposite:
        opposite = infer_ichimon_opposite_note(page, row)

    parts: list[str] = ['<div class="q-exp">']

    parts.append(
        '<section class="q-exp-section" aria-labelledby="q-exp-correct-h">'
        '<h3 id="q-exp-correct-h" class="q-exp-h3">正解の理由</h3>'
    )
    if correct_body:
        parts.append(f"<p>{text_to_html(correct_body)}</p>")
    if not ichimon_body_already_states_truth(
        f"{summary}\n{correct_body}", is_true=is_true
    ):
        truth = "正しい" if is_true else "誤っている"
        parts.append(
            f'<p class="q-exp-correct-opt">'
            f"設問文は<strong>{truth}</strong>記述のため、答えは "
            f'<strong class="q-marubatsu">{html.escape(ans)}</strong> です。'
            f"</p>"
        )
    parts.append("</section>")

    parts.append(
        '<section class="q-exp-section" aria-labelledby="q-exp-opposite-h">'
        '<h3 id="q-exp-opposite-h" class="q-exp-h3">'
        f"{html.escape(wrong)} を選びやすい考え方</h3>"
        f"<p>{text_to_html(opposite)}</p></section>"
    )

    parts.append("</div>")
    return "\n    ".join(parts)
