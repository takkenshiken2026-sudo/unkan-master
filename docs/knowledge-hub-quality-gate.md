# 知識ハブ（比較・数値・誤答）公開前ゲート

`comparisons.csv` / `numbers.csv` / `mistakes.csv` を資格向けに執筆・公開する際の**必須チェック**です。  
機械検証は体裁とリンクの門番であり、**事実の正しさは専門監修が担保**します。

関連: [knowledge-hub-article-templates.md](./knowledge-hub-article-templates.md) · [editorial-quality.md](./editorial-quality.md)

---

## 公開の条件（すべて必須）

| # | 項目 | 担当 |
|---|------|------|
| 1 | `python3 tools/validate_csv.py` → **ERROR 0** | 機械 |
| 2 | `python3 tools/audit_editorial_quality.py`（利用可能なサイト）→ 未執筆マーカーなし | 機械 |
| 3 | `python3 tools/build_all.py` 成功 | 機械 |
| 4 | `validate_internal_links` / `validate_public_content` 成功 | 機械 |
| 5 | 数値・期限が一次情報と一致（年度明記） | **資格専門家** |
| 6 | 誤答の wrong/correct が試験上妥当 | **資格専門家** |
| 7 | 誤字・表記ゆれ・他資格用語の混入なし | **校正** |
| 8 | リード・表・FAQ の矛盾なし | 執筆者＋監修 |
| 9 | テンプレ汎用行（過去問と模擬試験の違い 等）をそのまま公開していない | 執筆者 |

---

## 記事ごとの監修シート（1行＝1記事）

| 列 | 記入内容 |
|----|----------|
| slug / title | CSV の識別 |
| 一次情報 URL | 試験要項・省令・団体公式 |
| 根拠 | 条文・要項箇所・過去問番号 |
| 監修者 | 氏名またはイニシャル |
| 監修日 | YYYY-MM-DD |
| 校正 | 済 / 未 |

**numbers / mistakes は監修者・監修日が空の行を公開しない。**

---

## 執筆の進め方（推奨）

1. 資格ごとのトピック台帳（S30原本 + S31–S44）を `write_*_hub_sXX_content.py` で管理  
2. `python3 tools/write_*_hub_data.py` で **150件/種** を再生成（`MIN_ANGLE_COLLAPSE_BATCH=99`）  
3. `scaffold_knowledge_hub_article.py --append` → 置換 → 監修 → 校正  
4. 上表ゲートを通過してから commit / push  

テンプレの宅建・汎用サンプル行は `data/archive/hub-template-placeholders/` に退避済みであること。資格向けに書き直す。

---

## ビルド上の注意

- 本番150件確認: `python3 ~/Projects/scripts/_hub_sync_and_verify.py`（横断）  
- 数値照合: `~/Projects/docs/hub_numbers_verified.json` + `scripts/_hub_numbers_bulk_verify_pending.py`  
- `build_all.py` は `build_glossary_pages` の**後**に `build_compare_pages` / `build_numbers_mistakes_pages` を実行すること  
- `build_glossary_pages.py` は `compare` / `numbers` / `mistakes` ディレクトリを削除しない（`PRESERVED_TERM_SUBDIRS`）  
- kikenbutsu / kangyou は push 後 **gh-pages** 同期を忘れない  

Step 0 適用: `python3 tools/apply_knowledge_hub_step0.py --target /path/to/site`
