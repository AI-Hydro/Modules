'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const vm = require('vm');
const H = require('./helpers');
const { makeElement, run } = require('./fakedom');

function load(extra) {
  const document = { createElement: (t) => makeElement('', { tag: t }), body: makeElement('body', {}), getElementById: () => null, querySelectorAll: () => [] };
  const win = { document, console, Math, JSON, matchMedia: () => ({ matches: false }) };
  win.window = win;
  const ctx = vm.createContext(win);
  vm.runInContext(H.read('shared/a11y.js') + '\n' + (extra || ''), ctx);
  return { ctx, A: vm.runInContext('HydroA11y', ctx) };
}

test('keyValue implements the WAI-ARIA slider keys, snaps to the step grid and clamps', () => {
  const { A } = load();
  const o = { min: 0.9, max: 0.995, step: 0.005 };
  assert.equal(A.keyValue('ArrowRight', 0.925, o), 0.93);
  assert.equal(A.keyValue('ArrowLeft', 0.925, o), 0.92);
  assert.equal(A.keyValue('Home', 0.925, o), 0.9);
  assert.equal(A.keyValue('End', 0.925, o), 0.995);
  assert.equal(A.keyValue('PageUp', 0.925, o), 0.975);
  assert.equal(A.keyValue('ArrowRight', 0.995, o), 0.995, 'clamped at max');
  assert.equal(A.keyValue('ArrowLeft', 0.9, o), 0.9, 'clamped at min');
  assert.equal(A.keyValue('Tab', 0.925, o), null, 'other keys are left alone');
});

test('slider() gives an element role, tab stop, value range, readable text, and drives set() from the keyboard', () => {
  const { ctx, A } = load();
  const el = makeElement('t', { tag: 'span' });
  let v = 50; const seen = [];
  ctx.el = el;
  vm.runInContext("var h = HydroA11y.slider(el, { label: 'Divider', min: 5, max: 95, step: 5, page: 15, get: function () { return globalThis.v; }, set: function (n) { globalThis.v = n; }, text: function (n) { return n + ' percent'; } }); globalThis.v = 50;", ctx);
  assert.equal(el.getAttribute('role'), 'slider');
  assert.equal(el.getAttribute('tabindex'), '0');
  assert.equal(el.getAttribute('aria-label'), 'Divider');
  assert.equal(el.getAttribute('aria-valuemin'), '5');
  assert.equal(el.getAttribute('aria-valuemax'), '95');
  el.dispatch('keydown', { key: 'ArrowRight', preventDefault() { seen.push('pd'); } });
  assert.equal(ctx.v, 55);
  assert.equal(el.getAttribute('aria-valuenow'), '55');
  assert.equal(el.getAttribute('aria-valuetext'), '55 percent');
  assert.deepEqual(seen, ['pd'], 'handled keys prevent the default (page scroll)');
  el.dispatch('keydown', { key: 'End', preventDefault() {} });
  assert.equal(ctx.v, 95);
  el.dispatch('keydown', { key: 'a', preventDefault() { seen.push('bad'); } });
  assert.deepEqual(seen, ['pd']);
});

test('activatable() makes a non-button operable with Enter and Space as well as click', () => {
  const { ctx } = load();
  const el = makeElement('c', { tag: 'div' });
  ctx.el = el; ctx.n = 0;
  vm.runInContext('HydroA11y.activatable(el, function () { n++; }, "button")', ctx);
  assert.equal(el.getAttribute('role'), 'button');
  assert.equal(el.getAttribute('tabindex'), '0');
  el.dispatch('click'); el.dispatch('keydown', { key: 'Enter', preventDefault() {} }); el.dispatch('keydown', { key: ' ', preventDefault() {} });
  el.dispatch('keydown', { key: 'x', preventDefault() {} });
  assert.equal(ctx.n, 3);
});

const ids = fs.readdirSync(`${H.ROOT}/modules`).filter((d) => fs.existsSync(`${H.ROOT}/modules/${d}/module.html`));

