'use strict';
/* runoff-generation: the controls work without the AI-Hydro bridge, the readouts and code panes follow them, the models
   keep their invariants, and the prose that states an antecedent-wetness pattern is generated from computed numbers. */
const test = require('node:test');
const assert = require('node:assert/strict');
const H = require('./helpers');
const { run } = require('./fakedom');

const MOD = 'runoff-generation';
const T = H.moduleText(MOD);
const BLOB = H.blob(T, 'runoff-events');
const GIDS = ['14305500', '02472000', '09484000'];
const core = H.load(['lyne_hollick.js'], H.coreBlock(T));
const key = (el, k) => el.dispatch('keydown', { key: k, preventDefault() {} });

test('the page loads with no bridge and fills its readouts, plots and code panes', () => {
  const { els, ctx } = run(T);
  assert.equal(ctx.window.aihydro, undefined);
  assert.match(els.gaReadout.textContent, /t_p = 48\.0 min \(F_p = 20\.0 mm\)/);
  assert.match(els.massReadout.textContent, /residual 0\.000000000 mm/);
  assert.match(els.massReadout.textContent, /infiltration excess/);
  assert.ok(els.synSource.textContent.includes('SYNTHETIC column') && els.synSource.textContent.includes('I = 25.0'));
  assert.ok(els.evSource.textContent.includes('GAUGE = "14305500"') && els.evSource.textContent.includes('REAL DATA'));
  assert.ok(els.gaSvg.children.length > 20 && els.massSvg.children.length > 10 && els.mapGrid.children.length > 100 && els.hillSvg.children.length > 40);
  assert.equal(els['card-14305500'].getAttribute('aria-pressed'), 'true');
  assert.equal(els['card-02472000'].getAttribute('aria-pressed'), 'false');
});

test('every slider is a keyboard slider: role, value range, arrow/Home/End/Page keys, live text', () => {
  const { els } = run(T);
  for (const [id, lo, hi, v0] of [['sl-i', 2, 60, 25], ['sl-T', 0.5, 6, 2], ['sl-D', 10, 120, 60], ['sl-P', 0, 100, 30]]) {
    const el = els[id];
    assert.equal(el.getAttribute('role'), 'slider', id);
    assert.equal(el.getAttribute('tabindex'), '0');
    assert.equal(+el.getAttribute('aria-valuemin'), lo);
    assert.equal(+el.getAttribute('aria-valuemax'), hi);
    assert.equal(+el.getAttribute('aria-valuenow'), v0);
    assert.ok(el.getAttribute('aria-label').length > 10 && el.getAttribute('aria-valuetext'));
    key(el, 'End'); assert.equal(+el.getAttribute('aria-valuenow'), hi);
    key(el, 'Home'); assert.equal(+el.getAttribute('aria-valuenow'), lo);
    key(el, 'ArrowRight'); assert.ok(+el.getAttribute('aria-valuenow') > lo);
    key(el, 'PageDown'); assert.equal(+el.getAttribute('aria-valuenow'), lo);
  }
  assert.equal(els['v-i'].textContent, '2 mm/h');
});

test('moving the rain intensity rewrites the readout, the plots and the code with no bridge', () => {
  const { els } = run(T);
  const before = els.gaReadout.textContent, src0 = els.synSource.textContent;
  key(els['sl-i'], 'ArrowLeft'); key(els['sl-i'], 'ArrowLeft');
  assert.equal(els['sl-i'].getAttribute('aria-valuenow'), '23');
  assert.notEqual(els.gaReadout.textContent, before);
  const r = core.gaRun(23, 2, 60);
  assert.ok(els.gaReadout.textContent.includes('t_p = ' + (r.tp * 60).toFixed(1) + ' min'));
  assert.ok(els.gaReadout.textContent.includes('R_IE = ' + r.RIE.toFixed(2) + ' mm'));
  assert.match(els.synSource.textContent, /^I = 23\.0 /m);
  assert.notEqual(els.synSource.textContent, src0);
  assert.equal(els['v-i'].textContent, '23 mm/h');
  assert.equal(els['m-tp'].textContent, (r.tp * 60).toFixed(1));
});

