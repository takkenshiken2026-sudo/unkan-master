/**
 * 問題一覧（過去問 / 実践演習 / 一問一答）— 絞り込み・アプリ連携
 * 設定: #q-index-config（未指定時は過去問 q/index.html 相当）
 */
(() => {
  'use strict';

  const PAGE_SIZE = 50;
  const DEBOUNCE_MS = 150;

  const DEFAULT_CONFIG = {
    variant: 'past',
    groupBy: 'year',
    groupPrefix: 'year',
    groupLabel: '年度',
    searchInputLabel: '過去問検索',
    searchPlaceholder: '例：第1問、分野名、問題文…',
    emptyTitle: '条件に一致する過去問がありません',
    emptyHint: '検索語を短くするか、分野・学習状況を「すべて」に戻してお試しください。',
    appLinkTemplate: '../index.html#past-play-{id}',
    appLinkLabel: '演習',
    rowLabelField: 'qno',
    statusFilters: ['wrong', 'bookmark', 'exempt', 'invalid'],
    answerKind: 'choice',
  };

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function categoryOrderIndex(cat) {
    const order = CONFIG.categoryOrder || [];
    const i = order.indexOf(cat);
    return i >= 0 ? i : order.length;
  }

  function sortCategoryNames(cats) {
    return cats.slice().sort((a, b) => {
      const da = categoryOrderIndex(a);
      const db = categoryOrderIndex(b);
      if (da !== db) return da - db;
      return String(a).localeCompare(String(b), 'ja');
    });
  }

  const configEl = document.getElementById('q-index-config');
  const CONFIG = configEl
    ? { ...DEFAULT_CONFIG, ...JSON.parse(configEl.textContent || '{}') }
    : DEFAULT_CONFIG;

  const dataEl = document.getElementById('q-index-data');
  const ITEMS_RAW = dataEl ? JSON.parse(dataEl.textContent || '[]') : [];
  const ITEMS = CONFIG.categoryOrder?.length
    ? ITEMS_RAW.slice().sort((a, b) => {
        const ca = categoryOrderIndex(a.category);
        const cb = categoryOrderIndex(b.category);
        if (ca !== cb) return ca - cb;
        if (CONFIG.rowLabelField === 'id') {
          return String(a.appId).localeCompare(String(b.appId), 'ja');
        }
        return (a.qno || 0) - (b.qno || 0);
      })
    : ITEMS_RAW;

  const q = document.getElementById('q-index-q');
  const chips = $$('.q-index-chip-btn[data-cat]');
  const statusChips = $$('.q-index-status-btn[data-status]');
  const viewBtns = $$('.q-index-view-btn[data-view]');
  const hit = document.getElementById('q-index-hit');
  const empty = document.getElementById('q-index-empty');
  const toolbarReset = document.getElementById('q-index-reset');
  const activeFilters = document.getElementById('q-index-active-filters');
  const toolbar = document.querySelector('.past-index-tools');
  const yearRow = document.getElementById('q-index-year-row');
  const jumpLinks = $$('.q-index-year-link[data-year], .q-index-year-link[data-group]');
  const topBtn = document.getElementById('q-index-top');
  const pagBar = document.getElementById('q-index-pagination');
  const yearView = document.getElementById('q-index-view-year');
  const catView = document.getElementById('q-index-view-cat');
  const flatView = document.getElementById('q-index-view-flat');
  const flatBody = document.getElementById('q-index-flat-body');
  const catMount = document.getElementById('q-index-cat-mount');

  let activeCat = 'all';
  let activeStatus = 'all';
  let activeView = 'year';
  let page = 1;
  let urlSyncTimer = null;

  const norm = (s) => (s || '').toString().trim().toLowerCase();

  const appData = (() => {
    try {
      const raw = localStorage.getItem('exam_site_shell_v1');
      if (!raw) return null;
      const db = JSON.parse(raw);
      const u = db.__guest__ || Object.values(db).find((x) => x && (x.answers || x.bookmarks));
      if (!u) return null;
      return { answers: u.answers || {}, bookmarks: u.bookmarks || {} };
    } catch (e) {
      return null;
    }
  })();

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

  function matchesStatus(item) {
    if (activeStatus === 'all') return true;
    if (activeStatus === 'exempt') return item.exempt;
    if (activeStatus === 'invalid') return item.invalidated;
    if (!appData) return false;
    const id = String(item.appId);
    if (activeStatus === 'bookmark') return !!appData.bookmarks[id];
    if (activeStatus === 'wrong') {
      const a = appData.answers[id];
      if (!a || a.ans == null) return false;
      if (CONFIG.answerKind === 'marubatsu') {
        const userMaru = Number(a.ans) === 0;
        return userMaru !== item.correctAnswer;
      }
      return Number(a.ans) !== Number(item.correct);
    }
    return true;
  }

  function itemVisible(item) {
    const tokens = parseSearchTokens(q?.value || '');
    const catOk = activeCat === 'all' || item.category === activeCat;
    return catOk && matchesSearch(item, tokens) && matchesStatus(item);
  }

  function hasActiveFilters() {
    return (
      !!(q?.value || '').trim() ||
      activeCat !== 'all' ||
      activeStatus !== 'all'
    );
  }

  function syncFiltersDrawer() {
    const details = document.querySelector('.q-index-filters-more');
    if (!details || !window.matchMedia('(max-width: 760px)').matches) return;
    if (hasActiveFilters()) details.open = true;
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
    const lower = raw.toLowerCase();
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
        return sp.hl ? `<mark class="q-hit-mark">${escapeHtml(part)}</mark>` : escapeHtml(part);
      })
      .join('');
  }

  function tagBadges(item) {
    const tags = item.tags || [];
    return tags.length
      ? tags.map((tag) => `<span class="q-tag-badge">${escapeHtml(tag)}</span>`).join('')
      : '—';
  }

  function rowLabel(item) {
    if (CONFIG.rowLabelField === 'id') return item.label || String(item.appId);
    return `第${item.qno}問`;
  }

  function actionLinks(item) {
    const appHref = (CONFIG.appLinkTemplate || '').replace('{id}', encodeURIComponent(item.appId));
    const appLabel = escapeHtml(CONFIG.appLinkLabel || '演習');
    const appLink = appHref
      ? ` <a class="q-row-link q-row-link-app" href="${escapeHtml(appHref)}" onclick="event.stopPropagation()">${appLabel}</a>`
      : '';
    return `<a class="q-row-link" href="${escapeHtml(item.href)}" onclick="event.stopPropagation()">解説</a>${appLink}`;
  }

  function rowHtml(item, query) {
    const preview = item.preview
      ? highlightText(item.preview, query)
      : '<span class="q-year-table-desc--empty">問題文は各ページで確認できます</span>';
    return `<tr class="q-year-table-row" tabindex="0" data-app-id="${escapeHtml(String(item.appId))}" data-href="${escapeHtml(item.href)}" data-category="${escapeHtml(item.category)}">
<td class="q-year-table-no" data-label="問"><a href="${escapeHtml(item.href)}" onclick="event.stopPropagation()">${escapeHtml(rowLabel(item))}</a></td>
<td class="q-year-table-cat" data-label="分野">${escapeHtml(item.category)}</td>
<td class="q-year-table-tags" data-label="タグ">${tagBadges(item)}</td>
<td class="q-year-table-desc" data-label="問題文">${preview}</td>
<td class="q-year-table-action" data-label="操作">${actionLinks(item)}</td>
</tr>`;
  }

  function tableHead() {
    return `<thead><tr>
<th scope="col">問</th><th scope="col">分野</th><th scope="col">タグ</th>
<th scope="col">問題文（抜粋）</th><th scope="col">操作</th>
</tr></thead>`;
  }

  function bindRows(root) {
    root.querySelectorAll('.q-year-table-row').forEach((row) => {
      if (row.dataset.bound) return;
      row.dataset.bound = '1';
      const go = (href) => {
        if (href) window.location.href = href;
      };
      row.addEventListener('click', (e) => {
        if (e.target.closest('a')) return;
        go(row.dataset.href);
      });
      row.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          go(row.dataset.href);
        }
      });
    });
  }

  function renderActiveFilters() {
    if (!activeFilters) return;
    const tags = [];
    const query = (q?.value || '').trim();
    if (query) tags.push({ type: 'q', label: `検索: ${query}` });
    if (activeCat !== 'all') tags.push({ type: 'cat', label: activeCat });
    if (activeStatus !== 'all') {
      const labels = {
        wrong: '不正解のみ',
        bookmark: 'ブックマーク',
        exempt: '免除',
        invalid: '無効',
      };
      tags.push({ type: 'status', label: labels[activeStatus] || activeStatus });
    }
    if (!tags.length) {
      activeFilters.classList.add('hide');
      activeFilters.innerHTML = '';
      return;
    }
    activeFilters.classList.remove('hide');
    activeFilters.innerHTML =
      '<span class="q-index-active-label">適用中</span>' +
      tags
        .map(
          (t) =>
            `<button type="button" class="q-index-active-tag" data-remove="${t.type}">${escapeHtml(t.label)} <span class="q-index-active-tag-remove" aria-hidden="true">×</span></button>`
        )
        .join('');
    activeFilters.querySelectorAll('[data-remove]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const t = btn.dataset.remove;
        if (t === 'q' && q) q.value = '';
        if (t === 'cat') {
          activeCat = 'all';
          chips.forEach((b) => b.classList.toggle('on', (b.dataset.cat || 'all') === 'all'));
        }
        if (t === 'status') {
          activeStatus = 'all';
          statusChips.forEach((b) => b.classList.toggle('on', (b.dataset.status || 'all') === 'all'));
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
      if (activeStatus !== 'all') params.set('status', activeStatus);
      if (page > 1) params.set('page', String(page));
      const qs = params.toString();
      const next = qs ? `${location.pathname}?${qs}` : location.pathname;
      history.replaceState(null, '', next);
    }, 200);
  }

  function availableCategories() {
    return new Set(ITEMS.map((item) => item.category).filter(Boolean));
  }

  function allowedStatusValues() {
    return new Set(['all', ...(CONFIG.statusFilters || [])]);
  }

  function sanitizeFiltersFromUrl() {
    let changed = false;
    const cats = availableCategories();
    if (activeCat !== 'all' && ITEMS.length && !cats.has(activeCat)) {
      activeCat = 'all';
      changed = true;
    }
    if (activeStatus !== 'all' && !allowedStatusValues().has(activeStatus)) {
      activeStatus = 'all';
      changed = true;
    }
    if ((activeStatus === 'wrong' || activeStatus === 'bookmark') && !appData) {
      activeStatus = 'all';
      changed = true;
    }
    if (changed) {
      chips.forEach((b) => b.classList.toggle('on', (b.dataset.cat || 'all') === activeCat));
      statusChips.forEach((b) =>
        b.classList.toggle('on', (b.dataset.status || 'all') === activeStatus)
      );
      syncUrl();
    }
  }

  function readUrl() {
    const params = new URLSearchParams(location.search);
    if (params.has('q') && q) q.value = params.get('q') || '';
    activeCat = params.get('cat') || 'all';
    activeStatus = params.get('status') || 'all';
    activeView = 'year';
    page = Math.max(1, parseInt(params.get('page') || '1', 10) || 1);
    sanitizeFiltersFromUrl();
  }

  function visibleItems() {
    return ITEMS.filter(itemVisible);
  }

  function paginate(list) {
    const totalPages = Math.max(1, Math.ceil(list.length / PAGE_SIZE));
    if (page > totalPages) page = totalPages;
    const start = (page - 1) * PAGE_SIZE;
    return { slice: list.slice(start, start + PAGE_SIZE), totalPages, total: list.length };
  }

  function renderPagination(total, totalPages) {
    if (!pagBar) return;
    if (total <= PAGE_SIZE) {
      pagBar.classList.add('hide');
      pagBar.innerHTML = '';
      return;
    }
    pagBar.classList.remove('hide');
    const prev = page > 1 ? page - 1 : null;
    const next = page < totalPages ? page + 1 : null;
    pagBar.innerHTML = `
<button type="button" class="q-index-page-btn" data-page="${prev || ''}" ${prev ? '' : 'disabled'}>前へ</button>
<span class="q-index-page-info">${page} / ${totalPages} ページ（${total}問）</span>
<button type="button" class="q-index-page-btn" data-page="${next || ''}" ${next ? '' : 'disabled'}>次へ</button>`;
    pagBar.querySelectorAll('[data-page]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const p = parseInt(btn.dataset.page, 10);
        if (!p) return;
        page = p;
        apply(false);
        $('.q-index-toolbar')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
  }

  function categorySlug(key) {
    return (
      String(key)
        .replace(/[^0-9A-Za-z\u4e00-\u9fff]+/g, '-')
        .replace(/^-+|-+$/g, '') || 'other'
    );
  }

  function groupBlockId(key) {
    const prefix = CONFIG.groupPrefix || 'year';
    if (CONFIG.groupBy === 'category') {
      return `${prefix}-${categorySlug(key)}`;
    }
    return `${prefix}-${key}`;
  }

  function applyYearView(visible, query) {
    if (!ITEMS.length) {
      if (yearView) {
        $$('.q-index-year-block', yearView).forEach((block) => {
          block.classList.remove('hide');
          $$('.q-year-table-row', block).forEach((row) => row.classList.remove('hide'));
        });
      }
      bindRows(yearView);
      return;
    }
    const ids = new Set(visible.map((x) => String(x.appId)));
    $$('.q-index-year-block', yearView).forEach((block) => {
      const rows = $$('.q-year-table-row', block);
      let shown = 0;
      rows.forEach((row) => {
        const id = row.dataset.appId;
        const ok = ids.has(id);
        row.classList.toggle('hide', !ok);
        if (ok) shown++;
      });
      block.classList.toggle('hide', shown === 0);
      const countEl = $('.q-index-year-count', block);
      if (countEl) {
        const total = Number(countEl.dataset.total) || rows.length;
        countEl.textContent = shown === total ? `${total}問` : `${shown} / ${total}問`;
      }
    });
    jumpLinks.forEach((link) => {
      const key = link.dataset.group || link.dataset.year;
      const block = document.getElementById(groupBlockId(key));
      const hidden = !block || block.classList.contains('hide');
      link.classList.toggle('hide', hidden);
      if (hidden) link.setAttribute('tabindex', '-1');
      else link.removeAttribute('tabindex');
    });
    $$('.q-year-table-desc', yearView).forEach((cell) => {
      const row = cell.closest('tr');
      if (!row || row.classList.contains('hide')) return;
      const item = ITEMS.find((x) => String(x.appId) === row.dataset.appId);
      if (!item) return;
      cell.innerHTML = item.preview
        ? highlightText(item.preview, query)
        : '<span class="q-year-table-desc--empty">問題文は各ページで確認できます</span>';
    });
    bindRows(yearView);
  }

  let catBuilt = false;
  function renderCatView(visible, query) {
    if (!catMount) return;
    const groups = {};
    visible.forEach((item) => {
      groups[item.category] = groups[item.category] || [];
      groups[item.category].push(item);
    });
    const html = sortCategoryNames(Object.keys(groups))
      .map((cat) => {
        const items = groups[cat].sort((a, b) => {
          if (CONFIG.rowLabelField === 'id') return String(a.appId).localeCompare(String(b.appId));
          return (b.year - a.year) || (a.qno - b.qno);
        });
        return `<section class="q-index-cat-block"><h2 class="q-index-cat-heading">${escapeHtml(cat)} <span>${items.length}問</span></h2>
<div class="q-year-table-wrap"><table class="q-year-table">${tableHead()}<tbody>
${items.map((it) => rowHtml(it, query)).join('')}
</tbody></table></div>`;
      })
      .join('');
    catMount.innerHTML = html;
    bindRows(catMount);
    catBuilt = true;
  }

  function renderFlatView(visible, query) {
    if (!flatBody) return;
    const { slice } = paginate(visible);
    flatBody.innerHTML = slice.map((it) => rowHtml(it, query)).join('');
    bindRows(flatView);
  }

  function ensureYearLayout() {
    activeView = 'year';
    yearView?.classList.remove('hide');
    catView?.classList.add('hide');
    flatView?.classList.add('hide');
    yearRow?.classList.remove('hide');
  }

  function apply(syncUrlFlag = true) {
    const query = q?.value || '';
    const visible = visibleItems();
    const total = ITEMS.length;
    const shown = visible.length;

    applyYearView(visible, query);

    if (hit) hit.textContent = `${shown} / ${total} 問`;
    if (empty) empty.classList.toggle('hide', shown !== 0);
    renderPagination(shown, Math.max(1, Math.ceil(shown / PAGE_SIZE)));
    renderActiveFilters();
    syncFiltersDrawer();
    syncReset();
    if (syncUrlFlag) syncUrl();
  }

  function syncReset() {
    if (toolbarReset) toolbarReset.classList.toggle('hide', !hasActiveFilters());
  }

  function resetAll() {
    if (q) q.value = '';
    activeCat = 'all';
    activeStatus = 'all';
    page = 1;
    chips.forEach((b) => b.classList.toggle('on', (b.dataset.cat || 'all') === 'all'));
    statusChips.forEach((b) => b.classList.toggle('on', (b.dataset.status || 'all') === 'all'));
    apply();
    q?.focus();
  }

  function initYearCollapse() {
    const blocks = $$('.q-index-year-block', yearView);
    const openSet = new Set(blocks.slice(0, 2).map((b) => b.id));
    blocks.forEach((block) => {
      const open = openSet.has(block.id);
      block.classList.toggle('is-collapsed', !open);
      const btn = $('.q-index-year-toggle', block);
      if (btn) {
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        btn.addEventListener('click', () => {
          const now = block.classList.toggle('is-collapsed');
          btn.setAttribute('aria-expanded', now ? 'false' : 'true');
        });
      }
    });
  }

  function initJumpSpy() {
    const links = jumpLinks.filter((a) => !a.classList.contains('hide'));
    if (!links.length) return;
    const blocks = links
      .map((a) => {
        const key = a.dataset.group || a.dataset.year;
        return document.getElementById(groupBlockId(key));
      })
      .filter(Boolean);
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((en) => {
          if (!en.isIntersecting) return;
          const blockId = en.target.id;
          links.forEach((a) => {
            const key = a.dataset.group || a.dataset.year;
            const active = groupBlockId(key) === blockId;
            a.classList.toggle('is-current', active);
            a.classList.toggle('on', active);
          });
        });
      },
      { rootMargin: '-30% 0px -55% 0px', threshold: 0 }
    );
    blocks.forEach((b) => obs.observe(b));
  }

  let inputDebounceTimer = null;
  q?.addEventListener('input', () => {
    page = 1;
    if (inputDebounceTimer) clearTimeout(inputDebounceTimer);
    inputDebounceTimer = setTimeout(() => {
      inputDebounceTimer = null;
      apply();
    }, DEBOUNCE_MS);
  });
  toolbarReset?.addEventListener('click', resetAll);
  document.getElementById('q-index-empty-reset')?.addEventListener('click', resetAll);

  chips.forEach((btn) => {
    btn.addEventListener('click', () => {
      chips.forEach((b) => b.classList.remove('on'));
      btn.classList.add('on');
      activeCat = btn.dataset.cat || 'all';
      page = 1;
      apply();
    });
  });
  statusChips.forEach((btn) => {
    btn.addEventListener('click', () => {
      statusChips.forEach((b) => b.classList.remove('on'));
      btn.classList.add('on');
      activeStatus = btn.dataset.status || 'all';
      page = 1;
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
      page = 1;
      apply();
      return;
    }
    if (hasActiveFilters()) resetAll();
  });

  if (toolbar) {
    const onScroll = () => {
      const top = toolbar.getBoundingClientRect().top;
      toolbar.classList.toggle('is-scrolled', top <= 56);
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
  chips.forEach((b) => b.classList.toggle('on', (b.dataset.cat || 'all') === activeCat));
  statusChips.forEach((b) => b.classList.toggle('on', (b.dataset.status || 'all') === activeStatus));
  ensureYearLayout();
  initYearCollapse();
  initJumpSpy();
  bindRows(yearView);
  apply(false);
})();
