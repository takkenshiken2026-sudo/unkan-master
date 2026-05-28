# レスポンシブ UI（静的ページ + SPA）

スマホ・タブレットでヘッダー・表・一覧が崩れないための契約です。  
**正本はこのファイル**。Cursor 要約は `.cursor/rules/responsive-layout.mdc`。

関連: [site-chrome.md](./site-chrome.md) · [integration-checklist.md](./integration-checklist.md) §1.8 · [performance-loading.md](./performance-loading.md)

---

## 0. よくある原因（非レスポンシブサイト）

| 症状 | 典型原因 | 対処 |
|------|----------|------|
| スマホで横スクロールがページ全体に出る | **旧 `site-pages.css`**（~1.6k 行）のまま | テンプレ最新版へ **同期**（~5.8k 行・§レスポンシブ節あり） |
| ヘッダーが折り返して高さが暴れる | 旧 `site-page-header` / 手書き topnav | [site-chrome.md](./site-chrome.md) … `site_page_header()` + `build_all` |
| 表・信頼性パネルがはみ出す | モバイル用 `@media` 未適用 | 同上 + `site-theme.css` リンク |
| SPA だけスマホ対応 | `index.html` のみ更新、静的 CSS 未同期 | `sync_from_template` + `apply_site_config` + `build_all` |
| サイト別 `mobile.css` を追加 | **禁止**（二重管理） | `site-pages.css` に集約 |

---

## 1. CSS の正本（二層）

| 層 | ファイル | 対象 |
|----|----------|------|
| **静的・生成 HTML** | `site-pages.css` | `q/`, `terms/`, `articles/`, `about.html` 等 |
| **SPA** | `index.html` インライン CSS | 演習 UI・ハンバーガー・ドロワー |
| **色トークンのみ** | `site-theme.css`（生成） | アクセント・チップ色。**@media 禁止** |

### 1.1 静的 CSS の必須節

`site-pages.css` 末尾付近に **`/* ===== 全ページ共通レスポンシブ ===== */`** があること。  
未同期サイトではこのコメント自体が **存在しない**（行数 ~1600 vs 最新 ~5800）。

---

## 2. ブレークポイント（変更時は両方を意識）

| 名前 | px | 適用先 | 主な挙動 |
|------|-----|--------|----------|
| `tablet` | 761–960 | 静的 | 用語表・過去問表の横スクロール、列幅調整 |
| **`mobile-static`** | **≤760** | **`site-pages.css`** | topnav 縮小、一覧 H1/パンくず簡略、表カード化、タブ 3 列 |
| **`mobile-spa`** | **≤700** | **`index.html`** | ハンバーガー、`.topnav-links` 非表示、グリッド 1–2 列 |
| `narrow` | ≤480 | 静的 | sticky top 調整、フッター折り返し |
| `tiny` | ≤400 | SPA | 年度グリッド 2 列等 |

**注意:** 静的 760px と SPA 700px は **意図的に近接**。同一端末で切替タイミングが数 px ずれるが、許容。将来 `site-app.css` 抽出時に統一を検討。

---

## 3. 必須パターン（静的ページ）

### 3.1 viewport と CSS 読込

