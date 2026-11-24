'use strict';
/* T3: HydroTheme resolves the four kinds, falls back to prefers-color-scheme and fires onChange. */
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('vm');
const H = require('./helpers');

function load(opts) {
  opts = opts || {};
  const attrs = {}, observers = [], mqls = [];
  const root = { getAttribute: (n) => (n in attrs ? attrs[n] : null), setAttribute: (n, v) => { attrs[n] = v; observers.forEach((o) => o.cb([{ attributeName: n }])); },
                 removeAttribute: (n) => { delete attrs[n]; observers.forEach((o) => o.cb([{ attributeName: n }])); } };
  let dark = !!opts.dark;
  const tokens = opts.tokens || { '--hy-axis': ' #57606a ', '--hy-series-2': '#c25400', '--hy-dash-2': 'none', '--hy-dash-3': '8 4' };
  class MutationObserver { constructor(cb) { this.cb = cb; } observe(el, o) { this.o = o; observers.push(this); } disconnect() { const i = observers.indexOf(this); if (i >= 0) observers.splice(i, 1); } }
  const win = {
    document: { documentElement: root }, MutationObserver,
    matchMedia: () => ({ get matches() { return dark; }, addEventListener: (t, f) => mqls.push(f), removeEventListener: (t, f) => { const i = mqls.indexOf(f); if (i >= 0) mqls.splice(i, 1); } }),
    getComputedStyle: () => ({ getPropertyValue: (n) => tokens[n] || '' }),
  };
  win.window = win;
  const ctx = vm.createContext(Object.assign({ console }, win));
  ctx.MutationObserver = MutationObserver; ctx.document = win.document;
  vm.runInContext(H.read('shared/theme.js'), ctx);
  return { T: vm.runInContext('HydroTheme', ctx), root, observers, mqls, setDark: (v) => { dark = v; mqls.slice().forEach((f) => f()); } };
}

test('kind() returns the host attribute for each of the four kinds', () => {
  const { T, root } = load();
  for (const k of ['light', 'dark', 'hc-dark', 'hc-light']) { root.setAttribute('data-aihydro-theme', k); assert.equal(T.kind(), k); }
});

test('no attribute (or a junk one): prefers-color-scheme decides, light when there is no preference', () => {
  let l = load({ dark: false });
  assert.equal(l.T.kind(), 'light');
  l.root.setAttribute('data-aihydro-theme', 'solarized');
  assert.equal(l.T.kind(), 'light', 'an unknown value is ignored');
  l = load({ dark: true });
  assert.equal(l.T.kind(), 'dark');
});

test('color() reads --hy-* tokens with or without the prefix, trimmed; series() and dash() read the numbered ones', () => {
  const { T } = load();
  assert.equal(T.color('axis'), '#57606a');
  assert.equal(T.color('hy-axis'), '#57606a');
  assert.equal(T.color('--hy-axis'), '#57606a');
  assert.equal(T.series(2), '#c25400');
  assert.equal(T.dash(2), '', '"none" means a solid line');
  assert.equal(T.dash(3), '8 4');
  assert.equal(T.color('missing'), '');
});

test('onChange fires on a host attribute change and on an OS scheme change, only when the kind really changed, and stops when asked', () => {
  const { T, root, setDark, observers, mqls } = load();
  const seen = [];
  const stop = T.onChange((k) => seen.push(k));
  root.setAttribute('data-aihydro-theme', 'dark');
  root.setAttribute('data-aihydro-theme', 'dark');                 /* no change */
  root.setAttribute('data-aihydro-theme', 'hc-light');
  assert.deepEqual(seen, ['dark', 'hc-light']);
  root.removeAttribute('data-aihydro-theme');                       /* back to the OS preference: light */
  setDark(true);
  assert.deepEqual(seen, ['dark', 'hc-light', 'light', 'dark']);
  stop();
  assert.equal(observers.length, 0);
  assert.equal(mqls.length, 0);
  root.setAttribute('data-aihydro-theme', 'light');
  assert.equal(seen.length, 4, 'no calls after stop()');
});
