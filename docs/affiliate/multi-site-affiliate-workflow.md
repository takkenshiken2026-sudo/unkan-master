# マルチサイト・アフィリエイト実装手順（ミス防止版）

資格サイトごとに **同じ導線・同じ UI** を再現するための作業手順。  
設計の正本: [placement-and-rollout.md](./placement-and-rollout.md) · 執筆: [affiliate-article-rules.md](./affiliate-article-rules.md)

**原則:** 各フェーズの **ゲート（検証）を通過するまで次に進まない**。1サイトずつ完了させてから次サイトへ。

---

## 0. 全体像

```
フェーズA  現状把握（サイトごと）
フェーズB  エンジン同期（テンプレ → 本番）
フェーズC  比較記事 1本目（パイロット）
フェーズD  guideIndexPicks（3ハブ・3枚）
フェーズE  通常ガイド導線（related_links + 本文）
フェーズF  比較記事 2〜4本 + 相互リンク
フェーズG  本番デプロイ + 目視確認
```

収益導線（全サイト共通）:

```
通常ガイド → affiliate-* 比較記事 → ASP
```

---

## 1. サイト選定と優先順位

[site-registry.md](../site-registry.md) の **1サイト = 1ロールアウト単位**。

| 優先 | サイト | 理由 |
|------|--------|------|
| 参照完了 | `takken-master` | 4本公開・導線・3枚カード済み（お手本） |
| 高 | `eisei1shu-master` | 比較記事2〜3本あり。**guideIndexPicks 未設定** |
| 中 | その他8サイト | draft placeholder のみが多い |

**同時に2サイト以上のフェーズC以降を進めない**（ASP・価格・slug の取り違え防止）。

---

## 2. フェーズA — 現状把握（サイトごと・30分）

### A-1. パス確認

```bash
SITE=~/Projects/eisei1shu-master   # 例
cd ~/Projects/exam-site-shell
python3 tools/check_template_drift.py --target "$SITE"
```

- drift が大きい場合は先に [multi-site-workflow.md](../multi-site-workflow.md) の通常同期を検討
- `takken-master` は `sites/takken-master/manifest-phase*.txt` で段階同期

### A-2. アフィリエイト棚卸し

本番リポジトリで実行:

```bash
cd "$SITE"

# 比較記事行（published / draft）— utf-8-sig で BOM 付き CSV に対応
python3 - <<'PY'
import csv
from pathlib import Path
from tools.affiliate_links import affiliate_external_links_in_row, is_affiliate_article

text = Path("data/guide_articles.csv").read_text(encoding="utf-8-sig")
rows = list(csv.DictReader(text.splitlines()))
for r in rows:
    if not is_affiliate_article(r):
        continue
    asp = "ASPあり" if affiliate_external_links_in_row(r) else "ASPなし"
    print(f"{r['slug']:40} {r.get('content_status',''):10} {asp}")
PY

# brief 数
ls -1 data/affiliate-briefs/*.yaml 2>/dev/null | wc -l

# 画像
ls -1 images/affiliate/*.webp 2>/dev/null | wc -l

# guideIndexPicks の有無
python3 -c "import json; c=json.load(open('site-config.json')); print('guideIndexPicks:', 'items' in (c.get('guideIndexPicks') or {}))"
```

### A-3. 運用メモ作成

```bash
cp docs/affiliate/SITE.template.md "$SITE/docs/affiliate/SITE.md"
# または sites/<site-id>/SITE.md にアフィリエイト節を追記
```

棚卸し結果を `SITE.md` に記入（公開済み slug・ASP・guideIndexPicks 有無・導線本数）。

### A-4. ゲート（次へ進む条件）

- [ ] 本番パス・デプロイ方式を把握した
- [ ] 公開済み `affiliate-*` の一覧を書いた
- [ ] `guideIndexPicks` の有無を確認した
- [ ] **やることリスト**（パイロット slug・ASP 案件）が決まった

---

## 3. フェーズB — エンジン同期

テンプレ root で実行:

```bash
cd ~/Projects/exam-site-shell
python3 tools/sync_from_template.py --target "$SITE" --dry-run
python3 tools/sync_from_template.py --target "$SITE" --build
```

### 同期される主なもの

`tools/template_sync_manifest.txt` より:

- `tools/affiliate_*.py`, `guide_index_picks_ui.py`, `guide_slug_prose.py`
- `tools/build_article_pages.py` 他ビルド一式
- `docs/affiliate/` 一式
- `site-pages.css`, `seo-editorial.css`

