# 用語・問題解説向け HTML 図解

静的サイトに **React なし**で差し込む図解ブロックの契約です。  
**正本はこのファイル**。Cursor 要約は `.cursor/rules/term-diagrams.mdc`。

---

## 0. 設計方針（必読）

| 項目 | ルール |
|------|--------|
| **公開形態** | **記事の中に埋め込み**（別 URL の図解専用ページは作らない） |
| **データ** | `data/term_diagrams/{id}.json` が正本 |
| **参照** | 各 CSV の任意列 **`diagram_id`**（拡張子なし ID） |
| **再利用** | 1つの JSON を **用語記事・問題解説の両方**から参照してよい |
| **執筆量** | 全ページに付けない。**混同されやすい対比テーマ**に限定 |

プレビュー用（noindex）のみ別 HTML がある:

- `terms/diagram-samples/` … 図解単体の執筆確認
- `terms/g-diagram-sample.html` … 用語記事への差し込み見本

---

## 1. 対応状況（テンプレ）

| ページ種別 | 状態 | 挿入位置 |
|------------|------|----------|
| **用語解説** `terms/*.html` | ✅ 実装済 | 「定義と基本理解」の直後 → **図解で理解する** |
| **過去問** `q/past/...` | 📋 契約のみ（未実装） | 解説ブロック内（正解の理由の後を推奨） |
| **実践演習** `q/practice/...` | 📋 同上 | 同上 |
| **一問一答** `q/ichimon/...` | 📋 同上 | 同上 |

問題解説への実装は `tools/build_past_question_pages.py` / `build_practice_ichimon_pages.py` に  
`diagram_id` 列と `term_diagram.diagram_body_html()` の挿入を追加する（本ドキュメント §7 参照）。

---

## 2. 新規サイト（テンプレから立ち上げ）

1. テンプレをコピーし `site-config.json` / `data/*.csv` を差し替え
2. 図解が不要なら **何もしない**（`diagram_id` 列がなくても可）
3. 図解を使う場合:
   - `data/term_diagrams/` に JSON を配置（例: `kenpei-yoseki.json`）
   - `data/glossary_terms.csv` のヘッダに `diagram_id` を追加（任意列）
   - 必要な用語行だけ `diagram_id=kenpei-yoseki` を指定
4. `python3 tools/build_all.py` で生成・検証

サンプル確認:

```bash
python3 tools/build_glossary_pages.py   # 用語 + diagram-samples + 執筆見本
# ブラウザ: terms/g-diagram-sample.html, terms/diagram-samples/kenpei-yoseki.html
```

---

## 3. 既存サイト（本番へ取り込み）

**原則:** テンプレで直す → `sync_from_template.py` → 本番で `build_all.py`。  
生成物 `terms/`・`q/` は手編集しない。

### 3.1 同期するファイル（共通エンジン）

`tools/template_sync_manifest.txt` に含まれるもの（抜粋）:

| パス | 役割 |
|------|------|
| `tools/term_diagram.py` | JSON → HTML |
| `tools/build_glossary_pages.py` | 用語ページへ挿入 |
| `tools/build_term_diagram_sample_pages.py` | サンプル HTML |
| `data/term_diagrams/` | 図解データ（**サイト固有**なら本番 `data/` に直接追加可） |
| `site-pages.css` | `.term-diagram-*` スタイル |

手順:

```bash
# テンプレで build_all 成功を確認
python3 tools/check_template_drift.py --target /path/to/production-site
python3 tools/sync_from_template.py --target /path/to/production-site --dry-run
python3 tools/sync_from_template.py --target /path/to/production-site --build
```

### 3.2 本番だけ行う作業（同期されない）

| 作業 | 内容 |
|------|------|
| CSV | `glossary_terms.csv` に `diagram_id` 列を追加し、対象行だけ ID を記入 |
| JSON | 本番 `data/term_diagrams/*.json` を追加・編集 |
| 問題 CSV | 将来: `past_questions.csv` 等にも `diagram_id`（§6） |
| ビルド | 本番で `python3 tools/build_all.py` |

### 3.3 部分同期サイト（例: 宅建マスター）

`docs/multi-site-workflow.md` のフェーズ同期に従う。  
図解は **用語ビルドが動くフェーズ**で `build_glossary_pages.py` まで含める。  
`sites/<サイトID>/SITE.md` に「図解 JSON の有無・対象用語数」をメモしておく。

