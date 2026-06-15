# exam-site-shell 整理ガイド

このリポジトリが「ぐちゃぐちゃ」に感じる主な理由と、**どこを正本として読むか**を1枚にまとめたものです。

---

## 1. このリポジトリの役割（3つだけ）

| 役割 | 中身 | 触るタイミング |
|------|------|----------------|
| **A. 共通エンジン** | `tools/` のビルド・検証・`html_footer.py` など | UI修正・バグ修正・全サイトへ sync するとき |
| **B. ルールの正本** | `docs/` の運用ドキュメント | 記事・用語・フッター・同期手順を決めるとき |
| **C. 動作サンプル** | ルートの `index.html`, `data/`, 生成された `articles/` `terms/` `q/` | テンプレで `build_all` を試すとき |

**本番10サイトの実データはここには置かない。** 各サイトは `~/Projects/<サイトID>/` が正本です。

---

## 2. ルールは3層 — 矛盾したらこの順

```
① 機械の正本 … build_all.py が実行する validate_*.py / audit_*.py
② 人間の正本 … docs/ 内の「マスター」3本（下表）
③ Cursor要約 … .cursor/rules/*.mdc（編集補助。②と食い違ったら②＋①に従う）
```

### マスター3本（まずここだけ読む）

| 用途 | ドキュメント |
|------|----------------|
| **テンプレ → 本番へ反映** | [multi-site-workflow.md](./multi-site-workflow.md) |
| **フッター・過去問ハブ・用語一覧を揃える** | [integration-checklist.md](./integration-checklist.md) + [site-chrome.md](./site-chrome.md) |
| **記事・用語・色・公開境界** | [seo-article-guidelines.md](./seo-article-guidelines.md) |

### 横断運用（全10サイト）

| 用途 | ドキュメント |
|------|----------------|
| **本番サイト一覧・URL・Git** | [site-registry.md](./site-registry.md) |
| **デプロイ標準（GitHub Actions）** | [DEPLOY.md](./DEPLOY.md) |
| **一括スクリプト** | [~/Projects/scripts/README.md](../../scripts/README.md) |

### サブガイド（必要なときだけ）

| トピック | ドキュメント |
|----------|----------------|
| 試験ガイドの書き方 | [guide-article-template.md](./guide-article-template.md), [guide-article-genres.md](./guide-article-genres.md) |
| 用語詳細 | [glossary-term-template.md](./glossary-term-template.md) |
| 過去問静的 `q/` | [question-static-pages.md](./question-static-pages.md) |
| スマホレイアウト | [responsive-layout.md](./responsive-layout.md) |
| 全サイトSEO展開（完了済み作業の記録） | [seo-editorial-rollout-checklist.md](./seo-editorial-rollout-checklist.md) |
| 知識ハブ（比較・数値・誤答 — **各150件/種**） | [knowledge-hub-article-templates.md](./knowledge-hub-article-templates.md) · [knowledge-hub-quality-gate.md](./knowledge-hub-quality-gate.md) |

### Cursor ルール（`.cursor/rules/`）

`.mdc` は上記 `docs/` の**要約**。新規ルールを増やすより、**マスター3本を直して要約を追従**させる。

---

## 3. フォルダの意味

```
exam-site-shell/
├── README.md              … クイックスタート
├── docs/
│   ├── README.md          … ドキュメント索引（詳細版）
│   ├── ORGANIZATION.md    … このファイル
│   ├── audit/             … 監査CSV・ログ用（本番データではない）
│   └── affiliate/         … アフィリエイト（placement-and-rollout・記事ルール・SITE.template）
├── sites/
│   ├── README.md          … 本番サイトID一覧・SITE.md への入口
│   └── <サイトID>/        … 本番パス・同期メモ（コードは置かない）
├── tools/
│   ├── README.md          … スクリプト分類（日常 / 同期 / バッチ）
│   ├── build_all.py       … 日常の入口
│   ├── sync_from_template.py
│   └── template_sync_manifest.txt  … 本番へコピーするファイル一覧
├── data/                  … テンプレ用サンプル CSV
├── articles/ terms/ q/    … build_all の生成物（手編集しない）
└── public_site/           … 配布用出力（.gitignore）
```

### ここにないもの（混同注意）

| 場所 | 正体 |
|------|------|
| `~/Projects/scripts/` | **モノレポ用**の一括運用（`_deploy_*.py`, `_hub_*.py` 等） |
| `~/Projects/docs/hub_numbers_verified.json` | 全サイト共通の数値照合レジストリ（正本） |
| 各本番 `docs/seo-editorial-rollout-checklist.md` | テンプレからコピーされた**コピー**（正本はテンプレ側） |

---

## 4. tools/ が多い理由

約150本の `.py` がありますが、**日常は16本だけ**（`build_all.py` から呼ばれるもの）。

| 分類 | 件数目安 | 使う？ |
|------|----------|--------|
| **build_all 本線** | 16 | 毎回 |
| **manifest 同期対象** | 40前後 | テンプレ修正時 |
| **run_* / write_*_hub_* バッチ** | 60前後 | 過去の一括作業用。普段は不要 |
| **\*_guide_content_lib.py** | 10前後 | サイト別ガイド原稿生成（テンプレ検証用） |

一覧: [tools/README.md](../tools/README.md)

---

## 5. 整理後の日常フロー（これだけ覚える）

### テンプレの見た目・ビルドを直す

```bash
cd ~/Projects/exam-site-shell
# 1. マスター3本のどれに関係するか確認
# 2. tools/ または site-pages.css を編集
python3 tools/build_all.py
```

### 本番1サイトへ反映

```bash
python3 tools/check_template_drift.py --target ~/Projects/takken-master
python3 tools/sync_from_template.py --target ~/Projects/takken-master --dry-run
python3 tools/sync_from_template.py --target ~/Projects/takken-master --build
cd ~/Projects/takken-master && git status && git commit && git push
```

### 本番のコンテンツだけ直す

**exam-site-shell は触らない。** `~/Projects/<サイト>/data/*.csv` を編集 → そのサイトで `build_all.py`。

---

## 6. 知識ハブ Phase B（2026-05-31 完了）

| 項目 | 正本 |
|------|------|
| 件数目標 | `tools/knowledge_hub_rules.py`（150〜153件/種） |
| 再生成 | 各サイト `tools/write_*_hub_data.py` |
| 一括検証 | `~/Projects/scripts/_hub_sync_and_verify.py` |
| 数値照合 | `~/Projects/docs/hub_numbers_verified.json` + `_hub_numbers_bulk_verify_pending.py` |
| 監査 | 各サイト `tools/audit_hub_quality.py`（`ROOT=parents[1]`） |

横断手順: `~/Projects/docs/HUB_QUALITY_PIPELINE.md`

---

## 7. 整理状況（2026-05-31）

- [x] マスター3本 + `ORGANIZATION.md` を入口に統一
- [x] `.cursor/rules/` を 3 ファイルに集約（template / site-workflow / content-authoring）
- [x] 一括バッチは `tools/archive/`（約90本）
- [x] モノレポ一括は `~/Projects/scripts/`
- [x] 本番の重複 checklist をテンプレ参照スタブに差し替え
- [x] 生成物方針: [generated-artifacts.md](./generated-artifacts.md)
