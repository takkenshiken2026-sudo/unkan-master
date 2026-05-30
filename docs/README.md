# ドキュメント一覧

資格対策サイトテンプレート（exam-site-shell）の運用ルールは、この `docs/` と `.cursor/rules/` に集約しています。

**フォルダがごちゃついて見えるときは先に [ORGANIZATION.md](./ORGANIZATION.md)**（役割・ルール3層・マスター3本・日常フロー）。

## 読む順番

1. **[ORGANIZATION.md](./ORGANIZATION.md)** … 全体像・どのルールが正本か
2. リポジトリ直下の [README.md](../README.md) … セットアップとビルド
3. **[integration-checklist.md](./integration-checklist.md)** … **過去問ハブ・3モードタブ・フッター・用語一覧を一回で揃える**（本番同期・再発防止）
3. **[seo-article-guidelines.md](./seo-article-guidelines.md)** … 記事・用語・色・内部リンク・公開前チェック（**正本**）
   - **試験ガイド × 用語解説の立ち位置:** **[content-positioning.md](./content-positioning.md)**
   - **編集品質（専門家×プロライター）:** **[editorial-quality.md](./editorial-quality.md)**
   - 試験ガイドのジャンル MECE（12区分）: **[guide-article-genres.md](./guide-article-genres.md)**
   - 100本以上の slug 例: **[guide-article-catalog.md](./guide-article-catalog.md)**
   - 新規記事テンプレ（CSV・スクリプト）: **[guide-article-template.md](./guide-article-template.md)**
   - **用語詳細記事テンプレ（全用語必須）:** **[glossary-term-template.md](./glossary-term-template.md)**
   - **知識ハブ（比較・数値・誤答）:** **[knowledge-hub-article-templates.md](./knowledge-hub-article-templates.md)**（各 **150〜153 件** 目標）
   - **HTML 図解（用語・問題解説への埋め込み）:** **[term-diagrams.md](./term-diagrams.md)**
   - **ヘッダー・フッター統一:** **[site-chrome.md](./site-chrome.md)**（過去問演習 vs 過去問一覧の分離）
   - **レスポンシブ UI:** **[responsive-layout.md](./responsive-layout.md)**（`site-pages.css`・viewport・モバイル目視）
   - 過去問・実践演習・一問一答（静的 `q/`）: **[question-static-pages.md](./question-static-pages.md)**
   - **読み込み性能（一覧・SPA）:** **[performance-loading.md](./performance-loading.md)**
   - アフィリエイト記事（テーマ→自動作成）: **[affiliate/README.md](./affiliate/README.md)**
4. [.cursor/rules/site-integration.mdc](../.cursor/rules/site-integration.mdc) … Cursor 向け要約（`q/`・フッター・用語一覧・本番同期）
4b. [.cursor/rules/site-chrome-nav.mdc](../.cursor/rules/site-chrome-nav.mdc) … ヘッダー過去問（`/#past`）とフッター過去問一覧（`q/index.html`）の分離
4d. [.cursor/rules/knowledge-hub-content.mdc](../.cursor/rules/knowledge-hub-content.mdc) … 比較/数値/誤答 各150件/種・CSV品質
5. [.cursor/rules/practice-ichimon-static.mdc](../.cursor/rules/practice-ichimon-static.mdc) … 実践・一問一答 CSV・一覧 UI・取り込み
6. [.cursor/rules/seo-article-template.mdc](../.cursor/rules/seo-article-template.mdc) … Cursor 向け要約（SEO / CSV / CSS 編集時）
7. [.cursor/rules/glossary-term-template.mdc](../.cursor/rules/glossary-term-template.mdc) … 用語詳細記事（全用語フル記事必須）
7b. [.cursor/rules/term-diagrams.mdc](../.cursor/rules/term-diagrams.mdc) … HTML 図解（新規サイト・既存サイト同期）
8. [.cursor/rules/editorial-quality.mdc](../.cursor/rules/editorial-quality.mdc) … 専門家×プロライター水準の執筆・検証
8b. **[seo-editorial-rollout-template.md](./seo-editorial-rollout-template.md)** … SEO 記事デザイン確定分の全サイト展開テンプレ（2026-05）
8c. **[seo-editorial-rollout-checklist.md](./seo-editorial-rollout-checklist.md)** … 全サイト反映の手順・ゲート・台帳（**展開時はここから**）
8d. [.cursor/rules/seo-editorial-rollout.mdc](../.cursor/rules/seo-editorial-rollout.mdc) … 上記の Cursor 向け要約
9. [.cursor/rules/affiliate-article.mdc](../.cursor/rules/affiliate-article.mdc) … アフィリエイト記事・ブリーフ編集時
10. [.cursor/rules/exam-site-shell-template.mdc](../.cursor/rules/exam-site-shell-template.mdc) … テンプレ全体の必須事項（常時適用）