for (const id of ids) {
  const t = H.moduleText(id);
  test(`${id}: no mouse-only wiring is left (no inline handlers, scroll nav is data-driven)`, () => {
    assert.ok(!/\son(click|change|input|keydown|mouse\w+|load)=/.test(t), 'inline event-handler attribute found');
    for (const m of t.matchAll(/<div[^>]*\sdata-scroll="([^"]+)"/g)) assert.ok(t.includes(`id="${m[1]}"`), `data-scroll target ${m[1]} exists`);
  });
  test(`${id}: has a polite live region for dynamic readouts and honours reduced motion CSS`, (tc) => {
    if (id === 'course-certificate') return tc.skip('no quiz; its name preview is deliberately not live (one keystroke = one announcement)');
    assert.ok(/aria-live="polite"/.test(t) || /aria-live['"],\s*['"]polite/.test(t) || /HydroA11y\.live\(/.test(t));
    assert.ok(/prefers-reduced-motion: reduce/.test(t));
  });
}

test('every control that can only be operated by dragging has a keyboard path (role=slider / spinbutton / application)', () => {
  const need = {
    'reading-a-hydrograph': ['HydroA11y.slider(el'],           /* tangle numbers */
    'baseflow-separation': ['HydroA11y.slider(handle'],        /* compare wipe */
    'dem-to-twi': ['HydroA11y.slider(handle', "role: 'button'"],            /* compare wipe + SVG cells */
    'watershed-runoff': ['role="application"'],                /* the canvas */
  };
  for (const [mod, needles] of Object.entries(need)) for (const n of needles) assert.ok(H.moduleText(mod).includes(n), `${mod}: ${n}`);
});

test('the watershed canvas can be driven from the keyboard and gives a text readout', () => {
  const { els, ctx } = run(H.moduleText('watershed-runoff'));
  const canvas = els.routingCanvas;
  assert.ok(canvas, 'routing canvas exists');
  const keys = [];
  /* the fake canvas records listeners; dispatch arrows then Enter */
  for (const key of ['ArrowRight', 'ArrowRight', 'ArrowDown', 'Enter']) canvas.dispatch('keydown', { key, shiftKey: false, preventDefault() { keys.push(key); } });
  assert.deepEqual(keys, ['ArrowRight', 'ArrowRight', 'ArrowDown', 'Enter']);
  assert.ok(/Cell \[18, 17\]|Cell \[18,/.test(els.flowMsg.textContent) || /cells/.test(els.flowMsg.textContent), 'selection is described in text: ' + els.flowMsg.textContent);
  assert.ok(els.statPath.textContent.length > 0);
});

const QUIZ_ROOTS = { 'baseflow-separation': 'bfQuiz', 'reading-a-hydrograph': 'm3-quiz', 'watershed-runoff': 'watershedQuiz',
  'water-cycle-in-motion': 'cycleQuiz', 'real-streamflow-data': 'm5-quiz', 'capstone-basin-story': 'm7-quiz', 'dem-to-twi': 'm6-quiz' };

for (const [mod, rootId] of Object.entries(QUIZ_ROOTS)) {
  test(`${mod}: before any attempt the checkpoint DOM holds no answer, explanation, mark or answer attribute`, () => {
    const { els, ctx } = run(H.moduleText(mod));
    const items = vm.runInContext('HydroQuiz.instances', ctx);
    const api = Object.values(items)[0];
    const root = els[rootId];
    assert.ok(root && root.children.length, 'quiz rendered');
    let text = '';
    (function walk(n) {
      text += ' ' + (n.textContent || '');
      for (const k of Object.keys(n.attrs || {})) {
        assert.ok(!/answer|correct|solution/i.test(k) && !/answer|correct|solution/i.test(String(n.attrs[k])), `${k}=${n.attrs[k]}`);
      }
      if (n.checked) assert.fail('a radio is pre-checked');
      (n.children || []).forEach(walk);
    })(root);
    for (const it of api.describe()) {
      assert.ok(it.explain && !text.includes(it.explain), `explanation of ${it.id} is not in the DOM`);
    }
  });
}
