# 試験ガイド記事カタログ（100本以上の例）

`data/guide_articles.csv` に追加するときの **slug / genre** の例です。資格名・制度・数値は本文で差し替えます。既存5本（`exam-overview` など）は含めません。

ジャンルの意味・MECE ルールは **[guide-article-genres.md](./guide-article-genres.md)** を正本とします。

## 使い方

新規1本の雛形は **[guide-article-template.md](./guide-article-template.md)** の `scaffold_guide_article.py` から作ると、ジャンル別の見出し・FAQ が入った CSV 行が得られます。

1. 対象資格に不要な行はスキップする（記述試験がなければ記述系 slug を省略、など）。
2. **分野別対策** は `site-config.json` の `fields` に合わせて `field-{id}-*` を複製する（3分野なら最低9〜15本を想定）。
3. 同じ検索意図の重複 slug を避ける。似たテーマはタイトルで差別化する。
4. 追加後は `python3 tools/build_all.py` で検証・再生成する。

---

## 試験概要（5）

| slug | genre |
|------|-------|
| official-info-sources | 試験概要 |
| learning-app-guide | 試験概要 |
| exam-purpose-and-career | 試験概要 |
| first-time-exam-guide | 試験概要 |
| compare-similar-qualifications | 試験概要 |

## 受験資格（5）

| slug | genre |
|------|-------|
| exam-eligibility | 受験・申込 |
| exemption-system | 受験・申込 |
| work-experience-requirement | 受験・申込 |
| education-requirement | 受験・申込 |
| concurrent-exam-rules | 受験・申込 |

## 日程・申込（6）

| slug | genre |
|------|-------|
| exam-schedule | 受験・申込 |
| exam-fees | 受験・申込 |
| exam-application-flow | 受験・申込 |
| application-deadline-checklist | 受験・申込 |
| exam-venue-and-region | 受験・申込 |
| reschedule-and-absence | 受験・申込 |

## 試験形式（5）

| slug | genre |
|------|-------|
| exam-format-overview | 出題・形式 |
| subject-breakdown | 出題・形式 |
| cbt-computer-exam | 出題・形式 |
| written-essay-section | 出題・形式 |
| time-limit-strategy | 出題・形式 |

## 出題範囲（6）

| slug | genre |
|------|-------|
| exam-scope-overview | 出題・形式 |
| syllabus-how-to-read | 出題・形式 |
| scope-revision-history | 出題・形式 |
| weight-by-topic | 出題・形式 |
| new-topics-trend | 出題・形式 |
| scope-vs-past-questions | 出題・形式 |

## 合格・難易度（5）

| slug | genre |
|------|-------|
| pass-rate | 合格・難易度 |
| exam-difficulty | 合格・難易度 |
| pass-score | 合格・難易度 |
| pass-rate-how-to-read | 合格・難易度 |
| difficulty-for-beginners | 合格・難易度 |

## 学習計画（8）

| slug | genre |
|------|-------|
| study-plan-3months | 学習計画 |
| study-plan-6months | 学習計画 |
| study-plan-1year | 学習計画 |
| study-plan-working | 学習計画 |
| study-plan-beginner | 学習計画 |
| first-30-days-plan | 学習計画 |
| balance-work-study | 学習計画 |
| time-management | 学習計画 |

## 独学対策（6）

| slug | genre |
|------|-------|
| self-study-start | 独学対策 |
| self-study-schedule | 独学対策 |
| self-study-mistakes | 独学対策 |
| self-study-environment | 独学対策 |
| self-study-motivation | 独学対策 |
| self-study-without-school | 独学対策 |

## 教材選び（6）

| slug | genre |
|------|-------|
| textbook-selection | 独学対策 |
| problem-book-selection | 独学対策 |
| correspondence-course-guide | 独学対策 |
| free-materials-online | 独学対策 |
| textbook-vs-past-questions | 独学対策 |
| material-update-cycle | 独学対策 |

## 過去問活用（8）

| slug | genre |
|------|-------|
| past-questions-by-year | 過去問活用 |
| past-questions-by-field | 過去問活用 |
| past-questions-review-cycle | 過去問活用 |
| past-questions-score-analysis | 過去問活用 |
| bookmark-review-method | 過去問活用 |
| past-questions-first-attempt | 過去問活用 |
| past-questions-wrong-reasons | 過去問活用 |
| past-questions-latest-year | 過去問活用 |

## 模試・演習（6）

| slug | genre |
|------|-------|
| mock-exam-how-to | 過去問活用 |
| ichimon-practice | 過去問活用 |
| drill-volume-guide | 過去問活用 |
| timed-practice | 過去問活用 |
| essay-practice-method | 過去問活用 |
| simulation-exam-schedule | 過去問活用 |

## 分野別対策（15＋α）

`fields` の id を `{field}` に置き換えて増やします（例: `law`, `rights`, `limit`）。

| slug | genre |
|------|-------|
| field-{field}-basics | 分野別対策 |
| field-{field}-frequent-topics | 分野別対策 |
| field-{field}-calculation | 分野別対策 |
| field-{field}-case-study | 分野別対策 |
| field-{field}-past-question-focus | 分野別対策 |

テンプレート標準の3分野なら次の15本:

| slug | genre |
|------|-------|
| field-law-basics | 分野別対策 |
| field-law-frequent-topics | 分野別対策 |
| field-law-calculation | 分野別対策 |
| field-law-case-study | 分野別対策 |
| field-law-past-question-focus | 分野別対策 |
| field-rights-basics | 分野別対策 |
| field-rights-frequent-topics | 分野別対策 |
| field-rights-calculation | 分野別対策 |
| field-rights-case-study | 分野別対策 |
| field-rights-past-question-focus | 分野別対策 |
| field-limit-basics | 分野別対策 |
| field-limit-frequent-topics | 分野別対策 |
| field-limit-calculation | 分野別対策 |
| field-limit-case-study | 分野別対策 |
| field-limit-past-question-focus | 分野別対策 |

