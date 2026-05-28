# 問題静的ページ（過去問・実践演習・一問一答）

CSV を編集し `python3 tools/build_all.py` で、SPA 用 JS と SEO 向け静的 HTML（`q/`）を一括生成する手順です。**`q/` 配下の HTML は手編集しません。**

フッター・3モードタブ・用語一覧を**まとめて**直すときは [integration-checklist.md](./integration-checklist.md) を先に読んでください（本ドキュメントは CSV・ビルド詳細に特化）。

一覧・SPA の読み込みが重くなる場合は [performance-loading.md](./performance-loading.md)（データの載せ方・フェーズ分割）を参照してください。

## 一覧 URL と個別ページ

| 種別 | 一覧 | 個別ページ URL | データ CSV |
|------|------|----------------|------------|
| 過去問 | `/q/index.html` | `/q/past/y{年}/q{番号2桁}/index.html` | `data/past_questions.csv` |
| 実践演習 | `/q/practice/index.html` | `/q/practice/p{番号3桁}/index.html` | `data/practice_questions.csv` |
| 一問一答 | `/q/ichimon/index.html` | `/q/ichimon/y{年}/i{月2桁}-{枝番}/index.html` | `data/ichimon_questions.csv` |

例（テンプレサンプル）:

- 実践演習 第1問 → `/q/practice/p001/index.html`
- 一問一答 `2026-01-1` → `/q/ichimon/y2026/i01-1/index.html`

一覧ページは過去問と同型（検索・分野絞り込み・学習状況・グループジャンプ・折りたたみ）。挙動は共通の `site-q-index.js` が `#q-index-config` を読んで切り替えます。

## ビルドの流れ

```bash
python3 tools/build_all.py
```

| 順序 | スクリプト | 出力 |
|------|------------|------|
| CSV 検証 | `validate_csv.py` | — |
| SPA 用 JS | `csv_to_exam_site_past_js.py` | `exam-site-data-past.js`, `exam-site-data-practice.js` |
| SPA 用 JS | `csv_to_exam_site_ichimondou_js.py` | `exam-site-data-ichimondou.js` |
| 過去問静的 | `build_past_question_pages.py` | `q/past/`, `q/index.html` |
| 実践・一問一答静的 | `build_practice_ichimon_pages.py` | `q/practice/`, `q/ichimon/` |
| サイトマップ | `build_sitemap.py` | `sitemap.xml` |
| リンク検証 | `validate_internal_links.py` | — |

本番サイトでは `tools/sync_from_template.py --target <path>` のあと、**本番の `data/*.csv` のまま** `build_all.py` を実行します（`data/` は同期されません）。

## HTML「テンプレ」の正本（コード内）

別ファイルの `.html` テンプレはありません。次の Python 関数が HTML を組み立てます。

| ページ | 関数 | ファイル |
|--------|------|----------|
| 過去問一覧 | `build_q_index()` | `tools/build_past_question_pages.py` |
| 過去問 各問 | `build_question_html()` | 同上 |
| 実践・一問一答 一覧 | `build_mode_index()` | `tools/build_practice_ichimon_pages.py` |
| 実践 各問 | `build_practice_question_html()` | 同上 |
| 一問一答 各問 | `build_ichimon_question_html()` | 同上 |
| 解説ブロック | `build_explanation_html()` / `build_ichimon_explanation_html()` | `tools/q_explanation.py` |
| 類似の問題 | `build_similar_questions_html()` | `tools/q_similar_questions.py` |
| ヘッダー・フッター | `site_page_header()` 等 | `tools/html_footer.py` |
| 一覧 JS | — | `site-q-index.js` |
| 見た目 | — | `site-pages.css`, `site-theme.css` |

一覧のモード設定（実践・一問一答）は `tools/build_practice_ichimon_pages.py` の `INDEX_CONFIG` と、生成 HTML 内の `#q-index-config` JSON が対応します。

| キー | 実践 | 一問一答 | 備考 |
|------|------|----------|------|
| `groupBy` | `category` | `category` | **年度別にしない**（id の `y{年}` は URL のみ） |
| `groupLabel` | 分野 | 分野 | ジャンプ行ラベル |
| `categoryOrder` | ビルド時注入 | 同左 | `site-config.json` の `fields` 順 |
| `statusFilters` | wrong, bookmark | 同左 | 過去問の exempt/invalid は載せない |
| `rowLabelField` | qno | id | 表の「問」列 |

`site-q-index.js` は `categoryOrder` で分野ブロック・フラット一覧を並べ替えます。ジャンプリンクは `data-group` 属性（`data-year` と併用可）。

## CSV 執筆

### コピー元（`data/templates/`）

| ファイル | 用途 |
|----------|------|
| `practice_question_row.template.csv` | 実践演習 1 行の雛形 |
| `ichimon_question_row.template.csv` | 一問一答 1 行の雛形 |

過去問は列が多いため、サンプルは `data/past_questions.csv` を参照してください。