### 3.4 ロールバック

- `diagram_id` を空にして再ビルド → 図解セクションは出ない
- JSON を削除した ID を CSV に残すと `validate_csv.py` が **ERROR**

---

## 4. 用語解説での使い方

### 4.1 CSV

```csv
term,...,diagram_id
建ぺい率,...,kenpei-yoseki
```

- ID は `[a-z0-9][a-z0-9-]*` のみ
- 空欄 = 図解なし
- 列自体が無くてもビルドは通る（後方互換）

### 4.2 生成される HTML 構造

```
<section class="term-diagram-section">
  <h2>図解で理解する</h2>
  <figure class="term-diagram term-diagram--compare-dual">…</figure>
</section>
```

### 4.3 執筆の役割分担

| 場所 | 書く内容 |
|------|----------|
| `term_detail_body` | 定義・制度上の位置づけ |
| 図解 JSON | 2概念の対比・式・数値例・一問一答 |
| `compare` 記事 | 表形式の軸整理（細部） |
| 問題解説 | その問の正誤理由（図解は概念の整理のみ） |

同じ文言を3箇所にコピペしない。

---

## 5. JSON 仕様（`compare_dual`）

ファイル: `data/term_diagrams/{id}.json`

```json
{
  "type": "compare_dual",
  "eyebrow": "宅建 図解",
  "title": "建ぺい率と容積率の違い",
  "subtitle": "ポイントは「真上から見るか」「すべての階を合計するか」",
  "left": {
    "label": "建ぺい率",
    "catch": "…",
    "formula": "建築面積 ÷ 敷地面積 × 100",
    "example": "…",
    "memo": "見る方向：真上から",
    "visual": "land"
  },
  "right": {
    "label": "容積率",
    "catch": "…",
    "formula": "延床面積 ÷ 敷地面積 × 100",
    "example": "…",
    "memo": "見る方向：すべての階を合計",
    "visual": "floors",
    "floors": ["3階 80㎡", "2階 80㎡", "1階 80㎡"]
  },
  "exam_point": "試験では…",
  "quiz": {
    "question": "…",
    "answers": [
      { "text": "建ぺい率：50%", "highlight": false },
      { "text": "容積率：120%", "highlight": true }
    ]
  }
}
```

| `visual` | 意味 |
|----------|------|
| `land` | 敷地＋建築面積（平面） |
| `floors` | 階別積み上げ（`floors` 配列でラベル） |

新しい `type` を増やすときは `tools/term_diagram.py` の `render_diagram()` を拡張し、このドキュメントに型を追記し、**§6 デザイン仕様** に HTML クラスと見た目を追記する。

---

## 6. デザイン仕様（必須）

図解は **学習用の図表** として読みやすさ・サイト全体との統一を最優先する。  
JSON や HTML を独自デザインで書き換えず、**`site-pages.css` の `.term-diagram-*` と CSS 変数**に従う。

**スタイルの正本:** `site-pages.css`（`/* 用語解説 HTML 図解 */` ブロック）  
**色・タイポの親ルール:** [seo-article-guidelines.md](./seo-article-guidelines.md)（`theme.accent` は図解では補助、主役は `--ink` / `--green`）

### 6.1 デザイン原則

| 原則 | 内容 |
|------|------|
| **サイトトーンに合わせる** | 白背景・細いボーダー・控えめな影。派手なグラデ・原色の直書きは禁止 |
| **CSS 変数のみ** | `#121212` 等の直書きは `site-pages.css` 内のみ。JSON・HTML に `style=` やインライン色を入れない |
| **図は装飾、文字が本体** | 図形（`aria-hidden`）は補助。式・例・キャッチコピーが主情報 |
| **2カラムは md 以上** | 768px 未満は1カラム縦積み。横スクロール前提の幅固定は禁止 |
| **アクセントは緑で統一** | ラベル「例」・ハイライト答え・eyebrow に `--green`（サイト共通の成功・強調色） |
| **新規サイトも既存サイトも同型** | テンプレの `site-pages.css` を同期すれば見た目は揃う。サイトごとに図解 CSS を分叉しない |

### 6.2 レイアウト構成（`compare_dual`）

