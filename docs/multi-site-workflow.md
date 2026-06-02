# マルチサイト運用（テンプレ → 本番）

`exam-site-shell` を**正本**にし、資格ごとの本番リポジトリへ「共通エンジン」だけを流し込む手順です。

## 原則

| 層 | 置き場所 | 編集 |
|----|----------|------|
| 共通 UI・ビルド・検証 | **exam-site-shell** | ここだけ直す |
| サイト名・色・CSV・SPA | **本番リポジトリ** | サイト側だけ |
| 公開 HTML（`q/`, `articles/`, `terms/`） | 本番で **生成** | 手編集しない |

「テンプレを再現する」= マニフェストのファイルを同期し、本番で `build_all.py` を回して生成物を揃える、という意味に統一します。

**過去問ハブ・フッター・用語一覧を同時に直すとき**は、先に [integration-checklist.md](./integration-checklist.md) の契約一覧と検証手順に従ってください（個別修正だけだと再発しやすい項目をまとめています）。

## ファイル一覧

| ファイル | 役割 |
|----------|------|
| `tools/template_sync_manifest.txt` | テンプレ → 本番へ**コピーする**パス |
| `tools/template_site_only.paths` | 本番だけが持つパス（**上書きしない**） |
| `tools/sync_from_template.py` | 同期実行 |
| `tools/check_template_drift.py` | 差分確認 |
| `sites/<サイトID>/` | サイトメモ・固有拡張の置き場（テンプレ内） |

## 手順（本番へ反映するとき）

1. **テンプレで修正** — `site-pages.css`, `tools/build_*.py`, `tools/html_footer.py` など
2. **テンプレでビルド確認** — `python3 tools/build_all.py`
3. **差分確認（任意）** — 本番パスを自分で指定:

   ```bash
   python3 tools/check_template_drift.py --target /path/to/your-production-site
   ```

4. **同期** — `--target` は必須（特定リポジトリは自動では触らない）:

   ```bash
   python3 tools/sync_from_template.py --target /path/to/your-production-site --dry-run
   python3 tools/sync_from_template.py --target /path/to/your-production-site --build
   ```

5. **本番リポジトリで commit / push** — 運用者が実施

`--build` は先方ディレクトリで `tools/build_all.py` を実行します。本番の `data/*.csv` と `site-config.json` はそのまま使われます。

## コピーしないもの（生成・固有データ）

- `site-config.json`, `data/`, `index.html`（SPA）
- `q/`, `articles/`, `terms/`, `public_site/`
- サイト固有 `tools/past_question_seo.py` など（`template_site_only.paths` 参照）

詳細は `tools/template_site_only.paths` を正とします。

## 新規サイトを立ち上げるとき

1. テンプレをコピーして新リポジトリを作る（または fork）
2. `sites/_example/` を参考に `sites/<新サイトID>/SITE.md` を追加
3. `site-config.json` と `data/*.csv` を差し替え
4. `python3 tools/build_all.py`
5. 以降の UI 修正はテンプレ → `sync_from_template.py` のループ

## サイト固有の拡張

本番だけのロジック（例: 過去問 SEO 拡張・マスターデータ JS）は、本番リポジトリの `tools/` に置き、**マニフェストに含めない**でください。

テンプレ側では `sites/<サイトID>/notes.md` に「何を固有にしているか」だけ記録します（コードの二重管理を防ぐため）。

## Cursor で編集するとき

- 見た目・HTML 構造・共通 generator の変更は **exam-site-shell のみ**
- 会話で「テンプレ再現」と言われたら、先に `check_template_drift` で差分を見てからテンプレを直す
- 本番リポジトリの URL を明示されない限り、エージェントは本番を直接編集しない

## デプロイ（本番公開）

全10サイトは **GitHub Actions → GitHub Pages** を標準とします。詳細: [DEPLOY.md](./DEPLOY.md) · 一覧: [site-registry.md](./site-registry.md)

```bash
# ローカル確認
python3 tools/build_all.py
git push origin main   # → Deploy GitHub Pages workflow
```

| サイト種別 | 備考 |
|------------|------|
| 標準（8サイト + 移行中2サイト） | `.github/workflows/deploy-pages.yml` |
| eisei1shu | 独自 workflow（Supabase 等）— 標準 workflow で上書きしない |
| kangyou / kikenbutsu | 旧 `gh-pages` 配信 → Actions へ移行（Pages Source を切替） |

横断状態確認: `bash ~/Projects/scripts/check_deploy_status.sh`

## トラブルシュート

| 症状 | 対処 |
|------|------|
| 一覧は直ったが個別過去問だけ古い | 本番で `build_past_question_pages.py` または `build_all.py` 未実行 |
| 実践・一問一答がサンプル数のまま | CSV 未拡充・[integration-checklist.md §6](./integration-checklist.md) の取り込み → `build_all` |
| 一問一答が年度順 | テンプレ同期 + `build_all`（`groupBy: category` 必須） |
| CSS だけ古い | 同期漏れ or ブラウザキャッシュ（`site-pages.css?v=` を確認） |
| 同期したのにレイアウトが違う | 本番に `template_site_only.paths` 外の独自 HTML/CSS が残っていないか `drift` で確認 |
| フッター過去問が遷移しない / ハブにタブがない / 用語定義が空 | [integration-checklist.md](./integration-checklist.md) §2・§5 |
| push したが本番が古い | [DEPLOY.md](./DEPLOY.md) — Pages Source が Actions か、workflow 成功か確認 |
| `main` は新しいが本番だけ古い（kangyou / kikenbutsu） | **レガシー `gh-pages` 配信の残存**。Pages Source を GitHub Actions に切替 |