### 同期されないもの（本番のまま）

- `site-config.json`
- `data/guide_articles.csv`, `data/affiliate-briefs/`
- `images/affiliate/`
- `q/`, `articles/`, `terms/`（`--build` で再生成）

### B ゲート

```bash
cd "$SITE"
test -f tools/affiliate_links.py && test -f tools/guide_index_picks_ui.py
python3 tools/build_all.py
```

- [ ] `build_all.py` が **エラーなし**で完走
- [ ] `validate_internal_links.py` エラーなし
- [ ] 既存公開ページが壊れていない（diff をざっと確認）

**ここではまだ push しなくてよい**（フェーズC〜F とまとめてでも可）。

---

## 4. フェーズC — 比較記事 1本目（パイロット）

**最初の1本は必ずどちらか一方から:**

| 順番 | slug | ASP | 向いている試験 |
|------|------|-----|----------------|
| 推奨1 | `affiliate-textbooks-recommend` | Amazon | 参考書市場が明確 |
| 推奨2 | `affiliate-online-course-compare` | A8 / afb | 講座案件が先に決まっている |

### C-1. ASP・商品確定（執筆前）

- [ ] 各商品の **販売ページ URL** が確定（プレースホルダー禁止）
- [ ] 各 URL を開き **価格・版・料金体系** をメモ（`fact_checked_at` 用）
- [ ] Amazon トラッキング ID / A8 プログラム ID を `original_note` に記録（公開しない）

### C-2. brief 作成

```bash
cd "$SITE"
mkdir -p data/affiliate-briefs images/affiliate

# 書籍
cp ~/Projects/exam-site-shell/docs/affiliate/templates/affiliate-textbooks-recommend/brief.yaml \
   data/affiliate-briefs/affiliate-textbooks-recommend.yaml
# 講座の場合は affiliate-online-course-compare のテンプレをコピー

# 資格名・商品名・URL・price_yen を編集
```

### C-3. CSV 行（draft 行の上書き or 新規）

**ミス防止:**

- 既存の **draft プレースホルダー行** がある場合は **その行をリライト**（新 slug を増やさない）
- `content_status` は **ASP 確定まで `draft`**
- `tags` に `アフィリエイト` を含める
- `layout: product-comparison` は brief 側で指定（scaffold 利用時は自動）

```bash
# URL 確定後のみ append 可
python3 tools/scaffold_affiliate_article.py \
  --from-brief data/affiliate-briefs/affiliate-textbooks-recommend.yaml \
  --append   # 行が無いときのみ
```

### C-4. オリジナル執筆（必須）

- [ ] テンプレ置換だけでない **記事固有の本文**
- [ ] section 1 = 選び方基準（「この記事でわかること」は書かない）
- [ ] 各商品の強み弱みが **3パターン区別できる**
- [ ] `related_links`: 非アフィリ3 + アフィリ3（他比較記事は未公開なら通常ガイドで埋める）

### C-5. 画像

```bash
python3 tools/fetch_affiliate_product_images.py --slug affiliate-textbooks-recommend
ls images/affiliate/   # webp が実在すること
git add images/affiliate/
```

### C-6. 公開

1. `content_status=published` に変更
2. ビルド・検証:

```bash
python3 tools/validate_csv.py
python3 tools/build_article_pages.py
```

3. 生成 HTML 確認:

```bash
SLUG=affiliate-textbooks-recommend
grep -E 'affiliate-product-hub|images/affiliate/' "articles/$SLUG/index.html" | head
```

### C ゲート

- [ ] `articles/<slug>/index.html` が生成されている
- [ ] 比較 hub・要点右端表紙が **404 なし**
- [ ] 本文・表に `【PR・広告】` がない
- [ ] 通常ガイド本文に **ASP URL が無い**
- [ ] 価格が brief と本文で一致

---

## 5. フェーズD — guideIndexPicks（3ハブ・3枚）

**前提:** フェーズCで **公開済み比較記事が1本以上**。

### D-1. `site-config.json` 編集

