'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const H = require('./helpers');
const { run } = require('./fakedom');

const ids = fs.readdirSync(`${H.ROOT}/modules`).filter((d) => fs.existsSync(`${H.ROOT}/modules/${d}/module.html`));

for (const id of ids) {
  test(`${id}: every inline script loads against a fake DOM without throwing`, () => {
    run(H.moduleText(id), { anyId: false });
  });
}

test('baseflow: page shows the computed BFI and the live source after load', () => {
  const t = H.moduleText('baseflow-separation');
  const { els } = run(t);
  const c = H.load(['lyne_hollick.js'], H.coreBlock(t));
  const s = c.makeSyntheticSeries();
  const want = c.baseflowIndex(s.Q, c.lyneHollick(s.Q, 0.925)).toFixed(3);
  assert.equal(els.bfiEstDisplay.textContent, want);
  assert.ok(els.pathBase.getAttribute('d').length > 1000);
});

test('capstone: the story is filled from computed values on load and when the gauge changes', () => {
  const t = H.moduleText('capstone-basin-story');
  const { els, getEl, ctx } = run(t);
  const c = H.load(['lyne_hollick.js', 'd8.js'], H.coreBlock(t));
  const G = H.blob(t, 'camels-5yr').gauges;
  const st = c.gaugeStats(G['01013500']);
  assert.equal(els['tl3-bfi'].textContent, st.bfi.toFixed(3));
  assert.equal(els['tl4-flood'].textContent, String(st.floodDays));
  assert.ok(els.srcSigs.textContent.length > 5000);
  const card = { dataset: { gaugeId: '09484000' } };
  ctx.window.selectGauge(card);
  assert.equal(els['tl3-bfi'].textContent, c.gaugeStats(G['09484000']).bfi.toFixed(3));
  assert.equal(els['tl0-name'].textContent, 'Sabino Creek near Tucson, AZ');
});

test('real-streamflow / reading: the Python cell source is generated at load', () => {
  const rs = run(H.moduleText('real-streamflow-data'));
  assert.ok(rs.els.cellSource.textContent.includes('REAL DATA'));
  assert.ok(rs.els.nwisSource.textContent.includes('NWIS'));
  const rd = run(H.moduleText('reading-a-hydrograph'));
  assert.ok(rd.els.pySource.textContent.includes('Lyne–Hollick'));
  assert.ok(rd.els.peakRatio.textContent.includes('13.2'));
});

test('dem-to-twi: calculator and class labels are populated', () => {
  const { els } = run(H.moduleText('dem-to-twi'));
  assert.ok(Number(els.liveTWI.textContent) > 0);
  assert.ok(els.pyPointSource.textContent.includes('TAN_FLOOR'));
});
