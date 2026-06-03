# マルチサイト アフィリエイト記事運用

資格サイトごとにアフィリエイト記事を **新規作成・リライト・公開** するときの手順。  
**正本は exam-site-shell**（ルール・テンプレ・生成ツール・CSS）。

## 読む順番

1. [affiliate-article-rules.md](./affiliate-article-rules.md) — 執筆・UI・チェックリスト
2. 本書 — テンプレ同期・本番反映
3. [auto-create-workflow.md](./auto-create-workflow.md) — scaffold / AI フロー
4. [multi-site-workflow.md](../multi-site-workflow.md) — 共通エンジン同期（一般ガイド）

---

## 1. 正本と本番の役割

| 層 | exam-site-shell | 各本番サイト |
|----|-----------------|--------------|
| ルール・テンプレ | `docs/affiliate/` | **コピーしない**（Cursor は shell 正本を参照） |
| 生成ツール | `tools/affiliate_*.py` 等 | `sync_from_template.py` で同期 |
| CSS | `seo-editorial.css`（affiliate ブロック） | 同上 |
| brief / CSV | サンプルのみ | **`data/affiliate-briefs/` + `guide_articles.csv`** |
| 公開 HTML | プレビュー用 | **`articles/` で生成** |
| 表紙画像 | — | `images/affiliate/` + デプロイ |

**本番サイトの `docs/affiliate/` に旧版フルコピーがある場合**は [PRODUCTION-SITE-STUB.md](./PRODUCTION-SITE-STUB.md) に差し替え、正本へのリンクだけ残す。

---

## 2. テンプレ同期（product-comparison UI を使うサイト）

`tools/template_sync_manifest.txt` にアフィリエイト一式が登録済み。本番へ流す:

```bash
cd ~/Projects/exam-site-shell

python3 tools/check_template_drift.py --target ~/Projects/YOUR-SITE
python3 tools/sync_from_template.py --target ~/Projects/YOUR-SITE --dry-run
python3 tools/sync_from_template.py --target ~/Projects/YOUR-SITE --build
```

同期対象（主要）:

| パス | 用途 |
|------|------|
| `tools/affiliate_product_ui.py` | 比較表・カード・要点表紙 UI |
| `tools/affiliate_body_links.py` | 本文「」+ ASP リンク |
| `tools/affiliate_brief.py` | brief 読込 |
| `tools/affiliate_links.py` | ASP 判定 |
| `tools/fetch_affiliate_product_images.py` | 表紙・サムネ取得 |
| `tools/build_article_pages.py` | hub / 要点 自動挿入 |
| `seo-editorial.css` | カード・黒リンク・2行ラベル |
| `tools/seo_editorial_chrome.py` | CSS キャッシュバージョン |
| `tools/prepare_public_site.sh` | `images/` を public_site へ |
| `.cursor/rules/affiliate-article.mdc` | Cursor 編集ルール |

**同期後の確認:**

```bash
cd ~/Projects/YOUR-SITE
grep -c 'affiliate-compare-name-link' seo-editorial.css   # 1 以上
grep 'affiliate_product_ui' tools/build_article_pages.py    # import あり
bash tools/prepare_public_site.sh
test -d public_site/images/affiliate || echo 'images 未コピー — prepare_public_site を確認'
```

---

## 3. 新規記事（1本）の標準フロー

### 前提

- ASP URL **確定済み**
- 各商品の **最新価格を URL で確認済み**
- `layout: product-comparison` を使う（書籍 `books` / 講座 `courses`）

### 手順

```bash
cd ~/Projects/YOUR-SITE

# 1. brief 作成（shell テンプレをコピーして資格・商品を差し替え）
cp ~/Projects/exam-site-shell/docs/affiliate/templates/affiliate-textbooks-recommend/brief.yaml \
   data/affiliate-briefs/affiliate-YOUR-slug.yaml
# → products.*_url / price_yen / name を実値に。URL 未確定なら CSV 行は作らない

# 2. CSV 行を追加（URL 無しは scaffold がエラー）
python3 tools/scaffold_affiliate_article.py \
  --from-brief data/affiliate-briefs/affiliate-YOUR-slug.yaml \
  --append

# 3. （任意）shell テンプレの section 雛形を CSV に反映 — slug 行が既にあることが前提
python3 tools/apply_affiliate_article_template.py \
  --template affiliate-textbooks-recommend \
  --slug affiliate-YOUR-slug

# 4. オリジナル執筆（テンプレ置換のみで公開しない）
#    guide_articles.csv: section_* / FAQ / user_intent / key_points
#    fact_checked_at（CSV 列）を更新

# 5. 表紙・サムネ
python3 tools/fetch_affiliate_product_images.py --slug affiliate-YOUR-slug

# 6. 公開
# content_status=published
python3 tools/validate_csv.py
python3 tools/build_article_pages.py
bash tools/prepare_public_site.sh
git push origin main
```

**apply と scaffold の順序:** `scaffold --append` で **CSV 行を先に作る**。`apply_affiliate_article_template.py` は **既存行の上書き** のみ（行が無いとエラー）。

---

## 4. リライト（既存公開記事）

```bash
# 1. 各 ASP URL で価格・版・キャンペーンを再確認 → brief / CSV 更新
# 2. fact_checked_at（CSV）を更新
# 3. section 本文をオリジナルで全面見直し（機械文・他記事流用を除去）
# 4. ビルド・デプロイ
python3 tools/validate_csv.py
python3 tools/build_article_pages.py
```

UI 仕様変更（黒リンク・カード等）は **shell 同期 → 全記事 rebuild** で反映:

```bash
python3 tools/build_article_pages.py   # CSS バージョン更新で全 HTML 再生成される
```

---

## 5. サイト固有 bulk スクリプト（任意）

一衛・二衛では `write_eisei1_affiliate_*_articles.py` 等で brief + CSV を一括生成している。

| 用途 | 方針 |
|------|------|
| 初回5〜10本の一括投入 | サイト固有スクリプト可。生成後は **1本ずつオリジナル執筆** で上書き |
| 通常の追加・更新 | **§3 標準フロー**（scaffold + 手執筆）を推奨 |
| 正本への取り込み | bulk スクリプトは shell に置かない。サイト `tools/` に残す |

---

## 6. 公開前チェック（全サイト共通）

[affiliate-article-rules.md §11](./affiliate-article-rules.md#11-公開前チェックリスト) をすべて確認。

特に UI:

- [ ] 比較表の商品名/講座名が **黒テキストリンク**
- [ ] 要点右下: 表紙 + **名称ラベル（黒下線・2行以内）**
- [ ] 商品カード hub が section 1 直後
- [ ] `images/affiliate/` が 404 にならない（prepare_public_site 確認）
- [ ] `seo-editorial.css?v=` が最新（キャッシュ対策）

---

## 7. サイト別 ASP 公開状況（2026-06-03 時点）

| サイト | product-comparison UI | 公開アフィリ本数 |
|--------|----------------------|------------------|
| eisei1shu-master | ✅ 同期済 | 5本（書籍+講座） |
| eisei2shu-master | ✅ 同期済 | 2本（講座） |
| その他 *-master | ❌ 要 sync | 0本（ASP 未設定） |

新規サイトで ASP を設定したら: **§2 同期 → §3 で1本ずつ** 公開。

---

*最終更新: 2026-06-03*