## ルールの優先順位（矛盾したとき）

1. **`tools/build_all.py` が通る検証**（`validate_csv` / `validate_generated_seo` / `validate_internal_links` / `validate_public_content`）… 公開物の実態に最も近い
2. **[integration-checklist.md](./integration-checklist.md)** … `q/` ハブ・フッター・用語一覧の統合（フッター過去問 URL、タブ、`shortDef` 等）
3. **[seo-article-guidelines.md](./seo-article-guidelines.md)** … 人間向けの正本。検証に落とし込めていない細部はこちらに従う
4. **`.cursor/rules/*.mdc`** … 編集支援用の要約。上記と食い違う記述は 1〜3 を優先する

## テンプレート標準（要約）

| 項目 | ルール |
|------|--------|
| 本番ボリューム | 試験ガイド 100本以上、用語 300件以上、**比較/数値/誤答 各150件/種**、アフィリエイト **10本目安** |
| 公開ページ | 運用者向け（独自メモ・更新方針・テンプレ説明等）を表・一覧・本文に出さない |
| 内部リンク | リンク切れゼロ（`validate_csv` + `validate_internal_links`） |
| 色 | `site-config.json` の `theme.accent`、カードは中立・ラベルのみジャンル色 |
| ビルド | `python3 tools/build_all.py` 成功後のみ公開 |

## 主要ツール

| スクリプト | 役割 |
|------------|------|
| `tools/build_all.py` | 一括ビルド（検証込み） |
| `tools/validate_csv.py` | CSV と内部リンク先の事前検証 |
| `tools/audit_editorial_quality.py` | 試験ガイド・用語の編集品質（`build_all` 含む。`--strict` で WARN も失敗） |
| `tools/scaffold_guide_article.py` | 試験ガイド CSV 行の雛形生成 |
| `tools/scaffold_glossary_term.py` | 用語詳細記事 CSV 行の雛形生成 |
| `tools/scaffold_affiliate_article.py` | アフィリエイト記事（ブリーフ YAML + CSV 行） |
| `tools/validate_generated_seo.py` | 生成 HTML の構成・禁止行 |
| `tools/validate_site_integration.py` | フッター過去問 URL・q ハブタブ・用語 `shortDef`・**実践/一問一答 CSV 件数・分野順一覧** |
| `tools/audit_integration_rules.py` | マニフェスト・build_all・ドキュメント・Cursor ルールの整合監査 |
| `tools/import_orig_questions_to_practice_csv.py` | SPA `ORIG_QUESTIONS` → `practice_questions.csv` |
| `tools/import_base_questions_to_ichimon_csv.py` | 過去問＋実践4択 → `ichimon_questions.csv` |
| `tools/validate_internal_links.py` | 全内部 `href` の整合性 |
| `tools/validate_public_content.py` | 公開 HTML の運用者向け文言・禁止表の検出 |
| `tools/audit_article_freshness.py` | 更新管理列の監査（任意） |
| `tools/stress_config_build.py` | 長いサイト名・多分野での表示確認（任意） |
| `tools/sync_from_template.py` | 共通エンジンを本番へコピー（`--target` 必須） |
| `tools/check_template_drift.py` | テンプレと本番の差分一覧 |

## 生成物について

- `public_site/` … `build_all` の出力（Git 管理外）。配布用バンドル。
- `exam-site-data-past.js` / `exam-site-data-practice.js` / `exam-site-data-ichimondou.js` … SPA 用（CSV から自動生成）
- `q/past/` … 過去問静的ページ、`q/practice/` … 実践演習、`q/ichimon/` … 一問一答（`build_past_question_pages.py` / `build_practice_ichimon_pages.py`）
