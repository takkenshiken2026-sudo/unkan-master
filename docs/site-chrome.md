# サイト共通 chrome（ヘッダー・フッター）

静的ページ間をフッターで移動しても、**ヘッダーの見た目・項目・生成元が変わらない**ことを契約にします。  
**正本はこのファイル**。Cursor 要約は `.cursor/rules/site-chrome-nav.mdc` と `.cursor/rules/site-integration.mdc`。

関連: [integration-checklist.md](./integration-checklist.md) §1.7

---

## 0. 問題の整理

「フッターのリンクを押すとヘッダーが変わる」は、次のどちらか（または両方）です。

| 種類 | 例 | 対応 |
|------|-----|------|
| **許容（意図した変化）** | 用語ページ→過去問一覧へ移動し、フッターの **aria-current** が「用語解説」→「過去問一覧」に切り替わる | 仕様。同一 chrome のままフッターだけハイライトが変わる |
| **不可（バグ・不整合）** | 項目数が減る、ロゴ横の試験名が消える、旧 `q-static-header` に戻る、手書き topnav と生成 topnav が混在 | **本ルールで禁止**。`build_all` + 検証で防ぐ |
| **不可（混同バグ）** | ヘッダー「過去問」とフッター「過去問一覧」が**同じコンテンツ**として扱われ、両方 active になる／ヘッダーが `q/index.html` を指す | **§3 で禁止**。`validate_site_integration.py` で検出 |

---

## 1. 単一の生成元（必須）

| 部位 | 生成関数 | 設定の正本 |
|------|----------|------------|
| **ヘッダー（学習ナビ）** | `tools/html_footer.site_page_header()` | `LEARNING_NAV_ITEMS`（同ファイル） |
| **フッター** | `tools/html_footer.site_page_footer()` → `site_shell_footer()` | `site-config.json` → `navigation.footer` |
| **SPA トップ** | `apply_site_config` → `site_shell_footer()` | 同上（`index.html` フッターは手編集しない） |

### 禁止

| 禁止 | 理由 |
|------|------|
| 生成 HTML（`q/`, `terms/`, `articles/`）に **topnav を手書き** | フッター遷移後にヘッダーだけ別物になる |
| 新規ページで **`static_site_header()` / `q-static-header`** を使う | 学習ナビ欠落の旧型ヘッダー |
| `about.html` 等のヘッダーを **apply_site_config なしで放置** | テンプレ更新と乖離 |
| フッターだけ `site-config` と別 URL を直書き | 二重管理 |
| ヘッダー「過去問」を **`q/index.html` に向ける** | フッター「過去問一覧」と別コンテンツ（§3） |

手書き静的ページ（`about.html`, `privacy.html`, `related-sites.html`, `articles/index.html`）は **`apply_site_config.py` がヘッダー・フッターを差し替え**ます。文言だけ直し、`<header>` / `<footer>` ブロックは編集しない。

---

## 2. `current` 引数の契約（ヘッダーとフッターは別）

`site_page_header(..., current=)` と `site_page_footer(..., current=)` は **同じ引数名だが役割が異なります**。

### 2.1 ヘッダー `current` — 学習ナビの active のみ

| `current` 値 | active になる nav id | 使うページ |
|--------------|----------------------|------------|
| `terms` | `tnav-glossary` | `terms/**` |
| `practice` | `tnav-orig` | `q/practice/**` |
| `ichimon` | `tnav-ichimondou` | `q/ichimon/**` |
| `about`, `privacy`, `articles`, `related`, `None`, **`q`** 等 | **なし**（全リンク非 active） | ポリシー・ガイド・**過去問一覧** |

**重要:** `q/index.html` および `q/past/**` では **`current="q"` をヘッダーに渡しても active にしない**。  
過去問一覧はフッター専用コンテンツ（§3）。`LEARNING_NAV_ACTIVE_BY_PAGE` に **`q` キーを含めない**。

**各ビルドスクリプトで必ず正しい値を渡す:**

```python
site_page_header(rel_path, current="terms")      # build_glossary_pages
site_page_header(rel_path, current="q")          # build_past_question_pages（フッター用。ヘッダー active なし）
site_page_header(rel_path, current="practice")   # build_practice_*（"q" 禁止）
site_page_header(rel_path, current="ichimon")
site_page_header(rel_path, current="articles")   # build_article_pages（active なしで OK）
```

### 2.2 フッター `current` — フッターリンクの `aria-current`

`site-config.json` の `navigation.footer[].key` と一致させる。

| key 例 | ページ |
|--------|--------|
| `top` | （通常は付けない） |
| `about` | about.html |
| **`q`** | **`q/index.html` 系（過去問一覧）** |
| `terms` | terms/index.html 系 |
| `articles` | articles/index.html |
| `privacy` | privacy.html |

### 2.3 二重ハイライト抑制（用語・実践・一問一答のみ）

ヘッダーとフッターが**同じ静的一覧**を指す項目（用語解説・実践演習・一問一答）では、  
`FOOTER_SUPPRESS_CURRENT_WHEN_HEADER` により **フッター側 `aria-current` を付けない**。

**`q`（過去問一覧）は含めない。** ヘッダー「過去問」は SPA 演習のため、フッター「過去問一覧」とは別物。

---

## 3. ヘッダー「過去問」とフッター「過去問一覧」は別コンテンツ（必須）