### 実践演習（`practice_questions.csv`）

過去問と同型の 4 択問題です。`site-config.json` の `fields` にある **分野名（`category`）** と一致させます。

| 列 | 必須 | 説明 |
|----|------|------|
| `question_no` | ○ | 1 からの通し番号（重複不可） |
| `type` | ○ | 例: `single` |
| `category` | ○ | 分野名 |
| `tags` | — | 一覧検索・用語リンク用（`;` 区切り） |
| `stem` | ○ | 問題文 |
| `preamble`, `statement_a`〜`d` | — | 組み合わせ問題用（過去問と同じ） |
| `choice_1`〜`choice_4` | ○ | 選択肢 |
| `correct` | ○ | 正答番号（1〜4） |
| `explanation` | ○ | 解説（1 段落でも可） |

任意で過去問と同様に `explanation_summary`, `explanation_correct`, `explanation_choices`, `explanation_point` を足すと、解説ブロックが詳細になります。

**他の選択肢**の `explanation_choices` は、誤肢ごとに「なぜ正答でないか」「正答（番号）との対比」「よくある誤解」を書いてください。「本肢は妥当です」だけの1文は表示時に推論へ置き換えられます（`tools/q_explanation.py` の `resolve_wrong_choice_note`）。

SPA の問題 ID は `900000 + question_no` です。一覧の「不正解」「ブックマーク」フィルタはこの ID と連携します。

#### 既存 JS バンクからの一括取り込み（宅建など）

SPA 用 `takken-data-original.js` の `ORIG_QUESTIONS` が正本で CSV がサンプルのみの場合:

```bash
python3 tools/import_orig_questions_to_practice_csv.py
python3 tools/import_base_questions_to_ichimon_csv.py --keep-manual
python3 tools/build_all.py
```

- 実践演習: `import_orig_questions_to_practice_csv.py` → `data/practice_questions.csv`（1000 問規模）
- 一問一答: `import_base_questions_to_ichimon_csv.py` が過去問＋実践の4択から ○× 1 文を生成（個数・組合せ問題は除外）。`--keep-manual` で手書き行を先頭に残す

### 一問一答（`ichimon_questions.csv`）

| 列 | 必須 | 説明 |
|----|------|------|
| `id` | ○ | `YYYY-問番号-枝番`（例: `2026-01-1`）。重複不可 |
| `question` | ○ | 正誤を判断する **1 文** |
| `answer` | ○ | `○`（記述は正しい）または `×`（記述は誤り） |
| `explanation` | ○ | 解説（1 段落でも可。未分割時は自動展開） |
| `explanation_summary` | — | 冒頭の要約（過去問・実践と同型） |
| `explanation_correct` | — | 正解の理由（○/× が正しい根拠） |
| `explanation_opposite` | — | **もう一方の記号**を選びやすい考え方（過去問の `explanation_choices` に相当） |
| `explanation_point` | — | 学習のヒント |
| `category` | ○ | 分野名 |
| `tags` | — | 検索・用語リンク用 |
| `source` | — | 出典表示（静的ページに表示） |
| `note` | — | 内部メモ（静的 HTML には出さない想定） |

静的ページの解説ブロックは **要約 → 正解の理由 → もう一方の記号 / 他の選択肢 → 学習のヒント** の順で、過去問・実践演習・一問一答で同じ見出し粒度に揃えます（`tools/q_explanation.py`）。

### HTML 図解（`diagram_id`・任意）

| 列 | 必須 | 説明 |
|----|------|------|
| `diagram_id` | — | `data/term_diagrams/{id}.json` を参照（拡張子なし）。用語記事と **同じ JSON を共用可** |

- **契約・新規/既存サイト手順:** [term-diagrams.md](./term-diagrams.md)
- **用語ページ:** ✅ 実装済（定義の直後に「図解で理解する」）
- **問題ページ:** 📋 未実装。実装時は解説内「正解の理由」の後に **図解で整理** を挿入（`diagram_body_html()` を共用）
- `validate_csv.py` は 3 種 CSV とも `diagram_id` があれば JSON 存在を検証（ERROR）

`id` の年部分は個別ページ URL の `y{年}` に使われます。**一覧のグループは分野（category）** です（`groupBy: category`）。

SPA の `publicPath` は `q/ichimon/y{年}/i{月}-{枝番}/index.html` に自動設定されます（`csv_to_exam_site_ichimondou_js.py`）。

### 過去問の `related_links`（参考）

過去問 CSV の `related_links` は静的ページの「関連ページ」に使えます（実践・一問一答はビルド時に自動補完が中心）。

| トークン | 例 | 意味 |
|----------|-----|------|
| `guide:slug:ラベル` | `guide:study-plan:学習計画` | 試験ガイド記事 |
| `term:用語名` | `term:試験要項` | 用語ページ |
| `past:2026-2` | — | 同年の別問 |
| `qindex` | — | 過去問一覧 |
| `terms` | — | 用語一覧 |
| `review` | — | SPA 復習 |
| `field` | — | 当該分野の用語ハブ |
| `page:path/to.html:ラベル` | — | 任意静的パス |

