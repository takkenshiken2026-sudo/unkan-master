/**
 * 知識ハブ一覧（数値早見 / 誤答パターン等）
 * body[data-hub-index-prefix] で ID を解決。再生成: tools/build_numbers_mistakes_pages.py
 */
(() => {
  'use strict';

  document.documentElement.classList.add('js');

  const prefix = document.body.dataset.hubIndexPrefix;
  if (!prefix) return;

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const dataEl = document.getElementById(`${prefix}-data`);
  const ITEMS = dataEl ? JSON.parse(dataEl.textContent || '[]') : [];

  const q = document.getElementById(`${prefix}-q`);
  const chips = $$('.terms-idx-chip[data-cat]');
  const hit = document.getElementById(`${prefix}-hit`);
  const empty = document.getElementById(`${prefix}-empty`);
  const toolbarReset = document.getElementById(`${prefix}-reset`);
  const activeFilters = document.getElementById(`${prefix}-active-filters`);
  const toolbar = document.querySelector('.terms-index-tools');
  const topBtn = document.getElementById(`${prefix}-top`);
  const flatBody = document.getElementById(`${prefix}-flat-body`);
  const HUB_BASE = document.body.dataset.hubBase || '';
  const col1 = document.body.dataset.hubCol1 || '項目';
  const col3 = document.body.dataset.hubCol3 || '概要';
  const tableClass = prefix.replace(/-idx$/, '-idx-table');

  let activeCat = 'all';
  let urlSyncTimer = null;
  const DEBOUNCE_MS = 150;
  let inputDebounceTimer = null;

  const norm = (s) => (s || '').toString().trim().toLowerCase();

  function parseSearchTokens(raw) {
    const parts = norm(raw).split(/\s+/).filter(Boolean);
    const inc = [];
    const exc = [];
    parts.forEach((p) => {
      if (p.startsWith('-') && p.length > 1) exc.push(p.slice(1));
      else inc.push(p);
    });
    return { inc, exc };
  }

  function matchesSearch(item, tokens) {
    const hay = norm(item.search);
    if (tokens.inc.length && !tokens.inc.every((t) => hay.includes(t))) return false;
    if (tokens.exc.some((t) => hay.includes(t))) return false;
    return true;
  }

  function itemVisible(item) {
    const tokens = parseSearchTokens(q?.value || '');
    const catOk = activeCat === 'all' || item.category === activeCat;
    return catOk && matchesSearch(item, tokens);
  }

  function hasActiveFilters() {
    return !!(q?.value || '').trim() || activeCat !== 'all';
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function highlightText(text, query) {
    const raw = (text || '').toString();
    const tokens = parseSearchTokens(query).inc.filter((t) => t.length >= 1);
    if (!tokens.length) return escapeHtml(raw);
    let spans = [{ start: 0, end: raw.length, hl: false }];
    tokens.forEach((tok) => {
      const next = [];
      spans.forEach((sp) => {
        if (sp.hl) {
          next.push(sp);
          return;
        }
        const slice = raw.slice(sp.start, sp.end);
        const sliceLower = slice.toLowerCase();
        let idx = 0;
        while (idx < slice.length) {
          const at = sliceLower.indexOf(tok, idx);
          if (at < 0) {
            next.push({ start: sp.start + idx, end: sp.end, hl: false });
            break;
          }
          if (at > idx) next.push({ start: sp.start + idx, end: sp.start + at, hl: false });
          next.push({ start: sp.start + at, end: sp.start + at + tok.length, hl: true });
          idx = at + tok.length;
        }
      });
      spans = next;
    });
    return spans
      .map((sp) => {
        const part = raw.slice(sp.start, sp.end);
        return sp.hl ? `<mark class="terms-hit-mark">${escapeHtml(part)}</mark>` : escapeHtml(part);
      })
      .join('');
  }

  function sortItems(list) {
    return [...list].sort((a, b) => {
      const c = a.category.localeCompare(b.category, 'ja');
      if (c) return c;
      return a.title.localeCompare(b.title, 'ja');
    });
  }

  function resolveEntryHref(href) {
    if (!href) return href;
    if (/^https?:\/\//i.test(href) || href.startsWith('/')) return href;
    return `${HUB_BASE}${String(href).replace(/^\.\//, '')}`;
  }

  function rowHtml(item, query) {
    const href = resolveEntryHref(item.href);
    const hrefAttr = ` data-entry-href="${escapeHtml(href)}"`;
    const summary = item.summary || '';
    const subjects = item.subjects || '';
    return `<tr class="terms-idx-table-row ${tableClass}-row">
<td class="terms-idx-td-term ${tableClass}-td-title" data-label="${escapeHtml(col1)}"${hrefAttr} tabindex="0"><div class="terms-idx-term-cell"><a href="${escapeHtml(href)}">${highlightText(item.title, query)}</a></div></td>
<td class="terms-idx-td-cat" data-label="分野"${hrefAttr}>${escapeHtml(item.category)}</td>
<td class="terms-idx-td-snippet ${tableClass}-td-detail" data-label="${escapeHtml(col3)}"${hrefAttr}>${highlightText(subjects || summary, query)}</td>
</tr>`;
  }

  function bindRows() {
    if (!flatBody) return;
    const go = (href) => {
      const target = resolveEntryHref(href);
      if (target) window.location.href = target;
    };
    flatBody.querySelectorAll('[data-entry-href]').forEach((cell) => {
      if (cell.dataset.bound) return;
      cell.dataset.bound = '1';
      const href = cell.dataset.entryHref;
      cell.addEventListener('click', (e) => {
        if (e.target.closest('a')) return;
        go(href);
      });
      if (cell.classList.contains(`${tableClass}-td-title`)) {
        cell.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            go(href);
          }
        });
      }
      cell.addEventListener('mouseenter', () => {
        flatBody.querySelectorAll(`[data-entry-href="${CSS.escape(href)}"]`).forEach((c) => {
          c.classList.add('is-entry-hover');
        });
      });
      cell.addEventListener('mouseleave', () => {
        flatBody.querySelectorAll(`[data-entry-href="${CSS.escape(href)}"]`).forEach((c) => {
          c.classList.remove('is-entry-hover');
        });
      });
    });
  }

  function renderActiveFilters() {
    if (!activeFilters) return;
    const tags = [];
    const query = (q?.value || '').trim();
    if (query) tags.push({ type: 'q', label: `検索: ${query}` });
    if (activeCat !== 'all') tags.push({ type: 'cat', label: activeCat });
    if (!tags.length) {
      activeFilters.classList.add('hide');
      activeFilters.innerHTML = '';
      return;
    }
    activeFilters.classList.remove('hide');
    activeFilters.innerHTML =
      '<span class="terms-idx-active-label">適用中</span>' +
      tags
        .map(
          (t) =>
            `<button type="button" class="terms-idx-active-tag" data-remove="${t.type}">${escapeHtml(t.label)}<span aria-hidden="true">×</span></button>`
        )
        .join('');
    activeFilters.querySelectorAll('[data-remove]').forEach((btn) => {
      btn.addEventListener('click', () => {
        if (btn.dataset.remove === 'q' && q) q.value = '';
        if (btn.dataset.remove === 'cat') {
          activeCat = 'all';
          chips.forEach((b) => b.classList.toggle('on', (b.dataset.cat || 'all') === 'all'));
        }
        apply();
      });
    });
  }

  function syncUrl() {
    if (urlSyncTimer) clearTimeout(urlSyncTimer);
    urlSyncTimer = setTimeout(() => {
      const params = new URLSearchParams();
      const query = (q?.value || '').trim();
      if (query) params.set('q', query);
      if (activeCat !== 'all') params.set('cat', activeCat);
      const qs = params.toString();
      const next = qs ? `${HUB_BASE}?${qs}` : HUB_BASE;
      history.replaceState(null, '', next);
    }, 200);
  }

  function readUrl() {
    const params = new URLSearchParams(location.search);
    if (params.has('q') && q) q.value = params.get('q') || '';
    activeCat = params.get('cat') || 'all';
    chips.forEach((b) => b.classList.toggle('on', (b.dataset.cat || 'all') === activeCat));
  }

  function visibleItems() {
    return sortItems(ITEMS.filter(itemVisible));
  }

  function renderTable(visible, query) {
    if (!flatBody) return;
    flatBody.innerHTML = visible.map((item) => rowHtml(item, query)).join('');
    bindRows();
  }

  function syncReset() {
    if (toolbarReset) toolbarReset.classList.toggle('hide', !hasActiveFilters());
  }

  function apply(syncUrlFlag = true) {
    const query = q?.value || '';
    const visible = visibleItems();
    const total = ITEMS.length;
    const shown = visible.length;

    renderTable(visible, query);

    if (hit) hit.textContent = `${shown} / ${total} 件`;
    if (empty) {
      const hideEmpty = shown !== 0;
      empty.classList.toggle('hide', hideEmpty);
      if (hideEmpty) empty.setAttribute('hidden', '');
      else empty.removeAttribute('hidden');
    }
    renderActiveFilters();
    syncReset();
    if (syncUrlFlag) syncUrl();
  }

  function resetAll() {
    if (q) q.value = '';
    activeCat = 'all';
    chips.forEach((b) => b.classList.toggle('on', (b.dataset.cat || 'all') === 'all'));
    apply();
    q?.focus();
  }

  q?.addEventListener('input', () => {
    if (inputDebounceTimer) clearTimeout(inputDebounceTimer);
    inputDebounceTimer = setTimeout(() => {
      inputDebounceTimer = null;
      apply();
    }, DEBOUNCE_MS);
  });
  toolbarReset?.addEventListener('click', resetAll);
  document.getElementById(`${prefix}-empty-reset`)?.addEventListener('click', resetAll);

  chips.forEach((btn) => {
    btn.addEventListener('click', () => {
      chips.forEach((b) => b.classList.remove('on'));
      btn.classList.add('on');
      activeCat = btn.dataset.cat || 'all';
      apply();
    });
  });

  document.addEventListener('keydown', (e) => {
    const tag = (e.target && e.target.tagName) || '';
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(tag) || e.target?.isContentEditable;
    if (e.key === '/' && !typing) {
      e.preventDefault();
      q?.focus();
      return;
    }
    if (e.key !== 'Escape' || typing) return;
    if (document.activeElement === q && q?.value) {
      q.value = '';
      apply();
      return;
    }
    if (hasActiveFilters()) resetAll();
  });

  if (toolbar) {
    const onScroll = () => {
      toolbar.classList.toggle('is-scrolled', toolbar.getBoundingClientRect().top <= 56);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  topBtn?.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
  window.addEventListener(
    'scroll',
    () => {
      if (!topBtn) return;
      topBtn.classList.toggle('is-visible', window.scrollY > 480);
    },
    { passive: true }
  );

  readUrl();
  apply(false);
})();
