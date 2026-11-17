'use strict';
/* evapotranspiration-budyko: the page works with no bridge (code panes follow the controls, readouts
   update), every control is keyboard operable, and the pure CORE block keeps its invariants. */
const test = require('node:test');
const assert = require('node:assert/strict');
const H = require('./helpers');
const { run } = require('./fakedom');

const MOD = 'evapotranspiration-budyko';
const T = H.moduleText(MOD);
const BLOB = H.blob(T, 'et-budyko');
const key = (k) => ({ key: k, preventDefault() {} });
const core = H.load([], H.coreBlock(T, 'CORE') + '\n' + H.coreBlock(T, 'CORE2'));

test('standalone: no bridge, the page populates itself and both code panes are filled', () => {
  const { els, ctx } = run(T);
  assert.equal(ctx.window.aihydro, undefined);
  assert.match(els.petSource.textContent, /^GAUGE  = "09484000"/m);
  assert.match(els.petSource.textContent, /^ALPHA  = 1\.26 /m);
  assert.ok(els.budykoSource.textContent.includes('OMEGA_SLIDER = 2.0'));
  assert.match(els.nUsed.textContent, /^670$/);
  assert.match(els.countsReadout.innerHTML, /<b>0<\/b> above E\/P = 1, <b>3<\/b> above the energy limit/);
  assert.match(els.hsReadout.innerHTML, /Sabino Creek/);
  assert.ok(els.reproBody.innerHTML.split('<tr>').length === 5, 'four basin rows');
  assert.ok(els.ptSteps.innerHTML.includes('PET<sub>PT</sub>'));
  assert.ok(els.ptsRest.getAttribute('d').length > 5000 && els.ptsSnow.getAttribute('d').length > 500, 'the 670 points are drawn');
  assert.ok(els.fuPath.getAttribute('d').startsWith('M'));
});

test('alpha slider: role=slider, arrow keys change aria-valuenow, the readout and the Python source with no bridge', () => {
  const { els } = run(T);
  const s = els.alphaSlider;
  assert.equal(s.getAttribute('role'), 'slider');
  assert.equal(s.getAttribute('aria-valuemin'), '1');
  assert.equal(s.getAttribute('aria-valuemax'), '1.5');
  assert.equal(s.getAttribute('aria-valuenow'), '1.26');
  const readout0 = els.petReadout.innerHTML;
  s.dispatch('keydown', key('ArrowUp'));
  assert.equal(s.getAttribute('aria-valuenow'), '1.27');
  assert.equal(els.alphaVal.textContent, '1.27');
  assert.match(els.petSource.textContent, /^ALPHA  = 1\.27 /m);
  assert.notEqual(els.petReadout.innerHTML, readout0);
  assert.match(els.petReadout.innerHTML, /α 1\.27/);
  s.dispatch('keydown', key('End'));
  assert.equal(s.getAttribute('aria-valuenow'), '1.5');
  s.dispatch('keydown', key('Home'));
  assert.equal(s.getAttribute('aria-valuenow'), '1');
  s.dispatch('keydown', key('PageUp'));
  assert.equal(s.getAttribute('aria-valuenow'), '1.1');
  assert.match(els.alphaSlider.getAttribute('aria-valuetext'), /alpha 1\.10/);
});

test('alpha changes PT PET in proportion: the readout means follow alpha', () => {
  const { els } = run(T);
  const mean = (html, label) => parseFloat(new RegExp(label + ' <b>([0-9.]+)</b>').exec(html)[1]);
  els.alphaSlider.dispatch('keydown', key('Home'));                  /* alpha = 1 */
  const a1 = mean(els.petReadout.innerHTML, 'Priestley–Taylor \\(α 1\\.00\\)');
  els.alphaSlider.dispatch('keydown', key('End'));                   /* alpha = 1.5 */
  const a15 = mean(els.petReadout.innerHTML, 'Priestley–Taylor \\(α 1\\.50\\)');
  assert.ok(Math.abs(a15 / a1 - 1.5) < 2e-3, `${a15} / ${a1}`);
});

