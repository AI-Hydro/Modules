'use strict';
/* Helpers for the node tests: load shared sources and the hand-maintained CORE
   blocks of a module into a fresh vm context (no DOM, no network). */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..', '..');

function read(rel) { return fs.readFileSync(path.join(ROOT, rel), 'utf8'); }
function moduleText(id) { return read(`modules/${id}/module.html`); }

function coreBlock(text, tag) {
  tag = tag || 'CORE';
  const re = new RegExp(`/\\*@@${tag}-BEGIN@@\\*/([\\s\\S]*?)/\\*@@${tag}-END@@\\*/`);
  const m = re.exec(text);
  if (!m) throw new Error(`no ${tag} block`);
  return m[1];
}

function blob(text, id) {
  const m = new RegExp(`<script type="application/json" id="${id}">([\\s\\S]*?)</script>`).exec(text);
  if (!m) throw new Error(`no blob ${id}`);
  return JSON.parse(m[1].replace(/<\\\//g, '</'));
}

/* Evaluate shared files + extra code in one context; returns the context. */
function load(shared, extra, globals) {
  const ctx = vm.createContext(Object.assign({ console, Math, JSON, Date }, globals || {}));
  const code = shared.map((n) => read(`shared/${n}`)).join('\n') + '\n' + (extra || '');
  vm.runInContext(code, ctx, { filename: 'test-bundle.js' });
  return ctx;
}

module.exports = { ROOT, read, moduleText, coreBlock, blob, load };
