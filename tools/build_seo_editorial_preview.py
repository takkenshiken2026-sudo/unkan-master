#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEO 記事スタイルのプレビューページを生成する。

  python3 tools/build_seo_editorial_preview.py
  → terms/samples/seo-editorial-preview.html
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.html_footer import (  # noqa: E402
    breadcrumb_html,
    shell_body_class,
    site_page_footer,
    site_page_header,
    site_page_wrap_close,
    site_page_wrap_open,
)
from tools.knowledge_hub_seo import faq_items_html  # noqa: E402
from tools.seo_editorial_chrome import (  # noqa: E402
    seo_editorial_article_class,
    seo_editorial_head_fonts,
    seo_editorial_stylesheet_links,
)

OUT = ROOT / "terms" / "samples" / "seo-editorial-preview.html"
REL = OUT.relative_to(ROOT)


def main() -> int:
    rel_path = REL
    crumb = breadcrumb_html(rel_path, [("トップ", "index.html"), ("スタイルプレビュー", None)])
    styles = seo_editorial_stylesheet_links(rel_path, site_pages_ver="preview")
    article_class = seo_editorial_article_class()
    preview_faq_html = faq_items_html(
        [
            {
                "question": "試験日程はいつ公開されますか？",
                "answer": "年度開始前後に協会サイトで公開されるのが例年のパターンです。前年度の要項を参考にしつつ、新年度のPDFが掲載されたら必ず差し替えて確認してください。",
            },
            {
                "question": "申込期間を過ぎた場合はどうなりますか？",
                "answer": "原則としてその年度の受験はできません。次回試験の日程を公式サイトで確認し、学習計画を見直してください。",
            },
            {
                "question": "CBTと紙試験で日程は異なりますか？",
                "answer": "試験方式によって実施時期や申込方法が異なる場合があります。受験案内で自分が申し込む方式の日程を確認してください。",
            },
        ]
    )

    body = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SEO記事スタイルプレビュー｜seo-editorial.css</title>
