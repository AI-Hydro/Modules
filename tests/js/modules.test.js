'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const H = require('./helpers');

/* ── water-cycle bathtub: mass conservation ─────────────────── */
test('water-cycle bucket conserves mass for every step and over long runs', () => {
  const ctx = H.load([], H.coreBlock(H.moduleText('water-cycle-in-motion')));
  let S = 45, maxErr = 0, sumP = 0, sumET = 0, sumR = 0;
  const seq = [0, 3, 10, 10, 10, 0.5, 7, 2, 0, 10, 10, 10, 10, 0];
  for (let k = 0; k < 2000; k++) {
    const P = seq[k % seq.length], dt = 0.05;
    const s = ctx.stepBucket(S, P, 2.0, dt);
    maxErr = Math.max(maxErr, Math.abs((S + (P - s.ET - s.R) * dt) - s.S));
    assert.ok(s.S >= -1e-12 && s.S <= ctx.BUCKET.cap + 1e-12);
    sumP += P * dt; sumET += s.ET * dt; sumR += s.R * dt; S = s.S;
  }
  assert.ok(maxErr < 1e-10, `per-step balance error ${maxErr}`);
  assert.ok(Math.abs(45 + sumP - sumET - sumR - S) < 1e-8, 'closure over the whole run');
});

/* ── reading-a-hydrograph: SCS curve number + volume conservation ─ */
const rd = H.moduleText('reading-a-hydrograph');
const r = H.load(['lyne_hollick.js'], H.coreBlock(rd));

test('reading: SCS-CN Q(P) matches (P-Ia)^2/(P+0.8S) and is zero below Ia', () => {
  const S = 25400 / 75 - 254, Ia = 0.2 * S;
  for (const P of [5, Ia, 25, 50, 100]) {
    const want = P <= Ia ? 0 : (P - Ia) ** 2 / (P + 0.8 * S);
    assert.ok(Math.abs(r.STORM.runoff(P) - want) < 1e-12, `P=${P}`);
  }
});

test('reading: both demo storms (25 mm and 50 mm) produce runoff; ratio is only formed then', () => {
  const a = r.STORM.stats(r.STORM.P_SMALL), b = r.STORM.stats(r.STORM.P_SMALL * 2);
  assert.ok(a.runoff_mm > 0 && b.runoff_mm > 0 && a.peakQuick > 0 && b.peakQuick > 0);
  for (let m = 1; m <= 4; m += 0.1) assert.ok(r.STORM.stats(r.STORM.P_SMALL * m).runoff_mm > 0);
});

test('reading: routed quickflow volume equals runoff depth x area', () => {
  for (const P of [25, 37.5, 50, 100]) {
    const s = r.STORM.stats(P);
    const want = s.runoff_mm / 1000 * r.STORM.A_KM2 * 1e6;
    assert.ok(Math.abs(s.volume_m3 - want) / want < 1e-9, `P=${P}`);
  }
});

test('reading: the 96-hour BFI falls as alpha rises (quiz Q2)', () => {
  const bfi = (a) => r.baseflowIndex(r.EVENT_Q, r.lyneHollick(r.EVENT_Q, a));
  assert.ok(bfi(0.985) < bfi(0.925));
});

/* ── real-streamflow-data ───────────────────────────────────── */
const rs = H.moduleText('real-streamflow-data');
const rsc = H.load([], H.coreBlock(rs));

test('real-streamflow: custom gauge ids are validated before use', () => {
  for (const ok of ['01013500', '123456789012345']) assert.ok(rsc.validSite(ok));
  for (const bad of ['', 'abc', '0101350', '01013500; import os', '1234567890123456', "01013500'"])
    assert.ok(!rsc.validSite(bad), bad);
});

test('real-streamflow: there is no synthetic-data branch in the generated cells', () => {
  const g = H.blob(rs, 'camels-5yr').gauges['01013500'];
  const src = rsc.buildSnapshotSource(g, '2026-11-17') + rsc.buildNwisSource('01013500');
  for (const banned of ['default_rng', 'synthetic fallback', 'rng.', 'np.random'])
    assert.ok(!src.includes(banned), banned);
});