全公開 HTML の `<head>`:

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<link rel="stylesheet" href="…/site-pages.css">
<link rel="stylesheet" href="…/site-theme.css">
```

- 生成ページはビルダーが付与。手書きページは **`apply_site_config.py`** が theme を注入。
- **`site-pages.css` 未リンク** = 実質非レスポンシブ。

### 3.2 レイアウト shell

| 要素 | ルール |
|------|--------|
| body | `site-shell-column-page`（`shell_body_class()`） |
| ラッパ | `.site-page-wrap` + 下 padding（固定フッター分 + `safe-area-inset-bottom`） |
| ヘッダー | `.topnav.site-shell-header` … モバイル高さ 52px、`topnav-links` 横スクロール可 |
| フッター | `.site-footer` 固定 + `.site-footer-scroll` 横スクロール |
| 本文幅 | `--site-readable-w: 860px` 付近、`clamp()` 見出し |

### 3.3 表・一覧（モバile ≤760px）

| 種類 | 挙動 |
|------|------|
| `.seo-info-table`（信頼性パネル） | **行カード化**（横スクロールにしない） |
| 本文内の一般 `<table>` | 親で **横スクロール** |
| 過去問 `.q-year-table` | `table-layout: fixed`、列幅比率、説明 2 行クランプ |
| `q/index`, `terms/index`, `articles/index` | パンくず・リード非表示、ツールバー非 sticky（一覧優先） |

### 3.4 safe-area

固定フッター・FAB・固定ボタンに `env(safe-area-inset-*)` を使用（`site-pages.css` 実装済み）。

---

## 4. SPA（`index.html`）の追加契約

| 項目 | ルール |
|------|--------|
| viewport | 静的と同型 |
| ≤700px | `.menu-btn` 表示、`.mobile-drawer`、`.topnav-links { display:none }` |
| フッター | モバイルは **文書フロー**（静的の fixed とは異なる — 仕様） |
| 演習中 | `body.is-solving` でフッター非表示 |

SPA CSS を大きく変える場合は、静的トークン（色・フォント）との **視覚的整合**を目視確認。

---

## 5. 新規サイト / 既存サイトの直し方

### 5.1 標準（フル同期可能サイト）

```bash
python3 tools/sync_from_template.py --target /path/to/site
cd /path/to/site
python3 tools/apply_site_config.py
python3 tools/build_all.py
python3 tools/validate_site_integration.py
```

**必ず同期するファイル:** `site-pages.css`, `site-pages.css` 依存の `tools/html_footer.py`, `site-q-index.js`, `site-terms-index.js`

### 5.2 フェーズ同期サイト（例: takken-master）

`manifest-phase*.txt` に `site-pages.css` が含まれることを確認。含まれていればフェーズ1で CSS を先に揃える。

### 5.3 長い試験名・ブランド名

```bash
python3 tools/stress_config_build.py   # 任意
```

`topnav-logo-sub` の `max-width: min(220px, 52vw)` 等が効くか **目視**（375px 幅）。

---

## 6. 検証

### 6.1 機械チェック（`validate_site_integration.py`）

- `site-pages.css` に「全ページ共通レスポンシブ」節と `@media (max-width: 760px)`
- `site-pages.css` 行数が閾値以上（旧版検出）
- 代表 HTML に viewport + `site-pages.css` リンク

### 6.2 目視（DevTools 推奨幅）

| 幅 | 確認 URL |
|----|----------|
| **375px** | `/`, `/articles/index.html`, `/terms/index.html`, `/q/index.html`, 試験ガイド記事 1 本 |
| **768px** | 同上 + 過去問表の横スクロール |
| **1280px** | デスクトップレイアウト・max-width 1080px 中央寄せ |

**チェック項目:**

- [ ] ページ全体の不要な横スクロールがない
- [ ] topnav 6 項目が使える（横スクロール or SPA ハンバーガー）
- [ ] 固定フッターがコンテンツを隠さない（下 padding 十分）
- [ ] 信頼性テーブルがカード表示（375px）
- [ ] 過去問一覧が読める（表 or カード）

---

## 7. 禁止

| 禁止 | 理由 |
|------|------|
| サイト別 `*-mobile.css` / インライン `@media` で静的だけ上書き | テンプレ同期で上書きされる |
| 生成 HTML の viewport / CSS リンク削除 | ビルドで復元されるが公開事故の原因 |
| 旧 `site-page-header` / `q-static-header` の復活 | モバイル未対応 + chrome 不整合 |
| `site-theme.css` にレイアウト用 `@media` | 生成物。再生成で消える |

---

## 8. サイトメモ（`sites/<id>/`）

各本番サイトの `SITE.md` または `UI_ALIGNMENT.md` に追記:

- 最終 `site-pages.css` 同期日
- モバイル目視完了日（375 / 768）
- 既知 issue（例: 特定表のみはみ出す）

雛形: [sites/chintaikanrishi-master/UI_ALIGNMENT.md](../sites/chintaikanrishi-master/UI_ALIGNMENT.md)

---

## 9. 関連

- [site-chrome.md](./site-chrome.md) — ヘッダー・フッター統一
- [seo-article-guidelines.md](./seo-article-guidelines.md) — 目次 2 列 / 1 列、本文幅
- [term-diagrams.md](./term-diagrams.md) — 図解は `site-pages.css` の `.term-diagram-*` のみ
- `tools/stress_config_build.py` — 長名称ストレスビルド
