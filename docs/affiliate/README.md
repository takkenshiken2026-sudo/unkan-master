# アフィリエイト記事ドキュメント

資格試験サイト向けアフィリエイト記事の **作成ルール** と **テーマ入力→自動生成** の手順。

| ファイル | 用途 |
|----------|------|
| [affiliate-article-rules.md](./affiliate-article-rules.md) | 運用・UI・法務の正本（汎用） |
| [theme-brief.template.yaml](./theme-brief.template.yaml) | 記事テーマ入力テンプレ（コピーして使う） |
| [auto-create-workflow.md](./auto-create-workflow.md) | 人間・AI・CLI の自動作成フロー |

## クイックスタート

```bash
# 定義済みテーマ一覧
python3 tools/scaffold_affiliate_article.py --list-themes

# テーマからブリーフ YAML + CSV 行を生成（確認のみ）
python3 tools/scaffold_affiliate_article.py --theme textbooks-recommend --slug affiliate-textbooks-recommend

# CSV に追記 + ブリーフ保存
python3 tools/scaffold_affiliate_article.py --theme textbooks-recommend --slug affiliate-textbooks-recommend --append

# ビルド
python3 tools/build_all.py
```

生成されたブリーフ: `data/affiliate-briefs/{slug}.yaml`

Cursor で編集するときは `.cursor/rules/affiliate-article.mdc` を参照。

関連: [seo-article-guidelines.md](../seo-article-guidelines.md)（識別・ASP・10本目安）、[guide-article-catalog.md](../guide-article-catalog.md)（slug 例）
