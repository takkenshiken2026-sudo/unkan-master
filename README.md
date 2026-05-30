# 運管マスター（unkan-master）

運行管理者試験の対策学習サイト。`exam-site-shell` テンプレートをベースに、SPA（過去問・実践演習・一問一答）と静的 SEO ページ（試験ガイド・用語集・過去問ハブ）を生成します。

- 公開 URL: https://unkan-master.jp
- テンプレート（正本）: `~/Projects/exam-site-shell`
- 試験実施団体: 公益財団法人 運行管理者試験センター（https://www.unkan.or.jp/）

## クイックスタート

```bash
python3 tools/build_all.py
python3 -m http.server 8765
```

- トップ（SPA）: http://127.0.0.1:8765/
- 試験ガイド: http://127.0.0.1:8765/articles/
- 用語集: http://127.0.0.1:8765/terms/
- 過去問ハブ: http://127.0.0.1:8765/q/

## このリポジトリで編集するファイル

サイト固有部のみ編集してください。共通 UI／ビルドエンジンはテンプレ側（`exam-site-shell`）で更新し、`sync_from_template.py` で取り込みます。

| 編集対象 | 内容 |
|----------|------|
| `site-config.json` | ブランド名・試験名・ドメイン・分野・ナビ・公式リンク |
| `data/past_questions.csv` | 過去問 |
| `data/practice_questions.csv` | 実践演習（任意） |
| `data/ichimon_questions.csv` | 一問一答（任意） |
| `data/glossary_terms.csv` | 用語集 |
| `data/guide_articles.csv` | 試験ガイド |
| `index.html` | 学習 SPA（過去問・一問一答・用語など） |
| `CNAME` | 公開ドメイン |

## 自動生成（手編集しない）

`exam-site-data-past.js`, `exam-site-data-practice.js`, `exam-site-data-ichimondou.js`,
`site-config.js`, `site-theme.css`, `sitemap.xml`,
`articles/**`, `terms/g-*.html`, `q/**`, `public_site/`

## テンプレからの同期

UI やビルドの修正はテンプレ側で行い、本リポジトリへ取り込みます。

```bash
cd ~/Projects/exam-site-shell
python3 tools/check_template_drift.py --target ~/Projects/unkan-master
python3 tools/sync_from_template.py    --target ~/Projects/unkan-master --dry-run
python3 tools/sync_from_template.py    --target ~/Projects/unkan-master --build
```

詳しくはテンプレの `docs/multi-site-workflow.md` を参照。

## 注意

同梱 CSV・`example.com` リンクはサンプルです。本番公開前に公式 URL・権利・プライバシー・GA4 を必ず確認してください。
