'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const H = require('./helpers');

/* ── watershed-runoff ───────────────────────────────────────── */
const ws = H.moduleText('watershed-runoff');
const w = H.load(['d8.js'], H.coreBlock(ws));

test('watershed DEM: at least 95% of cells reach the outlet (claim in the lesson)', () => {
  assert.ok(w.reachFraction() >= 0.95, `reach fraction ${w.reachFraction()}`);
});

test('watershed DEM: outlet is the lowest cell on the grid edge', () => {
  const N = w.N, dem = w.DEM;
  let best = Infinity;
  for (let r = 0; r < N; r++) for (let c = 0; c < N; c++)
    if (r === 0 || c === 0 || r === N - 1 || c === N - 1) best = Math.min(best, dem[r][c]);
  assert.equal(dem[w.ROUTE.outlet.r][w.ROUTE.outlet.c], best);
});

test('watershed DEM has interior pits, and filling removes them (the old bug)', () => {
  const N = w.N, dem = w.DEM, dirs = w.D8_DIRS;
  let pits = 0;
  for (let r = 1; r < N - 1; r++) for (let c = 1; c < N - 1; c++)
    if (!dirs.some(([a, b]) => dem[r + a][c + b] < dem[r][c])) pits++;
  assert.ok(pits > 0, 'the DEM must contain pits or this test proves nothing');
  const R = w.ROUTE, o = R.outlet.r * N + R.outlet.c;
  for (let i = 0; i < N * N; i++) if (i !== o) assert.ok(R.rec[i] >= 0, 'every non-outlet cell has a receiver');
});

test('every flow step goes strictly downhill on the filled surface; paths are guarded', () => {
  const R = w.ROUTE;
  for (let i = 0; i < R.rec.length; i++) if (R.rec[i] >= 0) assert.ok(R.filled[i] > R.filled[R.rec[i]]);
  const p = w.d8Path(R.rec, 0, 3);
  assert.ok(p.length <= 4, 'step guard must bound the walk');
});

test('D8 uses drop / distance, not raw drop', () => {
  /* centre 10; E neighbour drops 3 at distance 1 (=3.0); SE neighbour drops 4 at distance √2 (=2.83) */
  const dem = [[20, 20, 20, 20], [20, 10, 7, 20], [20, 20, 6, 20], [0, 0, 0, 0]];
  const R = w.d8Route(dem, 1, { outlet: { r: 3, c: 0 } });
  assert.equal(R.rec[1 * 4 + 1], 1 * 4 + 2, 'raw drop would pick SE (4); drop/distance picks E');
});

test('stream network is derived from flow accumulation', () => {
  const R = w.ROUTE;
  const streams = R.acc.filter((a) => a >= w.STREAM_MIN_CELLS).length;
  assert.ok(streams > 0 && streams < R.acc.length / 2);
});

/* ── dem-to-twi ─────────────────────────────────────────────── */
const dm = H.moduleText('dem-to-twi');
const d = H.load(['d8.js'], H.coreBlock(dm));

/* independent brute-force steepest drop/distance neighbour */
function steepest(dem, r, c, cell) {
  let best = 0, to = null;
  for (let dr = -1; dr <= 1; dr++) for (let dc = -1; dc <= 1; dc++) {
    if (!dr && !dc) continue;
    const nr = r + dr, nc = c + dc;
    if (nr < 0 || nc < 0 || nr > 4 || nc > 4) continue;
    const g = (dem[r][c] - dem[nr][nc]) / (cell * (dr && dc ? Math.SQRT2 : 1));
    if (g > best) { best = g; to = [nr, nc]; }
  }
  return to;
}

test('dem-to-twi: FLOW_TO is computed from the DEM, equal to an independent brute force', () => {
  for (let r = 0; r < 5; r++) for (let c = 0; c < 5; c++) {
    if (r === 4 && c === 2) { assert.equal(d.FLOW_TO[r][c], null); continue; }
    assert.deepEqual(Array.from(d.FLOW_TO[r][c]), steepest(d.DEM_EL, r, c, 10), `cell ${r},${c}`);
  }
});

test('dem-to-twi: the four cells the old hand-typed table got wrong now follow drop/distance', () => {
  const old = { '0,1': [1, 2], '0,2': [1, 3], '0,4': [1, 3], '1,3': [2, 2] };
  for (const k of Object.keys(old)) {
    const [r, c] = k.split(',').map(Number);
    assert.notDeepEqual(Array.from(d.FLOW_TO[r][c]), old[k], `cell ${k}`);
  }
});

test('dem-to-twi: the source holds no hand-typed FLOW_TO literal', () => {
  assert.ok(!/FLOW_TO\s*=\s*\[\s*\[\s*\[/.test(dm));
});

test('dem-to-twi: TWI = ln(a / tan beta) with a = accumulation * cell, slope floor applied', () => {
  const R = d.ROUTE;
  for (let i = 0; i < 25; i++)
    assert.ok(Math.abs(R.twi[i] - Math.log(R.acc[i] * 10 / Math.max(R.tanBeta[i], 0.001))) < 1e-12);
  assert.ok(R.tanBeta.every((t) => t >= 0.001));
});
