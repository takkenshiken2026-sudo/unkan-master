#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""アフィリエイト記事の誤字·slug連結·誤配置セクションを一括修正。"""

from __future__ import annotations

import csv
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.affiliate_links import is_affiliate_article  # noqa: E402
from tools.guide_slug_prose import resolve_slug_references, slug_link_label  # noqa: E402

CSV_PATH = ROOT / "data" / "guide_articles.csv"

TEXT_KEYS = (
    "meta_description",
    "lead",
    "user_intent",
    "action_items",
    "section_1_heading",
    "section_1_body",
    "section_2_heading",
    "section_2_body",
    "section_3_heading",
    "section_3_body",
    "section_4_heading",
    "section_4_body",
    "section_5_heading",
    "section_5_body",
    "section_6_heading",
    "section_6_body",
    "faq_1_question",
    "faq_1_answer",
    "faq_2_question",
    "faq_2_answer",
    "faq_3_question",
    "faq_3_answer",
)

# slug直後に日本語が続く連結（resolve_slug_references の境界外）
CONCAT_FIXES: list[tuple[str, str]] = [
    (r"past-question-strategy100問計測", "過去問の使い方記事で100問計測"),
    (r"past-question-strategy3日解き直し", "過去問の使い方記事の3日解き直し"),
    (r"pass-score12/20", "合格点記事で12/20"),
    (r"exam-format-overview記事", "試験形式記事"),
    (r"exam-format-overviewCBT操作", "試験形式記事でCBT操作"),
    (r"self-study-roadmap週次ループ", "独学の始め方記事の週次ループ"),
    (r"affiliate-textbooks-recommend1冊", "おすすめテキスト3選で1冊"),
    (r"affiliate-problem-books記事", "おすすめ問題集3選記事"),
    (r"CBT4週前3728週25問", "CBT4週前から3728で週25問"),
    (r"CBT6週前3760週1", "CBT6週前から3760を週1回"),
    (r"3728週25問", "3728で週25問"),
    (r"CBT4週前4862753760導入", "CBT4週前から令和8年8月CBT版導入"),
    (r"4862753760導入", "令和8年8月CBT版導入"),
]

LITERAL_FIXES: list[tuple[str, str]] = [
    ("公論重要", "公論社重要"),
    ("公論3728", "公論社3728"),
    ("公論3736", "公論社3736"),
    ("公論3760", "公論社3760"),
    ("条文章20分", "条文を20分"),
    ("要項目次一致", "要項の目次一致"),
    ("頁·", "ページ·"),
    ("（512頁", "（512ページ"),
    ("（560頁", "（560ページ"),
    ("（544頁", "（544ページ"),
    ("（320頁", "（320ページ"),
    ("（288頁", "（288ページ"),
    ("（256頁", "（256ページ"),
    ("（304頁", "（304ページ"),
    ("exam-format-overview記事との2列比較表", "試験形式記事との2列比較表"),
    ("おすすめ問題集3選記事", "「おすすめ問題集3選」記事"),
    ("CBT6週前から4862753760", "CBT6週前から令和8年8月CBT版"),
    ("CBT6週前から3760", "CBT6週前から令和8年8月CBT版"),
    ("CBT6週前3760", "CBT6週前から令和8年8月CBT版"),
    ("3760だけ始める", "令和8年8月CBT版だけ始める"),
    ("CBT6週前本記事3760", "CBT6週前に本記事の令和8年8月CBT版"),
    ("CBT6週前——3760", "CBT6週前——令和8年8月CBT版"),
    ("3728＋3760", "重要問題厳選集＋令和8年8月CBT版"),
    ("3728+3760", "重要問題厳選集＋令和8年8月CBT版"),
    ("公論社3728·3736·3760", "公論社の重要問題厳選集・旅客版・令和8年8月CBT版"),
]