実践・一問一答の各問ページには、一覧・隣接問・用語・試験ガイド・他モード一覧・アプリ導線が自動で付きます。

### 類似の問題（自動）

各問ページの**解説の下・関連ページの上**に「類似の問題」を最大4件表示します（`tools/q_similar_questions.py`）。

- 判定: **同分野**、**共通タグ**、問題文のキーワード重なり（過去問・実践・一問一答を横断）
- 手動列は不要。類似度が低い場合は同分野の問題をフォールバック表示
- 運用のコツ: `category` と `tags` を揃えると、モードをまたいだおすすめが出やすくなります

## 公開前チェック

1. `python3 tools/validate_csv.py` … CSV だけ先に確認
2. `python3 tools/build_all.py` … 必須（内部で `validate_site_integration.py`）
3. `validate_site_integration.py` … CSV 件数 = `#q-index-data`、一問一答 `groupBy: category`
4. ブラウザで一覧の検索・絞り込み、各問ページの meta・パンくず・「アプリで演習する」
5. 本番では `site-config.json` の `siteOrigin` と公式 URL を実値に差し替え

## よくある作業

| やりたいこと | 操作 |
|--------------|------|
| 問題を増やす | 該当 CSV に行を追加 → `build_all.py` |
| SPA バンクから一括 | §実践の取り込み → `build_all.py` |
| 解説だけ直す | CSV の `explanation` 等を編集 → `build_all.py` |
| 一覧 UI を変える | `site-q-index.js` / `tools/html_footer.py`（`q_index_tools_*`）→ テンプレ同期 |

### 一覧のレスポンシブ（3モード共通）

過去問・実践演習・一問一答の一覧はいずれも `body.q-index-page` と同じ CSS（`site-pages.css`）です。

- スマホ: リード・注記・パネル内 H2 を非表示、検索＋件数を1行、**絞り込みは `<details>` で初期閉じ**
- 実践演習のみ: 分野ジャンプと分野チップが重複するため、**分野チップ行は非表示**（ジャンプ行のみ）
- 再生成: `python3 tools/build_all.py`（`Q_INDEX_CSS_VER` で CSS キャッシュ更新）
| 個別ページの構成を変える | `build_*_question_html()` を編集 → テンプレ同期 |

## SEO 文言（模試・模擬試験・3モード）

一覧・各問ページのリード・`meta description`・短い注記（`.q-study-modes-note`）に、`site-config.json` の `seoCopy` を反映します。

```json
"seoCopy": {
  "mockExam": "模試・模擬試験",
  "studyModes": "過去問・実践演習・一問一答"
}
```

正本: `tools/q_page_seo.py`（ビルド時に `build_past_question_pages.py` / `build_practice_ichimon_pages.py` から利用）。

### title / H1（試験名を先頭に）

| ページ | H1 例 | title 例 |
|--------|-------|----------|
| 過去問一覧 | `{試験名} 過去問` | `{試験名} 過去問一覧｜模試・模擬試験対策｜{ブランド}` |
| 各過去問 | `{試験名} 過去問 {年}年 第{n}問（{分野}）` | 同上＋`｜{ブランド}` |
| 実践一覧 | `{試験名} 実践演習` | `…一覧｜模試・模擬試験前の演習｜…` |
| 各実践問 | `{試験名} 実践演習 第{n}問（{分野}）` | 同上 |
| 一問一答一覧 | `{試験名} 一問一答` | `…一覧｜模試・模擬試験前の確認｜…` |
| 各一問一答 | `{試験名} 一問一答 {id}（{分野}）` | 同上 |

関数: `index_h1` / `index_page_title` / `question_h1` / `question_page_title`（すべて `tools/q_page_seo.py`）。

## ナビ・フッター・3モードタブ（要約）

| 項目 | 正 |
|------|-----|
| フッター「過去問一覧」 | `site-config.json` → `href: q/index.html`（実践 URL にしない） |
| ルート `index.html` フッター | **`apply_site_config.py`** が `site-config` から再生成（手編集は例外時のみ） |
| 過去問ハブ `/q/index.html` | `build_q_index()` に `q_hub_links_html(..., current="past")` |
| 用語一覧 | `shortDef` + `definition`；JS は `shortDef \|\| definition` |
| 検証 | `validate_site_integration.py`（`build_all` 内） |

詳細: [integration-checklist.md](./integration-checklist.md)

## 関連ドキュメント

- [integration-checklist.md](./integration-checklist.md) … 一回で揃える統合手順（**フッター・タブ・用語一覧**）
- [seo-article-guidelines.md](./seo-article-guidelines.md) … 内部リンク・公開境界の共通ルール
- [multi-site-workflow.md](./multi-site-workflow.md) … 本番への同期
- [data/README.md](../data/README.md) … CSV ファイル一覧
