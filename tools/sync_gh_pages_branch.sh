echo "sync_gh_pages_branch.sh: 非推奨 — GitHub Actions デプロイへ移行してください（exam-site-shell/docs/DEPLOY.md）" >&2
#!/usr/bin/env bash
# 本番が gh-pages ブランチ配信のリポジトリ向け: ビルド済み main を gh-pages に同期する。
# kikenbutsu-master / kangyou-master など。リモートに gh-pages が無い場合は何もしない。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "sync_gh_pages_branch.sh: git リポジトリではありません" >&2
  exit 1
fi

branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$branch" != "main" && "$branch" != "master" ]]; then
  echo "sync_gh_pages_branch.sh: main または master 上で実行してください（現在: ${branch}）" >&2
  exit 1
fi

if ! git ls-remote --exit-code origin gh-pages >/dev/null 2>&1; then
  echo "sync_gh_pages_branch.sh: origin に gh-pages が無いためスキップします。"
  exit 0
fi

echo "sync_gh_pages_branch.sh: ${branch} → origin/gh-pages"
if git push origin "HEAD:gh-pages" --force-with-lease; then
  echo "sync_gh_pages_branch.sh: OK"
else
  echo "sync_gh_pages_branch.sh: force-with-lease 失敗。force で再試行します。" >&2
  git push origin "HEAD:gh-pages" --force
  echo "sync_gh_pages_branch.sh: OK (force)"
fi
