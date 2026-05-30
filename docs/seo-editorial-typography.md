# SEO 記事タイポグラフィ（試験ガイド・用語解説・知識ハブ）

試験ガイド（`/articles/`）・用語解説（`/terms/g-*.html`）・知識ハブ詳細（比較 / 数値 / 誤答）の**読みやすさ**は、HTML テンプレートではなく **`seo-editorial.css`** で調整します。

サイト共通の `site-pages.css` / `site-theme.css` はナビ・一覧・演習 UI も共有するため、SEO 長文だけを触る場合は本レイヤーを使います。

---

## 1. 対象ページ

| 種別 | body class | 生成スクリプト |
|------|------------|----------------|
| 試験ガイド詳細 | `guide-article-page` | `tools/build_article_pages.py` |
| 用語解説詳細 | `term-article-page` | `tools/build_glossary_pages.py` |
| 比較・整理表 | `compare-article-page` | `tools/build_compare_pages.py` |
| 数値・期限早見 | `numbers-article-page` | `tools/build_numbers_mistakes_pages.py` |
| よくある誤答 | `mistakes-article-page` | `tools/build_numbers_mistakes_pages.py` |

記事本体には `<article class="seo-article-card article-body seo-editorial">` が付きます。

---

## 2. 調整の入口

**ファイル:** リポジトリ直下 [`seo-editorial.css`](../seo-editorial.css)

**変数（例）:**

| 変数 | 意味 | 初期値の目安 |
|------|------|-------------|
| `--seo-font-weight` | 本文・表・リンク等 | `500`（Medium） |
| `--seo-font-weight-heading` | H1 / H2 / H3 | `700`（Bold） |
| `--seo-fs-body` | 本文サイズ | `16px` |
| `--seo-fs-lead` | リード文サイズ | `16px` |
| `--seo-fs-h3` | 小見出しサイズ | `16px` |
| `--seo-fs-table` | 表（th / td） | `16px` |
| `--seo-table-head-bg` | 見出しセル背景 | `#dde1e6`（濃いめグレー） |
| `--seo-table-head-text` | 見出しセル文字 | `#505660` |
| `--seo-table-border` | 表の枠線 | `rgba(0,0,0,0.14)` |
| `--seo-line-body` | 本文行間 | `1.88` |
| `--seo-text-body` | 本文色 | `#2a2a2a` |
| `--seo-text-title` | 見出し色 | `#141414` |
| `--seo-strong` | 強調（`strong`） | `#2563a8`（太字） |
| `--seo-accent` | 見出し左ライン・番号・引用・強調 | `#2563a8` |
| `--seo-accent-soft` | 引用ブロック背景 | `#eef4fb` |
| リンク（`a`） | 本文と同色（色付けなし） | `#2a2a2a` + 下線 |
| `--seo-font-body` | 本文フォント | Noto Sans JP |
| `--seo-panel-bg` | 目次・関連記事背景 | `#f7f8f9`（グレー系） |
| `--seo-callout-bg` | 信頼性・行動ボックス | `#f4f4f5`（グレー） |
| `--seo-callout-side` | 左ライン | `var(--accent)`（サイト黒系） |

見出しだけ明朝にしたい例:

```css
--seo-font-heading: "Noto Serif JP", "Yu Mincho", serif;
```

Google Fonts 追加は `tools/seo_editorial_chrome.py` の `seo_editorial_head_fonts()` を編集します。

---

## 3. ビルド・プレビュー

CSS を変えたら **バージョン** を上げる:

```python
# tools/seo_editorial_chrome.py
SEO_EDITORIAL_CSS_VER = "20260527-editorial-v2"  # 日付 + 連番
```

### スタイルプレビュー（1 ページ）

```bash
python3 tools/build_seo_editorial_preview.py
# → terms/samples/seo-editorial-preview.html
```

ブラウザで `terms/samples/seo-editorial-preview.html` を開き、目次・本文・表・FAQ などの見え方を確認します。

### 本番 HTML へ反映

shell で確認後、各サイトで該当ビルドを実行:

```bash
python3 tools/build_article_pages.py
python3 tools/build_glossary_pages.py
python3 tools/build_compare_pages.py
python3 tools/build_numbers_mistakes_pages.py
```

---

## 4. 触らないもの（この段階）

- 一覧ページ（`/articles/index.html`, `/terms/index.html` 等）
- 過去問・演習 UI（`/q/`）
- CSV 本文データ

フォント・色の A/B は **CSS だけ** で完結させ、内容変更は別タスクに分けます。

---

## 6. アクセント方針（最小限）

**色を入れるのは次の要素**（目次・バッジ・リンクはグレー系のまま）。

| 要素 | 扱い |
|------|------|
| 信頼性・行動ボックス | グレー背景 + 左 4px ライン（`--accent` / `#333`） |
| 番号付き H2 | 左 3px ライン + 番号をアクセント塗り（文字色は黒系） |
| H3 / 小見出し | 左 3px ライン（文字色は黒系） |
| 引用（`blockquote`） | 薄青背景 + 左 4px ライン |
| 表（`th`） | 薄グレー背景 + グレー文字（黒ヘッダー廃止）+ 枠線 |
| 表（`td`） | 白背景、偶数行は `#f7f8f9`（2列型は白統一） |
| 強調（`strong`） | 青 `#2563a8` + **700**（Bold） |
| リンク（`a`） | 本文同色（色付けなし）+ 下線 |

サイトナビの `--accent` とは独立。記事本文の階層だけ控えめブルーで区切ります。

---

## 5. 関連ファイル

| ファイル | 役割 |
|---------|------|
| `seo-editorial.css` | 読みやすさトークンと上書き |
| `tools/seo_editorial_chrome.py` | head フォント + stylesheet リンク生成 |
| `tools/build_seo_editorial_preview.py` | プレビュー HTML 生成 |
| `site-pages.css` | レイアウト・表組みのベース（SEO 詳細セクション） |
