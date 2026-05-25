# アフィリエイト記事ブリーフ

記事テーマの入力ファイルを `{slug}.yaml` として置く。

- テンプレ: `docs/affiliate/theme-brief.template.yaml`
- 生成: `python3 tools/scaffold_affiliate_article.py --theme <key> --slug <slug> --append`
- または: `python3 tools/scaffold_affiliate_article.py --from-brief data/affiliate-briefs/<slug>.yaml --append`

このディレクトリの YAML はビルド対象外（運用・AI 用）。
