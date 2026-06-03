# アフィリエイト記事（本番サイト用スタブ）

**このファイルは本番リポジトリの `docs/affiliate/` に置く短い案内用です。**  
詳細ルール・テンプレ・UI 仕様は **exam-site-shell 正本** を参照してください。

## 正本（必読）

| 文書 | パス（exam-site-shell） |
|------|-------------------------|
| ルール全体 | `docs/affiliate/affiliate-article-rules.md` |
| マルチサイト手順 | `docs/affiliate/multi-site-affiliate-workflow.md` |
| 作成フロー | `docs/affiliate/auto-create-workflow.md` |
| 書籍テンプレ | `docs/affiliate/templates/affiliate-textbooks-recommend/` |
| 講座テンプレ | `docs/affiliate/templates/affiliate-online-course-compare/` |
| Cursor ルール | `.cursor/rules/affiliate-article.mdc` |

## 本番で編集するファイル

| パス | 内容 |
|------|------|
| `data/affiliate-briefs/{slug}.yaml` | 商品・ASP URL・価格 |
| `data/guide_articles.csv` | 記事本文・`fact_checked_at`・`related_links` |
| `images/affiliate/` | 表紙・サムネ（fetch 後） |

## テンプレ同期

UI（比較表・カード・要点表紙）を更新するとき:

```bash
cd ~/Projects/exam-site-shell
python3 tools/sync_from_template.py --target ~/Projects/THIS-SITE --build
```

## 禁止事項（正本と同じ）

- ASP URL 未確定で CSV 公開行を作らない
- 【PR・広告】を載せない
- テンプレ置換のみで公開しない
- 価格を URL 確認なしで転記しない

---

*このスタブ以外の長文ルールを本番 `docs/affiliate/` に置かない（旧版コピーは削除推奨）。*