**よくあるミス:** テンプレ既定は `textbook-selection/` 等の **通常ガイド** を指している。  
本番では必ず **`affiliate-*` slug** を指す。

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
  "items": [
    {
      "kind": "course",
      "kindLabel": "講座",
      "title": "（比較記事タイトル短縮）",
      "description": "（1〜2文）",
      "href": "affiliate-correspondence-course/",
      "cta": "比較記事を読む",
      "image": "images/affiliate/xxx-course.webp",
      "imageAlt": "（講座名）"
    },
    {
      "kind": "textbook",
      "kindLabel": "テキスト",
      "title": "…",
      "href": "affiliate-textbooks-recommend/",
      "cta": "比較記事を読む",
      "image": "images/affiliate/xxx-book.webp",
      "imageAlt": "（テキスト名）"
    },
    {
      "kind": "problem-book",
      "kindLabel": "問題集",
      "title": "…",
      "href": "affiliate-problem-books/",
      "cta": "比較記事を読む",
      "image": "images/affiliate/xxx-workbook.webp",
      "imageAlt": "（問題集名）"
    }
  ]
}
```

**未公開 slug のカードは置かない。** 公開1本だけの間は:

- 公開済み1枚 + 残り2枚は **同じ記事を一時的に使わない**（3枚そろうまで2枚のみ等は UI 崩れのため不可）
- **実務:** 最低2本（テキスト+講座 or テキスト+問題集）公開してから3枚出すのが安全

### D-2. 3ハブ再生成

```bash
python3 tools/build_article_pages.py
python3 tools/build_glossary_pages.py
python3 tools/build_past_question_pages.py
```

### D ゲート

3ファイルすべてで確認:

```bash
for f in articles/index.html terms/index.html q/index.html; do
  echo "=== $f ==="
  grep -c 'hub-promo\|article-index-pick' "$f" || true
done
```

- [ ] `/articles/`・`/terms/`・`/q/` の index に **同じ3枚**（または公開本数に応じた枚数）
- [ ] カード `href` が **比較記事**（ASP 直リンクではない）
- [ ] `image` が実ファイルを指す
- [ ] トップ `index.html` には **出ていない**

---

## 6. フェーズE — 通常ガイド導線

**1記事あたり:** `related_links` に比較記事 **1〜2本** + 本文に slug **1文**。

### E-1. 送り先マッピング（検索意図）

| 通常ガイドのジャンル・テーマ | 送る比較記事 |
|------------------------------|--------------|
| 独学・教材選び・テキスト | `affiliate-textbooks-recommend` |
| 問題集・演習量・過去問活用 | `affiliate-problem-books` |
| 通信・社会人・学習スタイル | `affiliate-correspondence-course` / `affiliate-online-course-compare` |
| 模試・直前・時間配分 | `affiliate-mock-exam-materials` |

### E-2. 繋がない記事（意図的除外）

- 合格率の読み方、合格後手続き、年収、会場案内
- 他資格との制度比較のみ（`compare-similar-qualifications` 等）
- 純粋なキャリア・制度説明

### E-3. `related_links` 記法

```text
affiliate-textbooks-recommend:おすすめテキスト3選【2026年度版・独学】
past-question-strategy:過去問の回し方
```

### E-4. 本文 slug 記法

`section_*_body` に1文（括弧・URL 不要）:

```text
テキスト1冊は、affiliate-textbooks-recommend で出版社別の解説量を比較してから固定すると途中で変えずに済みます。
```

### E-5. 進め方（ミス防止）

1. **10本ずつ** CSV を編集（一括50本は slug 取り違えやすい）
2. 毎バッチ `validate_csv.py` → `build_article_pages.py`
3. `SITE.md` の「導線済み本数」を更新

優先して繋ぐガイド（各サイトで slug 名は異なるがジャンルは共通）:

- 独学ロードマップ / 学習計画 / テキスト選び / 問題集選び
- 過去問の回し方 / 分野別対策 / 独学の注意点
- 仕事との両立 / 通信・オンライン学習

### E ゲート

```bash
python3 tools/validate_csv.py
python3 tools/validate_internal_links.py
```

- [ ] 通常ガイドに `https://amazon` / `px.a8.net` 等が **本文に無い**
- [ ] `related_links` の比較記事 slug が **すべて CSV に存在**
- [ ] 学習系ガイドの **半数前後** が比較記事へ1本以上接続（目標）

---

## 7. フェーズF — 比較記事 2〜4本 + 相互リンク

### 推奨順序

```
1. affiliate-textbooks-recommend   （Cで実施済み）
2. affiliate-problem-books
3. affiliate-online-course-compare または affiliate-correspondence-course
4. affiliate-mock-exam-materials
```

