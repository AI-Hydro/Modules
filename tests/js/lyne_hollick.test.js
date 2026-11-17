'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const H = require('./helpers');

const bf = H.moduleText('baseflow-separation');
const ctx = H.load(['lyne_hollick.js'], H.coreBlock(bf));
const { lyneHollick, baseflowIndex, makeSyntheticSeries } = ctx;
const series = makeSyntheticSeries();

/* Independent reference written from the definition (not copied from the module):
   each pass takes the previous pass's baseflow as input; series reflected at both ends. */
function reference(Q, alpha, passes, reflect) {
  const n = Q.length, r = Math.min(reflect, n - 1);
  let cur = [];
  for (let i = r; i >= 1; i--) cur.push(Q[i]);
  cur = cur.concat(Q);
  for (let i = 1; i <= r; i++) cur.push(Q[n - 1 - i]);
  for (let p = 0; p < passes; p++) {
    const idx = [...cur.keys()];
    if (p % 2 === 1) idx.reverse();
    const out = new Array(cur.length);
    let f = 0, prev = null;
    for (const i of idx) {
      if (prev === null) { out[i] = cur[i]; }
      else {
        f = Math.max(alpha * f + (1 + alpha) / 2 * (cur[i] - cur[prev]), 0);
        out[i] = Math.max(cur[i] - f, 0);
      }
      prev = i;
    }
    cur = out;
  }
  return cur.slice(r, r + n);
}

test('matches an independent definition-level reference', () => {
  for (const a of [0.8, 0.925, 0.98]) {
    const x = lyneHollick(series.Q, a), y = reference(series.Q, a, 3, 30);
    for (let i = 0; i < x.length; i++) assert.ok(Math.abs(x[i] - y[i]) < 1e-12, `alpha ${a} day ${i}`);
  }
});

test('each pass filters the previous pass (not the raw series)', () => {
  const one = lyneHollick(series.Q, 0.925, 1), three = lyneHollick(series.Q, 0.925, 3);
  const sumOne = one.reduce((a, b) => a + b, 0), sumThree = three.reduce((a, b) => a + b, 0);
  assert.ok(sumThree < sumOne, 'cascading passes must remove more quickflow, not re-filter the raw Q');
});

test('baseflow is bounded: 0 <= b <= Q', () => {
  const b = lyneHollick(series.Q, 0.925);
  b.forEach((v, i) => { assert.ok(v >= 0 && v <= series.Q[i] + 1e-12); });
});

test('constant flow is all baseflow', () => {
  const b = lyneHollick(new Array(200).fill(3.5), 0.925);
  b.forEach((v) => assert.ok(Math.abs(v - 3.5) < 1e-12));
});

test('reflection changes the edges (spin-up) but not the series length', () => {
  const Q = []; for (let i = 0; i < 100; i++) Q.push(1 + 5 * Math.exp(-i / 5));   /* recession starting at the edge */
  const withRef = lyneHollick(Q, 0.925, 3, 30), noRef = lyneHollick(Q, 0.925, 3, 0);
  assert.equal(withRef.length, Q.length);
  assert.ok(withRef.slice(0, 10).some((v, i) => Math.abs(v - noRef[i]) > 1e-6), 'edge values must differ');
});

test('BFI falls monotonically as alpha rises (module quiz Q2)', () => {
  let last = Infinity;
  for (let a = 0.80; a <= 0.98 + 1e-9; a += 0.01) {
    const bfi = baseflowIndex(series.Q, lyneHollick(series.Q, a));
    assert.ok(bfi < last, `BFI must decrease at alpha ${a.toFixed(2)}`);
    last = bfi;
  }
});

test('every module that embeds the filter carries the shared text verbatim', () => {
  const shared = H.read('shared/lyne_hollick.js').replace(/\n+$/, '');
  for (const id of ['baseflow-separation', 'reading-a-hydrograph', 'capstone-basin-story']) {
    assert.ok(H.moduleText(id).includes(shared), `${id} must inline shared/lyne_hollick.js`);
  }
});
