# サイト統合チェックリスト

過去問ハブ・3モードタブ・フッター・用語一覧を**漏れなく**揃える手順です。  
「ドキュメントを読むだけ」では不十分なので、**`build_all.py` 内の `validate_site_integration.py`** で契約違反を検出します。

関連: [question-static-pages.md](./question-static-pages.md)（CSV 詳細）、[multi-site-workflow.md](./multi-site-workflow.md)（同期）

---

## 0. まず知ること（期待値の整理）

| サイト種別 | 「一回」でできること | できないこと |
|------------|----------------------|--------------|
| **テンプレ / フル同期可の本番** | `site-config.json` を直し **`python3 tools/build_all.py` 1回** → 静的 HTML・`index.html` フッター・用語 JSON まで再生成＋検証 | 本番の `data/*.csv` や独自 `build_past` をテンプレで上書きしない運用は別問題 |
| **宅建マスター等（部分同期）** | フェーズごとに同期・マージ → **各フェーズで `build_all` + 検証** | マニフェスト1回コピーだけでは完結しない（`build_past` / `build_all` は本番固有のまま） |

以前のドキュメントにあった **`FOOTER_ROOT_HREFS` はテンプレに存在しません**。静的フッターは `footer_href()` による**相対パス**、3モードタブは `q_hub_links_html()` による**ルート絶対パス**（`/q/practice/index.html` 等）です。

---

## 1. 単一の正（契約）

### 1.1 フッター「過去問一覧」

| 層 | 正 | 誤 |
|----|----|-----|
| **設定の正本** | `site-config.json` → `navigation.footer` で `label: 過去問一覧`, `href: q/index.html` | `q/practice/index.html`、フッターに「実践演習一覧」「一問一答一覧」を追加 |
| **SPA (`index.html`)** | `tools/apply_site_config.py` が `site_shell_footer()` で**自動差し替え**（`build_all` の先頭で実行） | `index.html` フッターを手編集だけして `site-config` と二重管理 |
| **静的 HTML** | `site_page_footer()` → 同上の `SITE_FOOTER_NAV` | 生成済み `q/**/*.html` を手修正 |

過去問ハブ = **`/q/index.html`**（年度別過去問一覧）。実践一覧 **`/q/practice/index.html`** とは別です。

### 1.2 3モードタブ

| 項目 | 実装 |
|------|------|
| 挿入箇所 | `build_q_index()` および実践・一問一答一覧（`q_hub_links_html(rel_path, current=...)`） |
| 非 current のリンク | `/q/index.html`, `/q/practice/index.html`, `/q/ichimon/index.html` |
| ビルド順 | `build_past_question_pages.py` → **`build_practice_ichimon_pages.py`**（`build_all.py` に両方必須） |

### 1.3 用語一覧

| 層 | 正 |
|----|-----|
| `tools/build_glossary_pages.py` | `terms_index_item_dict` が **`shortDef` と `definition`** に同じ抜粋 |
| `site-terms-index.js` | 表示は **`item.shortDef \|\| item.definition`** |
| 再生成 | `build_glossary_pages.py`（`terms/index.html` の JSON を更新） |

### 1.4 コードの正本（テンプレ）

| 役割 | ファイル |
|------|----------|
| フッター・タブ HTML | `tools/html_footer.py`（`site_shell_footer`, `q_hub_links_html`, `footer_href`） |
| 過去問ハブ | `tools/build_past_question_pages.py` |
| 実践・一問一答 | `tools/build_practice_ichimon_pages.py`（`INDEX_CONFIG`, `build_practice_index_table_row`） |
| 一覧 JS | `site-q-index.js`（`#q-index-config`, `categoryOrder`） |
| SPA フッター反映 | `tools/apply_site_config.py`（`update_index_shell_footer`） |
| CSV → SPA JS | `csv_to_exam_site_past_js.py`, `csv_to_exam_site_ichimondou_js.py` |
| 大量取り込み | `import_orig_questions_to_practice_csv.py`, `import_base_questions_to_ichimon_csv.py` |
| 機械検証 | `tools/validate_site_integration.py` |

