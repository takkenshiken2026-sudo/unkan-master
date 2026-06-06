# ガイド手書きリライト（5本 batch 運用）

試験ガイド記事を **5 slug ずつ** 手書きし、1 batch ごとに公開ゲートを通す手順。

**編集合格（全件）:** [guide-expert-rewrite-program.md](./guide-expert-rewrite-program.md)（正本は `exam-site-shell` 同パス）  
**お手本:** 基本 `exam-schedule` / `tools/mankan_rewrite_exemplar.py`、具体例 `study-plan-6months` / `tools/mankan_rewrite_exemplar_concrete.py`

## 原則

1. **batch 正本**（`tools/*_rewrite_batchN.py` の `REWRITES`）が唯一の本文ソース
2. **`enrich_short_guide_sections` は使わない**（180字未満は batch で書き足す）
3. **`revision_note` に手書きとあっても禁止句・量産パターンは ERROR**（**非アフィリエイトのみ**）
4. **1 batch = 5 slug**、ジャンル単位で揃える（例: 試験概要5本）
5. **1 batch ごとに目視5本** → 問題があれば apply 前に batch を直す

### アフィリエイト記事（対象外）

`tags` に **`アフィリエイト`** がある行は **本手順の対象外** です。手書き batch（`validate_guide_hand_batch.py`）に含めないでください。

| 種別 | 正本 | 合格印（例） |
|------|------|-------------|
| 通常ガイド | 本書・`guide-prose-quality.mdc` | `編集合格（手書きリライト）` |
| アフィリエイト | [affiliate/affiliate-article-rules.md](./affiliate/affiliate-article-rules.md) | `Amazon URL確定・本文全面リライト` 等 |

検証: `tools/affiliate_article_rules.py`（`validate_csv.py` から自動適用）

## batch 必須列（各 slug）

| 列 | 要件 |
|---|---|
| `title` | 試験名の重複なし（「試験の試験」禁止） |
| `lead` | 80字以上・量産テンプレ禁止 |
| `meta_description` | 70字以上 |
| `user_intent` | 50字以上 |
| `action_items` | 5項目（`;` 区切り） |
| `section_1_heading` … `section_5_heading` | 本文と意味一致 |
| `section_1_body` … `section_5_body` | **各180字以上**（sanitize 後も180字以上推奨） |
| `faq_1_question` … `faq_3_question` | **質問の重複なし** |
| `faq_1_answer` … `faq_3_answer` | 各100字以上（2回答以上に具体例、1回答以上に例えば/たとえば） |
| `revision_note` | `手書きリライト・具体例` を含める（例: `2026-06-05: 編集合格（手書きリライト・具体例）`） |

## 1 batch のコマンド

```bash
# 1) batch ファイルの機械チェック（apply 前）
python3 tools/validate_guide_hand_batch.py --batch tools/mankan_rewrite_batch19.py

# 2) 適用 → パディング除去 → CSV/監査（enrich なし）
python3 tools/run_guide_hand_batch.py --batch tools/mankan_rewrite_batch19.py

# 3) 目視5本（ブラウザ or articles/*/index.html）

# 4) 問題なければ build → デプロイ
python3 tools/build_all.py
git add … && git commit && git push
```

## 禁止パターン（published で ERROR）

- `主体・期限・数値をメモしながら演習`
- `演習→用語解説→1週間後の解き直し`（節末尾の定型追記）
- `の論点として、公式テキスト該当章`（enrich 系）
- `マ管受験者が現場で迷いやすい論点と試験での出題パターン`
- `3分野の全体像`（マン管は7分野）

## 進捗の見方

```bash
python3 tools/validate_guide_rewrite.py --strict
python3 tools/audit_guide_prose_quality.py --root . --strict
```

`hand_done` は **batch 必須列を満たし、禁止パターン0・目視OK** の slug のみ。