SECTION_OVERRIDES: dict[str, dict[str, str]] = {
    "affiliate-textbooks-recommend": {
        "section_6_body": (
            "購入前に次を確認してください。\n\n"
            "| # | 確認 |\n"
            "| --- | --- |\n"
            "| 1 | 受験区分（貨物/旅客）と表紙表記 |\n"
            "| 2 | 要項④の5科目目次と章立て一致 |\n"
            "| 3 | 最新版·正規版（中古は版を確認） |\n"
            "| 4 | 手元テキストと同系統の問題集があるか |\n"
            "| 5 | Amazon価格·在庫·配送日 |\n\n"
            "例えば6/17（水）——要項区分確認——3冊の目次30分対照——"
            "6/17夕方に1冊決定——[おすすめ問題集3選](../affiliate-problem-books/)へ——"
            "してください。"
        ),
        "section_5_body": (
            "一般のテキスト選びと本記事（Amazon3冊比較）は2記事で分担します。"
            "テキスト選び記事は要項照合·1冊完走·テキスト先·問題集後、"
            "本記事はユーキャン·翔泳社3冊の具体比較·週次配分·演習接続·Amazonリンクに特化します。\n\n"
            "| 論点 | テキスト選び記事 | 本記事（3冊比較） |\n"
            "| --- | --- | --- |\n"
            "| 焦点 | 選定基準 | 商品比較 |\n"
            "| 成果物 | 1冊決定 | 3冊から1冊 |\n"
            "| 時期 | 6/14 Day0 | 6/14〜6/17 |\n"
            "| 出口 | [独学の始め方](../self-study-start/) | [おすすめ問題集3選](../affiliate-problem-books/) |\n\n"
            "例えば6/14（日）テキスト選び——本記事3冊比較——6/17（水）1冊決定——"
            "[独学の始め方](../self-study-start/)——の順が定番です。"
            "3冊同時購入が典型ミスです。"
        ),
    },
    "affiliate-problem-books": {
        "section_6_body": (
            "本記事の過去問3冊は、テキスト1冊確定後の演習メイン用です。"
            "CBT直前の頻出絞りは別記事で扱います。\n\n"
            "| 時期 | 本記事（過去問3冊） | CBT対策3選 |\n"
            "| --- | --- | --- |\n"
            "| 6/21〜7月 | 演習1冊決定 | まだ不要 |\n"
            "| 12/20×5後 | 解き直し中心 | 導入検討 |\n"
            "| CBT6週前 | 週25問維持 | 100問通し |\n\n"
            "例えば8/10（月）——12/20×5達成——"
            "[CBT対策問題集3選](../affiliate-mock-exam-materials/)比較——"
            "CBT6週前導入——の順が定番です。"
        ),
        "section_5_body": (
            "過去問の回し方と本記事（Amazon3冊比較）は2記事で分担します。"
            "過去問活用法記事は100問計測·/20週次記録·3日解き直し·100問通し180分、"
            "本記事はユーキャン·成美堂3冊の具体比較·テキスト縦串·演習1冊選びに特化します。\n\n"
            "| 論点 | 過去問活用法記事 | 本記事（3冊比較） |\n"
            "| --- | --- | --- |\n"
            "| 焦点 | 回し方·記録 | 商品比較 |\n"
            "| 成果物 | /20週次表 | 演習1冊 |\n"
            "| 時期 | 6/21計測 | 7/1決定 |\n"
            "| 出口 | [合格点の目安](../pass-score/) | [CBT対策問題集3選](../affiliate-mock-exam-materials/) |\n\n"
            "例えば6/21（日）過去問活用法——100問計測——7/1（火）本記事1冊——"
            "CBT6週前通し180分——の順が定番です。問題集3冊同時購入が典型ミスです。"
        ),
    },
    "affiliate-mock-exam-materials": {
        "meta_description": (
            "運行管理者試験のCBT対策問題集3選（2026年度版）。"
            "公論社重要問題厳選·旅客版·令和8年8月CBT版を比較。"
            "5科目12/20·100問180分を前提にCBT6週前の使い方を具体例付き解説。"
        ),
        "section_5_heading": "試験形式記事との2列比較表",
        "section_5_body": (
            "試験形式の確認と本記事（Amazon3冊比較）は2記事で分担します。"
            "試験形式記事はCBT操作·100問180分·科目合格制·当日フロー、"
            "本記事は公論社3728·3736·3760の具体比較·CBT6週前·4週前導入に特化します。\n\n"
            "| 論点 | 試験形式記事 | 本記事（3冊比較） |\n"
            "| --- | --- | --- |\n"
            "| 焦点 | CBT形式·手順 | 商品比較 |\n"
            "| 時期 | 6/14 Day0 | CBT6週前〜 |\n"
            "| 成果物 | 形式メモ | 直前1〜2冊 |\n"
            "| 出口 | [当日の流れ](../exam-day-flow/) | [合格点の目安](../pass-score/) |\n\n"
            "例えば6/14（日）試験形式——8/10（月）12/20×5——"
            "CBT6週前本記事3760——CBT2週前最終通し——の順が定番です。"
            "CBT対策だけで完走しようとするのが典型ミスです。"
        ),
        "section_6_body": (
            "購入前に次を確認してください。\n\n"
            "| # | 確認 |\n"
            "| --- | --- |\n"
            "| 1 | 貨物/旅客区分と表紙表記 |\n"
            "| 2 | テキスト·問題集で12/20×5達成済みか |\n"
            "| 3 | 令和8年8月CBT版の受験回と一致するか |\n"
            "| 4 | 重要問題厳選とCBT版の役割分担 |\n"
            "| 5 | Amazon価格·在庫·版情報 |\n\n"
            "例えばCBT6週前——3760で100問180分——"
            "CBT4週前——3728で弱点25問/週——"
            "の段階導入が定番です。"
            "ブログやSNSの情報は試験センター（公式）と必ず照合してください。"
        ),
    },
    "affiliate-beginner-material-set": {
        "section_5_body": (
            "CBT直前の第4冊は次の条件で検討します。\n\n"
            "テキスト+問題集+無料演習で12/20×5達成後にCBT形式1冊を検討。\n\n"
            "例えば2026年3月1日5科目12/20以上なら4862753728重要問題、"
            "11/20未満科目ありなら第4冊より弱点25問/週、"
            "[試験形式](../exam-format-overview/)を参照。"
            "3月15日CBT前12/20×5確認。3728は2,200円参考·256ページ。"
        ),
    },
}