test('a rain rate at or below Ks says the surface never ponds, and a small deficit shifts the mechanism to saturation excess', () => {
  const { els } = run(T);
  for (let k = 0; k < 30; k++) key(els['sl-i'], 'ArrowLeft');            // down to 2 mm/h
  assert.match(els.gaReadout.textContent, /i ≤ Ks: no ponding/);
  assert.equal(els['u-tp'].textContent, 'i ≤ Ks: never ponds');
  key(els['sl-D'], 'Home');                                              // 10 mm of room
  key(els['sl-T'], 'End');                                               // 6 h
  assert.match(els.massReadout.textContent, /saturation excess/);
  const r = core.gaRun(2, 6, 10);
  assert.equal(r.RIE, 0);
  assert.ok(els.massReadout.textContent.includes('R_SE ' + r.RSE.toFixed(2)));
});

test('with the bridge present, a control change asks it to rewrite the cell (and the learner still clicks Run)', () => {
  const calls = [];
  const { els } = run(T, { globals: { aihydro: { rewriteCell(id, fn, auto) { calls.push([id, fn(), auto]); } } } });
  calls.length = 0;
  key(els['sl-D'], 'ArrowRight');
  key(els['sl-P'], 'ArrowRight');
  els.wetToggle.click();
  els['card-09484000'].click();
  assert.deepEqual(calls.map((c) => c[0]), ['column-hillslope', 'column-hillslope', 'column-hillslope', 'event-runoff-ratios']);
  assert.ok(calls.every((c) => c[2] === false));
  assert.match(calls[0][1], /^D = 65\.0 /m);
  assert.match(calls[3][1], /GAUGE = "09484000"/);
});

test('the mechanism map is keyboard operable and described in text', () => {
  const { els } = run(T);
  const map = els.mapGrid;
  /* static attributes live in the markup (the fake DOM only records attributes set at run time) */
  const tag = /<svg id="mapGrid"[^>]*>/.exec(T)[0];
  assert.ok(/tabindex="0"/.test(tag) && /role="application"/.test(tag) && /aria-describedby="mapReadout"/.test(tag));
  assert.ok(/aria-label="[^"]{60,}"/.test(tag));
  assert.match(els.mapReadout.textContent, /^Rain 25 mm\/h for 2\.00 h on a deficit of 60 mm: infiltration excess dominates/);
  const seen = [];
  for (const k of ['ArrowRight', 'ArrowRight', 'ArrowUp', 'Home', 'End', 'PageUp', 'PageDown']) {
    let prevented = false;
    map.dispatch('keydown', { key: k, preventDefault() { prevented = true; } });
    assert.ok(prevented, k + ' is handled');
    seen.push(els.mapReadout.textContent);
  }
  assert.match(seen[0], /Rain 30 mm\/h/);
  assert.match(seen[3], /Rain 5 mm\/h/);
  assert.match(seen[4], /Rain 60 mm\/h/);
  assert.match(seen[5], /deficit of 10 mm/);
  assert.match(seen[6], /deficit of 120 mm/);
  let other = false;
  map.dispatch('keydown', { key: 'a', preventDefault() { other = true; } });
  assert.ok(!other, 'other keys are left alone');
  /* the grid is recomputed from the storm duration slider: the text of the same cell changes with T */
  map.dispatch('keydown', { key: 'Home', preventDefault() {} });
  const a = els.mapReadout.textContent;
  key(els['sl-T'], 'End');
  assert.notEqual(els.mapReadout.textContent, a);
  assert.match(els.mapReadout.textContent, /for 6\.00 h/);
  /* clicking a cell selects it (the fake box is 360 px wide, the grid is drawn in 720 units) */
  map.dispatch('click', { clientX: (64 + 54 * 3 + 10) / 2, clientY: (22 + 28 * 2 + 10) * 360 / 440 });
  assert.match(els.mapReadout.textContent, /^Rain 20 mm\/h for 6\.00 h on a deficit of 30 mm/);
});

test('every map cell carries a text label and the three classes use different fills', () => {
  const { els } = run(T);
  const kids = els.mapGrid.children;
  const labels = kids.map((k) => k.textContent);
  for (const l of ['IE', 'SE', 'none']) assert.ok(labels.includes(l), l);
  const fills = new Set(kids.filter((k) => k.getAttribute('width') === '54').map((k) => k.getAttribute('fill')));
  assert.equal(fills.size, 3);
  assert.ok(T.includes('legend-swatch sw-mie') && T.includes('sw-mno') && T.includes('diagonal hatch') && T.includes('dots'));
});