| ラベル | 場所 | 行き先 | 内容 | active の付け方 |
|--------|------|--------|------|-----------------|
| **過去問** | ヘッダー学習ナビ | **`/#past`**（SPA 演習） | 年度・分野を選んで解く **アプリ画面** | SPA 内 JS のみ。静的 HTML では **付けない** |
| **過去問一覧** | フッター | **`q/index.html`** | 静的・SEO 向け **目次・一覧** | `current="q"` で **フッターのみ** active |

### 3.1 コード上の正本（`tools/html_footer.py`）

```python
# LEARNING_NAV_ITEMS — 過去問は SPA ハッシュ
("tnav-past", "過去問", "#past", …),

# LEARNING_NAV_ACTIVE_BY_PAGE — q は含めない
LEARNING_NAV_ACTIVE_BY_PAGE = {
    "terms": "tnav-glossary",
    "practice": "tnav-orig",
    "ichimon": "tnav-ichimondou",
}

# 静的ページの SPA ハッシュリンクはルート絶対パス（試験ガイド等の深い階層でも壊れない）
def _learning_nav_href(rel_path, dest):
    if dest.startswith("#"):
        return "/" + dest   # → /#past, /#dash, /#review
    return footer_href(rel_path, dest)
```

### 3.2 禁止パターン

| 禁止 | 結果 |
|------|------|
| ヘッダー `tnav-past` → `q/index.html` / `../../q/index.html` | 試験ガイドから一覧へ飛び、演習が開けない |
| ヘッダー `tnav-past` に `aria-current`（`q/index.html` 上） | フッター「過去問一覧」と二重選択 |
| SPA ハッシュを相対パス（`../index.html#past` 等）だけに依存 | 階層によって誤解決・デプロイ差分の原因 |
| フッター「過去問一覧」を `/#past` にする | SEO 一覧と SPA 演習の役割が逆転 |

### 3.3 SPA トップ `index.html` との関係

- SPA トップのヘッダー「過去問」は `/#past` + `gotoPage('past-config')`（手書き・`apply_site_config` 対象）。
- 静的ページのヘッダーは **`site_page_header()` 生成**で、上記 §3.1 と同じ `/#past` を出力する。

---

## 4. その他の学習ナビリンク

| ラベル | ヘッダー行き先 | 備考 |
|--------|----------------|------|
| 一問一答 | `q/ichimon/index.html`（`footer_href` で相対解決） | 静的一覧 |
| 実践演習 | `q/practice/index.html` | 静的一覧 |
| 記録・分析 | **`/#dash`** | SPA |
| 復習 | **`/#review`** | SPA |
| 用語解説 | `terms/index.html` | 静的一覧 |

---

## 5. 見た目の統一

| 項目 | ルール |
|------|--------|
| クラス | `<header class="topnav site-shell-header">`（一覧のみ `site-shell-header--wide` 可） |
| ロゴ | `_topnav_logo()` — ブランド名・試験名は `site-config` 由来 |
| 学習ナビ 6 項目 | 一問一答 / 過去問 / 実践演習 / 記録・分析 / 復習 / 用語解説（順序固定） |
| フッター | `site-footer` + `navigation.footer` のリンクセット |
| body | `site-shell-column-page` を含める（`shell_body_class()`） |

---

## 6. 新規サイト / 既存サイト

### 新規

1. 静的ページはすべて `site_page_header` / `site_page_footer` 経由で生成  
2. `site-config.json` の `navigation.footer` を編集（過去問は `q/index.html`）  
3. `python3 tools/build_all.py`（先頭で `apply_site_config`）

### 既存（本番）

1. テンプレで `html_footer.py` / 各 `build_*.py` / `apply_site_config.py` を修正  
2. `sync_from_template.py --target <path> --build`  
3. **`html_footer.py` 変更後は `python3 tools/patch_header_nav.py` または `build_all.py` で全 HTML 再生成**  
4. 生成済み `q/**/*.html` を手修正しない

---

## 7. 検証

```bash
python3 tools/build_all.py
# 内包: validate_site_integration.py → _static_chrome + _header_learning_nav
```

### 機械チェック

- 代表静的ページに `topnav site-shell-header` がある  
- 生成 `q/` に `q-static-header` が **ない**  
- **`tnav-past` の href が `/#past`**（`q/index.html` を含まない）  
- **`tnav-dash` / `tnav-review` が `/#dash` / `/#review`**  
- `q/index.html`: ヘッダー「過去問」は **非 active**、フッター「過去問一覧」は **aria-current**  
- `tools/html_footer.py`: `LEARNING_NAV_ACTIVE_BY_PAGE` に **`q` キーがない**

### 目視（必須 4 パターン）

1. **`articles/*/index.html`** → ヘッダー「過去問」→ **SPA 過去問演習**（URL が `/#past` 系。`q/index.html` にならない）  
2. **`q/index.html`** → フッター「過去問一覧」のみ active。ヘッダー「過去問」は非 active  
3. **`terms/index.html`** → フッター「過去問一覧」→ `q/index.html` → フッターのみ active  
4. フッター経由で 3 ページ以上遷移 → 学習ナビ **6 項目・順序固定**・ロゴ同型

---

## 8. 関連

- [integration-checklist.md](./integration-checklist.md)  
- [multi-site-workflow.md](./multi-site-workflow.md)  
- [question-static-pages.md](./question-static-pages.md)  
- `tools/html_footer.py` — `LEARNING_NAV_*`, `_learning_nav_href`, `footer_href`, `FOOTER_SUPPRESS_*`  
- `tools/patch_header_nav.py` — ヘッダー/フッターだけ高速再生成
