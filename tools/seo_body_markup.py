#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEO 記事本文向けの軽量マークアップ → HTML 変換。"""

from __future__ import annotations

import html
import re
from collections.abc import Callable

# 段落内の「A、B、C」列挙を箇条書きに起こすトリガー（保守的に限定）
_ENUM_TRIGGER = re.compile(
    r"(特に見落としやすいのは、|"
    r"(?:押さえる|確認(?:すべき)?)(?:項目|点)(?:は、)|"
    r"チェック(?:したい|すべき)?(?:項目|点)(?:は、)|"
    r"(?:手順|流れ|ポイント|ステップ)(?:は、))"
    r"([^。]{4,160}?)"
    r"(?:です|。|であり)",
)

_GENERIC_ENUM = re.compile(
    r"(?:[^。]{0,100}?(?:は、|として、))"
    r"((?:[^、。]{2,42}、){2,}[^、。]{2,42})"
    r"(?:です|。|であり|と)",
)


def split_semicolon(value: str) -> list[str]:
    return [x.strip() for x in (value or "").split(";") if x.strip()]


def _comma_list_items(chunk: str) -> list[str]:
    items = [x.strip() for x in re.split(r"[、,]", chunk) if x.strip()]
    if len(items) < 2:
        return []
    if any(len(item) > 52 for item in items):
        return []
    return items


def _try_trigger_list(block: str) -> str | None:
    match = _ENUM_TRIGGER.search(block)
    if match:
        items = _comma_list_items(match.group(2))
    else:
        match = _GENERIC_ENUM.search(block)
        if not match:
            return None
        items = _comma_list_items(match.group(1))
    if not items:
        return None
    before = block[: match.start()].rstrip()
    after = block[match.end() :].strip().lstrip("。．. ")
    parts: list[str] = []
    if before:
        parts.append(before)
    parts.append("\n".join(f"- {item}" for item in items))
    if after:
        parts.append(after)
    return "\n\n".join(parts)


def inject_comma_sentence_list(text: str) -> str:
    """列挙トリガーが無い段落でも、読点の多い文から箇条書きを起こす（控えめ）。"""
    if not text.strip() or "\n-" in text or ";" in text:
        return text

    blocks = re.split(r"\n{2,}", text.strip())
    out: list[str] = []
    for block in blocks:
        if block.lstrip().startswith("- "):
            out.append(block)
            continue
        triggered = _try_trigger_list(block)
        if triggered:
            out.append(triggered)
            continue

        sentences = [s for s in re.split(r"(?<=[。！？])", block) if s.strip()]
        best_items: list[str] = []
        best_idx = -1
        best_prefix = ""
        for idx, sent in enumerate(sentences):
            if sent.count("、") < 2:
                continue
            if "とは、" in sent:
                continue
            pos = sent.rfind("は、")
            chunk = sent[pos + 2 :] if pos >= 0 else sent
            chunk = re.sub(r"(?:です|ます|でした|である|であり)[。]?$", "", chunk.strip())
            chunk = chunk.rstrip("。")
            items = _comma_list_items(chunk)
            if len(items) >= 2 and len(items) > len(best_items):
                best_items = items
                best_idx = idx
                best_prefix = sent[:pos].strip() if pos >= 0 else ""
        if best_idx < 0:
            out.append(block)
            continue
        rebuilt: list[str] = []
        if best_idx > 0:
            rebuilt.append("".join(sentences[:best_idx]).strip())
        if best_prefix:
            rebuilt.append(best_prefix + "。")
        rebuilt.append("\n".join(f"- {item}" for item in best_items))
        tail = "".join(sentences[best_idx + 1 :]).strip()
        if tail:
            rebuilt.append(tail)
        out.append("\n\n".join(p for p in rebuilt if p))
    return "\n\n".join(out)


def inject_enumeration_lists(text: str) -> str:
    """既存 CSV 本文から列挙句を検出し `- ` 行のブロックを挿入する。"""
    if not text.strip() or "\n-" in text:
        return text

    blocks = re.split(r"\n{2,}", text.strip())
    out_blocks: list[str] = []
    for block in blocks:
        if block.lstrip().startswith("- "):
            out_blocks.append(block)
            continue
        triggered = _try_trigger_list(block)
        if triggered:
            out_blocks.append(triggered)
        else:
            out_blocks.append(block)
    merged = "\n\n".join(out_blocks)
    return inject_comma_sentence_list(merged)


def _render_paragraph(text: str, *, term_hrefs: dict[str, str] | None = None, linked_terms: set[str] | None = None) -> str:
    if term_hrefs and linked_terms is not None:
        from tools.internal_links import link_terms_in_plaintext

        return f"<p>{link_terms_in_plaintext(text, term_hrefs, linked_terms)}</p>"
    return f"<p>{html.escape(text).replace(chr(10), '<br>')}</p>"


def _render_block(
    block: str,
    *,
    term_hrefs: dict[str, str] | None = None,
    linked_terms: set[str] | None = None,
) -> str:
    lines = block.split("\n")
    non_empty = [ln for ln in lines if ln.strip()]
    if non_empty and all(ln.lstrip().startswith("- ") for ln in non_empty):
        items = [ln.lstrip()[2:].strip() for ln in non_empty]
        return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"

    if ";" in block and "\n" not in block:
        items = split_semicolon(block)
        if len(items) >= 2:
            return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"

    if block.startswith("### "):
        heading = block[4:].split("\n", 1)[0].strip()
        rest = block[4:].split("\n", 1)[1] if "\n" in block[4:] else ""
        html_parts = [f'<h3 class="term-subheading">{html.escape(heading)}</h3>']
        if rest.strip():
            html_parts.append(
                _render_block(rest.strip(), term_hrefs=term_hrefs, linked_terms=linked_terms)
            )
        return "".join(html_parts)

    paras = [p.strip() for p in re.split(r"\n{2,}", block) if p.strip()] or [block.strip()]
    return "".join(
        _render_paragraph(p, term_hrefs=term_hrefs, linked_terms=linked_terms)
        for p in paras
        if p.strip()
    )


def seo_section_body_html(
    text: str,
    *,
    transform: Callable[[str], str] | None = None,
    term_hrefs: dict[str, str] | None = None,
    linked_terms: set[str] | None = None,
) -> str:
    """セクション本文 HTML。`- ` 行・`;` 区切り・`###` 小見出しに対応。"""
    body = (transform(text) if transform else text).strip()
    if not body:
        return ""
    body = inject_enumeration_lists(body)
    blocks = [b.strip() for b in re.split(r"\n{2,}", body) if b.strip()] or [body]
    return "".join(
        _render_block(block, term_hrefs=term_hrefs, linked_terms=linked_terms) for block in blocks
    )
