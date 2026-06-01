# 試験ガイド記事テンプレート

`data/guide_articles.csv` に1行追加すると、`articles/{slug}/index.html` が生成されます。本ドキュメントは **執筆・CSV入力のテンプレ** です。

- ジャンル一覧（21区分）: [guide-article-genres.md](./guide-article-genres.md)
- 100本以上の slug 例: [guide-article-catalog.md](./guide-article-catalog.md)
- SEO・公開境界の正本: [seo-article-guidelines.md](./seo-article-guidelines.md)
- **試験ガイドと用語解説の立ち位置:** [content-positioning.md](./content-positioning.md)
- **編集品質（専門家×プロライター）:** [editorial-quality.md](./editorial-quality.md)

## 記事の作り方（3通り）

### 1. スクリプトで雛形を生成（推奨）

```bash
# ジャンル一覧（12区分）
python3 tools/scaffold_guide_article.py --list-genres

# 1行分を標準出力（確認用）
python3 tools/scaffold_guide_article.py --slug exam-schedule --genre 日程・申込

# CSV に追記
python3 tools/scaffold_guide_article.py --slug exam-schedule --genre 日程・申込 --append

# コピー用テンプレ CSV を更新
python3 tools/scaffold_guide_article.py --write-template-csv
```

`--append` 後は **scaffold の本文をそのまま使わず全面リライト** し、`user_intent`・各 `section_*_body`・FAQ を記事固有のオリジナル文に差し替えてから `content_status` を `published` にします。機械的な共通文の禁止ルールは [editorial-quality.md](./editorial-quality.md#オリジナル執筆機械的な共通文を作らない) を参照。

### 2. テンプレ CSV 行をコピー

`data/templates/guide_article_row.template.csv` の1行を `guide_articles.csv` の末尾にコピーし、`slug`・`genre`・各列を編集します（**テンプレファイル自体はビルド対象外**）。

### 3. 既存記事を複製

近いジャンルの行（例: `study-plan`）をスプレッドシート上で複製し、`slug` と本文を差し替えます。

---

## 公開ページの構成（自動生成）

ビルド後、読者向けページは次の順序になります（`tools/build_article_pages.py`）。

1. タイトル（`title`）
2. リード文（`lead`）
3. 目次
4. この記事の信頼性について（執筆・確認・事実確認日・参照元）
5. この記事でできること（`user_intent` + `action_items`）
6. 本文（`section_1` 〜 `section_7`、空セクションは非表示）
7. よくある質問（`faq_1` / `faq_2` 必須）
8. 記事の基本情報（ジャンル・タグ）
9. 公式情報の確認
10. 関連記事（`related_links`）

運用者向け列（`original_note`・`update_policy` など）は **公開 HTML に出しません**。

---

## CSV 列の意味

| 列 | 公開 | 説明 |
|----|------|------|
| `slug` | URL | `exam-schedule` → `articles/exam-schedule/`。半角英小文字・ハイフン |
| `genre` | 表・一覧 | `guideArticleGenres` の label のみ（12種） |
| `title` | h1 | 「◯◯試験 + 知りたいこと」。`◯◯試験` は `site-config.json` の試験名に置換 |
| `meta_description` | meta | 120〜155文字目安 |
| `lead` | リード | 誰向けか・記事で分かることを2〜3文 |
| `priority` | 一覧順 | 小さいほど上。同ジャンル内の並びにも影響 |
| `tags` | 表 | セミコロン区切り（例: `学習計画;独学`）。**アフィリエイト記事は `アフィリエイト` を必ず含める**（本番目安10本。`validate_csv.py` がカウント） |
| `author_name` など | 信頼性表 | 執筆・確認・プロフィール |
| `fact_checked_at` | 信頼性表 | `YYYY-MM-DD` |
| `primary_sources` | 信頼性表 | `ラベル\|URL` をセミコロン区切りで複数可 |
| `original_note` | 非公開 | 編集メモ |
| `user_intent` | できること | 読者が得られること（1段落） |
| `action_items` | できること | 箇条書き。セミコロン区切りで2項目以上推奨 |
| `update_policy` | 非公開 | 更新ルール（監査用） |
| `last_reviewed_at` / `next_review_at` / `source_checked_at` | 非公開 | 更新管理 |
| `content_status` | 非公開 | 下書きは `draft`、公開前に `published` |
| `revision_note` | 非公開 | 変更履歴 |
| `section_N_heading` / `section_N_body` | 本文 | N=1〜7。見出しと本文の両方がある行だけ目次に載る |
| `faq_N_question` / `faq_N_answer` | FAQ | N=1,2（必須） |
| `related_links` | 関連 | `slug:表示ラベル` をセミコロン区切り。**同じ CSV に存在する slug のみ** |

---

## 本文の書き方

- 見出しは **5〜7個**（`section_1` 〜 `section_7`）。各 `section_*_body` は **180文字以上**（推奨 180〜300文字）。`published` では未満は **ERROR**。
- FAQ 回答は **100文字以上**（`published` では ERROR）。詳細は [editorial-quality.md](./editorial-quality.md)。
- 段落は空行で区切る（`\n\n`）。2つ以上の短文リストにしたいときは、本文中で **セミコロン区切り**（`項目1;項目2;項目3`）にすると HTML の `<ul>` になる。
- プレースホルダー `◯◯試験` はビルド時に `site-config.json` の `examName` に置換される。
- 本文に「CSVの増やし方」「テンプレ運用」など **運用者向けの説明を書かない**。
- 制度・数値・日程は **公式情報を確認したうえで** 資格固有の内容に差し替える。

### 試験会場・アクセス記事

`exam-venue-and-region`・`shiken-kaijo`・`*-center` など会場を扱う記事は [exam-venue-guide.md](./exam-venue-guide.md) に従う。

- 住所・駅名・具体ルートは**書かない**（公式リンクへ誘導）
- 受験票が正本である旨を必ず含める
- 新規・修復は `fix_exam_venue_guide_articles.py` / `fix_exam_venue_hub_articles.py` を使う

---

`scaffold_guide_article.py` がジャンルごとに見出しを入れます。手書きするときの参考:

| genre | section 見出しの例（5本） |
|-------|---------------------------|
| 試験概要 | 目的 → 公式情報 → サイトでできること → 押さえる項目 → 次に読む記事 |
| 受験・申込 | 資格 → スケジュール → 手数料 → 手順 → チェックリスト |
| 出題・形式 | 範囲 → 改定 → 科目 → 形式 → 過去問対応 |
| 学習計画 | 分野分け → 期間 → 週間表 → 復習日 → 直前調整 |
| 過去問活用 | 年度別 → 模試 → 間違い分類 → 解き直し → 用語へ戻る |
| 注意点・更新 | 誤解 → 改定 → 合格後 → 再受験 → 公式優先 |

---

## 公開前チェック

```bash
python3 tools/validate_csv.py
python3 tools/audit_editorial_quality.py
python3 tools/build_all.py
```

- `related_links` の slug がすべて CSV にあるか
- `genre` が12ラベルのいずれかか
- FAQ 2件、信頼性表4行、本文見出し5個以上
- `content_status` を `published` にしたか
- `primary_sources` の URL が `example.com` のままになっていないか

---

## 関連ファイル

| ファイル | 用途 |
|----------|------|
| `data/guide_articles.csv` | 本番データ |
| `data/templates/guide_article_row.template.csv` | コピー用1行 |
| `tools/scaffold_guide_article.py` | 雛形生成 |
| `tools/build_article_pages.py` | HTML 生成 |
