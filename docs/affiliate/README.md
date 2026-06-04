# アフィリエイト記事ドキュメント

資格試験サイト向けアフィリエイト記事の **作成ルール** と **テーマ入力→自動生成** の手順。  
**正本は exam-site-shell**（各本番サイトの `docs/` はスタブ）。

## 読む順番

1. **[affiliate-article-rules.md](./affiliate-article-rules.md)** — いつ作るか・書籍/講座・UI・チェックリスト
2. **[auto-create-workflow.md](./auto-create-workflow.md)** — CLI / AI フロー
3. [seo-article-guidelines.md](../seo-article-guidelines.md) — 識別・法務・本数
4. [guide-article-catalog.md](../guide-article-catalog.md) — 標準10 slug

## 記事テンプレ（完成形）

| テンプレ | 紹介対象 | 主 ASP |
|----------|----------|--------|
| [affiliate-textbooks-recommend](./templates/affiliate-textbooks-recommend/) | おすすめテキスト比較 | Amazon |
| [affiliate-online-course-compare](./templates/affiliate-online-course-compare/) | オンライン講座比較 | A8 / afb |

```bash
# 書籍
python3 tools/apply_affiliate_article_template.py --template affiliate-textbooks-recommend

# 講座
python3 tools/apply_affiliate_article_template.py --template affiliate-online-course-compare
```

`guide-row.yaml`（CSV 1行）と `brief.yaml`（商品・URL・`comparison_kind`）をセットで管理。  
各サイトでは apply 後に資格名・商品・ASP URL を差し替える。

## クイックスタート

```bash
# 1. テーマ一覧
python3 tools/scaffold_affiliate_article.py --list-themes

# 2. brief に ASP URL を入れる（書籍 or 講座テンプレをコピー）
cp docs/affiliate/theme-brief.template.yaml data/affiliate-briefs/affiliate-textbooks-recommend.yaml
# → comparison_kind / products.*_url / related_links を編集

# 3. CSV 追記（URL 無しはエラー）
python3 tools/scaffold_affiliate_article.py \
  --from-brief data/affiliate-briefs/affiliate-textbooks-recommend.yaml \
  --append

# 4. 本文完成 → published → ビルド
python3 tools/validate_csv.py
python3 tools/build_article_pages.py
```

## 覚えておく7点

1. **ASP URL 確定前は記事を作らない**（draft でも HTML 非生成）
2. **価格は必ず ASP / 公式 URL から最新を調査**してから brief・本文に反映（[§3 A](./affiliate-article-rules.md#a-価格は必ず-url-から最新を調査する)）
3. **機械的量産文禁止** — テンプレは雛形のみ。記事ごとにオリジナル執筆（[§3 B](./affiliate-article-rules.md#b-機械的な量産文を書かず記事ごとにオリジナル執筆する)）
4. **`【PR・広告】` は載せない** / `アフィリエイト` タグは表に出さない
5. **リンク済み公開本のみ** 10本目安にカウント
6. **書籍（`books`）と講座（`courses`）** で brief フィールド・ASP が異なる（[§6](./affiliate-article-rules.md#6-紹介対象の種類書籍講座)）
7. **product-comparison 記事**は要点→選び方→比較 hub の順（[§8](./affiliate-article-rules.md#8-ページ構成商品比較型-product-comparison)）。「この記事でわかること」section は使わない
8. **比較表・要点表紙下**の商品名/講座名は **ASP 黒テキストリンク（黒下線）**。要点表紙下ラベルは **最大2行**

## 関連ファイル

| パス | 用途 |
|------|------|
| [theme-brief.template.yaml](./theme-brief.template.yaml) | テーマ入力テンプレ（書籍・講座フィールド例） |
| `data/affiliate-briefs/{slug}.yaml` | 記事ごとのブリーフ |
| `data/guide_articles.csv` | 記事メタ |
| `.cursor/rules/affiliate-article.mdc` | Cursor 編集時のルール |