DRAFT_BODY_OPENER: dict[str, dict[str, str]] = {
    "affiliate-online-course-compare": {
        "section_1_body": "オンライン講座は、次の信号が出た週に比較を始めます。",
        "section_2_body": "比較では次の3項目を並べます。",
        "section_3_body": "独学との役割分担は次のとおりです。",
        "section_4_body": "無料体験は次の手順で活用します。",
        "section_5_body": "申込前に次を確認してください。",
    },
    "affiliate-correspondence-course": {
        "section_1_body": "通信講座は次の5項目で比較します。",
        "section_2_body": "買い切り型と月額型の違いは次のとおりです。",
        "section_3_body": "教材セットは次の5点で見ます。",
        "section_4_body": "演習量と/20記録は次の配分が目安です。",
        "section_5_body": "申込前は次のチェックリストで確認します。",
    },
    "affiliate-cram-school": {
        "section_1_body": "通学講座が向く受験生と向かない受験生は次のとおりです。",
        "section_2_body": "通学とオンライン塾の比較は次のとおりです。",
        "section_3_body": "カリキュラムと演習量は次の5点で確認します。",
        "section_4_body": "現場経験者が陥りやすい落とし穴は次のとおりです。",
        "section_5_body": "説明会では次の5点を質問してください。",
    },
    "affiliate-free-vs-paid-study": {
        "section_1_body": "無料で揃う学習素材は次のとおりです。",
        "section_2_body": "有料教材が効く場面は次のとおりです。",
        "section_3_body": "1冊と無料演習の週次型は次のとおりです。",
        "section_4_body": "12/20未満時の配分は次のとおりです。",
        "section_5_body": "費用を抑える購入順序は次のとおりです。",
    },
    "affiliate-beginner-material-set": {
        "section_1_body": "初学者が最初に揃える3点は次のとおりです。",
        "section_2_body": "貨物/旅客で変わる1冊は次のとおりです。",
        "section_3_body": "最初の4週間は次の流れが目安です。",
        "section_4_body": "12/20未満時の追加は次のとおりです。",
        "section_5_body": "CBT直前の第4冊は次の条件で検討します。",
    },
    "affiliate-retake-short-course": {
        "section_1_body": "再受験では前回と同じやり方を避け、次の点を見直します。",
        "section_2_body": "8週短期プランの型は次のとおりです。",
        "section_3_body": "教材の絞り込みは次の5点で行います。",
        "section_4_body": "短期講座の向き不向きは次のとおりです。",
        "section_5_body": "直前2週間の配分は次のとおりです。",
    },
    "affiliate-qualification-support-service": {
        "section_1_body": "受験支援サービスが向くケースは次のとおりです。",
        "section_2_body": "公式手続きとの違いは次のとおりです。",
        "section_3_body": "比較する4項目は次のとおりです。",
        "section_4_body": "費用とサポート範囲は次のとおりです。",
        "section_5_body": "個人情報と契約で確認する点は次のとおりです。",
    },
}