## 用語ハブ活用法（6）

| slug | genre |
|------|-------|
| glossary-study-method | 用語ハブ活用法 |
| important-terms-list | 用語ハブ活用法 |
| confusing-terms | 用語ハブ活用法 |
| related-terms-navigation | 用語ハブ活用法 |
| terms-with-past-questions | 用語ハブ活用法 |
| terms-importance-levels | 用語ハブ活用法 |

## 数値・計算（5）

| slug | genre |
|------|-------|
| numbers-and-deadlines | 用語ハブ活用法 |
| formula-memorization | 用語ハブ活用法 |
| calculation-drill | 用語ハブ活用法 |
| rate-and-percentage | 用語ハブ活用法 |
| numeric-trap-choices | 用語ハブ活用法 |

## 復習・苦手克服（6）

| slug | genre |
|------|-------|
| review-cycle-spaced | 復習・苦手克服 |
| mistake-notebook | 復習・苦手克服 |
| weak-field-recovery | 復習・苦手克服 |
| note-taking-method | 復習・苦手克服 |
| almost-correct-review | 復習・苦手克服 |
| plateau-breakthrough | 復習・苦手克服 |

## 直前対策（5）

| slug | genre |
|------|-------|
| final-week-prep | 直前・当日 |
| final-day-checklist | 直前・当日 |
| final-scope-narrowing | 直前・当日 |
| final-sleep-and-health | 直前・当日 |
| final-mock-last-run | 直前・当日 |

## 試験当日（5）

| slug | genre |
|------|-------|
| exam-day-items | 直前・当日 |
| exam-day-flow | 直前・当日 |
| exam-day-time-allocation | 直前・当日 |
| mental-prep-exam-day | 直前・当日 |
| exam-day-troubleshooting | 直前・当日 |

## 合格後手続き（4）

| slug | genre |
|------|-------|
| after-pass-procedure | 注意点・更新 |
| pass-announcement-guide | 注意点・更新 |
| registration-after-pass | 注意点・更新 |
| career-after-qualification | 注意点・更新 |

## 再受験対策（4）

| slug | genre |
|------|-------|
| fail-retry-plan | 注意点・更新 |
| retake-strategy | 注意点・更新 |
| retake-schedule-adjustment | 注意点・更新 |
| score-gap-analysis | 注意点・更新 |

## 制度変更・更新（4）

| slug | genre |
|------|-------|
| exam-changes | 注意点・更新 |
| legal-revision-impact | 注意点・更新 |
| syllabus-update-tracker | 注意点・更新 |
| official-info-update-habits | 注意点・更新 |

## よくある誤解（5）

| slug | genre |
|------|-------|
| common-misconceptions | 注意点・更新 |
| pass-only-past-questions-myth | 注意点・更新 |
| study-hours-myth | 注意点・更新 |
| eligibility-myths | 注意点・更新 |
| difficulty-myths | 注意点・更新 |

## アフィリエイト記事（10本目安）

- **ASP / 商品 URL が確定してから** `guide_articles.csv` に行を追加し HTML を公開する。リンク未用意の slug は **記事を作らない**（`build_article_pages.py` も HTML を生成しない）。
- 既に CSV 行だけある場合は **`content_status=draft`（非公開）** のまま置き、ASP URL 確定後に `published` へ切り替える。

- **`tags` に `アフィリエイト`**（リンク済み行のみ本数カウント）
- 詳細: **[seo-article-guidelines.md](./seo-article-guidelines.md)** / **[affiliate/affiliate-article-rules.md](./affiliate/affiliate-article-rules.md)**

| slug | genre | 主なASP |
|------|-------|---------|
| affiliate-textbooks-recommend | 独学対策 | Amazon（＋A8の教材案件があれば） |
| affiliate-problem-books | 独学対策 | Amazon |
| affiliate-online-course-compare | 独学対策 | A8.net / afb |
| affiliate-correspondence-course | 独学対策 | A8.net / afb |
| affiliate-cram-school | 独学対策 | A8.net / afb |
| affiliate-mock-exam-materials | 過去問活用 | Amazon / A8 |
| affiliate-free-vs-paid-study | 独学対策 | 内部リンク中心（アフィリ弱め可） |
| affiliate-beginner-material-set | 学習計画 | Amazon + 講座A8 |
| affiliate-retake-short-course | 学習計画 | A8.net / afb |
| affiliate-qualification-support-service | 受験・申込 | A8.net / afb（試験に該当サービスがある場合のみ） |

- 上記 slug は **ASP URL 確定後に1本ずつ追加** する。プレースホルダー行を先に10本作らない。
- 上記のうち不要な行（取得支援サービスがない試験など）は省略し、別カテゴリで10本に届ける。
- 既存の「教材選び（6）」slug と **検索意図が重複しない** よう、選び方ガイドかおすすめ比較のどちらかに寄せる。

---

## 本数の目安

上記テンプレート行だけで **約120 slug**（分野別15本込み）＋ **アフィリエイト10本**。資格に合わせて削った場合は、次で100本に届けやすいです。

- 分野を4つ以上に増やしたとき → `field-*` を5本セット×分野数
- 同ジャンル内の「対象者別」（初学者 / リスキリング / 短期合格）
- 年度・制度更新ごとの差し替え記事（`制度変更・更新`）
- アフィリエイト記事は **tags に `アフィリエイト`** を付けた行を **10本前後**（本番テンプレート標準）
