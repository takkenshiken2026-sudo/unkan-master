# SEO 記事デザイン・機能 — 全サイト展開テンプレート

**正本リポジトリ:** `exam-site-shell`（Phase 2 テンプレ）  
**最終更新:** 2026-05-30  
**CSS バージョン（最新）:** `20260530-editorial-link-cards`（`tools/seo_editorial_chrome.py` の `SEO_EDITORIAL_CSS_VER`）

他資格サイトへ展開するときは、本ドキュメントの順に **ファイルコピー → ビルド → 目視確認** する。

---

## 1. デザイン仕様（確定）

### タイポグラフィ

| 要素 | サイズ | 備考 |
|------|--------|------|
| H1（`.article-title`） | **24px** | `--seo-fs-h1` |
| H2 本文見出し | clamp（既存） | 番号付き左ライン 3px |
| H3 / 小見出し | **19px** | `--seo-fs-h3` |
| 本文・表 | 16px | Medium 500 |
| **この記事の要点** 見出し | **19px** | 信頼性パネルと同系 callout |
| **関連記事** / 関連ボックス見出し | **19px** | `site-pages.css` より詳細度で上書き |
| FAQ 質問（`summary`） | **19px** | font-weight 700 |

### カラー・パネル

| ブロック | スタイル |
|----------|----------|
| 要点ボックス（`.seo-key-points-box`） | **信頼性パネルと同じ** callout（グレー背景 + 左 4px `--seo-callout-side`）。薄青は使わない |
| 信頼性・行動ボックス | 同上（`--seo-callout-bg`） |
| 目次 | `--seo-toc-bg` グレー系 |

### FAQ

- 形式: `<details class="term-faq-item" open>`（表形式・1列リストは**使わない**）
- 番号: H2「よくある質問」のみ `section-heading-num`。質問行に番号なし
- すべて `open`（初期展開）

### 目次アンカー着地

- `scroll-margin-top: var(--seo-scroll-anchor-offset)`
- 余白（`--seo-scroll-anchor-gutter`）: PC **24〜40px**、タブレット 28px、モバイル 24px
- 知識ハブ（用語・比較等）は `--seo-hub-tabs-sticky-h` を加算

### 内部リンク（デザイン）

| 種別 | 見た目 |
|------|--------|
| **関連記事・知識ハブ・関連用語・過去問**（`.related-link`） | **カード型**: 白背景、左 3px アクセント、右 **→**、ホバーで薄青 + 軽シャドウ + 矢印が右に |
| **目次** | 太字 + アクセント下線、ホバーで薄青ハイライト |
| **本文インライン**（用語自動リンク等） | 青系 + 太字 + 下線（ホバーでアクセント色） |
| **信頼性パネル内参照** | 青 + 下線（カード型にしない） |

---

## 2. 内部リンク（機能）

**モジュール:** `tools/internal_links.py`

| 機能 | 内容 |
|------|------|
| ガイド → 知識ハブ | 末尾に用語一覧・比較・数値・誤答・過去問演習（+ 分野一致時は分野ハブ） |
| ガイド本文 → 用語 | `term_hrefs_for_auto_link` + `seo_body_markup.py`（初出のみ、記事最大12 / セクション3） |
| 用語 → 過去問 | `find_past_questions_for_term` セクション + 目次 |
| 用語「次に確認」 | 比較・数値・誤答タブへのリンク追加 |
| ハブ関連用語 | CSV 不足時 **同分野用語**でフォールバック（`related_terms_box_html`） |

---

## 3. 執筆品質ルール（オリジナル文）

**正本:** `docs/editorial-quality.md` §オリジナル執筆

- `published` の section / FAQ に **量産テンプレ禁止句** → ERROR（`EDITORIAL_BOILERPLATE_PHRASES`）
- **記事間コピペ** section 本文 → ERROR（`audit_guide_cross_duplicates`）
- 文字量目安: ガイド CSV **1,600〜2,000字**、生成 HTML **2,000〜2,350字**

```bash
python3 tools/audit_editorial_quality.py
```

---

## 4. コピー対象ファイル一覧

### 必須（デザイン + ビルド）