test('basin select rewrites both the visible source and the readouts', () => {
  const { els } = run(T);
  els.gaugeSelect.value = '14305500'; els.gaugeSelect.dispatch('change');
  assert.match(els.petSource.textContent, /^GAUGE  = "14305500"/m);
  assert.match(els.petSource.textContent, /Siletz River at Siletz, OR/);
  assert.match(els.hsReadout.innerHTML, /Siletz River/);
  assert.match(els.petReadout.innerHTML, /Siletz River/);
});

test('day slider is a keyboard slider and moves the table, the summary and the marker', () => {
  const { els } = run(T);
  const s = els.daySlider;
  assert.equal(s.getAttribute('role'), 'slider');
  assert.equal(s.getAttribute('aria-valuemax'), '365');
  const before = els.ptSummary.textContent;
  s.dispatch('keydown', key('Home'));
  assert.equal(s.getAttribute('aria-valuenow'), '1');
  assert.match(els.ptSummary.textContent, /1996-10-01 \(day 1\)/);
  assert.notEqual(els.ptSummary.textContent, before);
  s.dispatch('keydown', key('End'));
  assert.match(els.ptSummary.textContent, /1997-09-30 \(day 365\)/);
  assert.match(els.ptSteps.innerHTML, /1997-09-30/);
});

test('omega slider: arrow keys change aria-valuenow, the Fu curve and the RMSE; Fit reaches the least-squares value', () => {
  const { els } = run(T);
  const s = els.omegaSlider;
  assert.equal(s.getAttribute('role'), 'slider');
  assert.equal(s.getAttribute('aria-valuenow'), '2');
  const d0 = els.fuPath.getAttribute('d'), r0 = els.fitReadout.innerHTML;
  s.dispatch('keydown', key('ArrowUp'));
  assert.equal(s.getAttribute('aria-valuenow'), '2.01');
  assert.notEqual(els.fuPath.getAttribute('d'), d0);
  assert.notEqual(els.fitReadout.innerHTML, r0);
  assert.match(els.budykoSource.textContent, /^OMEGA_SLIDER = 2\.01 /m);
  els.fitBtn.click();
  assert.equal(s.getAttribute('aria-valuenow'), '2.383');
  assert.match(els.fitReadout.innerHTML, /least-squares fit: ω = <b>2\.383<\/b>/);
  assert.equal(els.omegaVal.textContent, '2.383');
});

test('course-basin buttons: pressing one selects it, sets aria-pressed and fills the readout', () => {
  const { els } = run(T);
  const ids = ['01013500', '02472000', '09484000', '14305500'];
  ids.forEach((g) => assert.equal(els['chip-' + g].tagName, 'BUTTON'));
  assert.equal(els['chip-02472000'].getAttribute('aria-pressed'), 'false');
  els['chip-02472000'].click();
  assert.equal(els['chip-02472000'].getAttribute('aria-pressed'), 'true');
  assert.equal(els['chip-01013500'].getAttribute('aria-pressed'), 'false');
  assert.match(els.basinReadout.innerHTML, /Leaf River near Collins, MS/);
  assert.match(els.basinReadout.innerHTML, /E\/P = 1 − Q\/P = <b>0\.681<\/b>/);
  els['chip-14305500'].click();
  assert.equal(els['chip-02472000'].getAttribute('aria-pressed'), 'false');
  assert.match(els.basinReadout.innerHTML, /Siletz River at Siletz, OR/);
});

test('snow toggle: aria-pressed flips and the snow-influenced markers change shape (filled circle <-> hollow diamond)', () => {
  const { els } = run(T);
  assert.notEqual(els.snowToggle.getAttribute('aria-pressed'), 'true');
  const d0 = els.ptsSnow.getAttribute('d');
  assert.equal(els.ptsSnow.getAttribute('data-marker'), 'circle-filled');
  assert.ok(d0.includes('a') && !d0.includes('L') && !d0.includes('Z'), 'circles are arcs');
  assert.equal(els.ptsSnow.getAttribute('fill') !== 'none', true);
  els.snowToggle.click();
  assert.equal(els.snowToggle.getAttribute('aria-pressed'), 'true');
  assert.equal(els.ptsSnow.getAttribute('data-marker'), 'diamond-hollow');
  const d1 = els.ptsSnow.getAttribute('d');
  assert.ok(d1.includes('L') && d1.includes('Z') && !d1.includes('a'), 'diamonds are straight-edged polygons');
  assert.equal(els.ptsSnow.getAttribute('fill'), 'none');
  assert.notEqual(els.ptsSnow.getAttribute('stroke'), 'none');
  assert.equal(els.ptsRest.getAttribute('d').includes('a'), true, 'other basins stay circles');
  els.snowToggle.click();
  assert.equal(els.snowToggle.getAttribute('aria-pressed'), 'false');
  assert.equal(els.ptsSnow.getAttribute('d'), d0);
});