test('the hillslope slider and wetter-start toggle change the saturated count, and the toggle is aria-pressed', () => {
  const { els } = run(T);
  const base = core.hillRun(30, false);
  assert.match(els.hillReadout.textContent, new RegExp(base.satCount + ' of 20 columns saturated \\(saturated fraction ' + base.satFrac.toFixed(2)));
  assert.match(T, /id="wetToggle"[^>]*aria-pressed="false"/);
  els.wetToggle.click();
  assert.equal(els.wetToggle.getAttribute('aria-pressed'), 'true');
  const wet = core.hillRun(30, true);
  assert.ok(wet.satCount > base.satCount);
  assert.match(els.hillReadout.textContent, new RegExp(wet.satCount + ' of 20 columns saturated'));
  assert.match(els.hillReadout.textContent, /wetter start/);
  assert.match(els.synSource.textContent, /^WET = True /m);
  els.wetToggle.click();
  assert.equal(els.wetToggle.getAttribute('aria-pressed'), 'false');
  let prev = -1;
  key(els['sl-P'], 'Home');
  for (let P = 0; P <= 100; P += 5) {
    if (P > 0) key(els['sl-P'], 'ArrowRight');
    const m = /(\d+) of 20 columns saturated/.exec(els.hillReadout.textContent);
    assert.ok(+m[1] >= prev); prev = +m[1];
    assert.match(els.synSource.textContent, new RegExp('^PH = ' + P + '\\.0 ', 'm'));
  }
});

test('choosing a basin card rewrites the event source, readout, table and prose from computed numbers', () => {
  const { els } = run(T);
  for (const g of GIDS) {
    els['card-' + g].click();
    const s = core.eventStats(BLOB.basins[g]);
    const b = BLOB.basins[g];
    assert.equal(els['card-' + g].getAttribute('aria-pressed'), 'true');
    for (const o of GIDS) if (o !== g) assert.equal(els['card-' + o].getAttribute('aria-pressed'), 'false');
    assert.ok(els.evSource.textContent.includes('GAUGE = "' + g + '"'));
    assert.ok(els.evSource.textContent.includes('NAME = "' + b.name + '"'));
    assert.ok(els.evReadout.textContent.includes(s.n + ' events') && els.evReadout.textContent.includes('median RC ' + s.medianRC.toFixed(3)));
    assert.ok(els.evReadout.textContent.includes('CAMELS runoff_ratio ' + b.runoff_ratio.toFixed(3)));
    assert.equal(els.evTableBody.innerHTML.split('<tr>').length - 1, 5);
    assert.equal(els.evSensBody.innerHTML.split('<tr>').length - 1, 3);
    /* the antecedent wording is the one the numbers dictate */
    const diff = s.wetMedian - s.dryMedian;
    const word = Math.abs(diff) < 0.02 ? 'about the same' : (diff > 0 ? 'higher' : 'lower');
    assert.ok(els.evNarr.textContent.includes('have a ' + word + ' median'), els.evNarr.textContent);
    assert.ok(els.evNarr.textContent.includes('median RC of ' + s.wetMedian.toFixed(3)) && els.evNarr.textContent.includes('rank correlation between antecedent rain and RC is ' + s.rho.toFixed(2)));
    const higher = GIDS.filter((q) => { const t = core.eventStats(BLOB.basins[q]); return t.wetMedian > t.dryMedian; }).length;
    assert.ok(els.evNarr.textContent.includes('in ' + higher + ' of 3'));
    /* the daily-rate comparison states only what the numbers show */
    const below = s.maxRate < s.ksatMmH;
    assert.ok(els.evKsat.textContent.includes('The 24-hour mean is ' + (below ? 'below' : 'above') + ' that conductivity'));
    assert.ok(els.evKsat.textContent.includes(s.maxRate.toFixed(2) + ' mm/h') && els.evKsat.textContent.includes(s.ksatMmH.toFixed(2) + ' mm/h'));
    assert.ok(/cannot tell you whether infiltration excess happened/.test(els.evKsat.textContent));
  }
});