### 1.5 実践演習・一問一答（静的 `q/`）

| 項目 | 正 | 誤 |
|------|----|-----|
| **データ正本** | `data/practice_questions.csv`, `data/ichimon_questions.csv` | 生成 HTML / SPA JS の手編集のみ |
| **一覧件数** | CSV 行数 = `#q-index-data` 件数（`validate_site_integration`） | CSV 1問のまま SPA だけ1000問 |
| **一覧グループ** | 実践・一問一答とも **`groupBy: category`**（`site-config` の `fields` 順） | 一問一答を年度別グループのみ |
| **グループ内** | 実践: `question_no` 昇順 / 一問一答: `id` 昇順 | CSV 取り込み順のまま |
| **学習状況フィルタ** | `statusFilters`: `wrong`, `bookmark` のみ | 過去問の `exempt` / `invalid` を載せる |
| **表行** | `build_practice_index_table_row` / `build_ichimon_index_table_row` | 過去問用 `#past-play-*` 行 |
| **SPA リンク** | 一問一答 `publicPath`: `q/ichimon/y{年}/i{月}-{枝番}/` | `ichimon/y…`（`q/` 欠落） |

**SPA にだけ問題バンクがあるサイト**（例: 宅建 `ORIG_QUESTIONS`）は、静的化前に取り込みスクリプトで CSV を揃える。詳細は [question-static-pages.md](./question-static-pages.md) §大量取り込み。

```bash
python3 tools/import_orig_questions_to_practice_csv.py      # 任意・ORIG がある場合
python3 tools/import_base_questions_to_ichimon_csv.py --keep-manual
python3 tools/build_all.py
```

### 1.6 HTML 図解（用語・問題解説）

| 項目 | 正 |
|------|-----|
| **データ** | `data/term_diagrams/{id}.json` |
| **参照** | CSV 任意列 `diagram_id`（用語・過去問・実践・一問一答） |
| **公開形態** | **記事内埋め込み**（図解専用の本番 URL は作らない） |
| **用語** | `build_glossary_pages.py` → 定義の直後 |
| **問題** | 契約のみ（[term-diagrams.md](./term-diagrams.md) §6）。未実装時は CSV に ID を書かない |
| **同期** | `tools/term_diagram.py`, `site-pages.css`, 関連 `build_*.py` はマニフェスト対象 |
| **検証** | `validate_csv.py` … 存在しない `diagram_id` は ERROR |
| **デザイン** | `site-pages.css` の `.term-diagram-*` のみ（[term-diagrams.md](./term-diagrams.md) §6）。インライン色・サイト別 CSS 分叉は禁止 |

### 1.7 ヘッダー・フッター（Site chrome）

| 項目 | 正 |
|------|-----|
| **生成** | ヘッダー `site_page_header()`、フッター `site_page_footer()` のみ（[site-chrome.md](./site-chrome.md)） |
| **手書き topnav 禁止** | 生成 `q/`・`terms/`・`articles/` および apply 対象静的 HTML |
| **ヘッダー `current`** | active は `terms` / `practice` / `ichimon` のみ。**`q` は active にしない**（過去問一覧はフッター専用） |
| **フッター `current`** | `site-config.json` の `footer[].key` と一致 |
| **混同注意** | ヘッダー「過去問」= **`/#past`（SPA 演習）**。フッター「過去問一覧」= **`q/index.html`（静的一覧）**。別コンテンツ（[site-chrome.md](./site-chrome.md) §3） |
| **検証** | `validate_site_integration.py` … chrome + **`tnav-past` → `/#past`** |

新規サイト: `build_all` のみ。既存サイト: テンプレ同期 → 本番 `build_all`。ヘッダー構造の変更は `html_footer.py` 1 か所。

### 1.8 レスポンシブ UI

