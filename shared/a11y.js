/* Accessibility helpers shared by every module (keyboard access, live announcements,
 * reduced motion). Single source of truth: shared/a11y.js, inlined by scripts/build_modules.py.
 * Pure logic (keyValue) is unit-tested under node; the DOM helpers use only the standard DOM.
 */
var HydroA11y = (function () {
  'use strict';

  /* True when the user asked the OS/browser for less motion. Widgets must still update;
     they just must not animate or autoplay on their own. */
  function reducedMotion() {
    try {
      return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    } catch (e) { return false; }
  }

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  /* Round to the step grid anchored at min, trimming float noise. */
  function snap(v, min, step) {
    var n = Math.round((v - min) / step);
    var out = min + n * step;
    var decimals = (String(step).split('.')[1] || '').length;
    return parseFloat(out.toFixed(Math.min(decimals + 2, 12)));
  }

  /* WAI-ARIA slider keys. Returns the new value, or null when the key is not handled. */
  function keyValue(key, cur, o) {
    var step = o.step || 1, page = o.page || step * 10, v;
    switch (key) {
      case 'ArrowRight': case 'ArrowUp':   v = cur + step; break;
      case 'ArrowLeft':  case 'ArrowDown': v = cur - step; break;
      case 'PageUp':   v = cur + page; break;
      case 'PageDown': v = cur - page; break;
      case 'Home': v = o.min; break;
      case 'End':  v = o.max; break;
      default: return null;
    }
    return clamp(snap(v, o.min, step), o.min, o.max);
  }

  /* One polite live region for short announcements (selected cell, new scenario, ...). */
  function announce(msg) {
    var el = document.getElementById('hydro-announcer');
    if (!el) {
      el = document.createElement('div');
      el.id = 'hydro-announcer';
      el.className = 'hydro-sr-only';
      el.setAttribute('role', 'status');
      el.setAttribute('aria-live', 'polite');
      el.setAttribute('aria-atomic', 'true');
      document.body.appendChild(el);
    }
    el.textContent = '';
    el.textContent = String(msg);
  }

  /* Make `el` a keyboard-operable slider.
       o = { label, min, max, step, page, get(), set(v), text(v) }
     get() returns the current value, set(v) applies a new one (the caller redraws), text(v)
     is the human-readable value for screen readers. Call the returned sync() after the value
     changes by other means (mouse drag, a paired <input type=range>). */
  function slider(el, o) {
    el.setAttribute('role', 'slider');
    el.setAttribute('tabindex', '0');
    if (o.label) el.setAttribute('aria-label', o.label);
    el.setAttribute('aria-valuemin', String(o.min));
    el.setAttribute('aria-valuemax', String(o.max));
    function sync() {
      var v = o.get();
      el.setAttribute('aria-valuenow', String(v));
      el.setAttribute('aria-valuetext', o.text ? o.text(v) : String(v));
    }
    el.addEventListener('keydown', function (ev) {
      var nv = keyValue(ev.key, o.get(), o);
      if (nv === null) return;
      ev.preventDefault();
      if (nv !== o.get()) o.set(nv);
      sync();
    });
    sync();
    return { sync: sync };
  }

  /* Make a non-button element (a card, a node) operable from the keyboard: role, tab stop, and
     Enter/Space as well as click all call fn. */
  function activatable(el, fn, role) {
    if (!el.getAttribute('role')) el.setAttribute('role', role || 'button');
    if (el.getAttribute('tabindex') === null) el.setAttribute('tabindex', '0');
    el.addEventListener('click', fn);
    el.addEventListener('keydown', function (ev) {
      if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); fn(ev); }
    });
  }

  /* [data-scroll="section-id"] elements scroll to that section (replaces inline onclick). */
  function wireScrollNav() {
    var nodes = document.querySelectorAll('[data-scroll]');
    for (var i = 0; i < nodes.length; i++) (function (node) {
      activatable(node, function () {
        var t = document.getElementById(node.getAttribute('data-scroll'));
        if (!t) return;
        t.scrollIntoView({ behavior: reducedMotion() ? 'auto' : 'smooth', block: 'start' });
        t.setAttribute('tabindex', '-1');
        try { t.focus({ preventScroll: true }); } catch (e) {}
      });
    })(nodes[i]);
  }

  /* Mark readouts as polite live regions so screen readers hear changed values. */
  function live(ids) {
    ids.forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      el.setAttribute('aria-live', 'polite');
      el.setAttribute('aria-atomic', 'true');
    });
  }

  return { reducedMotion: reducedMotion, keyValue: keyValue, snap: snap, announce: announce,
           slider: slider, live: live, activatable: activatable, wireScrollNav: wireScrollNav };
})();
