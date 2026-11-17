'use strict';
/* A tiny fake DOM so each module's real inline scripts can run under node and we can
   assert that the page populates itself (no jsdom available; nothing is installed). */
const vm = require('vm');

function parseIds(html) {
  const info = {};
  const re = /<(\w+)([^>]*?)\sid="([^"]+)"([^>]*)>/g;
  let m;
  while ((m = re.exec(html))) {
    const attrs = (m[2] + ' ' + m[4]);
    const val = /\bvalue="([^"]*)"/.exec(attrs);
    info[m[3]] = { tag: m[1], value: val ? val[1] : '' };
  }
  const sel = /<select[^>]*\sid="([^"]+)"[^>]*>([\s\S]*?)<\/select>/g;
  while ((m = sel.exec(html))) {
    const opts = [...m[2].matchAll(/<option([^>]*)>/g)].map((o) => ({ v: (/value="([^"]*)"/.exec(o[1]) || [])[1] || '', sel: /\bselected\b/.test(o[1]) }));
    const pick = opts.find((o) => o.sel) || opts[0];
    if (pick) info[m[1]].value = pick.v;
  }
  const blob = /<script type="application\/json" id="([^"]+)">([\s\S]*?)<\/script>/g;
  while ((m = blob.exec(html))) info[m[1]] = Object.assign(info[m[1]] || {}, { text: m[2].replace(/<\\\//g, '</') });
  return info;
}

function makeElement(id, info) {
  const listeners = {};
  const attrs = {};
  const el = {
    id, tagName: (info.tag || 'div').toUpperCase(),
    textContent: info.text || '', innerHTML: '', value: info.value || '', checked: false, hidden: false, disabled: false,
    dataset: {}, children: [], width: 360, height: 360, offsetWidth: 400, offsetHeight: 300,
    style: new Proxy({}, { get: (t, k) => (k in t ? t[k] : ''), set: (t, k, v) => { t[k] = v; return true; } }),
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    setAttribute(k, v) { attrs[k] = String(v); }, getAttribute(k) { return k in attrs ? attrs[k] : null; },
    appendChild(c) { el.children.push(c); return c; },
    addEventListener(t, f) { (listeners[t] = listeners[t] || []).push(f); },
    removeEventListener() {},
    dispatch(t, ev) { (listeners[t] || []).forEach((f) => f(Object.assign({ target: el, preventDefault() {} }, ev))); },
    click() { el.dispatch('click'); },
    querySelector() { return null; }, querySelectorAll() { return []; },
    getBoundingClientRect() { return { left: 0, top: 0, width: 360, height: 360 }; },
    getContext() { return new Proxy(function () {}, { get: () => () => ({ addColorStop() {} }), apply: () => undefined }); },
    scrollIntoView() {}, focus() {}, closest() { return null; }, remove() {},
  };
  return el;
}

function run(html, opts) {
  opts = opts || {};
  const info = parseIds(html);
  const els = {};
  const getEl = (id) => (info[id] || opts.anyId ? (els[id] = els[id] || makeElement(id, info[id] || {})) : null);
  const document = {
    readyState: 'complete', body: makeElement('body', {}), documentElement: makeElement('html', {}),
    getElementById: getEl,
    querySelector() { return null; }, querySelectorAll() { return []; },
    createElement: () => makeElement('', {}), createElementNS: () => makeElement('', {}),
    addEventListener() {}, removeEventListener() {},
  };
  const timers = [];
  const win = {
    document, console, Math, JSON, Date, Event: function Event(t) { this.type = t; },
    matchMedia: () => ({ matches: true }), addEventListener() {}, removeEventListener() {}, parent: { postMessage() {} },
    setTimeout: (f) => { timers.push(f); return timers.length; }, clearTimeout() {},
    setInterval: () => 0, clearInterval() {}, requestAnimationFrame() { return 0; },
    sessionStorage: { getItem() { return null; }, setItem() {} }, location: { href: 'file:///module.html' },
    open() {}, print() {}, innerWidth: 1000,
  };
  win.window = win;
  Object.assign(win, opts.globals || {});
  const ctx = vm.createContext(win);
  const bodies = [];
  const sre = /<script(?<attr>[^>]*)>(?<body>[\s\S]*?)<\/script>/g;
  let m;
  while ((m = sre.exec(html))) {
    if (/src=|json/.test(m.groups.attr)) continue;
    bodies.push(m.groups.body);
  }
  bodies.forEach((b, i) => vm.runInContext(b, ctx, { filename: `inline-script-${i}.js` }));
  return { ctx, els, getEl };
}

module.exports = { run, makeElement };