各本は **フェーズCと同じ手順**（brief → 執筆 → 画像 → published）。

### 相互 `related_links`（4本そろったら）

各 `affiliate-*` の末尾:

- 非アフィリエイト3（独学・過去問・用語/演習）
- アフィリエイト3（他の3比較記事）
- ASP URL 行（関連ボックスには表示されないが brief 用に残す）

### F ゲート

- [ ] 公開比較記事が **4本**（またはサイト方針の本数）
- [ ] 4本間の相互リンクがそろっている
- [ ] `guideIndexPicks` の3 `href` が **すべて公開済み**

---

## 8. フェーズG — デプロイ・目視確認

### G-1. 最終ビルド

```bash
cd "$SITE"
python3 tools/build_all.py
```

### G-2. チェックリスト（公開前）

**比較記事**

- [ ] ASP URL・価格・画像が正しい
- [ ] 要点・hub・比較表のリンクが機能

**導線**

- [ ] 通常ガイド → 比較記事 → ASP の流れが1本通せる
- [ ] フッターに比較記事一括リンクが **ない**

**3ハブ**

- [ ] `articles/` `terms/` `q/` index にカード3枚・grid-3

**CI**

- [ ] `validate_csv.py` / `validate_generated_seo.py` / `validate_site_integration.py` / `validate_internal_links.py` すべて成功

### G-3. push・反映待ち

```bash
git add -A
git status   # site-config.json, data/, images/affiliate/, articles/ 等
git commit -m "…"
git push origin main
```

- GitHub Actions 完了まで **5〜7分** 待つ
- 本番は **スーパーリロード** でキャッシュ回避

### G-4. 本番目視（最低3 URL）

1. `/articles/affiliate-textbooks-recommend/` — hub・ASP
2. `/articles/` — 上部3枚 + 一覧に比較記事カード
3. 通常ガイド1本 — 関連記事ボックス + 本文リンク

---

## 9. よくあるミスと防止策

| ミス | 防止策 |
|------|--------|
| ASP 未確定で `published` | C-1 ゲート。`scaffold --append` は URL 必須 |
| テンプレ本文のまま公開 | 執筆チェックリスト（§11 affiliate-article-rules） |
| `guideIndexPicks` が通常ガイドを指す | D-1。必ず `affiliate-*` + `image` |
| 未公開 slug をカードに入れる | 公開済みのみ。3枚未満ならカード導入を遅らせる |
| 通常ガイドに Amazon URL | 本文・related_links を grep 禁止 |
| 画像未コミットで CI 404 | `images/affiliate/*.webp` を必ず git add |
| sync で `site-config` 上書き | `template_site_only.paths` — 本番 JSON は手編集のみ |
| 複数サイト同時で slug 取り違え | **1サイトずつ** フェーズC以降 |
| brief にだけ ASP があり CSV に無い | `affiliate_article_is_buildable()` は **CSV の https のみ** 判定。brief だけでは HTML 非生成 |
| 価格の転記ミス | 公開直前に ASP ページを開いて再確認 |
| build 退行で hub 消える | sync 後 `grep affiliate-product-hub articles/affiliate-*/index.html` |

---

## 10. サイト別ロールアウト記録

完了したら `docs/affiliate/SITE.md`（本番側）を更新:

| 項目 | 完了日 | 備考 |
|------|--------|------|
| フェーズB 同期 | | |
| 比較記事1本目 | | slug |
| guideIndexPicks | | |
| 導線 N 本 | | |
| 比較記事4本 | | |
| 本番確認 | | URL |

テンプレ側 `sites/<site-id>/SITE.md` にも「アフィリエイト展開済み」とリンクを残すと横断管理しやすい。

---

## 11. 参照

| 文書 | 用途 |
|------|------|
| [placement-and-rollout.md](./placement-and-rollout.md) | 設置箇所・設計 |
| [affiliate-article-rules.md](./affiliate-article-rules.md) | 執筆・UI |
| [auto-create-workflow.md](./auto-create-workflow.md) | CLI 詳細 |
| [multi-site-workflow.md](../multi-site-workflow.md) | テンプレ同期全般 |
| [integration-checklist.md](../integration-checklist.md) | フッター・q・用語の横断検証 |
| [guide-article-catalog.md](../guide-article-catalog.md) | 標準10 slug |

---

*最終更新: 2026-06-14*
