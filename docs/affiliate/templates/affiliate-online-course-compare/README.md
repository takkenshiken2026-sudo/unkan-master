# テンプレ: affiliate-online-course-compare

**オンライン講座比較** 型アフィリエイト記事テンプレ（A8 / afb 等）。  
書籍テンプレ [affiliate-textbooks-recommend](../affiliate-textbooks-recommend/README.md) と同じ `product-comparison` UI を使用。

## 含まれるファイル

| ファイル | 用途 |
|----------|------|
| [brief.yaml](./brief.yaml) | 講座・ASP URL・`comparison_kind: courses` |
| [guide-row.yaml](./guide-row.yaml) | CSV 1行分 |

## 使い方

```bash
cd ~/Projects/YOUR-SITE

# 1. brief 作成（ASP URL を実値に）
cp ~/Projects/exam-site-shell/docs/affiliate/templates/affiliate-online-course-compare/brief.yaml \
   data/affiliate-briefs/affiliate-online-course-compare.yaml

# 2. CSV 行追加
python3 tools/scaffold_affiliate_article.py \
  --from-brief data/affiliate-briefs/affiliate-online-course-compare.yaml \
  --append

# 3. section 雛形を CSV に反映
python3 tools/apply_affiliate_article_template.py \
  --template affiliate-online-course-compare

# 4. オリジナル執筆 → 画像（任意）→ ビルド
python3 tools/fetch_affiliate_product_images.py --slug affiliate-online-course-compare
python3 tools/validate_csv.py
python3 tools/build_article_pages.py
```

**順序:** scaffold（行作成）→ apply（上書き）→ 手執筆。プレビュー: `build_affiliate_template_preview.py --slug affiliate-online-course-compare`

## ページ構成

書籍テンプレと同じ `product-comparison` UI（[§8](../../affiliate-article-rules.md#8-ページ構成商品比較型-product-comparison)）。

### 自動 UI（ビルド時）

| ブロック | 仕様 |
|----------|------|
| 要点・右下サムネ | 1位講座の 16:9 サムネ + **下に講座名**（ASP リンク・**黒下線・最大2行**） |
| 比較表・講座名列 | brief `name` → **ASP 黒テキストリンク**（`.affiliate-compare-name-link`） |
| 商品カード hub | 2講座は **2列 grid**（`data-product-count="2"`）。760px 以下は1列 |

- 要点: brief 講座名3件 + `key_points` 追加分 + 右下1位サムネ
- 比較 hub: **section 1（選び方）の直後**
- 講座名は本文で括弧なし可 → ビルド時「」+ ASP リンク（青・要点リスト側）

### 執筆ルール（必須）

| 原則 | 内容 |
|------|------|
| **価格** | 各 `a8_url` / `affiliate_url` の **公式 LP** を開き、通常料金・キャンペーン・月額/一括を確認してから brief・本文に記載 |
| **オリジナル執筆** | テンプレ apply 後、**当該資格・各講座の特徴** に沿って section を1つずつ書き直す。他記事の流用禁止 |

詳細: [affiliate-article-rules.md §3](../../affiliate-article-rules.md#執筆の必須原則必ず運用)

## brief の書き方（講座）

| フィールド | 例 |
|------------|-----|
| `comparison_kind` | `courses` |
| `offer_type` | `course`（省略時は comparison_kind から推定） |
| `provider` | SMART合格講座 / オンスク |
| `price_yen` + `billing_type` | `19800` + `lump` または `9800` + `monthly` |
| `price_label` | `月額 ¥9,800〜`（複雑な料金はこちら） |
| `duration` | 受講期間6か月 / 2026年度版 |
| `lecture_hours` | 120 |
| `support` | 質問サポートあり |
| `a8_url` / `affiliate_url` | ASP リンク（必須） |
| `trial_label` + `trial_url` | 無料体験の訴求（任意） |
| `image_file` | `{exam}-smart-course-2026.webp` |

## 差し替えチェックリスト

- [ ] 要点右下: サムネ + **表紙下講座名（黒下線・2行以内）** が表示される
- [ ] 比較表: **講座名が黒テキストリンク** になっている
- [ ] 各 ASP / 公式 URL を開き **最新料金・キャンペーン** を brief / 本文に反映
- [ ] 本文を **記事ごとにオリジナル執筆**（テンプレ置換のみで公開しない）
- [ ] `◯◯試験` → 各サイトの試験名
- [ ] 講座名・提供元・料金を **公式ページと一致**
- [ ] `a8_url` / `affiliate_url` → 実 ASP URL
- [ ] キャンペーン表記は執筆日・`fact_checked_at` と整合
- [ ] 内部 slug（`self-study-roadmap` 等）がサイトに存在する
- [ ] `content_status=published`（URL 確定後のみ）

## ルール

- [affiliate-article-rules.md](../../affiliate-article-rules.md) § 紹介対象の種類
- 講座は **Amazon ではなく A8 / afb / 公式 ASP** が主