def _slug_titles(rows: list[dict[str, str]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in rows:
        slug = (row.get("slug") or "").strip()
        title = (row.get("title") or "").strip()
        if slug and title:
            out[slug] = title
    return out


def _apply_literal_fixes(text: str) -> str:
    out = text
    for old, new in LITERAL_FIXES:
        out = out.replace(old, new)
    out = re.sub(r"公論(?!社)", "公論社", out)
    return out


def _apply_concat_fixes(text: str) -> str:
    out = text
    for pattern, repl in CONCAT_FIXES:
        out = re.sub(pattern, repl, out)
    return out


def _strip_known_openers(slug: str, body: str) -> str:
    openers = DRAFT_BODY_OPENER.get(slug, {})
    rest = body.strip()
    changed = True
    while changed:
        changed = False
        for opener in openers.values():
            if rest.startswith(opener):
                rest = rest[len(opener) :].lstrip("\n")
                changed = True
                break
    return rest


def _fix_draft_opener(slug: str, key: str, body: str) -> str:
    openers = DRAFT_BODY_OPENER.get(slug, {})
    replacement = openers.get(key)
    if not replacement or not body:
        return body
    rest = _strip_known_openers(slug, body)
    if not rest:
        return replacement
    return replacement + "\n\n" + rest


def fix_row(row: dict[str, str], slug_titles: dict[str, str]) -> bool:
    slug = row["slug"]
    changed = False
    overrides = SECTION_OVERRIDES.get(slug, {})

    for key in TEXT_KEYS:
        if key not in row:
            continue
        val = row.get(key) or ""
        if not val and key not in overrides:
            continue

        new_val = overrides.get(key, val)
        new_val = _apply_literal_fixes(new_val)
        new_val = _apply_concat_fixes(new_val)

        if key.endswith("_body"):
            new_val = _fix_draft_opener(slug, key, new_val)
            new_val = resolve_slug_references(
                new_val,
                slug_titles,
                current_slug=slug,
                link_internal=True,
            )
        elif key in ("lead", "meta_description", "faq_1_answer", "faq_2_answer", "faq_3_answer", "user_intent"):
            new_val = resolve_slug_references(
                new_val,
                slug_titles,
                current_slug=slug,
                link_internal=False,
            )

        if new_val != val:
            row[key] = new_val
            changed = True

    if changed:
        note = row.get("revision_note") or ""
        if "誤字修正" not in note:
            row["revision_note"] = (note + " 2026-06-19: 誤字·slug連結修正").strip()
        row["fact_checked_at"] = "2026-06-19"

    return changed


def main() -> int:
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames:
            print("ERROR: empty CSV", file=sys.stderr)
            return 1
        rows = list(reader)

    slug_titles = _slug_titles(rows)
    changed_slugs: list[str] = []
    for row in rows:
        if not is_affiliate_article(row):
            continue
        if fix_row(row, slug_titles):
            changed_slugs.append(row["slug"])

    if not changed_slugs:
        print("OK: no affiliate typo fixes needed")
        return 0

    print(f"fix affiliate typos: {len(changed_slugs)} slug(s)")
    for s in changed_slugs:
        print(f"  - {s}")

    orig_rows = len(rows)
    fd, tmp = tempfile.mkstemp(suffix=".csv", dir=CSV_PATH.parent)
    try:
        with open(fd, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        with open(tmp, encoding="utf-8-sig", newline="") as f:
            new_rows = sum(1 for _ in csv.DictReader(f))
        if new_rows != orig_rows:
            print(f"ERROR: row count {orig_rows} -> {new_rows}", file=sys.stderr)
            return 1
        shutil.move(tmp, CSV_PATH)
    finally:
        if Path(tmp).exists():
            Path(tmp).unlink()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
