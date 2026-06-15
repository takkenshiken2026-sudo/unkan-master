# 資格試験サイト アフィリエイト記事ルール

試験ガイド内のアフィリエイト記事（参考書・問題集・通信講座など）の **作成・更新・公開** ルール。  
**exam-site-shell** テンプレートおよび各資格サイトの `articles/{slug}/` を前提とする。

## 文書の役割分担

| 文書 | 内容 |
|------|------|
| **本書** | 作成手順・UI・画像・ASP・チェックリスト |
| **[placement-and-rollout.md](./placement-and-rollout.md)** | **設置箇所マップ・通常ガイド導線・マルチサイト展開** |
| [seo-article-guidelines.md](../seo-article-guidelines.md) の「アフィリエイト記事」 | 識別・法務・本数 |
| [guide-article-catalog.md](../guide-article-catalog.md) | 標準 slug 一覧（10本目安） |
| [auto-create-workflow.md](./auto-create-workflow.md) | CLI / AI による雛形生成フロー |

各本番サイトの `docs/` はスタブ。**詳細は exam-site-shell を正本** とする。

---

## 1. いつ記事を作るか（最重要）

### 作る条件

次が **すべて揃ってから** CSV 追記・公開 HTML 生成を行う。

1. **ASP / 商品 URL が確定**（Amazon・A8.net・afb 等。プレースホルダー不可）
2. 1記事 = 1検索意図が決まっている
3. 比較対象・訴求ポイントがブリーフまたは `original_note` に書ける
4. **各商品の最新価格を ASP / 公式 URL で確認済み**（[§3 執筆の必須原則 A](#a-価格は必ず-url-から最新を調査する)）
5. **タイトル・商品に沿ったオリジナル本文が完成している**（[§3 執筆の必須原則 B](#b-機械的な量産文を書かず記事ごとにオリジナル執筆する)）

### 作らない・待つ

| 状況 | 対応 |
|------|------|
| URL 未確定 | **CSV 行を作らない**。ブリーフ YAML だけ用意してよい |
| 既に CSV 行だけある | `content_status=draft` のまま。**HTML は生成されない** |
| 標準10 slug を一括追加 | **禁止**。URL が付いた slug から1本ずつ |

### 公開の流れ

```
ASP URL 確定 → 各商品ページで価格確認 → brief 記入
→ オリジナル本文執筆 → scaffold --append（または CSV 更新）
→ content_status=published → build → デプロイ
```

**ASP URL が1本もないテーマは CSV 行・公開 HTML を作らない**（`content_status=draft` のまま待機）。

---

## 2. 識別・本数

| 項目 | ルール |
|------|--------|
| 記事種別 | 試験ガイド（`data/guide_articles.csv`）の1行 = 1 URL |
| 識別 | `tags` に **`アフィリエイト`**（CSV・validate 用） |
| 公開ページ | **`アフィリエイト` タグは表・一覧に出さない** |
| 本数目安 | **ASP リンク済み・公開 HTML あり** の行を **10本前後** |
| genre | 原則 `独学対策`。模試系 `過去問活用`、セット系 `学習計画`、申込系 `受験・申込` も可 |

---

## 3. コンテンツ・表記

### 載せる

- 読者向けの比較・選び方・学習との組み合わせ
- 信頼性パネル（執筆・確認・事実確認日）。Amazon 利用時はプログラム名
- 内部リンク（過去問・用語・学習計画）**2件以上**

### 載せない

- **【PR・広告】等の PR 定型文**（本文・表・一覧すべて）
- `アフィリエイト` タグ（公開ページの基本情報表・試験ガイド一覧）
- ASP プログラム ID・報酬条件（→ `original_note` に非公開で記録）
- 運用者向け文言（CSV 手順・テンプレ説明など）
- **テンプレのプレースホルダー文言をそのまま公開する文章**（後述「執筆の必須原則」）

### 執筆の必須原則（必ず運用）

以下2点は **すべてのアフィリエイト記事** で例外なく守る。AI・人のどちらが執筆しても同じ。

#### A. 価格は必ず URL から最新を調査する

価格の誤記は読者損害・信頼低下につながるため、**公開・更新のたびに** 各商品の ASP / 公式 URL を開き、**その時点の表示価格** を確認してから brief・CSV に反映する。

| 項目 | ルール |
|------|--------|
| 調査元 | brief の `amazon_url` / `a8_url` / `affiliate_url` 等 **リンク先の販売ページ**（短縮 URL も必ず遷移先まで確認） |
| 反映先 | brief の `price_yen` / `price_label` / `price_note`、本文・比較表に載る数値 |
| タイミング | 新規執筆時、**公開前**、価格改定・キャンペーン期の **再公開前** |
| 禁止 | テンプレ・他記事・記憶・推測からの価格転記、未確認のまま `published` |
| 記録 | `fact_checked_at` を更新。必要なら `revision_note` に確認日を残す |

**書籍（Amazon）:** 商品ページの税込価格・版・在庫状況を確認。  
**講座（A8 / afb / 公式）:** 通常料金・キャンペーン料金・月額/一括・受講期限を公式 LP で確認。キャンペーン表記は執筆日と整合させる。

brief の `price_yen` と本文の価格表記が **不一致のまま公開しない**。

#### B. 機械的な量産文を書かず、記事ごとにオリジナル執筆する

`guide-row.yaml` や scaffold 出力は **構成の雛形** であり、公開可能な完成原稿ではない。  
**1記事 = 1検索意図 = 1回のオリジナル執筆** とし、タイトル・紹介商品・資格・読者像に合わせて **section ごとに中身を書き直す**。

| 項目 | ルール |
|------|--------|
| 必須 | 当該記事の **タイトル・検索意図・brief の商品** に沿った独自の論旨・具体例・向き不向き |
| 禁止 | テンプレの `◯◯試験` 差し替えだけ、他 slug の本文流用、同一フレーズの使い回し、SEO 用の空疎な定型段落の連続 |
| 商品詳細 section | 各商品の **目次構成・解説量・強み弱み・組み合わせ** を個別に記述（3商品なら3パターンが読めること） |
| AI 利用時 | 雛形をベースに **全面リライト**。一括生成で複数 slug を同時に仕上げない |
| 公開ゲート | 「テンプレから機械置換しただけ」と判断できる段落が残っていたら **公開しない** |

読者が「この記事だけの比較・選び方」と感じられることを合格基準とする。

### リンクの分離

| 用途 | 置き場 |
|------|--------|
| 公式・一次情報 | `primary_sources` |
| ASP / 商品 | 本文 CTA・brief の `products.*_url`（**関連ボックスには出さない**） |
| 内部ガイド | `related_links` の `slug:ラベル` |

### 関連記事・知識ハブ（アフィリエイト記事）

公開ページ末尾の関連ボックスは **最大6件**。

| 種別 | 件数 | 例 |
|------|------|-----|
| その他コンテンツ（非アフィリエイト） | 3件 | 独学ガイド、過去問の回し方、用語解説への導線 |
| 別のアフィリエイト記事 | 3件 | テキスト比較、問題集比較、講座比較 |

- `related_links` には上記6件を **非アフィリエイト3 → アフィリエイト3** の順で記載
- 自動付与の知識ハブリンク（用語一覧・過去問演習など）は **付けない**
- Amazon / A8 等の外部商品 URL は `related_links` に書いても関連ボックスには表示されない（ASP 判定用に brief・本文に残す）

外部リンク属性: `target="_blank" rel="nofollow sponsored noopener noreferrer"`

---

## 4. 作成手順

### 4.1 新規1本

```bash
# 1. テーマ確認
python3 tools/scaffold_affiliate_article.py --list-themes

# 2. ブリーフに ASP URL を記入してから追記（URL 無しはエラー）
python3 tools/scaffold_affiliate_article.py \
  --from-brief data/affiliate-briefs/affiliate-textbooks-recommend.yaml \
  --append

# 3. 本文・画像を完成 → 公開状態へ
#    content_status=published（CSV）

# 4. 検証・ビルド
python3 tools/validate_csv.py
python3 tools/build_article_pages.py   # または build_all.py

# 5. デプロイ（各サイト main → GitHub Pages）
```

### 4.2 リンク未設定行を draft に戻す

```bash
python3 tools/draft_unlinked_affiliate_articles.py
```

### 4.3 PR 定型文の除去（既存 CSV 用）

```bash
python3 tools/strip_affiliate_pr_disclaimer.py
```

---

## 5. データとビルド

| 項目 | 内容 |
|------|------|
| 記事データ | `data/guide_articles.csv` |
| テーマ入力 | `data/affiliate-briefs/{slug}.yaml` |
| 本文 | CSV の `section_*`。**product-comparison brief なら商品名を本文から自動リンク** |
| ビルド | `python3 tools/build_article_pages.py` / `build_all.py` |
| 公開 URL | `https://{ドメイン}/articles/{slug}/` |
| 生成物 | `articles/{slug}/index.html`（**手編集しない**） |

**ビルド時の挙動:** `tags` に `アフィリエイト` があり **ASP URL が無い行は HTML を生成しない**（試験ガイド一覧にも出ない）。

---

## 6. 紹介対象の種類（書籍・講座）

アフィリエイト記事は **書籍（Amazon）** と **講座・サービス（A8 / afb 等）** の両方を扱う。  
brief の `comparison_kind` と各 `products[].offer_type` で UI・比較表・リンク先を切り替える。

| 種別 | `comparison_kind` | `offer_type` | 主 ASP | 比較表の主な列 |
|------|-------------------|--------------|--------|----------------|
| テキスト・問題集 | `books` | `book`（省略可） | Amazon | 価格・ページ数 |
| オンライン講座・通信・予備校 | `courses` | `course` | A8 / afb / 公式 ASP | 料金・学習期間 |

### brief フィールド（書籍）

| フィールド | 用途 |
|------------|------|
| `name`, `publisher`, `edition` | 商品名・出版社・版 |
| `price_yen`, `price_note`, `pages`, `format` | 価格・仕様 |
| `asin`, `amazon_url`, `image_file` | Amazon リンク・表紙 |
| `workbook_name`, `workbook_amazon_url`, `workbook_image_file` | セット問題集（任意） |
| `for_who`, `highlights` | 比較表・カード |

### brief フィールド（講座）

| フィールド | 用途 |
|------------|------|
| `name`, `provider` | 講座名・提供会社 |
| `price_yen`, `billing_type` (`monthly` / `lump`), `price_label` | 料金（複雑な表記は `price_label`） |
| `duration`, `lecture_hours`, `support` | 期間・学習量・サポート |
| `a8_url`, `affiliate_url`, `afb_url` | ASP リンク（いずれか必須） |
| `trial_label`, `trial_url` | 無料体験など（カード下部・本文リンク） |
| `image_file`, `image_url` | サムネイル（LP の og:image 取得可） |
| `for_who`, `highlights` | 比較表・カード |

**混在:** 1記事に書籍と講座を混在させることも可能だが、検索意図がブレやすいので **原則は `comparison_kind` ごとに1記事**。

### 完成テンプレ

| テンプレ | 用途 |
|----------|------|
| [affiliate-textbooks-recommend](./templates/affiliate-textbooks-recommend/) | おすすめテキスト比較 |
| [affiliate-online-course-compare](./templates/affiliate-online-course-compare/) | オンライン講座比較 |

```bash
python3 tools/apply_affiliate_article_template.py --template affiliate-textbooks-recommend
python3 tools/apply_affiliate_article_template.py --template affiliate-online-course-compare
```

---

## 7. 表紙・商品画像

- **SVG プレースホルダー禁止**。自サイト `images/affiliate/` にホスト
- 画像が無い間は CSS プレースホルダー（出版社名 / 提供元・商品名・年度）
- 命名: `{資格略称}-{商品略称}-{年度}.webp`（問題集は `-workbook-`、講座は `-course-` 等）

| 種別 | 推奨比率 | 取得元 |
|------|----------|--------|
| 書籍 | 約 5:7（縦長） | Amazon ASIN / 商品 URL |
| 講座 | 16:9（横長） | 公式 LP の og:image（`fetch_affiliate_product_images.py`） |

- 推奨幅: 320px 前後
- `amzn.to` は **商品リンク用**。画像 URL として使えないことが多い

---

## 8. ページ構成（商品比較型 `product-comparison`）

`layout: product-comparison` の brief があるアフィリエイト記事の **完成形レイアウト**。

| # | ブロック | データ源 |
|---|----------|----------|
| 1 | タイトル・メタ・リード | CSV |
| 2 | **この記事の要点** | `user_intent` + brief 商品名 + 任意 `key_points` |
| 3 | 目次 | ビルド自動 |
| 4 | 信頼性パネル | CSV / site-config |
| 5 | **section 1: 選び方の基準** | CSV `section_1_*`（例: テキスト選びの3つのポイント） |
| 6 | **商品比較 hub**（比較表 + 商品カード） | brief → **section 1 の直後**に自動挿入 |
| 7 | section 2〜: 各商品詳細・組み合わせ方など | CSV |
| 8 | FAQ | CSV |
| 9 | 記事基本情報・公式情報 | CSV |
| 10 | 関連記事（非アフィリ3 + アフィリ3） | CSV `related_links` |

### 使わないもの

| 項目 | 理由 |
|------|------|
| **「この記事でわかること」section** | 要点ボックスに統合。CSV に残っていても **ビルド時スキップ**（本文・目次・セクション番号から除外） |
| **「この記事でできること」独立ブロック** | 一般ガイドと同様、要点ボックスへ統合済み |
| ヒーロー（上位 N 件バナー） | 要点右端の1位表紙 + hub で代替 |

新規テンプレ（`guide-row.yaml`）では **section 1 を選び方基準から始める**。`この記事でわかること` 見出しは書かない。

---

## 8.1 この記事の要点（アフィリエイト + product-comparison）

ビルド: `tools/affiliate_product_ui.py` → `affiliate_key_points_box_html()`  
CSS: `.seo-key-points-box--affiliate`, `.seo-key-points-aside`（右下配置）

| 要素 | ルール |
|------|--------|
| 見出し | 「この記事の要点」（固定） |
| イントロ | CSV `user_intent` |
| リスト先頭 | brief `products[].name` を **フルネームで上位3件**（`affiliate_product_key_points()`） |
| リスト追加分 | CSV `key_points`（`;` 区切り、**最大2件推奨**）。商品名と重複・「この記事でわかること」は除外 |
| 右端表紙 | **1位商品**（`products[0]`）のみ。表紙下に **商品名・講座名ラベル** |
| 表紙下ラベル | ASP リンク（表紙＋名称を1リンク）。**黒文字・黒下線・最大2行**（`.seo-key-points-aside-label`） |
| レイアウト | 左: テキストリスト / **右下**: 表紙1枚 + 名称ラベル（列幅 `clamp(5rem, 20%, 7rem)`） |

**CSV `key_points` 例**（書籍比較）:

```text
選び方の基準;過去問との併用
```

**brief `products[].name` 例**（要点リスト先頭3件になる）:

```text
【2026年度版 ◯◯試験 完全攻略テキスト】;【2026 ◯◯試験 要点整理テキスト】;【2026 ◯◯試験 イラストで理解するテキスト】
```

`key_points` / `action_items` が無くても brief 商品名があれば要点ボックスは生成される。

---

## 8.2 商品名・講座名の表記（ビルド時自動）

ビルド: `tools/affiliate_body_links.py`

| 処理 | 内容 |
|------|------|
| **対象テキスト** | リード、各 section 本文、FAQ（質問は括るのみ / 回答は括り + リンク） |
| **括る対象** | brief の `name` / `workbook_name` / `trial_label` + 講座定型名（`AFFILIATE_COURSE_NAMES`、サイト固有はコード側に追加） |
| **形式** | 「商品名」 |
| **リンク化** | 括った後 `[「商品名」](asp_url)`（`【】` / `『』` 表記もリンク対象） |
| **除外** | 既に `「」『』【】` 内、Markdown リンク内、**比較表・要点表紙ラベル・商品カード内の名称**（構造化 HTML で別途リンク化） |

CSV 本文には商品名を **括弧なし** で書いてよい。ビルド時に統一される。

---

## 8.3 商品比較 hub

| 項目 | 値 |
|------|-----|
| 挿入位置 | **section 1 の直後**（`affiliate_hub_after_section=1`） |
| 目次 | hub 見出しを section 1 の次に追加（`affiliate_hub_toc_item()`） |
| 前提 | brief に `layout: product-comparison` |

`comparison_kind` に応じて比較表の列・CTA 文言（「Amazonで見る」/「公式サイトで見る」）が切り替わる。  
表紙・サムネは `fetch_affiliate_product_images.py` で `images/affiliate/` に取得。

### 比較表（書籍・講座共通）

| 項目 | 仕様 |
|------|------|
| 商品名 / 講座名列 | brief `products[].name` を **ASP テキストリンク**（`.affiliate-compare-name-link`） |
| リンク色 | **黒文字**（`var(--seo-text-title)`） |
| 下線 | **黒下線**（薄い青リンクスタイルは使わない） |
| 生成 | `affiliate_product_ui.py` → `product_name_link_html()` |

### 書籍カード UI（`comparison_kind: books`）

| 項目 | 仕様 |
|------|------|
| グリッド | **縦1列**（全幅カード、`data-comparison-kind="books"`） |
| カード内 | 表紙左・本文右（480px 以下は縦積み） |
| 表紙幅 | `clamp(7.5rem, 22%, 9.5rem)`、`max-height: 10.5rem` |
| カード meta | **価格のみ**（ページ数・判型は比較表側） |
| 問題集 | カード下部 supplement リンク（`workbook_name` + `workbook_amazon_url`） |

### 講座カード UI（`comparison_kind: courses`）

| 項目 | 仕様 |
|------|------|
| 比較表 | 上記「比較表（書籍・講座共通）」 |
| 商品カード grid | 961px〜3列 / 761〜960px 2列 / 760px以下 1列。**2商品は `data-product-count="2"` で2列** |
| CTA | 「公式サイトで見る」 |
| 要点右端 | 16:9 サムネ（`.seo-key-points-aside-cover--course`）+ **表紙下ラベル（黒下線・最大2行）** |

### レスポンシブ（講座・汎用 grid）

| 幅 | 商品カード grid |
|----|-----------------|
| 961px〜 | 3列 |
| 761〜960px | 2列 |
| 760px以下 | 1列。比較表は非表示（カードで代替） |

書籍 hub は常に **1列**（上記 grid ルールより優先）。

### CSS キャッシュ

`seo-editorial.css` を変更したら `tools/seo_editorial_chrome.py` の `SEO_EDITORIAL_CSS_VER` を更新する（例: `20260603-affiliate-aside-label`）。

---

## 8.4 アフィリエイト用バナー（一覧・記事内）

アフィリエイト導線の「バナー」は次の3か所に限定する。記事トップの大型ヒーローは使わない（§8）。

| 種別 | ページ | 設定 |
|------|--------|------|
| **一覧カード（3ハブ共通）** | `articles/index.html`・`terms/index.html`・`q/index.html` | `site-config.json` → `guideIndexPicks`（3枚） |
| **要点右端サムネ** | 各 `affiliate-*` 記事 | brief 1位商品 → `affiliate_key_points_box_html()` |
| **比較 hub カード** | 各 `affiliate-*` 記事 | brief 全商品 → `affiliate_product_hub_html()` |

### guideIndexPicks（一覧バナー）

- 試験ガイド・用語解説・過去問一覧の **3ページで同一内容**（`tools/guide_index_picks_ui.py`）
- 講座・テキスト・問題集の **3 item**。`href` は公開済みアフィリエイト slug（試験ガイド基準で `affiliate-…/`。用語・過去問一覧ではビルド時に `../articles/` を付与）
- 各 item に `image`（`images/affiliate/…`）と `imageAlt` を必須。brief と同じ webp を再利用してよい
- `kind` / `kindLabel` / `cta` はカード右下ラベル・左下ボタンに反映（`site-pages.css` の `.hub-promo-*` / `.article-index-pick-*`）
- **`layout`**（任意・既定 `grid-3`）: `grid-3`（3列）| `grid-2`（2列・最大2件）| `strip`（横長帯）| `compact`（画像小）| `text`（画像なし・内部導線）
- 画像取得は §7 と同じ `fetch_affiliate_product_images.py`。**webp はリポジトリにコミット**（CI が `build_all` で再生成するため）

### 記事内サムネ

- 比較 hub・要点右端は **brief の `image_file`** を `images/affiliate/` から解決（`affiliate_product_ui.image_href`）
- ローカルに無い場合は brief の `image_url`（外部 URL）にフォールバック可。本番は自サイトホストを推奨

### ビルド退行の防止

`tools/build_article_pages.py` から `affiliate_product_*` / `load_affiliate_brief` / `build_guide_index_picks_html` を削除しない。  
テンプレ同期後は `build_article_pages.py` を実行し、生成 HTML に `affiliate-product-hub` と `images/affiliate/` が含まれることを確認する。

Cursor 要約: `.cursor/rules/affiliate-banner.mdc`

---

## 9. 関連リンク・収益導線

**設置箇所の全体像:** [placement-and-rollout.md](./placement-and-rollout.md)

### 収益の本丸

```
通常ガイド → affiliate-* 比較記事 → ASP（Amazon / A8 / afb）
```

- **比較記事だけ** が ASP 直リンクを載せる
- **通常ガイド** は `related_links` と本文 slug で比較記事へ送る（ASP 直リンク禁止）
- 1 通常ガイドあたり比較記事への内部リンクは **1〜2 本**

### 比較記事の `related_links`（末尾ボックス）

```text
self-study-roadmap:独学の進め方
study-plan:学習計画の立て方
../../q/index.html:過去問を解く（無料）
affiliate-problem-books:おすすめ問題集3選
affiliate-mock-exam-materials:模試教材の選び方
affiliate-correspondence-course:通信講座の比較
https://px.a8.net/...:SMART合格講座（公式）
```

- 内部: 同 CSV に存在する slug のみ
- 表示順: **非アフィリ3 → アフィリ3**（計6件）。ASP `https://` 行は関連ボックスに出さない
- フッター一括貼り付けはしない

### 通常ガイドの `related_links`（末尾ボックス）

```text
affiliate-textbooks-recommend:おすすめテキスト3選【2026年度版・独学】
past-question-strategy:過去問の回し方
```

- 比較記事 slug は **1〜2 本**。残りは通常ガイド・演習・用語へ
- 本文 `section_*_body` に `affiliate-*` slug を **1文** 挿入可（ビルド時に内部リンク化）

### 送り先の選び方

| 通常ガイドの意図 | 比較記事 slug 例 |
|------------------|------------------|
| 独学・教材・学習計画 | `affiliate-textbooks-recommend` |
| 過去問・分野攻略 | `affiliate-problem-books` |
| 社会人・通信 | `affiliate-correspondence-course` |
| 模試・直前 | `affiliate-mock-exam-materials` |

合格率・合格後手続き・年収・会場案内・他資格制度比較のみの記事は **繋がない**

---

## 10. 標準10 slug の配分

[guide-article-catalog.md](../guide-article-catalog.md) を参照。資格に不要な行（申込支援サービスがない等）は省略し、別テーマで10本に届ける。

| タイプ | 主な ASP | brief |
|--------|----------|-------|
| テキスト・問題集 | Amazon | `comparison_kind: books` |
| オンライン講座・通信・予備校 | A8 / afb | `comparison_kind: courses` |
| 模試・直前 | Amazon + A8 | 混在可（要検索意図整理） |
| 無料 vs 有料 | A8 / afb / Amazon（URL 確定後） | brief 必須 |

---

## 11. 公開前チェックリスト

### 必須

- [ ] ASP / 商品 URL が related_links・本文・brief のいずれかに **実 URL** で入っている
- [ ] **各商品の価格を ASP / 公式 URL で確認**し、brief・本文・比較表が一致している
- [ ] **本文がオリジナル執筆**（テンプレ置換・他記事流用・機械的量産文でない）
- [ ] `content_status=published`
- [ ] `tags` に `アフィリエイト`
- [ ] `genre` が許可リスト内
- [ ] `related_links` に内部 slug **2件以上**
- [ ] 公開本文・表に `【PR・広告】` がない
- [ ] ASP と公式 URL を混同していない
- [ ] `python3 tools/validate_csv.py` がエラーなし
- [ ] `python3 tools/build_article_pages.py` 後、当該 slug の HTML が生成されている

### 商品比較 UI がある場合

- [ ] **「この記事でわかること」section が無い**（あってもビルドで非表示になるが、新規は書かない）
- [ ] 要点ボックスに brief 商品名3件 + 右下1位表紙 **+ 表紙下名称（黒下線・最大2行）**
- [ ] 比較 hub が **section 1（選び方）の直後** にある
- [ ] 比較表の **商品名・講座名が ASP 黒テキストリンク（黒下線）** になっている
- [ ] 要点リスト内リンク（青）と表紙下ラベル（黒）が混在してもスタイルが崩れない
- [ ] 本文・FAQ の商品名が「」括り + ASP リンクになっている
- [ ] 表紙・サムネが自サイトパスで表示（404 なし）
- [ ] スマホでカードが選べる
- [ ] **書籍:** テキスト用・問題集用 URL の取り違えなし
- [ ] **講座:** `a8_url` / `affiliate_url` が実 ASP、`billing_type` と本文の料金表記が一致
- [ ] `comparison_kind` と `offer_type` が記事の検索意図と一致

---

## 12. ツール一覧

| ツール | 用途 |
|--------|------|
| `scaffold_affiliate_article.py` | ブリーフ + CSV 行生成（`--append` は URL 必須） |
| `affiliate_links.py` | ASP リンク有無の判定（ビルド・validate 共通） |
| `draft_unlinked_affiliate_articles.py` | 未リンク行を `draft` に一括変更 |
| `strip_affiliate_pr_disclaimer.py` | PR 定型文を CSV から除去 |
| `validate_csv.py` | 本数・リンク・genre 検査 |
| `build_article_pages.py` | 記事 HTML 生成（要点・hub 挿入位置・skip section） |
| `affiliate_body_links.py` | 商品名「」括り + 本文 ASP リンク自動化 |
| `affiliate_product_ui.py` | 商品カード・比較表・要点右端表紙 |
| `fetch_affiliate_product_images.py` | Amazon 表紙・講座 LP サムネを `images/affiliate/` に取得 |
| `build_affiliate_template_preview.py` | テンプレ HTML プレビュー |
| `apply_affiliate_article_template.py` | テンプレ YAML → CSV 反映 |

---

## 13. サイト固有メモ（任意）

資格ごとに `sites/<site-id>/SITE.md` または `docs/affiliate/SITE.md` を置く。  
雛形: [SITE.template.md](./SITE.template.md)。展開手順: [placement-and-rollout.md](./placement-and-rollout.md) §6・§9。

| 項目 | 例 |
|------|-----|
| ドメイン | `https://example.jp/` |
| 公開済み `affiliate-*` slug | 本数・ASP・備考 |
| `guideIndexPicks` | layout・3 item の slug |
| 通常ガイド導線 | related_links 済 N 本 / 全 M 本 |
| 画像 | `images/affiliate/` |

---

## 14. 他サイトへの展開（要約）

1. `sync_from_template.py --target ~/Projects/<資格サイト>` でエンジン同期
2. サイト固有: `guide_articles.csv`・`affiliate-briefs/`・`images/affiliate/`・`site-config.json` の `guideIndexPicks`
3. 比較記事 1 本公開 → 一覧カード設定 → 学習系ガイドに導線 → `build_all.py` → デプロイ

詳細チェックリスト: [placement-and-rollout.md](./placement-and-rollout.md)

---

*最終更新: 2026-06-14（設置箇所・導線・マルチサイト展開を placement-and-rollout に分離）*
