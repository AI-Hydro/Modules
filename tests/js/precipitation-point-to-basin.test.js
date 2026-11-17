'use strict';
/* precipitation-point-to-basin: CORE invariants, and the page works with no bridge: toggles, sliders, basin cards and
   the code panes follow the controls; with a bridge the new source is pushed only after a learner's change. */
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('vm');
const H = require('./helpers');
const { run } = require('./fakedom');

const MOD = 'precipitation-point-to-basin';
const HTML = H.moduleText(MOD);
const DATA = H.blob(HTML, 'precip-data');
const core = () => H.load([], H.coreBlock(HTML) + '\n' + H.coreBlock(HTML, 'CORE2'), {});
const key = (el, k) => el.dispatch('keydown', { key: k, preventDefault() {} });

test('CORE: 1942 basin cells, Thiessen weights sum to 1, IDW equals the reading at a gauge cell, arithmetic is the gauge mean', () => {
  const c = core();
  const all = vm.runInContext('GAUGE_SITES.map(function (s) { return s.id; })', c);
  assert.equal(c.GRID.cells.length, 1942);
  for (const p of [1, 1.5, 2, 3.5, 4]) {
    const e = c.arealEstimates(all, p);
    assert.ok(Math.abs(e.weights.reduce((a, b) => a + b, 0) - 1) < 1e-12);
    assert.ok(Math.abs(e.arithmetic - e.readings.reduce((a, b) => a + b, 0) / e.readings.length) < 1e-12);
    vm.runInContext('GAUGE_SITES', c).forEach((s, k) => assert.equal(e.surface[s.iy * 60 + s.ix], e.readings[k]));
  }
  const one = c.arealEstimates(['G2'], 2);
  assert.equal(one.thiessen, one.readings[0]);            /* a single gauge owns the whole basin */
  assert.ok(Math.abs(one.idw - one.readings[0]) < 1e-12);
});

test('CORE: as the IDW power grows the IDW mean moves towards the Thiessen mean (the limit stated in the text)', () => {
  const c = core();
  const all = vm.runInContext('GAUGE_SITES.map(function (s) { return s.id; })', c);
  const th = c.arealEstimates(all, 2).thiessen;
  const gap = (p) => Math.abs(c.arealEstimates(all, p).idw - th);
  assert.ok(gap(40) < gap(4) && gap(4) < gap(1));
});

test('CORE: the high-precipitation count is an exact integer test and the snow fraction is monotone in the threshold', () => {
  const c = core();
  for (const g of Object.keys(DATA.basins)) {
    const b = DATA.basins[g], h = b.prcp_hundredths_mm, n = h.length, tot = h.reduce((a, v) => a + v, 0);
    assert.equal(c.highPrecDays(h), h.filter((v) => v * n >= 5 * tot).length);
    let prev = -1;
    for (let t = -2; t <= 3; t += 0.5) {
      const s = c.snowFraction(h, b.tmean_halfdeg_bin_on_wet_days, t);
      assert.ok(s >= prev && s >= 0 && s <= 1, `${g} ${t}`); prev = s;
    }
  }
});

test('page: toggling a gauge rewrites the areal-precip source and the readout with no bridge; the last gauge stays on', () => {
  const { els, ctx } = run(HTML);
  assert.equal(ctx.window.aihydro, undefined);
  const src0 = els.arealSource.textContent, read0 = els.arealReadout.textContent;
  assert.match(src0, /ACTIVE = \['G1', 'G2', 'G3', 'G4', 'G5', 'G6'\]/);
  assert.match(read0, /Gauges on: G1, G2, G3, G4, G5, G6 \(6 of 6\)/);
  els['gb-G4'].click();
  assert.match(els.arealSource.textContent, /ACTIVE = \['G1', 'G2', 'G3', 'G5', 'G6'\]/);
  assert.match(els.arealReadout.textContent, /Gauges on: G1, G2, G3, G5, G6 \(5 of 6\)/);
  assert.notEqual(els.arealReadout.textContent, read0);
  assert.equal(els['gb-G4'].getAttribute('aria-pressed'), 'false');
  assert.match(els.arealRows.innerHTML, /G5/); assert.doesNotMatch(els.arealRows.innerHTML, /<th scope="row">G4</);
  els['gb-G4'].click();                                                  /* back on, in G1..G6 order */
  assert.match(els.arealSource.textContent, /ACTIVE = \['G1', 'G2', 'G3', 'G4', 'G5', 'G6'\]/);
  for (const g of ['G1', 'G2', 'G3', 'G4', 'G5']) els['gb-' + g].click();
  assert.match(els.arealSource.textContent, /ACTIVE = \['G6'\]/);
  els['gb-G6'].click();                                                  /* ignored: at least one gauge must stay on */
  assert.notEqual(els['gb-G6'].getAttribute('aria-pressed'), 'false');     /* the HTML starts it pressed; the page never turned it off */
  assert.match(els.arealReadout.textContent, /\(1 of 6\)/);
});