| ファイル | 役割 |
|----------|------|
| `seo-editorial.css` | 記事 UI 正本 |
| `tools/seo_editorial_chrome.py` | CSS バージョン・head リンク |
| `tools/knowledge_hub_seo.py` | 要点・FAQ・品質パネル HTML |
| `tools/internal_links.py` | 内部リンク生成 |
| `tools/seo_body_markup.py` | 本文マークアップ + 用語自動リンク |
| `tools/glossary_past_questions.py` | 用語↔過去問 |
| `tools/build_article_pages.py` | ガイド |
| `tools/build_glossary_pages.py` | 用語（`load_glossary_entries` 含む） |
| `tools/build_compare_pages.py` | 比較（`HEAD_FONTS`→`seo_editorial_head_fonts` 修正済） |
| `tools/build_numbers_mistakes_pages.py` | 数値・誤答（同上） |
| `tools/build_seo_editorial_preview.py` | プレビュー |

### 品質ゲート

| ファイル | 役割 |
|----------|------|
| `tools/editorial_quality.py` | 禁止句・定型検出 |
| `tools/guide_article_rules.py` | ガイド CSV ルール |
| `tools/audit_editorial_quality.py` | 監査 CLI |

### ドキュメント・Cursor

| ファイル | 役割 |
|----------|------|
| `docs/seo-editorial-typography.md` | 変数リファレンス（リンク記述は本 doc が新しい） |
| `docs/editorial-quality.md` | 執筆・文字量 |
| `docs/seo-editorial-rollout-template.md` | **本ファイル** |
| `.cursor/rules/seo-editorial-rollout.mdc` | Agent 向け要約 |

---

## 5. 全サイト反映手順

**詳細チェックリスト（推奨）:** [seo-editorial-rollout-checklist.md](./seo-editorial-rollout-checklist.md)

### 5.1 概要（3 フェーズ）

1. **Phase 0（テンプレ 1 回）** — 正本凍結・マニフェスト確認・`build_all` OK
2. **Phase 1（サイトごと）** — drift → dry-run → sync → `verify_seo_editorial_rollout.py`
3. **Phase 2–3** — `build_all`（または SEO 最小ビルド）→ 機械ゲート G1–G5 → 目視 V1–V5 → 台帳記録

### 5.2 標準コマンド

```bash
# テンプレ root
python3 tools/check_template_drift.py --target /path/to/site --fail-on-drift
python3 tools/sync_from_template.py --target /path/to/site --dry-run
python3 tools/sync_from_template.py --target /path/to/site

# 反映確認
python3 tools/verify_seo_editorial_rollout.py --target /path/to/site

# 本番 root
python3 tools/build_all.py
```

### 5.3 特殊サイト

| サイト | 手順 |
|--------|------|
| `mankan-master` / `unkan-master` | `--site-only sites/<id>/site-only.paths` |
| `takken-master` | フル sync 禁止。[sites/takken-master/SITE.md](../sites/takken-master/SITE.md) フェーズ 1→3 |
| gh-pages 配信 | `main` ビルド後 `sync_gh_pages_branch.sh` |

### 5.4 編集品質で build_all が止まる場合

量産テンプレ ERROR のみ → [checklist §4.2](./seo-editorial-rollout-checklist.md#42-編集品質で-build_all-が止まる場合) の **SEO 最小ビルド**。本文リライトは別フェーズ。

### 5.5 目視

`terms/samples/seo-editorial-preview.html`、ガイド1本、用語1本、比較1本（375px 含む）

### 5.6 デプロイ

commit / push はサイト運用者の明示指示時のみ。

---

## 6. 既知・未完了

| 項目 | 状態 |
|------|------|
| ガイド 136本の量産テンプレ本文 | 監査 ERROR 多数。**オリジナルリライト待ち** |
| `validate_internal_links` | サンプル HTML 欠落等で ERROR あり得る |
| 用語 300+ 本番 | CSV 件数はサイトによる |
| `seo-editorial-typography.md` §6 リンク記述 | 本 rollout doc と不一致（更新予定） |

---

## 7. 変更履歴（セッション要約）

| 日付 | 内容 |
|------|------|
| 2026-05-30 | H1 24px、要点/関連 19px |
| 2026-05-30 | FAQ → details（表・1列リストから復帰） |
| 2026-05-30 | 要点ボックスを信頼性パネル同色に |
| 2026-05-30 | 目次アンカー余白拡大 |
| 2026-05-30 | 内部リンク強化（Python） |
| 2026-05-30 | リンク UI カード化 + 目次/本文リンク改善 |
| 2026-05-30 | オリジナル執筆ルール + boilerplate 検出 |
