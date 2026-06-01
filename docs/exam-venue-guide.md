# 試験会場ガイド記事の執筆ルール

`exam-venue-and-region`・`shiken-kaijo`・`*-center` など、**会場・アクセス**を扱う試験ガイドの正本です。

## 基本方針

| 載せる | 載せない |
|--------|----------|
| 公式サイトへのリンク（Markdown `[ラベル](URL)`） | 会場の住所・最寄り駅・徒歩ルート・出口番号 |
| 「受験票の表記が正本」という注意 | 地図・交通の二次転載（SNS・まとめサイト） |
| 前日確認チェックリスト（**項目名**のみ） | 当サイト独自の経路案内・所要時間の断定 |

アクセス節の箇条書き（「最寄り駅を確認する」等）は **読者が公式案内で埋める欄** として書く。具体的な駅名・住所は本文に書かない。

## 公式 URL の出どころ

| 試験 | 会場リンク |
|------|------------|
| JISSH 系（一衛・二衛・ボイラー等） | `tools/exam_venue_official_links.py` の `CENTER_PAGES` / `EXAM_PORTAL` / `JISSH_VENUE_HUB` |
| その他 | `site-config.json` の `externalLinks`（各試験の公式） |

センター slug は `chubu-center` のように `CENTER_PAGES` のキーと一致させる。

## 本文生成（手書き禁止）

`tools/archive/*_guide_content_lib.py` では次の shared 関数を使う（直書きしない）。

- `exam_venue_basic_info_prose` … センター「基本情報」
- `exam_venue_access_prose` … 「アクセス方法」（`venue_page_md` 必須）
- `exam_application_venue_prose` … 「申込手順と会場」（`official_page_md` 推奨）
- `jissh_center_list_prose` … `shiken-kaijo` の全国9センター一覧

lib 未対応時は `python3 tools/patch_guide_venue_official_links.py` でパッチ。

## CSV・公開ページで必須

1. **`primary_sources`** … 協会公式 + 試験案内 + 会場ページ（`|` 区切り）
2. **FAQ** … 「住所・アクセスはどこで確認」→ 公式リンク + 受験票が正本
3. **公式情報の確認** … `build_article_pages.py` が slug から自動挿入（`*-center` / ハブ）

## 新規・修復パイプライン

```bash
# exam-site-shell 正本
python3 tools/patch_guide_venue_official_links.py   # lib 初回・更新時

# サイトごと
python3 tools/sync_from_template.py --target ~/Projects/eisei2shu-master
python3 tools/fix_exam_venue_guide_articles.py --target ~/Projects/eisei2shu-master   # *-center
python3 tools/fix_exam_venue_hub_articles.py --target ~/Projects/eisei2shu-master    # ハブ
python3 tools/build_article_pages.py   # サイトルートで実行
```

全サイト一括: `bash tools/run_exam_venue_official_links_batch.sh`

## 記事種別

| slug 例 | 用途 |
|---------|------|
| `exam-venue-and-region` | 受験地・会場の確認（全試験共通ハブ） |
| `shiken-kaijo` | JISSH 全国センター一覧（二衛等） |
| `*-center` | 地域センター個別（JISSH のみ現状） |

## 監査

- 本文に住所パターン（都道府県+市区+番地）がないか目視
- `check_guide_row_coherence` が ERROR なら `fix_*` を再実行
- 配信前: `build_article_pages.py` → `prepare_public_site.sh` または CI
