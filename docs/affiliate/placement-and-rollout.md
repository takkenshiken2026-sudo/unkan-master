# アフィリエイト導線・設置箇所・マルチサイト展開

資格試験サイト共通の **収益導線の設計** と **設置箇所のルール**。  
比較記事の執筆・brief・UI の詳細は [affiliate-article-rules.md](./affiliate-article-rules.md) を正本とする。

**exam-site-shell が正本。** 各本番サイトは `sync_from_template.py` 後に **サイト固有データだけ** を差し替える。

---

## 1. 基本方針（必ず守る）

### 収益の本丸

```
通常ガイド（情報記事）→ affiliate-* 比較記事 → ASP（Amazon / A8 / afb）
```

| 層 | URL 例 | ASP 直リンク |
|----|--------|--------------|
| 通常ガイド | `/articles/takken-dokugaku/` | **禁止** |
| 比較記事 | `/articles/affiliate-textbooks-recommend/` | **可**（hub・比較表・本文） |
| 一覧カード | `/articles/` 上部 | **禁止**（比較記事への内部リンクのみ） |

### 原則

1. **比較記事だけが ASP を載せる** — 通常ガイド・用語・演習ページに Amazon/A8 を直貼りしない
2. **文脈に合った 1〜2 本** — 1 通常ガイドあたり比較記事への内部リンクは **最大 2 本**（`related_links`）
3. **フッター一括貼り付け禁止** — 全ページ共通の広告帯は作らない
4. **【PR・広告】表記禁止** — 公開ページの本文・表・一覧に載せない（`original_note` に運用メモ）

---

## 2. 設置箇所マップ（一覧）

| # | 設置箇所 | ページ | データ源 | リンク先 | 上限 |
|---|----------|--------|----------|----------|------|
| A | **一覧カード** | `articles/index.html`・`terms/index.html`・`q/index.html` | `site-config.json` → `guideIndexPicks` | 比較記事 | **3 枚**（講座・テキスト・問題集） |
| B | **関連記事ボックス** | 各通常ガイド末尾 | `guide_articles.csv` → `related_links` | 比較記事 + 他ガイド | 比較記事 **1〜2 本** / 全体 **6 件程度** |
| C | **本文の文脈リンク** | 各通常ガイド section 本文 | `section_*_body` に `affiliate-*` slug | 比較記事 | **1 文・1 箇所** 推奨 |
| D | **比較記事の相互リンク** | 各 `affiliate-*` 末尾 | `related_links`（非アフィリ 3 + アフィリ 3） | 他比較記事 + ガイド | 固定 6 件 + ASP URL 行 |
| E | **要点ボックス右端** | 各比較記事上部 | brief `products[0]` | ASP | 1 商品 |
| F | **比較 hub** | 各比較記事 section 1 直後 | brief `products[]` | ASP | 全商品 |
| G | **試験ガイド一覧カード** | `articles/index.html` グリッド | CSV 行（`tags` にアフィリエイト） | 比較記事 | 他記事と同列 |

### 設置しない（現行方針）

| 箇所 | 理由 |
|------|------|
| トップ `index.html` の大型バナー | 一覧ハブと重複。必要なら `guideIndexPicks` の `compact` を検討 |
| 全 351 用語詳細ページへの画像バナー | 工数・広告感。重要語のみ将来 `text` 1 行を検討 |
| 全ページフッター | スパム判定・CVR 低下 |
| 通常ガイドへの ASP 直リンク | 信頼性・ルール違反 |

---

## 3. 比較記事（`affiliate-*`）の作り方

**詳細:** [affiliate-article-rules.md](./affiliate-article-rules.md)・[auto-create-workflow.md](./auto-create-workflow.md)

### ゲート（すべて満たしてから公開）

1. ASP / 商品 URL 確定（プレースホルダー不可）
2. brief + オリジナル本文完成
3. 各商品の価格を **ASP ページで確認済み**
4. `tags` に `アフィリエイト`、`content_status=published`
5. `validate_csv.py` → `build_article_pages.py` 成功

### 標準 slug（10 本目安）

[guide-article-catalog.md](../guide-article-catalog.md) の「アフィリエイト記事」を参照。  
立ち上げは **1 本ずつ**。URL 未設定の行は CSV に載せない。

### クイックコマンド

```bash
python3 tools/scaffold_affiliate_article.py --list-themes
python3 tools/scaffold_affiliate_article.py \
  --from-brief data/affiliate-briefs/affiliate-textbooks-recommend.yaml \
  --append
python3 tools/fetch_affiliate_product_images.py --slug affiliate-textbooks-recommend
python3 tools/validate_csv.py
python3 tools/build_article_pages.py
```

