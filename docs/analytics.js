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
 * ★ THE LINE THIS FILE WILL NOT CROSS, and why it was written down before it was tested.
 *   Asked in August 2026 to "track as much detail as possible", the tempting answer was a tool
 *   with per-visitor identity -- journeys, funnels, retention, returning-visitor counts. Every
 *   one of those needs to know that two events came from the SAME PERSON, and this project
 *   refuses to publish its own IPFS PeerID precisely because it would manufacture a link between
 *   an identity and a residential IP. Applying a weaker standard to READERS than to ourselves
 *   would be indefensible.
 *
 *   So the expansion below adds only things that are true of a VISIT and never of a VISITOR:
 *   what kind of thing was copied, which section was jumped to, whether a page was printed, how
 *   long it was open, whether the in-browser cryptography threw. No identifier is created,
 *   nothing is stored on the device, and no two events can be tied together afterwards.
 *
 *   ⇒ If a question genuinely needs per-visitor identity, the honest move is to decide that
 *     openly and write down what changed -- not to let a tool choice make the decision quietly.
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
  // ---- copy, classified by WHAT was copied ----------------------------------------------
  // A bare "copy" count says someone copied something. WHICH KIND of thing they copied says
  // what they intended to do with it, and costs nothing extra to know: a 64-hex string is a
  // hash they are about to compare, a line starting `gpg`/`openssl`/`sha256sum` is a check they
  // are about to run, an address is something else entirely.
  //
  // ⚠️ The classification is done on the SHAPE of the selection and the shape is all that is
  // sent. The selected text itself never leaves the page.
  function classify(t) {
    var s = t.trim();
    if (/^[0-9a-f]{64}$/i.test(s)) return 'sha256';
    if (/^[0-9a-f]{40}$/i.test(s)) return 'fingerprint-or-sha1';
    if (/^(gpg|openssl|sha256sum|ots|python|curl|dig|git|rad)/.test(s)) return 'command';
    if (/^(bc1|[13])[a-km-zA-HJ-NP-Z1-9]{25,}$/.test(s)) return 'address';
    if (/-----BEGIN/.test(s)) return 'pem-or-signature';
    if (s.length > 400) return 'passage-long';
    return 'text';
  }
  document.addEventListener('copy', function () {
    var sel = (window.getSelection && String(window.getSelection())) || '';
    if (sel.trim().length < 8) return;
    ev('copy: ' + page + ' — ' + classify(sel), 'copy');
  }, true);

  // ---- in-page navigation ---------------------------------------------------------------
  // On long documents, WHICH section a reader jumps to is the closest thing to knowing what
  // they came for. Anchor clicks are already in the DOM; nothing new is collected.
  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('a[href^="#"]') : null;
    if (!a) return;
    var frag = (a.getAttribute('href') || '').slice(1, 80);
    if (frag) ev('section: ' + page + ' #' + frag, 'jump to section');
  }, true);

  // ---- print / save ---------------------------------------------------------------------
  // Printing or saving a page to PDF is a strong intent signal on documents meant to be kept:
  // the manifest, the certificates, the findings. It fires at most once per page view.
  var printed = false;
  window.addEventListener('beforeprint', function () {
    if (printed) return; printed = true;
    ev('print: ' + page, 'print or save-as-pdf');
  });

  // ---- dwell, bucketed ------------------------------------------------------------------
  // How long a page held someone separates a bounce from a read. Sent as a BUCKET at the end
  // of the visit, never as a timestamp, and only once.
  //
  // ⚠️ visibilitychange is used rather than unload: unload is unreliable on mobile and is being
  // removed from browsers. sendBeacon is not used because count.js has no beacon endpoint --
  // this simply fires the normal event and accepts that the last one is occasionally lost.
  var t0 = Date.now(), sent = false;
  function dwell() {
    if (sent) return; sent = true;
    var s = Math.round((Date.now() - t0) / 1000);
    var b = s < 10 ? '0-10s' : s < 60 ? '10-60s' : s < 300 ? '1-5m' : s < 1800 ? '5-30m' : '30m+';
    ev('dwell: ' + page + ' ' + b, 'time on page');
  }
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') dwell();
  });

  // ---- script errors --------------------------------------------------------------------
  // These pages run real cryptography in the browser -- a genesis block re-derived from source
  // bytes, signatures checked client-side. If that breaks on someone's device we would never
  // otherwise hear about it, and a silent failure on the flagship claim is the worst kind.
  //
  // Only the message and the file are sent, both truncated. No stack, no URL parameters.
  var errs = 0;
  window.addEventListener('error', function (e) {
    if (errs++ > 3) return;                       // never let a loop become a flood
    var where = (e.filename || '').split('/').pop().slice(0, 40);
    var what = String(e.message || 'error').slice(0, 80);
    ev('jserror: ' + page + ' — ' + where + ' — ' + what, 'script error');
  });
  window.addEventListener('unhandledrejection', function (e) {
    if (errs++ > 3) return;
    ev('jserror: ' + page + ' — promise — ' + String((e.reason && e.reason.message) || e.reason)
       .slice(0, 80), 'unhandled rejection');
  });
})();