test('page: the map radio group redraws and keeps the table; the IDW slider is a keyboard slider that changes the readout and the code', () => {
  const { els } = run(HTML);
  els.mapIdw.checked = true; els.mapIdw.dispatch('change');
  assert.match(els.fieldCanvas.getAttribute('aria-label'), /mode idw/);
  const t = els['t-idwp'];
  assert.equal(t.getAttribute('role'), 'slider');
  assert.equal(t.getAttribute('aria-valuenow'), '2');
  key(t, 'ArrowUp');
  assert.equal(t.getAttribute('aria-valuenow'), '2.5');
  assert.equal(t.getAttribute('aria-valuetext'), '2.5');
  assert.equal(els.idwSlider.value, 2.5);
  assert.match(els.arealReadout.textContent, /IDW p = 2\.5/);
  assert.match(els.arealSource.textContent, /IDW_POWER = 2\.5/);
  key(t, 'End'); assert.equal(t.getAttribute('aria-valuenow'), '4'); assert.match(els.arealSource.textContent, /IDW_POWER = 4\.0/);
  key(t, 'Home'); assert.equal(t.getAttribute('aria-valuenow'), '1');
  els.idwSlider.value = '3'; els.idwSlider.dispatch('input');           /* the range input drives the same state */
  assert.equal(t.getAttribute('aria-valuenow'), '3');
  assert.match(els.arealReadout.textContent, /IDW p = 3/);
});

test('page: the snow-threshold slider (role=slider, arrows, Home/End) updates the readout, the table and the precip-climate source', () => {
  const { els } = run(HTML);
  const t = els['t-snowT'];
  assert.equal(t.getAttribute('role'), 'slider');
  assert.equal(t.getAttribute('aria-valuemin'), '-2'); assert.equal(t.getAttribute('aria-valuemax'), '3');
  assert.equal(t.getAttribute('aria-valuenow'), '0');
  assert.match(els.climSource.textContent, /SNOW_T_C = 0\.0/);
  key(t, 'ArrowUp');
  assert.equal(t.getAttribute('aria-valuenow'), '0.5');
  assert.equal(els.snowVal.textContent, '0.5 °C');
  assert.match(els.snowReadout.textContent, /threshold 0\.5 °C/);
  assert.match(els.climSource.textContent, /SNOW_T_C = 0\.5/);
  key(t, 'Home'); assert.equal(t.getAttribute('aria-valuenow'), '-2'); assert.match(els.climSource.textContent, /SNOW_T_C = -2\.0/);
  key(t, 'End'); assert.equal(t.getAttribute('aria-valuenow'), '3');
  assert.match(els.snowRows.innerHTML, /aria-current="true"/);
});

test('page: a basin card rewrites the precip-climate source, the tables and every section that follows the choice', () => {
  const { els } = run(HTML);
  assert.match(els.climSource.textContent, /GAUGE = "02472000"/);
  els['bc-09484000'].click();
  assert.match(els.climSource.textContent, /GAUGE = "09484000"/);
  assert.match(els.climSource.textContent, /Sabino Creek near Tucson, AZ/);
  assert.equal(els['bc-09484000'].getAttribute('aria-pressed'), 'true'); assert.equal(els['bc-02472000'].getAttribute('aria-pressed'), 'false');
  assert.match(els.statsRows.innerHTML, /aria-current="true"><th scope="row">▶ Sabino Creek/);
  assert.equal(els.seasonBasin.textContent, 'Sabino Creek near Tucson, AZ');
  assert.equal(els.snowBasin.textContent, 'Sabino Creek near Tucson, AZ');
  assert.match(els.exceedSvg.getAttribute('aria-label'), /Sabino Creek/);
  assert.match(els.monthSvg.getAttribute('aria-label'), /Sabino Creek/);
  assert.match(els.snowSvg.getAttribute('aria-label'), /Sabino Creek/);
});

