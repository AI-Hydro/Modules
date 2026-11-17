'use strict';
/* Without the window.aihydro bridge every module must still be usable: code panes follow the
   controls, readouts update, and nothing depends on a host being there. (The fake DOM has no
   bridge: window.aihydro is undefined.) */
const test = require('node:test');
const assert = require('node:assert/strict');
const H = require('./helpers');
const { run } = require('./fakedom');

test('baseflow: dragging alpha rewrites the visible code and the BFI readout with no bridge', () => {
  const { els, ctx } = run(H.moduleText('baseflow-separation'));
  assert.equal(ctx.window.aihydro, undefined);
  const before = els.bfiEstDisplay.textContent;
  els.alphaSlider.value = '0.95';
  els.alphaSlider.dispatch('input');
  assert.match(els.lhSource.textContent, /^alpha = 0\.950/m);
  assert.notEqual(els.bfiEstDisplay.textContent, before);
  assert.equal(els.alphaDisplay.textContent, '0.950');
  assert.ok(els.pathBase.getAttribute('d').length > 1000, 'compare plot redrawn');
});

test('baseflow: the compare divider is a keyboard slider that moves the wipe', () => {
  const { els } = run(H.moduleText('baseflow-separation'));
  assert.equal(els.cmpHandle.getAttribute('role'), 'slider');
  els.cmpHandle.dispatch('keydown', { key: 'ArrowLeft', preventDefault() {} });
  assert.equal(els.cmpHandle.getAttribute('aria-valuenow'), '45');
  assert.equal(els.cmpDivider.style.left, '45.0%');
});

test('dem-to-twi: the point calculator rewrites its source and the compare divider works from the keyboard', () => {
  const { els } = run(H.moduleText('dem-to-twi'));
  els['p-area'].value = '300'; els['p-area'].dispatch('input');
  els['p-slope'].value = '5'; els['p-slope'].dispatch('input');
  assert.match(els.pyPointSource.textContent, /area_in  = 300 /);
  assert.match(els.pyPointSource.textContent, /slope_in = 5 /);
  assert.equal(els.liveTWI.textContent, (Math.log(300 / Math.tan(5 * Math.PI / 180))).toFixed(3));
  els.compHandle.dispatch('keydown', { key: 'End', preventDefault() {} });
  assert.equal(els.compHandle.getAttribute('aria-valuenow'), '98');
});

test('reading / real-streamflow / capstone: the gauge selectors regenerate the code panes', () => {
  const rd = run(H.moduleText('reading-a-hydrograph'));
  const rd0 = rd.els.pySource.textContent;
  rd.els.gaugeSelect.value = '02472000'; rd.els.gaugeSelect.dispatch('change');
  assert.notEqual(rd.els.pySource.textContent, rd0);
  assert.match(rd.els.pySource.textContent, /02472000/);

  const rs = run(H.moduleText('real-streamflow-data'));
  rs.els.gaugeSelect.value = '09484000'; rs.els.gaugeSelect.dispatch('change');
  assert.match(rs.els.cellSource.textContent, /09484000/);
  assert.match(rs.els.nwisSource.textContent, /09484000/);

  const cp = run(H.moduleText('capstone-basin-story'));
  cp.els.gaugeSelect.value = '14305500'; cp.els.gaugeSelect.dispatch('change');
  assert.match(cp.els.srcRecord.textContent, /14305500/);
  assert.match(cp.els.srcExport.textContent, /14305500/);
});

test('reading: tangle numbers are keyboard sliders wired to the same state as the range inputs', () => {
  const { els } = run(H.moduleText('reading-a-hydrograph'));
  const t = els['t-alpha'];
  assert.equal(t.getAttribute('role'), 'slider');
  assert.equal(t.getAttribute('aria-valuemin'), '0.9');
  t.dispatch('keydown', { key: 'ArrowUp', preventDefault() {} });
  assert.equal(els.alphaSlider.value, 0.93);
  assert.equal(t.getAttribute('aria-valuetext'), '0.930');
});

test('water cycle: with reduced motion the bathtub still re-steps when the slider moves', () => {
  const { els } = run(H.moduleText('water-cycle-in-motion'));        /* the fake reports prefers-reduced-motion: reduce */
  const s0 = els.bS.textContent;
  els.precipSlider.value = '10'; els.precipSlider.dispatch('input');
  assert.notEqual(els.bS.textContent, s0, 'storage changed after the slider moved');
  els.bathStep.dispatch('click');
  assert.match(els.bathMotionNote.textContent, /Reduced motion/);
});

test('capstone: reduced motion hides the auto-play control; the slider and dots still change the story', () => {
  const { els } = run(H.moduleText('capstone-basin-story'));
  assert.equal(els.tlPlayBtn.hidden, true);
  els.tlSlider.value = '3'; els.tlSlider.dispatch('input');
  assert.equal(els.tlStepLabel.textContent, '4 / 6');
});

test('watershed: without any host the terrain falls back to a plain 2-D relief map', () => {
  const t = H.moduleText('watershed-runoff');
  run(t);                                                   /* the fake window is embedded, so the fallback stays off here ... */
  assert.match(t, /HydroCmap\.relief\(fb, DEM/);            /* ... and it is wired for the standalone case */
  assert.match(t, /standalone = window\.parent === window/);
});