---

## 4. 通常ガイドから比較記事への導線

### 4.1 `related_links`（関連記事ボックス）

- 形式: `affiliate-textbooks-recommend:宅建士のおすすめテキスト3選【2026年度版・独学】`
- セミコロン区切り。slug は **同 CSV に存在する** `affiliate-*` のみ
- **1 記事あたり比較記事 1〜2 本**。他は通常ガイド・用語・演習へのリンク

### 4.2 本文リンク（`section_*_body`）

**通常ガイド → 比較記事**

- 比較記事 slug を **1 文** で自然に挿入（1 記事あたり 1 箇所推奨）
- ビルド時 `guide_slug_prose.resolve_slug_references` が内部 `<a class="related-link">` に変換
- ラベルは `slug_link_label` で短縮（末尾 `【…】` は除去）
- 記法例（CSV 本文）:

```text
テキスト1冊は、affiliate-textbooks-recommend で出版社別の解説量を比較してから固定すると途中で変えずに済みます。
```

**比較記事同士の相互リンク**

- 段落中は **短い Markdown リンク** を使う（長いタイトル付きカード化を防ぐ）
- 記法例:

```text
演習量が足りない場合は、[おすすめ問題集3選](../affiliate-problem-books/)を参照してください。
```

- 一括変換: `python3 tools/apply_affiliate_compare_short_links.py`（`section_*_body` のみ）
- **禁止:** `https://amazon...` や A8 URL を通常ガイド本文に書く

### 4.3 送り先の選び方（検索意図マッチ）

| 通常ガイドの意図 | 送る比較記事（例） |
|------------------|-------------------|
| 独学・教材選び・学習計画 | `affiliate-textbooks-recommend` |
| 過去問・分野攻略・演習量 | `affiliate-problem-books` |
| 社会人・通信・学習スタイル | `affiliate-correspondence-course` |
| 模試・直前・時間配分 | `affiliate-mock-exam-materials` |

**繋がない例:** 合格率の読み方、合格後手続き、年収、会場案内、他資格との制度比較のみの記事

### 4.4 比較記事同士の `related_links`

各 `affiliate-*` の末尾は **非アフィリエイト 3 + アフィリエイト 3**（計 6 件表示）。

推奨セット（公開済み 4 本がある場合）:

- テキスト ↔ 問題集 ↔ 模試 ↔ 講座 を相互にリンク
- 加えて独学・過去問・教材選びなど **通常ガイド 2〜3 本**
- ASP URL 行は `related_links` 末尾に残す（関連ボックスには出さない）

---

## 5. `guideIndexPicks`（一覧カード）

**正本設定:** 各サイトの `site-config.json`  
**生成:** `tools/guide_index_picks_ui.py`（`build_article_pages.py` / `build_glossary_pages.py` / `build_past_question_pages.py` が呼ぶ）

### ルール

| 項目 | 値 |
|------|-----|
| 設置ページ | `/articles/`・`/terms/`・`/q/` の **index のみ** |
| 枚数 | **3 枚固定**（講座 / テキスト / 問題集） |
| `layout` | 既定 **`grid-3`**（1 行 3 列） |
| `href` | 公開済み `affiliate-*` slug（末尾 `/` 可） |
| `image` | `images/affiliate/*.webp`（実ファイル必須・コミット） |
| `leadsByHub` | 任意。ハブごとにリード文を変える（`articles` / `terms` / `q`） |

### 設定例

```json
"guideIndexPicks": {
  "title": "おすすめの講座・教材",
  "lead": "2026年度版の比較記事から、講座・テキスト・問題集の選び方へ。",
  "leadsByHub": {
    "articles": "2026年度版の比較記事から、講座・テキスト・問題集の選び方へ。",
    "terms": "用語暗記と併用するテキスト・問題集・講座の比較記事へ。",
    "q": "無料演習と併用する問題集・講座の比較記事へ。"
  },
  "layout": "grid-3",
  "items": [ /* course, textbook, problem-book 各1 */ ]
}
```

### 変更手順

1. `site-config.json` を編集（**サイト固有**。テンプレの `site-config.json` はサンプル）
2. `python3 tools/build_article_pages.py`（記事一覧）
3. `python3 tools/build_glossary_pages.py`（用語一覧）
4. `python3 tools/build_past_question_pages.py`（演習一覧）
5. または一括: `python3 tools/build_all.py`

