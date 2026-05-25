# data/ — サイト固有コンテンツ（サンプル同梱）

このフォルダの CSV は**テンプレ用サンプル**です。本番サイトでは資格に合わせて差し替えます。

| ファイル | 内容 | 本番目安 |
|----------|------|----------|
| `past_questions.csv` | 過去問（静的 `q/past/` の元） | 試験年度分を順次 |
| `glossary_terms.csv` | 用語解説（**全行が詳細記事**） | **300件以上** |
| `guide_articles.csv` | 試験ガイド | **100本以上** |
| `ichimon_questions.csv` | 一問一答（SPA + 静的 `q/ichimon/`） | 任意 |
| `practice_questions.csv` | 実践演習（SPA + 静的 `q/practice/`） | 任意 |

## templates/

`data/templates/` は執筆用の**コピー元**だけ（ビルド対象外）。

| ファイル | 用途 |
|----------|------|
| `guide_article_row.template.csv` | 試験ガイド 1 行（[guide-article-template.md](../docs/guide-article-template.md)） |
| `glossary_term_row.template.csv` | 用語詳細 1 行（[glossary-term-template.md](../docs/glossary-term-template.md)） |
| `practice_question_row.template.csv` | 実践演習 1 行（[question-static-pages.md](../docs/question-static-pages.md)） |
| `ichimon_question_row.template.csv` | 一問一答 1 行（同上） |

過去問の列定義は `past_questions.csv` のヘッダーを参照してください。

## SPA バンクからの一括取り込み

本番にだけ大量の問題 JS（例: `takken-data-original.js` の `ORIG_QUESTIONS`）があり CSV がサンプルのみのとき:

```bash
python3 tools/import_orig_questions_to_practice_csv.py
python3 tools/import_base_questions_to_ichimon_csv.py --keep-manual
python3 tools/build_all.py
```

手順の正本: [integration-checklist.md §6](../docs/integration-checklist.md) · [question-static-pages.md](../docs/question-static-pages.md)

## テンプレ同期について

`data/` 全体は本番サイト専用です。`tools/sync_from_template.py` では**コピーしません**（`tools/template_site_only.paths`）。

共通のビルド・UI を直したあと、各サイトの CSV はそのまま残し、本番側で `python3 tools/build_all.py` を実行してください。