```
┌─ .term-diagram（外枠・bg2）────────────────────────────┐
│  .term-diagram-header（中央）                            │
│    eyebrow（緑・小） / title（太字） / subtitle          │
│  .term-diagram-grid（2列 ※モバイル1列）                  │
│  ┌─ .term-diagram-card ─┐  ┌─ .term-diagram-card ─┐   │
│  │ ピル型 label（ink）   │  │                       │   │
│  │ catch（太字）         │  │                       │   │
│  │ visual（land/floors） │  │                       │   │
│  │ 計算式ボックス（灰）   │  │                       │   │
│  │ 例ボックス（緑枠）     │  │                       │   │
│  │ memo                  │  │                       │   │
│  └───────────────────────┘  └───────────────────────┘   │
│  .term-diagram-exam-point（灰背景）                      │
│  .term-diagram-quiz（一問一答・2列答え）                 │
└──────────────────────────────────────────────────────────┘
```

- 用語記事では外側に `<section class="term-diagram-section">` + `<h2>図解で理解する</h2>`
- 問題解説（将来）は `.q-exp-diagram` 内に同じ `.term-diagram` をネスト

### 6.3 タイポグラフィ

| 要素 | クラス | サイズ・ウェイト |
|------|--------|------------------|
| カテゴリ見出し | `.term-diagram-eyebrow` | `--fs-caption`、700、`letter-spacing: 0.08em` |
| 図解タイトル | `.term-diagram-title` | `clamp(1.125rem … 1.375rem)`、800 |
| サブタイトル | `.term-diagram-subtitle` | `--fs-sub`（14px）、700、`--text2` |
| カード見出し（ピル） | `.term-diagram-card-label` | `--fs-body`（16px）、800、白文字 on `--ink` |
| キャッチ | `.term-diagram-card-catch` | `--fs-body`、700、`min-height: 3rem` |
| 式・例の本文 | `.term-diagram-card-box-body` | `--fs-sub`、700 |
| ブロック見出し | `.term-diagram-exam-point-title` 等 | `--fs-body`、800 |

本文より **やや強調** するが、記事 H2 よりは弱い（図解内は `h3` まで）。

### 6.4 色・ボーダー・余白

| 用途 | トークン |
|------|----------|
| 外枠・カード枠 | `--border2`、角丸 `--r2`（10px） |
| 外枠背景 | `--bg2` |
| カード背景 | `--bg` + `--sh`（軽い影） |
| 図形の線 | `2px solid var(--ink)`（平面図・階図） |
| 計算式ボックス | 背景 `--bg2`、枠 `--border2`、角丸 `--r` |
| 例ボックス | 背景 `color-mix(green 8%)`、枠 `color-mix(green 28%)`、キッカー `--green` |
| 試験ポイント | 背景 `--bg2` |
| クイズ正答ハイライト | `.term-diagram-quiz-answer--highlight`（緑系 mix） |

パディング目安: 外枠 `20px`、カード `18px`、ボックス `12px 14px`、グリッド gap `16px`。

### 6.5 図形（visual）の見た目

#### `land`（平面図）

- キャンバス: **14rem × 11rem**、中央配置
- 外枠 = 敷地、内矩形 = 建築面積（`--bg2` 塗り）
- ラベル「敷地」「建築面積」は **CSS テキストのみ**（画像不可）
- 装飾は矩形と2px線のみ。イラスト・写真は使わない

#### `floors`（階積み）

- 同サイズ **14rem × 11rem**、`flex` 下寄せ
- 各階: 高さ `2.75rem`、上・左右 `2px` 枠、階ラベルは JSON の `floors` 配列（中央・太字）
- 最下段: `.term-diagram-floors-base`（地盤、`--bg3`）

**新しい visual 型**を足すときは、上記と同程度のシンプルさ・固定幅（14rem）・`--ink` 線を維持する。

### 6.6 レスポンシブ

| ブレークポイント | 挙動 |
|------------------|------|
| `< 768px` | `.term-diagram-grid` 1列、クイズ答えも1列 |
| `≥ 768px` | 比較カード2列、クイズ答え2列 |

- 図解ブロックは親の `.seo-article-card` 幅に追従（最大 `--site-readable-w` 付近）
- `overflow-x: auto` で図だけ横スクロールさせない

### 6.7 アクセシビリティ

