# 用語詳細記事テンプレート

`data/glossary_terms.csv` の1行から `terms/g-*.html` が生成されます。**本番では全用語を詳細記事として公開**します（定義1行だけの薄いページは不可）。

- SEO・公開境界の正本: [seo-article-guidelines.md](./seo-article-guidelines.md)
- **試験ガイドと用語解説の立ち位置:** [content-positioning.md](./content-positioning.md)
- **編集品質（専門家×プロライター）:** [editorial-quality.md](./editorial-quality.md)
- 品質監査: `python3 tools/audit_glossary_article_quality.py`
- 演習 DB からの自動充填: `python3 tools/enrich_o4_glossary_details.py`

## 用語の作り方（3通り）

### 1. スクリプトで雛形を生成（推奨）

```bash
# 分野一覧（site-config の fields / category）
python3 tools/scaffold_glossary_term.py --list-categories

# 1行分を標準出力
python3 tools/scaffold_glossary_term.py --term 重要事項説明 --category 法令・制度 \
  --related "35条書面;37条書面"

# CSV に追記
python3 tools/scaffold_glossary_term.py --term 重要事項説明 --category 法令・制度 --append

# コピー用テンプレ CSV を更新
python3 tools/scaffold_glossary_term.py --write-template-csv
```

`--append` 後はプレースホルダをすべて差し替え、`python3 tools/validate_csv.py` → `python3 tools/build_all.py` を実行します。

### 2. テンプレ CSV 行をコピー

`data/templates/glossary_term_row.template.csv` の1行を `glossary_terms.csv` にコピーし、`term`・各列を編集します。

### 3. 演習 DB から一括充填

```bash
python3 tools/enrich_o4_glossary_details.py --dry-run
python3 tools/enrich_o4_glossary_details.py
```

自動生成後も人手で `term_detail_body`・FAQ・`related_terms` を確認してください。定型文だけの行は `audit_glossary_article_quality.py` で検出されます。

---

## 公開ページの構成（自動生成）

`tools/build_glossary_pages.py` が次の順序で HTML を出力します。

1. タイトル（`article_title`）
2. リード文（`article_lead` + 用語名）
3. 目次（**実際に生成される見出しのみ**）
4. この記事の信頼性について
5. この記事でできること（`exam_points` から自動）
6. まず押さえる要点（`short_def`）
7. 試験で押さえるポイント（`exam_points`）
8. 定義と基本理解（`term_detail_body` + `related_terms` 混同比較表）
9. **図解で理解する**（任意 — CSV の `diagram_id` → [term-diagrams.md](./term-diagrams.md)）
10. 法令・根拠（`legal_basis`、値がある場合のみ）
11. 選択肢で問われやすい点（`explanation`）
12. よくある誤解・注意点（`common_mistakes`）
13. 覚え方・整理のコツ（`memory_tip`）
14. 例題で確認（`example_question` / `example_answer`）
15. よくある質問（`faq_1` 〜 `faq_4` **必須・4件**）
16. 記事の基本情報
17. 公式情報の確認
18. 関連用語・次に確認するページ

---

## 全用語必須ルール（`validate_csv.py` が ERROR）

| 列 | 最低要件 |
|----|----------|
| `term` | 重複不可 |
| `category` | `site-config.json` の分野名 |
| `tags` | 1件以上（`;` 区切り） |
| `importance` | `A` / `B` / `C` / `S` |
| `short_def` | 12文字以上 |
| `definition` | 30文字以上 |
| `explanation` | 40文字以上（選択肢の論点） |
| `article_title` | 10文字以上（例: `〇〇とは？意味・試験ポイント`） |
| `article_lead` | 30文字以上 |
| `term_detail_body` | **180文字以上**（**2段落以上**） |
| `exam_points` | **2項目以上**（`;` 区切り、各8文字以上） |
| `common_mistakes` | 20文字以上 |
| `memory_tip` | 15文字以上 |
| `example_question` | 12文字以上 |
| `example_answer` | `○` / `×` または5文字以上 |
| `faq_1_*` 〜 `faq_4_*` | 質問6文字以上、回答**100文字以上**（**4件必須**） |

---

## 文体ルール（誰が読んでもわかりやすく）

受験者・初学者が初見でも理解できることを最優先にします。

| 方針 | 具体例 |
|------|--------|
| **です・ます調**で統一 | 「〜である」より「〜です」 |
| **1文は短く**（40〜60字目安） | 長文は2文に分割 |
| **専門語は初出で補足** | 「指定数量（危険物を貯蔵できる上限）」 |
| **誰が・いつ・何を**を明示 | 主体と条件を省略しない |
| **具体例・数字**で抽象を補う | 「早めに」→「申込開始から1週間以内に」 |
| **日常語に言い換える** | 「及び」→「と」、「当該」→具体的名称 |

避ける表現（`validate_csv.py` が WARN）: `当該` `前述` `において` `ものとする` `及び`（法令原文の写しに見える硬い語）

FAQ 4件の役割分担:

1. **定義** … 「〇〇とは何ですか？」
2. **誤解** … 「よくある誤解は？」
3. **試験** … 「試験でどう問われますか？」
4. **次の行動** … 「学んだあとに何を確認しますか？」
| `related_terms` | **登録済み用語2件以上**（混同比較表・内部リンク用） |

`legal_basis` は任意ですが、`法令・制度` 分野かつ `importance` が `A`/`S` の用語は記載を推奨（未記載は WARN）。

本番ボリューム目標: **300件以上**（未満は WARN）。

---

## 執筆の型（記事種別）

用語ごとに次のいずれかを意識し、空セクションを増やさないようにします。

| 型 | 厚く書く列 | 例 |
|----|------------|-----|
| 定義型 | `term_detail_body`, `definition` | 制度・手続の基本 |
| 数字・期限型 | `exam_points`, `common_mistakes` | 割合・日数・倍数 |
| 混同語型 | `related_terms`（3件以上推奨） | 似た用語の違い |
| 演習連動型 | `explanation`, `example_*` | 実践・一問一答の論点 |

演習 CSV の `tags` に `term:用語名` を付けると、問ページ → 用語ページへの双方向リンクになります（[question-static-pages.md](./question-static-pages.md)）。

---

## 公開してはいけないもの

- 検索意図・記事種別・更新方針・独自メモ（CSV 内部用）
- CSV 列名やテンプレ運用の説明文を `term_detail_body` に書くこと
- 全用語同じ定型リード・FAQ のコピペ

---

## 公開前チェック

```bash
python3 tools/validate_csv.py
python3 tools/audit_editorial_quality.py
python3 tools/audit_glossary_article_quality.py
python3 tools/build_all.py
```

`build_all.py` 内の `validate_generated_seo.py`・`validate_internal_links.py` も必須です。
