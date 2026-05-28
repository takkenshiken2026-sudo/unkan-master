# 知識ハブ記事テンプレート（用語 / 比較 / 早見 / 誤答）

`/terms/` 配下の4タブコンテンツの**執筆イメージ・CSV入力の正本**です。

| タブ | データ | ビルド | 読者が得ること |
|------|--------|--------|----------------|
| 用語解説 | `data/glossary_terms.csv` | `build_glossary_pages.py` | 1語の意味・根拠・試験論点 |
| 比較・整理表 | `data/comparisons.csv` | `build_compare_pages.py` | 似た2〜3項目の**差分** |
| 数値・期限早見表 | `data/numbers.csv` | `build_numbers_mistakes_pages.py` | 数字・日数・割合の**一覧** |
| よくある誤答 | `data/mistakes.csv` | `build_numbers_mistakes_pages.py` | 過去問の**引っかけ肢**整理 |

- 用語解説の詳細: [glossary-term-template.md](./glossary-term-template.md)
- **HTML 図解（用語・問題解説へ埋め込み）:** [term-diagrams.md](./term-diagrams.md) — `diagram_id` + `data/term_diagrams/*.json`
- 試験ガイド（学習法・制度読み物）: [guide-article-template.md](./guide-article-template.md) — **知識ハブと役割分担**
- SEO・公開境界: [seo-article-guidelines.md](./seo-article-guidelines.md)

---

## 本番ボリューム目標（3種それぞれ）

| 種別 | CSV | 目標件数 | 検証 |
|------|-----|----------|------|
| 比較・整理表 | `comparisons.csv` | **50〜100 件** | `validate_csv.py`（50 件未満で WARN） |
| 数値・期限早見表 | `numbers.csv` | **50〜100 件** | 同上 |
| よくある誤答 | `mistakes.csv` | **50〜100 件** | 同上 |

テンプレ同梱のサンプル行（各数件）は**執筆例**です。本番サイトでは上記目標まで **新規行を追加** してください。  
行品質の機械チェック: `tools/knowledge_hub_rules.py`（JSON 列・`related_terms`・FAQ 等）。

**新規追加の推奨手順:**

```bash
python3 tools/scaffold_knowledge_hub_article.py --type compare --title "…" --category "…" --append
python3 tools/validate_csv.py
python3 tools/build_glossary_pages.py   # 3種 HTML も連動再生成
```

---

## 役割分担（何をどこに書くか）

```
検索意図「〇〇とは？」        → 用語解説（g-*.html）
検索意図「AとBの違い」       → 比較・整理表（c-*.html）
検索意図「〇〇 何日 何%」     → 数値・期限早見表（n-*.html）
検索意図「〇〇 間違えやすい」 → よくある誤答（m-*.html）
検索意図「勉強法・申込の流れ」 → 試験ガイド（articles/）
```

**1記事 = 1検索意図**を守る。用語解説に比較表を全部詰め込まず、混同が強い組み合わせは比較・誤答へ切り出す。  
視覚で一発理解させたい対比（建ぺい率/容積率など）は、用語記事の **`diagram_id`** で図解ブロックを差し込む（比較表・図解・本文の重複は避ける）。

---

## 記事の作り方（3通り）

### 1. スクリプトで雛形を生成（推奨）

```bash
# 種別一覧
python3 tools/scaffold_knowledge_hub_article.py --list-types

# 1行分を標準出力（確認）
python3 tools/scaffold_knowledge_hub_article.py --type compare \
  --title "35条説明と37条書面の違い" --category 契約・実務

# CSV に追記
python3 tools/scaffold_knowledge_hub_article.py --type numbers \
  --title "契約前後の説明・交付期限" --category 契約・実務 --append

# コピー用テンプレ CSV を更新
python3 tools/scaffold_knowledge_hub_article.py --write-template-csv
```

`--append` 後は `【記入】` プレースホルダをすべて差し替え、`python3 tools/build_glossary_pages.py` を実行します（compare / numbers / mistakes も連動再生成）。

### 執筆サンプル HTML（ブラウザで確認）

ビルド後、以下の **見本ページ** が生成されます（`noindex` — 執筆参照用）。

| 種別 | URL |
|------|-----|
| **サンプル一覧** | `/terms/samples/index.html` |
| 用語解説 | `/terms/g-writing-sample.html` |
| 比較・整理表 | `/terms/compare/c-writing-sample.html` |
| 数値・期限早見表 | `/terms/numbers/n-writing-sample.html` |
| よくある誤答 | `/terms/mistakes/m-writing-sample.html` |

```bash
python3 tools/build_knowledge_hub_sample_pages.py   # 単体再生成
python3 tools/build_glossary_pages.py               # 通常ビルドに含まれる
```

### 2. テンプレ CSV 行をコピー