test('the antecedent-wetness pattern is computed, not typed: static prose names none, and the numbers agree in all three basins', () => {
  const stat = T.slice(T.indexOf('id="sec-real"'), T.indexOf('id="sec-quiz"')).replace(/<[^>]+>/g, ' ');
  assert.ok(!/wetter[^.]{0,80}(higher|larger|greater)/i.test(stat), 'no pattern asserted in static markup');
  assert.ok(!/consistent with/i.test(T), 'no "consistent with" wording without a computed check');
  for (const g of GIDS) {
    const s = core.eventStats(BLOB.basins[g]);
    assert.equal(s.wetMedian > s.dryMedian, s.rho > 0, g + ': direction of the split and of the rank correlation agree');
  }
});

test('the omitted basin and its reason come from the bundled attributes', () => {
  const { els } = run(T);
  const fs = BLOB.omitted['01013500'].frac_snow;
  assert.ok(els.omitNote.textContent.includes('01013500') && els.omitNote.textContent.includes(fs.toFixed(3)));
  for (const g of GIDS) { assert.ok(els.omitNote.textContent.includes(BLOB.basins[g].frac_snow.toFixed(3))); assert.ok(fs > BLOB.basins[g].frac_snow); }
  assert.ok(els.omitNote.textContent.includes('the largest of the four'));
  for (const g of GIDS) assert.ok(els['facts-' + g].textContent.includes('frac_snow ' + BLOB.basins[g].frac_snow.toFixed(3)));
});

test('CORE invariants: mass balance, ponding time, no IE at or below Ks, saturation only after the store is full', () => {
  for (const [i, T0, D] of [[25, 2, 60], [25, 2, 40], [60, 6, 15], [12, 0.5, 120], [5, 6, 10], [10, 3, 50], [30, 1, 120]]) {
    const r = core.gaRun(i, T0, D);
    assert.ok(Math.abs(r.P - (r.F + r.RIE + r.RSE)) < 1e-9, `mass ${i},${T0},${D}`);
    assert.ok(r.F <= D + 1e-12 && r.RIE >= 0 && r.RSE >= 0);
    if (i <= core.KS) assert.equal(r.RIE, 0);
    if (r.RSE > 0) assert.ok(r.tD !== null && r.tD < T0 && r.F === D);
    if (i > core.KS) assert.ok(Math.abs(r.tp - core.KS * core.M / (i * (i - core.KS))) < 1e-12);
  }
  const s = core.gaSeries(25, 3, 45, 150);
  for (let k = 0; k < s.t.length; k++) assert.ok(Math.abs(s.P[k] - s.F[k] - s.RIE[k] - s.RSE[k]) < 1e-9);
  for (let k = 1; k < s.t.length; k++) assert.ok(s.cap[k] >= core.KS - 1e-12);
  let prev = -1;
  for (let P = 0; P <= 100; P += 1) { const f = core.hillRun(P, false).satFrac; assert.ok(f >= prev); prev = f; }
  const e = core.eventStats(BLOB.basins['02472000']);
  assert.ok(e.events.every((v) => v.end - v.d <= 9 && v.P >= 10 && v.qf >= -1e-9));
});

test('the checkpoint has no answer, explanation or mark in the DOM before the first attempt, and the computed answers are accepted', () => {
  const { els, ctx } = run(T);
  const api = Object.values(ctx.HydroQuiz.instances)[0];
  const root = els['rg-quiz'];
  assert.ok(root && root.children.length, 'quiz rendered');
  let text = '';
  (function walk(n) {
    text += ' ' + (n.textContent || '');
    for (const k of Object.keys(n.attrs || {})) assert.ok(!/answer|correct|solution/i.test(k) && !/answer|correct|solution/i.test(String(n.attrs[k])), `${k}=${n.attrs[k]}`);
    if (n.checked) assert.fail('a radio is pre-checked');
    (n.children || []).forEach(walk);
  })(root);
  const items = api.describe();
  assert.equal(items.length, 7);
  assert.ok(items.filter((i) => i.type === 'choice').length >= 3 && items.filter((i) => i.type === 'numeric').length >= 1);
  for (const it of items) assert.ok(it.explain && !text.includes(it.explain), `explanation of ${it.id} is not in the DOM`);
  for (const it of items) { api.answer(it.id, it.expected); api.check(it.id); }
  assert.equal(api.state().passed, true);
});

test('the page keeps no timers of its own (nothing animates by itself)', () => {
  const { counters } = run(T);
  assert.equal(counters.setInterval, 0);
});