<meta name="description" content="試験ガイド・用語解説向け typography / color の調整プレビュー">
<meta name="robots" content="noindex, nofollow">
{seo_editorial_head_fonts()}
{styles}
</head>
<body class="{shell_body_class('seo-editorial-preview-page')}">
{site_page_wrap_open()}
{site_page_header(rel_path, current="terms")}
<main class="seo-article-main">
  {crumb}
  <p class="knowledge-hub-sample-banner" style="max-width:var(--site-readable-w);margin:0 auto 18px;">
    <strong>スタイル調整用プレビュー</strong> — 本番記事ではありません。
    <code>seo-editorial.css</code> の <code>--seo-*</code> 変数を編集し、
    このページを再生成して確認してください（<code>docs/seo-editorial-typography.md</code>）。
  </p>
  <article class="{html.escape(article_class)}">
    <div class="article-meta">
      <span class="meta-category">プレビュー</span>
      <span class="meta-updated">更新 2026-05-27</span>
    </div>
    <h1 class="article-title">管理業務主任者試験の試験日程</h1>
    <p class="article-lead"><strong>試験日程</strong>は年度ごとに変わるため、申込前に公式要項で最新情報を確認してください。本記事では例年の流れと、見落としやすい確認ポイントを整理します。</p>

    <section class="seo-key-points-box" aria-labelledby="key-points-title">
      <h2 id="key-points-title">この記事の要点</h2>
      <p>本記事を読むと、試験日程の確認手順と、申込前に押さえるべき公式情報のチェックポイントが分かります。読了後は演習・用語確認へ進められます。</p>
      <ul class="seo-key-points-list">
        <li>例年の申込〜試験〜合格発表の流れを把握する</li>
        <li>公式要項で確認すべき4項目（日程・手数料・持ち物・合格発表）をメモする</li>
        <li>非公式情報は参考程度にし、最終判断は公式サイトで行う</li>
      </ul>
    </section>

    <nav class="seo-toc" aria-labelledby="seo-toc-title">
      <h2 id="seo-toc-title">目次</h2>
      <ol>
        <li><a href="#key-points-title">この記事の要点</a></li>
        <li><a href="#quality-panel-title">この記事の信頼性について</a></li>
        <li><a href="#preview-sec-1">年間スケジュールの確認</a></li>
        <li><a href="#preview-sec-2">申込期間と受験手数料</a></li>
        <li><a href="#preview-sec-3">試験当日までの流れ</a></li>
        <li><a href="#preview-sec-faq">よくある質問</a></li>
      </ol>
    </nav>

    <section class="seo-quality-panel" aria-labelledby="quality-panel-title">
      <h2 id="quality-panel-title">この記事の信頼性について</h2>
      <table class="seo-info-table"><tbody>
        <tr><th>執筆</th><td>Sampleマスター編集部（スタイル確認用）</td></tr>
        <tr><th>確認</th><td>公式情報確認担当（公開前に一次情報との照合を想定）</td></tr>
        <tr><th>事実確認日</th><td>2026-05-30</td></tr>
      </tbody></table>
    </section>

    <section class="seo-article-section" aria-labelledby="preview-sec-1">
      <h2 id="preview-sec-1"><span class="section-heading-num">1</span>年間スケジュールの確認</h2>
      <p>例年は<strong>春〜秋</strong>に申込、<strong>11月頃</strong>に試験実施が多いです。ただし年度によって前後するため、<a href="#">試験要項</a>で必ず確認してください。協会サイトのトップから「受験案内」または「試験日程」を開き、PDFの更新日が直近かどうかも合わせて見ます。</p>
      <p>スケジュールをメモする際は、申込開始日・申込締切・試験日・合格発表日の4点をセットで記録しておくと後から見返しやすくなります。複数科目や免除制度を利用する場合は、追加の期限が設けられることもあるため、要項の該当章まで読み進めてください。</p>
      <h3 class="term-subheading">公式サイトでの確認手順</h3>
      <p>まず試験実施団体の公式ページを開き、最新年度の受験案内PDFをダウンロードします。目次から「試験日程」「申込方法」のページを特定し、カレンダーアプリや手帳に転記します。非公式なまとめサイトは参考程度に留め、最終判断は必ず公式情報に置きます。</p>
      <blockquote><p>制度・数値は改正されるため、最終判断は公式情報に置きます。本ページの例年情報は学習の参考用です。</p></blockquote>
    </section>

    <section class="seo-article-section" aria-labelledby="preview-sec-2">
      <h2 id="preview-sec-2"><span class="section-heading-num">2</span>申込期間と受験手数料</h2>
      <p>申込期間は<strong>数週間〜1か月程度</strong>が例年の目安です。締切直前はシステムが混み合うことがあるため、早めの申込がおすすめです。受験手数料も年度で改定される場合があるので、申込画面に表示される金額と要項の記載を照合してください。</p>
      <p>オンライン申込が基本となる試験が多く、支払方法（クレジットカード、コンビニ払い等）は申込フローの途中で選択します。申込完了メールや受付番号は必ず保存し、当日まで確認できる場所に控えておきましょう。</p>
      <ul>
        <li>申込開始日の前日までに必要書類・写真データを準備する</li>
        <li>手数料の支払期限（コンビニ払いの場合）をカレンダーに登録する</li>
        <li>申込後、受験票の発行時期を要項で確認する</li>
      </ul>
      <blockquote><p>数値・期限は対象試験の公式要項で必ず確認してください。ここに記載した例年の目安は変更されることがあります。</p></blockquote>
    </section>

    <section class="seo-article-section" aria-labelledby="preview-sec-3">
      <h2 id="preview-sec-3"><span class="section-heading-num">3</span>試験当日までの流れ</h2>
      <p>受験票は試験日の<strong>2〜3週間前</strong>頃に交付・ダウンロード開始となるケースが多いです。会場名、集合時間、持ち物（身分証、筆記用具等）を事前にチェックし、交通手段も含めて当日の行程を決めておきます。</p>
      <p>試験直前は新しい論点の詰め込みより、間違えた問題の見直しと用語確認に時間を使う方が得点につながりやすいです。本サイトの<a href="#">過去問演習</a>や<a href="#">用語解説</a>と組み合わせ、弱点分野だけを短時間で復習する計画にすると効率的です。</p>
      <h3 class="term-subheading">合格発表後の手続き</h3>
      <p>合格発表日は要項に明記されています。合格後に必要な手続き（登録申請、実務経験の証明等）は試験種別ごとに異なるため、合格証明の保存とあわせて公式の案内を確認してください。</p>
      <blockquote><p>出題範囲・制度・手数料は年度ごとに更新されます。学習中も月1回程度は公式ページを開き、変更告知がないか確認する習慣が有効です。</p></blockquote>
    </section>

    <section class="seo-article-section" aria-labelledby="preview-sec-faq">
      <h2 id="preview-sec-faq"><span class="section-heading-num">4</span>よくある質問</h2>
      {preview_faq_html}
    </section>

    <div class="related-box">
      <div class="related-box-title">関連記事</div>
      <div class="related-links">
        <a class="related-link" href="#">試験概要ガイド</a>
        <a class="related-link" href="#">受験手数料の確認</a>
        <a class="related-link" href="#">申込から合格までの流れ</a>
      </div>
    </div>
  </article>
</main>
{site_page_footer(rel_path, current="terms")}
{site_page_wrap_close()}
</body>
</html>
"""

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(body, encoding="utf-8")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