| 項目 | 正 |
|------|-----|
| **CSS 正本** | 静的 → `site-pages.css`（§「全ページ共通レスポンシブ」）。SPA → `index.html` インライン |
| **viewport** | 全公開 HTML: `width=device-width, initial-scale=1.0` |
| **CSS リンク** | 静的ページ: `site-pages.css` + `site-theme.css`（`apply_site_config`） |
| **モバイル閾値** | 静的 **≤760px** / SPA **≤700px**（[responsive-layout.md](./responsive-layout.md) §2） |
| **表** | `.seo-info-table` はモバイルでカード化。データ表は横スクロール |
| **禁止** | サイト別 `*-mobile.css`、旧 `site-page-header` |
| **検証** | `validate_site_integration.py` … CSS 行数・レスポンシブ節・viewport |
| **目視** | 375px / 768px … [responsive-layout.md §6.2](./responsive-layout.md) |

### 1.9 SPA トップ（`index.html`）の SNS / SEO

| 層 | 正 | 誤 |
|----|----|-----|
| **設定の正本** | `site-config.json`（`brandName`, `examName`, `siteOrigin`） | 宅建 fork の `index.html` をそのまま使う |
| **HTML head** | `tools/index_seo_head.py` が `<!--INDEX_SEO_HEAD-->` 内を再生成（`apply_site_config` 経由） | `twitter:title` だけ残して `og:title` 欠落 |
| **og:image** | `generate_brand_assets.py` + `inject_brand_head` | SEO ブロック内に別ドメインの `og:image` を二重定義 |
| **SPA 内メタ** | `PAGE_SEO` は `SITE_CONFIG` から組み立て | サイト名を JS にハードコード |
| **パンくず1段目** | 「トップ」 | ブランド名（例: 宅建マスター） |
| **noscript / FIELDS** | `INDEX_NOSCRIPT`・`INDEX_FIELDS_FALLBACK` を `apply_site_config` が `site-config.fields` から再生成 | 宅建3分野のハードコード |
| **site-config 読込順** | `site-config.js` を `var FIELDS` より前 | FIELDS がフォールバック固定 |
| **部分同期** | `tools/sync_index_spa_from_template.py` + `index_spa_patch_regions.txt` | `index.html` 手マージのみ |
| **再生成** | `build_all.py` 内の `generate_brand_assets` → **`apply_site_config.py`** | head を手編集だけ |

`index.html` は **テンプレ同期対象外**。新規サイトはテンプレ正本の `index.html` を取り込み、初回:

```bash
python3 tools/generate_brand_assets.py
python3 tools/apply_site_config.py
python3 tools/validate_site_integration.py
```

SPA エンジンだけテンプレから反映（`index.html` 全体は上書きしない）:

```bash
python3 tools/sync_index_spa_from_template.py --target /path/to/site --apply-config
```

