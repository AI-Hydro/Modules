/* HydroTheme: read the lesson's theme and its colour tokens from script (SVG, canvas, three.js, Plotly).
 *
 * The host (AI-Hydro Studio) sets html[data-aihydro-theme] to light | dark | hc-dark | hc-light and updates it
 * live. With no attribute the CSS follows prefers-color-scheme, and this helper does the same, so a lesson
 * opened in a plain browser tab still themes itself. Colours live in shared/theme.css (--hy-*); this file only
 * reads them, so there is one source of truth.
 *
 *   HydroTheme.kind()          -> 'light' | 'dark' | 'hc-dark' | 'hc-light'
 *   HydroTheme.color('axis')   -> '#57606a'  (computed value of --hy-axis; 'hy-axis' and '--hy-axis' also work)
 *   HydroTheme.series(i)       -> colour of --hy-series-<i>, i = 1..5;  HydroTheme.dash(i) -> dash array or ''
 *   HydroTheme.onChange(cb)    -> cb(kind) on every theme switch (attribute change or OS scheme change);
 *                                 returns a function that stops listening
 * Redraw canvases, three.js materials and Plotly layouts in the callback; SVG that uses var(--hy-...) needs none.
 */
var HydroTheme = (function () {
  var KINDS = ['light', 'dark', 'hc-dark', 'hc-light'];
  var ATTR = 'data-aihydro-theme';
  function root() { return typeof document !== 'undefined' ? document.documentElement : null; }
  function osDark() {
    try { return !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches); } catch (e) { return false; }
  }
  function kind() {
    var r = root(), a = r && r.getAttribute ? r.getAttribute(ATTR) : null;
    if (a && KINDS.indexOf(a) >= 0) return a;
    return osDark() ? 'dark' : 'light';
  }
  function color(name) {
    var n = String(name);
    if (n.indexOf('--') !== 0) n = '--' + (n.indexOf('hy-') === 0 ? n : 'hy-' + n);
    var r = root(), v = '';
    try { v = window.getComputedStyle(r).getPropertyValue(n); } catch (e) { v = ''; }
    return (v || '').trim();
  }
  function series(i) { return color('series-' + i); }
  function dash(i) { var d = color('dash-' + i); return d === 'none' ? '' : d; }
  function onChange(cb) {
    var stops = [], last = kind();
    function fire() { var k = kind(); if (k !== last) { last = k; cb(k); } }
    var r = root();
    if (r && typeof MutationObserver !== 'undefined') {
      var mo = new MutationObserver(fire);
      mo.observe(r, { attributes: true, attributeFilter: [ATTR] });
      stops.push(function () { mo.disconnect(); });
    }
    try {
      var mq = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)');
      if (mq && mq.addEventListener) { mq.addEventListener('change', fire); stops.push(function () { mq.removeEventListener('change', fire); }); }
    } catch (e) { /* no matchMedia: the attribute path still works */ }
    return function () { stops.forEach(function (s) { s(); }); };
  }
  return { kinds: KINDS.slice(), kind: kind, color: color, series: series, dash: dash, onChange: onChange };
})();
if (typeof window !== 'undefined') window.HydroTheme = HydroTheme;
