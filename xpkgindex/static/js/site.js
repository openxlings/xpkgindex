/* Progressive enhancement only: every page is complete static HTML, this just
   makes it nicer. The listing filters client-side today; when a server backs
   the index later, only `applyFilter` needs to call an API instead. */

(function () {
  'use strict';

  // ---------------------------------------------------------------- theme
  var toggle = document.querySelector('.theme-toggle');
  if (toggle) {
    toggle.addEventListener('click', function () {
      var next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem('xpi-theme', next); } catch (e) { /* private mode */ }
    });
  }

  // ----------------------------------------------------------------- copy
  document.addEventListener('click', function (ev) {
    var btn = ev.target.closest('[data-copy]');
    if (!btn) return;
    ev.preventDefault();
    var text = btn.getAttribute('data-copy');
    var done = function () {
      btn.classList.add('done');
      setTimeout(function () { btn.classList.remove('done'); }, 1200);
    };
    // The async clipboard API rejects when permission is denied (and does not
    // exist at all on older browsers), so the legacy path is a fallback for
    // both cases rather than only for "API missing" — otherwise the click
    // silently does nothing and the user has no idea whether it worked.
    var legacy = function () {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); done(); } catch (e) { /* nothing else to try */ }
      document.body.removeChild(ta);
    };

    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(done, legacy);
    } else {
      legacy();
    }
  });

  // ------------------------------------------------------------- install
  // Show the command for the visitor's platform instead of making Windows
  // users open a disclosure. All commands are in the HTML; this only chooses
  // which one is visible, so the no-JS page still lists every platform.
  function detectOs() {
    var ua = navigator.userAgentData;
    var p = ((ua && ua.platform) || navigator.platform || navigator.userAgent || '')
      .toLowerCase();
    if (p.indexOf('win') !== -1) return 'windows';
    if (p.indexOf('mac') !== -1 || p.indexOf('iphone') !== -1 || p.indexOf('ipad') !== -1)
      return 'macos';
    return 'linux';
  }

  function osMatches(id, current) {
    if (id === 'any' || id === current) return true;
    return id === 'unix' && (current === 'linux' || current === 'macos');
  }

  document.querySelectorAll('[data-os-group]').forEach(function (group) {
    var cmds = Array.prototype.slice.call(group.querySelectorAll('.os-cmd'));
    var tabs = Array.prototype.slice.call(group.querySelectorAll('[data-os-tab]'));
    if (cmds.length < 2) return;

    var current = detectOs();
    var chosen = cmds.filter(function (c) {
      return osMatches(c.getAttribute('data-os'), current);
    })[0] || cmds[0];

    function select(target) {
      cmds.forEach(function (c) { c.hidden = c !== target; });
      tabs.forEach(function (t) {
        t.classList.toggle('on', t.getAttribute('data-os-tab') === target.getAttribute('data-os'));
      });
    }

    var switcher = group.querySelector('[data-os-switch]');
    if (switcher) switcher.hidden = false;
    group.classList.add('js-switched');
    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        var id = tab.getAttribute('data-os-tab');
        var target = cmds.filter(function (c) { return c.getAttribute('data-os') === id; })[0];
        if (target) select(target);
      });
    });
    select(chosen);
  });

  // ------------------------------------------------------------ cta tilt
  // Gravity-style hover: the card leans toward the pointer and a highlight
  // follows it. Pure decoration — the card is a plain link without JS, and
  // the effect is skipped for anyone who asked for reduced motion.
  var reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.querySelectorAll('[data-tilt]').forEach(function (card) {
    if (reduceMotion) return;
    var frame = null;

    function apply(ev) {
      if (frame) return;
      frame = requestAnimationFrame(function () {
        frame = null;
        var r = card.getBoundingClientRect();
        var px = (ev.clientX - r.left) / r.width;
        var py = (ev.clientY - r.top) / r.height;
        var max = 7;                                  // degrees
        card.style.transform =
          'perspective(700px) rotateX(' + ((0.5 - py) * max).toFixed(2) + 'deg)' +
          ' rotateY(' + ((px - 0.5) * max).toFixed(2) + 'deg) translateY(-3px)';
        card.style.setProperty('--px', (px * 100).toFixed(1) + '%');
        card.style.setProperty('--py', (py * 100).toFixed(1) + '%');
      });
    }

    card.addEventListener('pointermove', apply);
    card.addEventListener('pointerleave', function () {
      if (frame) { cancelAnimationFrame(frame); frame = null; }
      card.style.transform = '';
    });
  });

  // ---------------------------------------------------------------- docs
  // Copy buttons on rendered markdown code blocks. Added here rather than in
  // the renderer so the docs stay plain markdown that also reads correctly
  // on GitHub.
  document.querySelectorAll('.prose pre').forEach(function (pre) {
    var code = pre.querySelector('code');
    if (!code) return;
    var wrap = document.createElement('div');
    wrap.className = 'prose-code';
    pre.parentNode.insertBefore(wrap, pre);
    wrap.appendChild(pre);
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'copy';
    btn.setAttribute('data-copy', code.textContent.replace(/\n$/, ''));
    btn.setAttribute('aria-label', 'Copy code');
    btn.innerHTML = '<svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">' +
      '<path fill="currentColor" d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1z"/>' +
      '<path fill="currentColor" d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0z"/></svg>';
    wrap.appendChild(btn);
  });

  // --------------------------------------------------------------- search
  // Type-ahead over search-index.json. Available on every page: pressing
  // Enter opens the best-matching package rather than bouncing the visitor
  // back to the homepage with a query string.
  var input = document.getElementById('q');
  var results = document.getElementById('search-results');
  var index = null;
  var indexPromise = null;
  var hits = [];
  var cursor = -1;

  function loadIndex() {
    if (indexPromise) return indexPromise;
    indexPromise = fetch(input.getAttribute('data-index'))
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (data) { index = data; return data; })
      .catch(function () { index = []; return []; });
    return indexPromise;
  }

  function score(pkg, q) {
    var name = (pkg.n || '').toLowerCase();
    var display = (pkg.d || '').toLowerCase();
    var ns = (pkg.ns || '').toLowerCase();
    if (name === q || display === q) return 0;
    if (name.indexOf(q) === 0 || display.indexOf(q) === 0) return 1;
    if (ns.indexOf(q) === 0) return 2;
    if (name.indexOf(q) !== -1 || display.indexOf(q) !== -1) return 3;
    if ((pkg.t || '').toLowerCase().indexOf(q) !== -1) return 4;
    return -1;
  }

  function search(q) {
    if (!index) return [];
    return index
      .map(function (p) { return { p: p, s: score(p, q) }; })
      .filter(function (h) { return h.s >= 0; })
      .sort(function (a, b) { return a.s - b.s || a.p.d.length - b.p.d.length; })
      .slice(0, 8)
      .map(function (h) { return h.p; });
  }

  function closeResults() {
    if (!results) return;
    results.hidden = true;
    results.innerHTML = '';
    input.setAttribute('aria-expanded', 'false');
    hits = [];
    cursor = -1;
  }

  function renderResults(list) {
    hits = list;
    cursor = list.length ? 0 : -1;
    if (!list.length) { closeResults(); return; }
    var base = input.getAttribute('data-packages');
    results.innerHTML = list.map(function (p, i) {
      return '<a class="sr' + (i === 0 ? ' on' : '') + '" role="option" href="' +
        base + encodeURIComponent(p.s) + '/">' +
        '<span class="sr-name">' + escapeHtml(p.d) + '</span>' +
        (p.v ? '<span class="sr-ver">' + escapeHtml(p.v) + '</span>' : '') +
        (p.t ? '<span class="sr-desc">' + escapeHtml(p.t) + '</span>' : '') +
        '</a>';
    }).join('');
    results.hidden = false;
    input.setAttribute('aria-expanded', 'true');
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function moveCursor(delta) {
    var items = results.querySelectorAll('.sr');
    if (!items.length) return;
    cursor = (cursor + delta + items.length) % items.length;
    items.forEach(function (el, i) { el.classList.toggle('on', i === cursor); });
    items[cursor].scrollIntoView({ block: 'nearest' });
  }

  if (input && results) {
    input.addEventListener('focus', loadIndex);
    input.addEventListener('input', function () {
      var q = input.value.trim().toLowerCase();
      if (!q) { closeResults(); return; }
      loadIndex().then(function () { renderResults(search(q)); });
    });
    input.addEventListener('keydown', function (ev) {
      if (ev.key === 'ArrowDown') { ev.preventDefault(); moveCursor(1); }
      else if (ev.key === 'ArrowUp') { ev.preventDefault(); moveCursor(-1); }
      else if (ev.key === 'Escape') { closeResults(); input.blur(); }
    });
    input.form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var items = results.querySelectorAll('.sr');
      if (items.length && cursor >= 0) { window.location.href = items[cursor].href; }
    });
    document.addEventListener('click', function (ev) {
      if (!ev.target.closest('.search')) closeResults();
    });
  }

  // --------------------------------------------------------------- filter
  // On the listing page typing also filters the rows in place; elsewhere the
  // type-ahead above is the whole search experience.
  var rows = Array.prototype.slice.call(document.querySelectorAll('#rows .row'));
  var empty = document.getElementById('empty');
  var facets = document.getElementById('facets');
  if (!rows.length) {
    bindSlash(input);
    return;
  }

  var active = { key: 'all', value: '' };

  function applyFilter() {
    var q = (input && input.value || '').trim().toLowerCase();
    var shown = 0;
    rows.forEach(function (row) {
      var hitText = !q || row.getAttribute('data-search').indexOf(q) !== -1;
      // Facet values are space-separated: a package can be both `module` and
      // `header`, so match a token rather than the whole attribute.
      var facetVal = row.getAttribute('data-facet-' + active.key) || '';
      var hitFacet = active.key === 'all' ||
        facetVal.split(/\s+/).indexOf(active.value) !== -1;
      var show = hitText && hitFacet;
      row.hidden = !show;
      if (show) shown++;
    });
    if (empty) empty.hidden = shown !== 0;
  }

  if (input) {
    input.addEventListener('input', applyFilter);
    var initial = new URLSearchParams(location.search).get('q');
    if (initial) { input.value = initial; }
  }

  if (facets) {
    facets.addEventListener('click', function (ev) {
      var more = ev.target.closest('.facet-more');
      if (more) {
        more.parentNode.querySelectorAll('.facet-extra').forEach(function (b) {
          b.hidden = false;
        });
        more.remove();
        return;
      }
      var btn = ev.target.closest('.facet');
      if (!btn) return;
      var key = btn.getAttribute('data-facet');
      var value = btn.getAttribute('data-value') || '';
      var already = active.key === key && active.value === value;
      active = already ? { key: 'all', value: '' } : { key: key, value: value };
      facets.querySelectorAll('.facet').forEach(function (b) {
        var isAll = b.getAttribute('data-facet') === 'all';
        var mine = b.getAttribute('data-facet') === active.key &&
          (b.getAttribute('data-value') || '') === active.value;
        b.classList.toggle('on', active.key === 'all' ? isAll : mine);
      });
      applyFilter();
    });
  }

  bindSlash(input);
  applyFilter();

  function bindSlash(el) {
    if (!el) return;
    document.addEventListener('keydown', function (ev) {
      if (ev.key === '/' && document.activeElement !== el) {
        ev.preventDefault();
        el.focus();
      }
    });
  }
})();