トップ URL の SNS カード: [X Card Validator](https://cards-dev.twitter.com/validator) で確認。

非レスポンシブサイトの典型: **旧 `site-pages.css`（~1.6k 行）未同期** → `sync_from_template` + `build_all`。

### 1.9 知識ハブ3種（比較・数値・誤答）の拡充

| 項目 | 正 |
|------|-----|
| **本番目標** | **各 150〜153 件**（`comparisons.csv` / `numbers.csv` / `mistakes.csv`） |
| **新規作成** | `scaffold_knowledge_hub_article.py --append` → 執筆 → `build_glossary_pages.py` |
| **正本** | [knowledge-hub-article-templates.md](./knowledge-hub-article-templates.md) |
| **検証** | `validate_csv.py` + `tools/knowledge_hub_rules.py` |
| **Cursor** | `.cursor/rules/knowledge-hub-content.mdc` |

50 件未満は WARN（ビルドは通る）。`related_terms` 未登録・JSON 不正は ERROR。

---

## 2. テンプレで直す手順（標準・1コマンド）

```bash
cd /path/to/exam-site-shell
```

### 2.1 編集するのは主にこれだけ

1. **`site-config.json`** — `navigation.footer` の「過去問一覧」→ `q/index.html`（実践 URL にしない）
2. **必要なら** `tools/html_footer.py` / `build_*.py` / `site-terms-index.js` / `build_glossary_pages.py`
3. **`index.html` フッターは原則触らない** — `apply_site_config` に任せる

### 2.2 必須コマンド（この順で1回）

```bash
python3 tools/build_all.py
```

内部で実行される主な処理:

1. `validate_csv.py`
2. `generate_brand_assets.py` … favicon / og-image
3. **`apply_site_config.py`** … `index.html` の **INDEX_SEO_HEAD**（SNS/OGP）・フッター・`site-theme.css` 等
4. 各 `build_*.py` … `q/`, `terms/`, `articles/`
5. **`validate_site_integration.py`** … 本チェックリストの契約（SPA SEO マーカー含む）
6. `validate_internal_links.py` ほか
7. `prepare_public_site.sh` … `public_site/` 配置

単体確認:

```bash
python3 tools/validate_site_integration.py
```

### 2.3 目視（検証が通っても推奨）

| URL | 確認 |
|-----|------|
| `/q/index.html` | タブ3つ・過去問が current |
| `/q/practice/index.html` | タブから過去問ハブへ遷移 |
| `/terms/index.html` | 概要列が JS 適用後も非空 |
| `/` | フッター「過去問一覧」→ `/q/index.html`（実践ではない） |
| `/`（トップ） | ページソースに `og:title` / `twitter:title` が **自サイト名**（`INDEX_SEO_HEAD` あり） |
| **375px 幅** | `/`, `articles/index.html`, `terms/index.html`, `q/index.html` … 横スクロールなし（[responsive-layout.md §6.2](./responsive-layout.md)） |

---

## 3. 本番へ反映

### 3.1 フル同期可

```bash
cd /path/to/exam-site-shell
python3 tools/sync_from_template.py --target /path/to/production --dry-run
python3 tools/sync_from_template.py --target /path/to/production --build
```

`--build` = 先方で `build_all.py`（本番の `site-config.json` / `data/` はそのまま）。

**本番でも** フッター変更は本番の `site-config.json` を直してから `build_all` すること。テンプレだけ直しても本番フッターは変わりません。

### 3.2 宅建マスター（フル同期不可）

[sites/takken-master/SITE.md](../sites/takken-master/SITE.md) の **フェーズ1→2→3** を順に実施。各フェーズの末尾:

```bash
python3 tools/build_all.py
python3 tools/validate_site_integration.py
python3 tools/validate_internal_links.py
```

`html_footer.py` / `build_past_question_pages.py` は**マージ**（上書き禁止リスト参照）。

---

## 4. 再発パターン早見表

| 症状 | 原因 | 対処 |
|------|------|------|
| フッター過去問が遷移しない | `href` が `q/practice/...` と同じ | `site-config` → `q/index.html` → **`build_all`**（`apply_site_config` で index も更新） |
| 過去問ハブにタブがない | `build_past` に `q_hub_links_html` 未挿入 | テンプレを直し本番にマージ → `build_all` |
| 用語定義が全部空 | JSON に `shortDef` なし / JS が `shortDef` のみ | `build_glossary_pages.py` + `site-terms-index.js` → `build_all` |
| 実践一覧で過去問フッターが効かない | 同上（実践 URL を指している） | §1.1 |
| 実践一覧で 0 件 / 過去問フィルタが効く | URL の `?status=exempt` 等・statusFilters 不一致 | `INDEX_CONFIG` は wrong/bookmark のみ → `build_all` |
| 実践・一問一答 件数が少ない | CSV がサンプルのみ・ORIG 未取り込み | §1.5 取り込み → `build_all` |
| 一問一答が年度順 | `groupBy: year` のまま | `groupBy: category` + `categoryOrder` → `build_all` |
| `validate_site_integration` 件数不一致 | CSV 変更後未ビルド | `build_all.py` |
| X でトップ URL が別サイト名 | `index.html` head が宅建 fork のまま / `apply_site_config` 未実行 | §1.9 → **`build_all`**（`apply_site_config` 含む） |
| 同期したのに過去問だけ旧式 | 本番 `build_past` が古いまま | 宅建はフェーズ2マージ。フル同期サイトは `--build` 忘れ |

---

## 5. チェックリスト（人間用・コピペ可）

テンプレまたは本番ルートで:

- [ ] `site-config.json` … 過去問一覧 `href: q/index.html`、フッターに実践/一問一答の**別項目なし**
- [ ] `python3 tools/build_all.py` 成功
- [ ] `validate_site_integration.py` が OK
- [ ] `validate_internal_links.py` が broken 0
- [ ] `index.html` … `INDEX_SEO_HEAD` あり、head 内 `og:title` が自サイト名（§1.9）
- [ ] 目視 §2.3 の URL（トップの SNS メタ含む）
- [ ] 実践・一問一答: CSV 行数 ≒ 一覧件数（§1.5）。一問一答は**分野順**ブロック

宅建の場合は上に加え:

- [ ] フェーズ1マニフェストで `build_*` を上書きしていない
- [ ] フェーズ2で `q_hub_links_html` を本番 `build_past` にマージ済み
- [ ] フェーズ3で `build_practice_ichimon` が本番 `build_all` から呼ばれる

---

## 6. 実践・一問一答を増やす／他サイトへ展開

### 6.1 標準サイト（フル同期可）

1. テンプレで `build_practice_ichimon_pages.py` / `site-q-index.js` を直す
2. テンプレ `build_all.py` 成功
3. `sync_from_template.py --target <本番> --build`
4. 本番の `data/practice_questions.csv` / `ichimon_questions.csv` を編集（または §6.2 取り込み）
5. 本番 `build_all.py` → 検証 → push

### 6.2 SPA バンクから CSV へ（宅建型）

| 手順 | コマンド | 備考 |
|------|----------|------|
| 実践 1000 問化 | `import_orig_questions_to_practice_csv.py` | 入力: `takken-data-original.js` 等 |
| 一問一答 拡充 | `import_base_questions_to_ichimon_csv.py --keep-manual` | 過去問＋実践から自動生成 |
| 再生成 | `build_all.py` | 1000+ ページは数分かかる場合あり |

取り込み後も SPA 側の旧バンク（例: `ORIG_QUESTIONS`）と CSV が二重管理になる。**長期は CSV を正本**にし、必要ならサイト固有 JS 生成を CSV 連動へ寄せる。

### 6.3 一覧 UI の必須設定（再発防止）

`tools/build_practice_ichimon_pages.py` の `INDEX_CONFIG` と生成 HTML の `#q-index-config` が一致すること:

```json
{
  "variant": "ichimon",
  "groupBy": "category",
  "groupPrefix": "group",
  "groupLabel": "分野",
  "categoryOrder": ["権利関係", "宅建業法", "…"],
  "statusFilters": ["wrong", "bookmark"]
}
```

`site-q-index.js` は `categoryOrder` でグループ・フラット表示を並べ替え。ジャンプリンクは `data-group` 対応必須。

### 6.4 部分同期サイト

フル `template_sync_manifest.txt` が使えないサイトは `sites/<id>/manifest-phase*.txt` で段階同期。最低限フェーズ3相当:

- `build_practice_ichimon_pages.py`, `site-q-index.js`, `csv_to_exam_site_*.py`
- `validate_site_integration.py`（本番 `build_all` に1行追加）
- 取り込みスクリプト（バンク移行するサイトのみ）

**監査:** テンプレまたは本番 root で `python3 tools/audit_integration_rules.py [--target /path/to/site]` を実行し、ERROR が 0 であること。

---

## 7. 参照

| 用途 | ファイル |
|------|----------|
| Cursor 統合 | `.cursor/rules/site-integration.mdc` |
| Cursor 実践・一問一答 | `.cursor/rules/practice-ichimon-static.mdc` |
| CSV・ビルド詳細 | `docs/question-static-pages.md` |
| 宅建 | `sites/takken-master/SITE.md`, `manifest-phase1.txt`, `manifest-phase3.txt` |
| 同期 | `tools/template_sync_manifest.txt`, `docs/multi-site-workflow.md` |
| ルール監査 | `tools/audit_integration_rules.py` |