| 種別 | テンプレファイル |
|------|------------------|
| 比較 | `data/templates/compare_row.template.csv` |
| 早見 | `data/templates/numbers_row.template.csv` |
| 誤答 | `data/templates/mistakes_row.template.csv` |

各1行を対応 CSV の末尾にコピーし、`title`・JSON列・本文列を編集します。

### 3. 既存サンプル行を複製

`data/comparisons.csv` などの既存行をスプレッドシート上で複製し、`title` と表データ（JSON）を差し替えます。

---

## 公開ページの共通構成（比較 / 早見 / 誤答）

詳細ページ（`c-*.html` / `n-*.html` / `m-*.html`）は次の順序で生成されます。

1. タブナビ（知識ハブ4種）
2. タイトル（`article_title`）
3. リード（`article_lead`）
4. **メイン表**（種別ごとの JSON → 表 HTML）
5. 試験で押さえるポイント（`exam_points`）
6. よくある誤解・注意点（`common_mistakes`）
7. 覚え方・整理のコツ（`memory_tip`）
8. よくある質問（`faq_1` 〜 `faq_4`）
9. 記事の基本情報
10. 関連用語リンク
11. 次に確認するページ（一覧・用語・過去問）

一覧ページは用語一覧と同型（検索・分野チップ・3列表）。

---

## 比較・整理表（comparisons.csv）

### 向いている記事

- 2〜3語・制度の**横並び比較**（例: 35条 vs 37条、媒介 vs 代理）
- サイト内モードの使い分け（過去問 / 実践 / 一問一答）
- 「似ているが違う」が検索キーワードになりやすいテーマ

### タイトルの型

- `AとBの違い`
- `A・B・Cの使い分け`（3列比較）
- `article_title`: `AとBの違い｜試験対策での整理`

### CSV 列

| 列 | 説明 |
|----|------|
| `title` | 一覧・h1 の元。比較ペア名 |
| `category` | 分野チップ（用語解説と同じ分野名） |
| `tags` | `;` 区切り |
| `summary` | 一覧3列目の補助・meta 用（1文） |
| `col_labels` | 比較対象名を `;` 区切り（**2件以上**） |
| `compare_rows` | JSON 配列（下記） |
| `article_title` / `article_lead` | 詳細ページ見出し |
| `exam_points` | `;` 区切り2項目以上 |
| `common_mistakes` / `memory_tip` | 本文セクション |
| `related_terms` | 登録済み用語名を `;` 区切り |
| `faq_1_*` 〜 `faq_4_*` | 質問・回答 |

### compare_rows の JSON 型

```json
[
  {"axis": "定義", "cols": ["Aの説明", "Bの説明"]},
  {"axis": "主な目的", "cols": ["…", "…"]},
  {"axis": "使うタイミング", "cols": ["…", "…"]}
]
```

- `axis`: 行見出し（比較軸）。**4〜6行**が目安
- `cols`: `col_labels` と**同じ列数**
- 3列比較なら `col_labels` も3件、`cols` も3要素

### 執筆イメージ（1記事）

> **タイトル:** 媒介と代理の違い  
> **表:** 行＝「名義」「双方代理」「報酬」「契約の相手方」、列＝媒介 / 代理  
> **リード:** 仲立ちか代行かで名義と効果が変わる。双方代理禁止は代理側の定番肢。  
> **関連用語:** 媒介契約;代理;双方代理  

### 記事ネタ例（資格共通）

| 分野 | 比較テーマ例 |
|------|-------------|
| 契約・実務 | 35条 vs 37条 / 媒介 vs 代理 / 手付 vs 定金 |
| 法令・制度 | 地上権 vs 賃借権 / 一般先取 vs 不動産先取 / 受験資格 vs 合格基準 |
| 演習 | 過去問 vs 模擬試験 / 一問一答 vs 実践演習 |
| 横断 | 用語解説 vs 比較表 / 公式情報 vs 試験要項 |

---

## 数値・期限早見表（numbers.csv）

### 向いている記事

- **数字・日数・割合・人数**が試験の核になるテーマ
- 1ページに**3〜8行**の早見表にまとめられるもの
- 用語解説より「一覧でさっと確認」向き

### タイトルの型

- `〇〇の期限一覧`
- `〇〇の数値・割合一覧`
- `article_title`: `契約前後の説明・交付期限｜数値早見表`

### CSV 列（比較との差分）

| 列 | 説明 |
|----|------|
| `highlight` | 一覧3列目に出す代表値（例: `35条8日 / 37条5日`） |
| `item_rows` | JSON 配列（下記） |

### item_rows の JSON 型

```json
[
  {"item": "重要事項説明（35条）", "value": "原則8日以内", "note": "契約前。自ら売主は2日"},
  {"item": "37条書面の交付", "value": "原則5日以内", "note": "契約後"}
]
```

