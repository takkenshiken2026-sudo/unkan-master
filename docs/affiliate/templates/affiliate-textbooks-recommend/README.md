# テンプレ: affiliate-textbooks-recommend

**おすすめテキスト比較** 型アフィリエイト記事テンプレ。講座比較は [affiliate-online-course-compare](../affiliate-online-course-compare/README.md) を参照。

## 含まれるファイル

| ファイル | 用途 |
|----------|------|
| [brief.yaml](./brief.yaml) | 商品・ASP URL・`comparison_kind: books` |
| [guide-row.yaml](./guide-row.yaml) | CSV 1行分のタイトル・リード・7節・FAQ |

## デザイン確認（プレビュー）

```bash
python3 tools/build_affiliate_template_preview.py
python3 -m http.server 8765
# → http://127.0.0.1:8765/articles/affiliate-textbooks-recommend/
```

`layout: product-comparison` の brief があると **商品カード・比較表・要点 UI** が自動挿入されます（[§8.3](../../affiliate-article-rules.md#83-商品比較-hub)）。

### ページ構成（完成形）

1. 要点（brief 商品名3 + 右下1位表紙 **+ 表紙下名称ラベル**）→ 目次 → 信頼性 → **section1 選び方** → **比較 hub** → 各商品詳細 …
2. **「この記事でわかること」section は使わない**（要点に統合）

### 自動 UI（ビルド時）

| ブロック | 仕様 |
|----------|------|
| 要点・右下表紙 | 1位 `products[0]` の表紙 + **下に商品名**（ASP リンク・**黒下線・最大2行**） |
| 比較表・商品名列 | brief `name` → **ASP 黒テキストリンク**（`.affiliate-compare-name-link`） |
| 商品カード hub | 縦1列。表紙左・本文右。meta は価格のみ |

CSS: `seo-editorial.css`（要点: `.seo-key-points-aside-label` / 比較表: `.affiliate-compare-name-link`）

### 要点用 CSV フィールド

| フィールド | 用途 |
|------------|------|
| `user_intent` | 要点ボックスのイントロ文 |
| `key_points` | 追加分（`;` 区切り、例: `選び方の基準;過去問との併用`）。商品名3件は brief から自動 |

brief の `products[].name` は **フルネーム**（例: `【2026年度版 ◯◯試験 完全攻略テキスト】`）にする。

### 執筆ルール（必須）

| 原則 | 内容 |
|------|------|
| **価格** | 各 `amazon_url` を開き **最新の税込価格** を確認してから `price_yen`・本文に記載。テンプレの数値をそのまま使わない |
| **オリジナル執筆** | `guide-row.yaml` は構成例のみ。apply 後は **当該資格・3冊それぞれ** に合わせて section を1つずつ書き直す |

詳細: [affiliate-article-rules.md §3](../../affiliate-article-rules.md#執筆の必須原則必ず運用)

### 表紙画像の取得

brief に `asin` / `amazon_url` / `image_file` を記入後:

```bash
python3 tools/fetch_affiliate_product_images.py --slug affiliate-textbooks-recommend
```

保存先: `images/affiliate/{image_file}`（自サイトホスト。SVG プレースホルダー禁止）

### 本文中の商品リンク

`layout: product-comparison` の brief に `products.name` / `workbook_name` を書いておくと、
CSV 本文の商品名をビルド時に **「」括り + ASP リンク** へ自動変換します（`affiliate_body_links.py`）。
CSV には括弧なしで書いてよい。手書きする場合は Markdown `[「商品名」](https://amzn.to/xxxx)` も可。

### brief で書く具体情報

| フィールド | 例 |
|------------|-----|
| `price_yen` | 3080 |
| `pages` / `format` / `edition` | 512 / A5判 / 2026年6月改訂 |
| `highlights` | 訴求ポイント（箇条書き3〜4） |
| `for_who` | 比較表の「向いている人」列 |

## 各サイトでの使い方

```bash
cd ~/Projects/YOUR-SITE   # 例: kikenbutsu-master

# 1. テンプレ適用（CSV 本文 + brief を data/ に反映）
python3 tools/apply_affiliate_article_template.py \
  --template affiliate-textbooks-recommend

# 2. 資格名・商品名・公式URLをサイト向けに手直し（brief.yaml も同様）

# 3. Amazon URL 記入後に CSV 追記（行が無い場合のみ）
python3 tools/scaffold_affiliate_article.py \
  --from-brief data/affiliate-briefs/affiliate-textbooks-recommend.yaml \
  --append

# 4. published → ビルド → デプロイ
python3 tools/validate_csv.py
python3 tools/build_article_pages.py
```

## 差し替えチェックリスト

- [ ] 要点右下: 表紙 + **表紙下商品名（黒下線・2行以内）** が表示される
- [ ] 比較表: **商品名が黒テキストリンク** になっている
- [ ] 各 Amazon URL を開き **最新価格・版** を brief / 本文に反映
- [ ] 本文を **記事ごとにオリジナル執筆**（テンプレ置換のみで公開しない）
- [ ] `◯◯試験` → 各サイトの試験名（`site-config.json`）
- [ ] `試験実施団体（公式）` → `primary_sources` の公式名
- [ ] `【テキストA/B/C】` → 実在する教材名
- [ ] `amazon_url` / `related_links` の `https://` → 実 ASP URL
- [ ] `self-study-roadmap` 等の内部 slug → サイトに存在する slug に変更
- [ ] `content_status=published`（URL 確定後のみ）

## ルール

- [affiliate-article-rules.md](../../affiliate-article-rules.md) を参照
- **【PR・広告】は載せない**
- URL 未確定のまま `published` にしない
