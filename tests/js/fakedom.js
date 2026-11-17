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
    const cl = /\bclass="([^"]*)"/.exec(attrs);
    const data = {};
    for (const d of attrs.matchAll(/\sdata-([\w-]+)="([^"]*)"/g)) data[d[1].replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = d[2];
    info[m[3]] = { tag: m[1], value: val ? val[1] : '', cls: cl ? cl[1].split(/\s+/) : [], data };
  }
  const sel = /<select[^>]*\sid="([^"]+)"[^>]*>([\s\S]*?)<\/select>/g;
  while ((m = sel.exec(html))) {
    const opts = [...m[2].matchAll(/<option([^>]*)>/g)].map((o) => ({ v: (/value="([^"]*)"/.exec(o[1]) || [])[1] || '', sel: /\bselected\b/.test(o[1]) }));
    const pick = opts.find((o) => o.sel) || opts[0];
    if (pick) info[m[1]].value = pick.v;
  }
  const blob = /<script type="application\/json" id="([^"]+)">([\s\S]*?)<\/script>/g;
  while ((m = blob.exec(html))) info[m[1]] = Object.assign(info[m[1]] || {}, { text: m[2].replace(/<\\\//g, '</') });
  /* static text of <pre id=...> code panes (what the learner reads before any script rewrites it) */
  const pre = /<pre[^>]*\sid="([^"]+)"[^>]*>([\s\S]*?)<\/pre>/g;
  while ((m = pre.exec(html))) {
    const text = m[2].replace(/<!--[\s\S]*?-->/g, '').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
    if (info[m[1]]) info[m[1]].text = text;
  }
  return info;
}

function makeElement(id, info) {
  const listeners = {};
  const attrs = {};
  const el = {
    id, tagName: (info.tag || 'div').toUpperCase(),
    textContent: info.text || '', innerHTML: '', value: info.value || '', checked: false, hidden: false, disabled: false,
    dataset: Object.assign({}, info.data || {}), children: [], width: 360, height: 360, offsetWidth: 400, offsetHeight: 300,
    style: new Proxy({}, { get: (t, k) => (k in t ? t[k] : ''), set: (t, k, v) => { t[k] = v; return true; } }),
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    setAttribute(k, v) { attrs[k] = String(v); }, getAttribute(k) { return k in attrs ? attrs[k] : null; },
    removeAttribute(k) { delete attrs[k]; }, hasAttribute(k) { return k in attrs; }, attrs,
    appendChild(c) { el.children.push(c); return c; },
    addEventListener(t, f) { (listeners[t] = listeners[t] || []).push(f); },
    removeEventListener() {},
    dispatch(t, ev) { (listeners[t] || []).forEach((f) => f.call(el, Object.assign({ target: el, preventDefault() {} }, ev))); },
    click() { el.dispatch('click'); },
    querySelector() { return null; }, querySelectorAll() { return []; },
    getBoundingClientRect() { return { left: 0, top: 0, width: 360, height: 360 }; },
    getContext() { return new Proxy(function () {}, { get: () => () => ({ addColorStop() {} }), apply: () => undefined }); },
    scrollIntoView() {}, focus() {}, closest() { return null; }, remove() {},
  };
  return el;
}

/* Static text of each executable cell's source (what a learner reads), for HydroQuiz.sourceConstant. */
function staticCellSources(html) {
  const out = {};
  const re = /<div class="aihydro-cell"[^>]*data-aihydro-cell-id="([^"]+)"[^>]*>[\s\S]*?<pre class="aihydro-source"[^>]*>([\s\S]*?)<\/pre>/g;
  let m;
  while ((m = re.exec(html))) {
    out[m[1]] = m[2].replace(/<!--[\s\S]*?-->/g, '').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
  }
  return out;
}

function run(html, opts) {
  opts = Object.assign({ cellSources: staticCellSources(html) }, opts || {});
  const info = parseIds(html);
  const els = {};
  const getEl = (id) => (info[id] || opts.anyId ? (els[id] = els[id] || makeElement(id, info[id] || {})) : null);
  const document = {
    readyState: 'complete', body: makeElement('body', {}), documentElement: makeElement('html', {}),
    getElementById: getEl,
    querySelectorAll(sel) { const m = /^\.([\w-]+)$/.exec(sel); return m ? Object.keys(info).filter((id) => (info[id].cls || []).includes(m[1])).map(getEl) : []; },
    querySelector(sel) { const m = /data-aihydro-cell-id="([^"]+)"\] \.aihydro-source/.exec(sel); return m && opts.cellSources && opts.cellSources[m[1]] ? { textContent: opts.cellSources[m[1]] } : null; },
    createElement: () => makeElement('', {}), createElementNS: () => makeElement('', {}),
    addEventListener() {}, removeEventListener() {},
  };
  const timers = [];
  const counters = { setInterval: 0, setTimeout: 0, postMessages: [] };
  const win = {
    document, console, Math, JSON, Date, Event: function Event(t) { this.type = t; },
    matchMedia: () => ({ matches: true }), addEventListener() {}, removeEventListener() {}, parent: { postMessage(m, o) { counters.postMessages.push([m, o]); } },
    setTimeout: (f) => { timers.push(f); return timers.length; }, clearTimeout() {},
    setInterval: () => { counters.setInterval++; return counters.setInterval; }   /* real timer ids are positive; shared/ready.js treats 0 as 'no timer' */, clearInterval() {}, requestAnimationFrame() { return 0; },
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
  return { ctx, els, getEl, counters };
}

module.exports = { run, makeElement, staticCellSources };