- `item`: 項目名（行見出し）
- `value`: **数字・期限・割合**を短く（一覧でも目立つ）
- `note`: 例外・条文・条件（1文）

### 執筆イメージ（1記事）

> **タイトル:** 手付金・報酬の上限  
> **highlight:** 手付金20% / 報酬定率  
> **表:** 手付金上限・手付解除・報酬算定・空き家特例…  
> **覚え方:** 「20%手付・倍返し解除」  

### 記事ネタ例

| カテゴリ | テーマ例 |
|----------|----------|
| 宅建業法 | 35条8日 / 37条5日 / 手付20% / 専任1/5 / クーリングオフ8日 |
| 借地借家 | 普通借地30年 / 定期50年 / 短期1年以下 |
| 民法 | 成年18歳 / 保佐17歳 / 時効5年・10年 |
| 税・登記 | 固定1.4%・都市計画0.3% / 相続登記3年 |
| 試験制度 | 合格点 / 出題数 / 科目配分 |

---

## よくある誤答（mistakes.csv）

### 向いている記事

- 過去問で**同じ引っかけ**が繰り返される論点
- 「正しいように見える誤肢」のパターン整理
- 比較表より**肢の文言**に焦点

### タイトルの型

- `〇〇の取り違え`
- `〇〇でよくある誤答`
- `article_title`: `35条説明と37条書面の取り違え｜誤答パターン`

### CSV 列（比較との差分）

| 列 | 説明 |
|----|------|
| `confusion_point` | 一覧3列目（混同の一言） |
| `pattern_rows` | JSON 配列（下記） |

### pattern_rows の JSON 型

```json
[
  {
    "topic": "実施時期",
    "wrong": "37条書面は契約前に交付",
    "correct": "35条説明は契約前、37条は契約後5日以内",
    "trap": "説明と交付の順序"
  }
]
```

- `topic`: 論点（行見出し）
- `wrong`: **誤答例**（肢に近い言い回し）
- `correct`: 正解の整理
- `trap`: 引っかけポイント（短く）

### 執筆イメージ（1記事）

> **タイトル:** 先取特権の順位  
> **confusion_point:** 一般先取が最優先ではない  
> **表:** 不動産→不動産先取 / 動産→動産先取 / 一般先取は最後  
> **ポイント:** 目的物ごとに順位が変わる  

### 記事ネタ例

| 分野 | テーマ例 |
|------|----------|
| 宅建 | 35条 vs 37条 / 広告規制 / 自己所有外物件 |
| 権利 | 取消 vs 無効 / 時効の起算 / 抵当 vs 質権 |
| 税 | 税率の入れ替え / 納税義務者 |
| 演習 | クーリングオフ vs 手付解除 |

---

## 相互リンクの付け方

| 起点 | リンク先 |
|------|----------|
| 用語解説 | 関連する比較・早見・誤答を `related_terms` 逆引きまたは本文で言及 |
| 比較・誤答 | `related_terms` に**登録済み用語**2件以上 |
| 早見表 | 各 `item` に対応する用語解説へ `related_terms` |
| すべて | 詳細ページ末尾「過去問演習で確認する」 |

演習 CSV の `tags` に `term:用語名` を付けると、問 ↔ 用語の双方向リンクになります。

---

## 文体・品質（共通）

[glossary-term-template.md](./glossary-term-template.md) と同じ方針を適用します。

- **です・ます調**、1文40〜60字目安
- 数字・期限は**公式テキストで裏取り**（早見表・誤答は特に）
- 表の下に「演習と公式テキストで確認」を入れる（ビルド時に自動注記あり）
- FAQ 4件: 定義 / 使い分け / 試験での見方 / 次に確認すること

---

## 公開前チェック

```bash
python3 tools/build_glossary_pages.py
python3 tools/build_sitemap.py
python3 tools/validate_internal_links.py
```

- JSON列（`compare_rows` / `item_rows` / `pattern_rows`）がパースできるか
- `col_labels` と `compare_rows[].cols` の列数一致
- `related_terms` が `glossary_terms.csv` に存在するか
- 一覧の `category` が site-config の分野名と一致するか

---

## 関連ファイル

| ファイル | 用途 |
|----------|------|
| `data/comparisons.csv` | 比較データ |
| `data/numbers.csv` | 早見表データ |
| `data/mistakes.csv` | 誤答パターンデータ |
| `data/templates/*_row.template.csv` | コピー用1行 |
| `tools/scaffold_knowledge_hub_article.py` | 雛形生成 |
| `tools/build_compare_pages.py` | 比較 HTML 生成 |
| `tools/build_numbers_mistakes_pages.py` | 早見・誤答 HTML 生成 |
| `tools/build_knowledge_hub_sample_pages.py` | 執筆サンプル HTML 生成 |
| `tools/knowledge_hub_tabs.py` | 4タブ HTML |