- 装飾図: `.term-diagram-visual` に **`aria-hidden="true"`**（`term_diagram.py` で固定）
- 意味は **テキスト**（catch / formula / example / memo）で伝える
- 色だけで正誤を伝えない（クイズは文字ラベル + 任意で `--highlight`）

### 6.8 禁止・要相談

| 禁止 | 理由 |
|------|------|
| JSON / HTML に `style=""` や `<img>` を直書き | サイト間でデザインが崩れる |
| 図解専用の別 CSS ファイル | 正本は `site-pages.css` 1か所 |
| 原色・グラデ・角丸の乱用 | 試験サイトの信頼感を損なう |
| 16:9 バナー型の横長図解 | モバイルで読みにくい |
| 1カード内に3列以上 | `compare_dual` の想定外 |

| 要相談（テンプレ変更が必要） | |
|------------------------------|--|
| イラスト PNG / SVG 差し込み | 新 `visual` 型 + デザインレビュー |
| `theme.accent` を図解の主色にする | 全サイトの accent 差し替え影響 |
| ダークモード専用配色 | 現状未対応 |

### 6.9 デザイン変更の手順

1. **テンプレ**の `site-pages.css` の `.term-diagram-*` を修正
2. `kenpei-yoseki` サンプルで `terms/diagram-samples/kenpei-yoseki.html` を目視
3. `python3 tools/build_all.py`
4. 既存サイトへ `sync_from_template.py`（`site-pages.css` はマニフェスト対象）
5. この §6 と [seo-article-guidelines.md](./seo-article-guidelines.md) の矛盾がないか確認

HTML 構造を変えるときは **`tools/term_diagram.py` と CSS を同時に** 更新する。

---

## 7. 問題解説への拡張（実装時の契約）

**未実装**だが、既存サイト・新規サイトで同じルールを使う。

### 7.1 CSV 列（任意）

| ファイル | 列名 |
|----------|------|
| `data/past_questions.csv` | `diagram_id` |
| `data/practice_questions.csv` | `diagram_id` |
| `data/ichimon_questions.csv` | `diagram_id` |

### 7.2 挿入位置（推奨）

`tools/q_explanation.py` の `build_explanation_html()` 出力の、  
**「正解の理由」セクションの後・「学習のヒント」の前**に:

```html
<section class="q-exp-section q-exp-diagram" aria-labelledby="q-exp-diagram-h">
  <h3 id="q-exp-diagram-h" class="q-exp-h3">図解で整理</h3>
  <!-- term_diagram.diagram_body_html(diagram_id) -->
</section>
```

クラス `term-diagram` は用語ページと共用（`site-pages.css`）。

### 7.3 実装チェックリスト（開発者向け）

- [ ] 3種ビルドで `diagram_id` を row から読む
- [ ] `validate_csv.py` で問題 CSV の `diagram_id` 参照を検証
- [ ] サンプル1問を `q/past/` または `q/practice/` に出力
- [ ] `docs/question-static-pages.md` の列一覧を更新
- [ ] `.cursor/rules/term-diagrams.mdc` の「対応状況」を ✅ に更新

---

## 8. 検証

```bash
python3 tools/validate_csv.py    # diagram_id → JSON 存在チェック（ERROR）
python3 tools/build_all.py
```

- 存在しない `diagram_id` → **ERROR**
- 未対応の `type` → ビルド時に図解 HTML が空（セクション非表示）。WARN は今後追加可

---

## 9. SEO・公開

- 図形部分は `aria-hidden`。**評価されるのは周辺テキスト**（式・例・一問一答）
- 用語・問題ページとも **index 対象**（執筆サンプル `g-diagram-sample.html` 等は `noindex`）
- 画像検索は想定しない（CSS 図）。将来 `og:image` 用サムネを別途用意する場合は別契約

---

## 10. 関連ドキュメント

| ドキュメント | 内容 |
|--------------|------|
| [glossary-term-template.md](./glossary-term-template.md) | 用語 CSV・ページ構成 |
| [knowledge-hub-article-templates.md](./knowledge-hub-article-templates.md) | 比較表・早見・誤答 |
| [question-static-pages.md](./question-static-pages.md) | 問題静的ページ |
| [multi-site-workflow.md](./multi-site-workflow.md) | テンプレ → 本番同期 |
| [integration-checklist.md](./integration-checklist.md) | サイト統合の全体 |

サンプル JSON: `data/term_diagrams/kenpei-yoseki.json`