**注意:** `tools/site_config.py` の `guide_index_picks()` は `grid-3` で最大 3 件、`grid-2` で最大 4 件。運用標準は **3 枚・grid-3**。

---

## 6. 他サイトへの展開手順

**作業手順（ミス防止・ゲート付き）:** [multi-site-affiliate-workflow.md](./multi-site-affiliate-workflow.md)

### 6.1 テンプレ同期（エンジン）

```bash
cd ~/Projects/exam-site-shell
python3 tools/sync_from_template.py --target ~/Projects/<資格サイト>
```

同期対象に含まれる主なファイル（`tools/template_sync_manifest.txt`）:

- `tools/build_article_pages.py`、`affiliate_*.py`、`guide_index_picks_ui.py`、`guide_slug_prose.py`
- `site-pages.css`、`seo-editorial.css`
- `docs/affiliate/` 一式

### 6.2 サイト固有で用意するもの

| 項目 | パス | 内容 |
|------|------|------|
| 比較記事 CSV 行 | `data/guide_articles.csv` | `affiliate-*` 行 + 通常ガイドの `related_links` / 本文 |
| brief | `data/affiliate-briefs/{slug}.yaml` | 商品・ASP URL・価格 |
| 画像 | `images/affiliate/*.webp` | 表紙・講座サムネ |
| 一覧カード | `site-config.json` → `guideIndexPicks` | 当サイトの公開済み slug・画像・文言 |
| サイトメモ | `docs/affiliate/SITE.md`（任意） | 公開済み slug 一覧・ASP メモ |

### 6.3 立ち上げ順（推奨）

```
1. 比較記事 1 本目（テキスト or 講座）を ASP 確定 → 公開
2. guideIndexPicks に 1〜3 枚を設定（公開済み分だけ）
3. 学習意図の強い通常ガイド 10 本に related_links + 本文 1 文
4. 比較記事を 4 本まで増やし相互リンクをそろえる
5. 学習系ガイドを段階的に拡充（目安: 学習関連の過半数）
6. build_all.py → デプロイ
```

### 6.4 ビルド・デプロイ

```bash
cd ~/Projects/<資格サイト>
python3 tools/build_all.py
# GitHub Pages: main push → CI（tools/ci_deploy_build.sh）→ public_site
```

**反映されないとき:** push 後 CI 完了を待つ（5〜7 分）。ブラウザはスーパーリロード。

---

## 7. 検証チェックリスト（サイトごと）

### 比較記事

- [ ] 公開 `affiliate-*` が ASP URL 付きで HTML 生成されている
- [ ] 比較 hub・要点・`images/affiliate/` が 404 ない
- [ ] 4 本以上ある場合、相互 `related_links` がそろっている

### 導線

- [ ] 通常ガイドに ASP 直リンクが **ない**
- [ ] 学習系ガイドの多くが比較記事へ 1 本以上つながっている
- [ ] `articles/`・`terms/`・`q/` に `guideIndexPicks` が **3 枚・grid-3**
- [ ] フッターに比較記事一括リンクが **ない**

### CI

- [ ] `validate_csv.py` エラーなし
- [ ] `validate_internal_links.py` エラーなし
- [ ] `validate_public_content.py` エラーなし

---

## 8. 関連ドキュメント・Cursor ルール

| 文書 / ルール | 内容 |
|---------------|------|
| [affiliate-article-rules.md](./affiliate-article-rules.md) | 比較記事の執筆・UI・画像・チェックリスト |
| [auto-create-workflow.md](./auto-create-workflow.md) | CLI / AI 雛形フロー |
| [seo-article-guidelines.md](../seo-article-guidelines.md) § アフィリエイト | 識別・法務・本数 |
| `.cursor/rules/affiliate-article.mdc` | CSV・brief 編集時 |
| `.cursor/rules/affiliate-banner.mdc` | 一覧カード・CSS |
| [multi-site-workflow.md](../multi-site-workflow.md) | テンプレ同期全般 |

---

## 9. サイト固有メモ（テンプレ）

各本番サイトに `sites/<site-id>/SITE.md` または `docs/affiliate/SITE.md` を置き、次を記録する。

```markdown
## 公開済み比較記事
| slug | ASP | 備考 |
|------|-----|------|

## guideIndexPicks
- layout: grid-3
- items: （3 slug）

## 通常ガイド導線
- related_links 済: N 本 / 全 M 本
```

---

*最終更新: 2026-06-14（設置箇所・マルチサイト展開を正本化）*