test('CORE: PET is non-negative and finite for every basin and alpha; Ra is physical', () => {
  for (const g of Object.keys(BLOB.basins)) {
    const b = core.decodeBasin(BLOB.basins[g], BLOB.wy.start);
    assert.equal(b.n, 365);
    for (const a of [1.0, 1.26, 1.5]) for (const v of core.ptSeries(b, a)) assert.ok(v >= 0 && isFinite(v));
    for (const v of core.hargreavesSeries(b)) assert.ok(v >= 0 && isFinite(v));
    for (const v of b.ra) assert.ok(v > 0 && v < 45);
  }
});

test('CORE: dates run 1996-10-01 .. 1997-09-30 with day-of-year across the new year', () => {
  const b = core.decodeBasin(BLOB.basins['09484000'], BLOB.wy.start);
  assert.equal(b.dates[0], '1996-10-01'); assert.equal(b.dates[364], '1997-09-30');
  assert.equal(b.doy[0], 275);                      /* 1996 is a leap year */
  assert.equal(b.doy[92], 1);                       /* 1997-01-01 */
  assert.equal(b.doy[364], 273);
});

test('CORE: Fu curve stays within 0..min(1, aridity), approaches the limits and the fit is interior to the grid', () => {
  for (const w of [1.1, 1.5, 2.383, 4, 6]) for (const p of [0.1, 0.5, 1, 2.5, 5]) {
    const e = core.fu(p, w);
    assert.ok(e >= 0 && e <= Math.min(1, p) + 1e-12, `w=${w} phi=${p}`);
  }
  assert.ok(Math.min(1, 1) - core.fu(1, 200) < 5e-3);
  const s = core.budykoSample(BLOB.all);
  assert.equal(s.phi.length, 670);
  assert.equal(JSON.stringify(s.skipped), '["03281100"]');
  const r = core.fitOmega(s.phi, s.ep);
  assert.ok(r.omega > 1.1 && r.omega < 6.0);
  assert.ok(core.rmseAt(s.phi, s.ep, r.omega) <= core.rmseAt(s.phi, s.ep, r.omega + 0.5));
  assert.ok(core.rmseAt(s.phi, s.ep, r.omega) <= core.rmseAt(s.phi, s.ep, r.omega - 0.5));
});

test('CORE: the Python cell sources hold the same data the page decodes (round trip)', () => {
  const g = '02472000', b = core.decodeBasin(BLOB.basins[g], BLOB.wy.start);
  const src = core.buildPetSource(g, BLOB.basins[g], BLOB.course[g].pet_mean, 1.3, BLOB.wy.start);
  assert.match(src, /^ALPHA  = 1\.3 /m);
  assert.match(src, /^LAT    = 32\.13 /m);
  assert.ok(src.includes(String(BLOB.basins[g].tmax_x100[0])));
  assert.ok(!/default_rng|np\.random/.test(src), 'no synthetic branch');
  const hs = core.mean(core.hargreavesSeries(b));
  assert.ok(hs > 0);
});

test('checkpoint: answers are computed from the page and a correct choice is accepted by the shared engine', () => {
  const { ctx } = run(T);
  const q = ctx.window.__etQuiz;
  assert.ok(q.expected('q2') > 3 && q.expected('q2') < 4);
  assert.equal(q.expected('q5'), 2.383);
  q.answer('q5', '2.383'); q.check('q5');
  q.answer('q2', String(q.expected('q2').toFixed(2))); q.check('q2');
  q.answer('q1', q.expected('q1')); q.check('q1');
  const st = q.state();
  assert.equal(st.items.filter((i) => i.correct).length, 3);
});