test('page: with a bridge the new source is pushed on a learner change and not at load', () => {
  const calls = [];
  const { els } = run(HTML, { globals: { aihydro: { rewriteCell(id, fn, flag) { calls.push([id, fn(), flag]); } } } });
  assert.equal(calls.length, 0, 'nothing is rewritten while the page loads');
  els['gb-G1'].click();
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], 'areal-precip'); assert.match(calls[0][1], /ACTIVE = \['G2'/); assert.equal(calls[0][2], false);
  els['bc-14305500'].click();
  assert.equal(calls[calls.length - 1][0], 'precip-climate'); assert.match(calls[calls.length - 1][1], /GAUGE = "14305500"/);
});

test('page: charts, tables and notes are written with no bridge (no empty placeholders left)', () => {
  const { els } = run(HTML);
  for (const id of ['arealReadout', 'arealNote', 'gaugeRatio', 'stormNote', 'seasonNote', 'snowReadout', 'reproNote', 'bcn-01013500', 'bcf-14305500']) {
    assert.ok(els[id].textContent && els[id].textContent !== '—', id);
  }
  for (const id of ['arealRows', 'methodRows', 'statsRows', 'seasonRows', 'snowRows', 'pmeanRows', 'highRows']) assert.ok(els[id].innerHTML.length > 50, id);
  assert.equal((els.statsRows.innerHTML.match(/<tr/g) || []).length, 4);
  assert.match(els.arealSource.textContent, /^import numpy as np/);
  assert.match(els.climSource.textContent, /^import numpy as np/);
});

test('checkpoint: wrong-answer feedback never names the right option; choices are computed or fixed; numerics are functions', () => {
  const html = HTML.replace("<script>\n(function () {\n  'use strict';", "<script>(function(){var m = HydroQuiz.mount; HydroQuiz.mount = function (r, s) { window.__spec = s; return m(r, s); };})();</script>\n<script>\n(function () {\n  'use strict';");
  const { ctx } = run(html);
  const spec = ctx.window.__spec;
  assert.ok(spec && spec.items.length === 7);
  for (const it of spec.items) {
    if (it.type === 'numeric') { assert.equal(typeof it.answer, 'function', it.id); continue; }
    const right = typeof it.correct === 'function' ? it.correct() : it.correct;
    const opts = it.options.map((o) => o.toLowerCase());
    it.options.forEach((_, i) => {
      if (i === right) return;
      const fb = String(it.feedback[i] || '').toLowerCase();
      assert.ok(fb.length > 10, `${it.id} option ${i} needs feedback`);
      assert.ok(!fb.includes(opts[right]), `${it.id}: feedback for option ${i} names the right answer`);
    });
    assert.equal(it.feedback[right] === null || it.feedback[right] === undefined || typeof it.feedback[right] === 'string', true);
  }
});

test('a11y structure: radiogroup is a native fieldset, toggles and cards carry aria-pressed, charts have names, reduced motion adds no animation', () => {
  assert.match(HTML, /<fieldset class="radio-set">\s*<legend>Map shows<\/legend>/);
  for (const g of ['G1', 'G2', 'G3', 'G4', 'G5', 'G6']) assert.match(HTML, new RegExp(`id="gb-${g}" class="toggle-btn on" type="button" aria-pressed="true"`));
  for (const g of Object.keys(DATA.basins)) assert.match(HTML, new RegExp(`id="bc-${g}" type="button" aria-pressed="(true|false)"`));
  for (const id of ['fieldCanvas', 'exceedSvg', 'monthSvg', 'snowSvg']) assert.match(HTML, new RegExp(`id="${id}"[^>]*(role="img")[^>]*aria-label="[^"]{20,}`));
  assert.match(HTML, /<caption>/);
  assert.match(HTML, /scope="col"/);
  assert.match(HTML, /prefers-reduced-motion: reduce/);
  assert.doesNotMatch(HTML, /requestAnimationFrame|setInterval\(/);       /* nothing animates on its own */
});
