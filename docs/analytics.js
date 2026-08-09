/* Analytics — GoatCounter enrichment.
 *
 * ONE file, loaded by every page, so the behaviour lives in a single place instead of being
 * sprinkled across a dozen static HTML files. It adds EVENTS on top of the pageview that
 * count.js already sends.
 *
 * WHAT IT DOES NOT DO, deliberately:
 *   - no cookies, no localStorage, no fingerprinting, no cross-site or per-visitor identifier
 *   - nothing that identifies a person, and nothing sent that a server log would not already see
 * GoatCounter is aggregate-only by design. "More detail" here means MORE KINDS OF EVENT,
 * never more identification of who did them. That ceiling is a property of the tool and a
 * feature of it; it is stated rather than worked around.
 *
 * PATH PREFIX: this site is the account's DEFAULT and reports bare paths ("/verify.html").
 * satoshioncha.in and bitcoinwhitepaper.online prefix themselves with their host, so the three
 * do not merge in the dashboard. Do NOT add a prefix here: it would split every page's existing
 * history into a before and an after for no gain.
 */
(function () {
  'use strict';

  // count.js is loaded async, so events fired early would be dropped. Queue until it exists.
  var queue = [], ready = false;

  function flush() {
    if (!(window.goatcounter && typeof window.goatcounter.count === 'function')) return false;
    ready = true;
    while (queue.length) { try { window.goatcounter.count(queue.shift()); } catch (e) {} }
    return true;
  }
  if (!flush()) {
    var tries = 0;
    var t = setInterval(function () {
      if (flush() || ++tries > 60) clearInterval(t);   // give up after ~30s
    }, 500);
  }

  /** Send one event. `name` becomes the path in the dashboard; keep it short and grep-able. */
  function ev(name, title) {
    if (!name) return;
    var o = { path: String(name).slice(0, 240), title: title || String(name), event: true };
    if (ready) { try { window.goatcounter.count(o); } catch (e) {} } else { queue.push(o); }
  }
  window.gcEvent = ev;   // pages call this for their own outcomes

  var page = (location.pathname.split('/').pop() || 'index').replace(/\.html$/, '') || 'index';

  // ---- outbound links -------------------------------------------------------------------
  // Which off-site sources people actually follow is the single most useful thing to know:
  // it says whether the evidence links are being READ or merely displayed.
  var DOWNLOAD = /\.(pdf|rar|zip|tar\.gz|tgz|asc|sig|ots|exe|ova|csv|json|txt|md)$/i;

  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    var href = a.getAttribute('href') || '';
    if (!href || href.charAt(0) === '#' || /^(mailto|javascript):/i.test(href)) return;

    var u;
    try { u = new URL(a.href, location.href); } catch (err) { return; }

    if (u.host && u.host !== location.host) {
      ev('outbound: ' + u.host + u.pathname, 'outbound → ' + u.host);
    } else if (DOWNLOAD.test(u.pathname)) {
      ev('download: ' + u.pathname.split('/').pop(), 'download');
    }
  }, true);

  // ---- evidence expansion ---------------------------------------------------------------
  // On a graded page, opening a <details> is the reader checking a claim rather than reading
  // past it. That is the behaviour these sites exist to invite, so it is worth counting.
  document.addEventListener('toggle', function (e) {
    var d = e.target;
    if (!d || d.tagName !== 'DETAILS' || !d.open) return;
    var s = d.querySelector('summary');
    var label = (s ? s.textContent : '').trim().replace(/\s+/g, ' ').slice(0, 60);
    ev('expand: ' + page + ' — ' + (label || 'details'), 'expand');
  }, true);

  // ---- read depth -----------------------------------------------------------------------
  // ⚠️ VOLUME: four milestones can multiply this account's event count per pageview. If the
  // GoatCounter plan starts to strain, cut MILESTONES to [50, 100] — that keeps the useful
  // "did they finish it?" signal at half the cost.
  var MILESTONES = [25, 50, 75, 100], hit = {};
  function depth() {
    var h = document.documentElement;
    var total = Math.max(h.scrollHeight - h.clientHeight, 1);
    var pct = Math.min(100, Math.round((window.scrollY || h.scrollTop || 0) / total * 100));
    for (var i = 0; i < MILESTONES.length; i++) {
      var m = MILESTONES[i];
      if (pct >= m && !hit[m]) { hit[m] = 1; ev('read: ' + page + ' ' + m + '%', 'read depth'); }
    }
  }
  var ticking = false;
  window.addEventListener('scroll', function () {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(function () { depth(); ticking = false; });
  }, { passive: true });
  window.addEventListener('load', depth);

  // ---- copy -----------------------------------------------------------------------------
  // These pages publish commands and hashes meant to be re-run. A copy is the strongest
  // available signal that someone intends to verify something themselves.
  document.addEventListener('copy', function () {
    var sel = (window.getSelection && String(window.getSelection())) || '';
    if (sel.trim().length < 8) return;
    ev('copy: ' + page, 'copy');
  }, true);
})();
