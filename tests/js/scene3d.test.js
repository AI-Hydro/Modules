'use strict';
/* watershed-runoff section 5 (Fish River): without the 3-D bridge the poster stays and nothing throws; with a bridge
   the poster is replaced only after a frame; the D8 drop reaches the outlet; the keyboard path works.
   Runs the page's real inline scripts in the fake DOM (tests/js/fakedom.js). */
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('vm');
const H = require('./helpers');
const { run } = require('./fakedom');

const T = H.moduleText('watershed-runoff');
const settle = () => new Promise((r) => setImmediate(r));

/* A scene graph with just enough of three.js to record what the page builds. */
function fakeTHREE() {
  class Obj { constructor() { this.children = []; this.position = { set() {} }; }
    add(o) { this.children.push(o); } remove(o) { this.children = this.children.filter((c) => c !== o); }
    traverse(f) { f(this); this.children.forEach((c) => c.traverse && c.traverse(f)); } }
  class Geo { constructor() { this.attrs = {}; this.index = null; } setAttribute(n, a) { this.attrs[n] = a; } setIndex(i) { this.index = i; }
    computeVertexNormals() {} dispose() {} }
  class Attr { constructor(a, n) { this.array = a; this.itemSize = n; } }
  class Mat { constructor(o) { this.o = o; } dispose() {} }
  class Mesh extends Obj { constructor(g, m) { super(); this.geometry = g; this.material = m; } }
  return { Scene: Obj, Group: Obj, Mesh, Line: Mesh, LineSegments: Mesh, Points: Mesh, PointsMaterial: Mat, BufferGeometry: Geo, SphereGeometry: class extends Geo {},
    Float32BufferAttribute: Attr, MeshLambertMaterial: Mat, MeshBasicMaterial: Mat, LineBasicMaterial: Mat,
    AmbientLight: Obj, DirectionalLight: Obj, DoubleSide: 2 };
}
function fakeCtx(canvas, THREE, lost) {
  return { THREE, scene: new THREE.Scene(), camera: { position: { set() {} } }, controls: { target: { set() {} }, update() {} },
    renderer: { getContext: () => ({ isContextLost: () => !!lost }) }, canvas, invalidate() { this.invalidated = (this.invalidated || 0) + 1; } };
}
const fish = (ctx) => vm.runInContext('window.__fishScene', ctx);

test('no bridge: the poster is in the markup, stays visible, the status says static, and nothing throws', async () => {
  const { els, ctx, counters, getEl } = run(T);
  const poster = els.fishPoster || getEl('fishPoster');
  assert.ok(poster, 'poster element exists');
  assert.equal(poster.hidden, false);
  assert.notEqual(poster.style.display, 'none');
  assert.match(T, /id="fishStatus"[^>]*role="status">Static view:/, 'the visible message is in the markup');
  assert.equal(getEl('fishStatus').textContent, '', 'no script touched it');
  assert.ok(fish(ctx) && fish(ctx).fish, 'the page decoded its payload');
  assert.ok(counters.setInterval <= 1, 'at most one poll for the bridge');
  await settle();
  assert.equal(poster.hidden, false);
  assert.equal(getEl('fishStatus').textContent, '');
});

test('the bridge cannot start WebGL (scene3d resolves null): the poster stays and the message says why', async () => {
  const { els } = run(T, { globals: { aihydro: { scene3d: () => Promise.resolve(null) } } });
  await settle();
  assert.equal(els.fishPoster.hidden, false);
  assert.notEqual(els.fishPoster.style.display, 'none');
  assert.match(els.fishStatus.textContent, /3-D view unavailable/);
});

test('a bridge that throws or rejects for this scene leaves the poster and the page working', async () => {
  for (const fail of [() => { throw new Error('boom'); }, () => Promise.reject(new Error('boom'))]) {
    const { els, getEl, ctx } = run(T, { globals: { aihydro: { scene3d: (o) => (o.canvas.id === 'fishCanvas' ? fail() : Promise.resolve(null)) } } });
    await settle();
    assert.equal((els.fishPoster || getEl('fishPoster')).hidden, false);
    assert.ok(fish(ctx).fish.trace(fish(ctx).fish.highest).reachesOutlet, 'the page still routes');
  }
});

test('a bridge that draws: the poster is replaced after a frame, the scene is the payload, markers follow the drop', async () => {
  const THREE = fakeTHREE();
  let live = null, frames = 0, lost = false;
  const globals = { THREE, requestAnimationFrame: (f) => { frames++; f(); return 1; },
    aihydro: { scene3d(opts) { live = fakeCtx(opts.canvas, THREE, lost); opts.setup(live); return Promise.resolve(live); } } };
  const { els, ctx } = run(T, { globals });
  await settle();
  assert.ok(live, 'setup ran');
  assert.equal(els.fishPoster.hidden, true);
  assert.equal(els.fishPoster.style.display, 'none');
  assert.match(els.fishStatus.textContent, /Drag to orbit/);
  const f = fish(ctx).fish, P = f.P;
  const mesh = live.scene.children.find((c) => c.geometry && c.geometry.index);
  const pos = mesh.geometry.attrs.position.array, idx = mesh.geometry.index;
  assert.equal(pos.length, 3 * f.terrain.length, 'one vertex per terrain cell');
  assert.ok(idx.length > 0 && idx.length % 3 === 0 && Math.max(...idx) < f.terrain.length);
  assert.ok(Array.from(pos).every(Number.isFinite));
  const yExt = (P.zmax - P.zmin) * P.ve / 10000;
  const ys = []; for (let i = 1; i < pos.length; i += 3) ys.push(pos[i]);
  assert.ok(Math.abs((Math.max(...ys) - Math.min(...ys)) - yExt) < 1e-3, 'the printed exaggeration is the drawn one');
  const lines = live.scene.children.filter((c) => c.geometry && !c.geometry.index);
  assert.equal(lines.length, 2, 'the divide and the channels');
  assert.ok(lines.every((l) => Array.from(l.geometry.attrs.position.array).every(Number.isFinite)));
  /* drop at the highest cell: a path line and two balls are added to the scene */
  els.fishHighBtn.click();
  els.fishDropBtn.click();
  const grp = live.scene.children.find((c) => c.children && c.children.length >= 2 && c !== mesh);
  assert.ok(grp, 'markers group');
  const path = grp.children.find((c) => c.geometry && c.geometry.attrs.position && c.geometry.attrs.position.itemSize === 3 && c.geometry.attrs.position.array.length > 6);
  assert.equal(path.geometry.attrs.position.array.length, 3 * f.drop.cells);
  assert.ok(live.invalidated >= 1, 'the bridge was asked to redraw');
});

test('a lost WebGL context keeps the poster', async () => {
  const THREE = fakeTHREE();
  const globals = { THREE, requestAnimationFrame: (f) => { f(); return 1; },
    aihydro: { scene3d(opts) { const c = fakeCtx(opts.canvas, THREE, true); opts.setup(c); return Promise.resolve(c); } } };
  const { els } = run(T, { globals });
  await settle();
  assert.equal(els.fishPoster.hidden, false);
});

test('the D8 drop reaches the outlet from the highest cell, the corners of the basin and every 37th terrain cell', () => {
  const { ctx } = run(T);
  const f = fish(ctx).fish, C = f.C;
  const probes = [f.highest, f.terrain[0], f.terrain[f.terrain.length - 1]];
  for (let i = 0; i < f.terrain.length; i += 37) probes.push(f.terrain[i]);
  for (const i of probes) {
    const t = f.trace(i);
    assert.equal(t.reachesOutlet, true, 'cell ' + i);
    assert.equal(t.path[t.path.length - 1], f.outletIdx);
    assert.ok(t.path.every((j) => f.valid[j] === 1), 'the path stays on terrain');
    assert.ok(t.length_km >= 0 && Number.isFinite(t.length_km) && t.area_km2 > 0);
  }
  /* exhaustive: every terrain cell reaches the outlet */
  const rec = f.getRoute().rec;
  for (const i of f.terrain) {
    let j = i, guard = 0;
    while (rec[j] >= 0 && guard++ < f.N) j = rec[j];
    assert.equal(j, f.outletIdx, 'cell ' + i);
  }
  assert.equal(f.trace(f.outletIdx).cells, 1);
});

test('the polygon area read from the payload is within 1% of basin_ref (2258.5 km²)', () => {
  const { ctx } = run(T);
  const a = fish(ctx).fish.outlineAreaKm2();
  assert.ok(Math.abs(a / 2258.5 - 1) < 0.01, String(a));
});

test('keyboard: arrows move the cursor, Enter drops, the result is in the live region; a masked cell is refused in words', () => {
  const { els } = run(T);
  const map = els.fishMap;
  assert.equal(map.getAttribute('role') || 'application', 'application');
  assert.match(T, /id="fishMap"[^>]*tabindex="0"[^>]*role="application"/);
  for (const key of ['ArrowRight', 'ArrowDown', 'Enter']) map.dispatch('keydown', { key, shiftKey: false, preventDefault() {} });
  assert.match(els.fishMsg.textContent, /^Dropped at column \d+, row \d+, block-mean elevation [\d.]+ m\. The D8 path reaches the outlet after \d+ steps/);
  assert.match(els.fishStatLen.textContent, /^[\d.]+ km$/);
  assert.match(els.fishStatArea.textContent, /^[\d.]+ km²$/);
  assert.match(els.fishCursorMsg.textContent, /^Cursor: column \d+, row \d+/);
  assert.match(els.fishMsg.textContent, /The straight line to the outlet is [\d.]+ km\./);
  assert.match(els.fishMsg.textContent, /A D8 path along a grid is not a river length\./);
  assert.equal(els.fishStatRow ? els.fishStatRow.getAttribute('aria-live') : null, null, 'one announcement only: #fishMsg is the live region');
  /* the top-left corner of the grid is outside the divide */
  map.dispatch('keydown', { key: 'Home', shiftKey: false, preventDefault() {} });
  for (let i = 0; i < 40; i++) map.dispatch('keydown', { key: 'ArrowUp', shiftKey: true, preventDefault() {} });
  map.dispatch('keydown', { key: ' ', shiftKey: false, preventDefault() {} });
  assert.match(els.fishMsg.textContent, /^No terrain at column 0, row 0/);
});

test('the go-to buttons place the cursor, and the drop buttons work without the 3-D scene', () => {
  const { els, ctx } = run(T);
  els.fishHighBtn.click();
  assert.match(els.fishCursorMsg.textContent, /^Cursor: column \d+, row \d+ · block-mean elevation/);
  els.fishDropBtn.click();
  const f = fish(ctx).fish;
  assert.equal(f.drop.idx, f.highest);
  els.fishOutletBtn.click();
  els.fishDropBtn.click();
  assert.equal(f.drop.cells, 1);
});

test('the checkpoint item answers from the scene data and the page mounts', () => {
  const { ctx } = run(T);
  const inst = vm.runInContext('HydroQuiz.instances', ctx);
  const items = Object.values(inst)[0].describe();
  const q6 = items.find((i) => i.id === 'q6');
  const f = fish(ctx).fish;
  assert.ok(q6 && q6.type === 'numeric');
  assert.ok(Math.abs(q6.expected - f.trace(f.highest).length_km) < 1e-12);
  assert.match(q6.explain, /steps \(\d+ straight of 0\.51 km, \d+ diagonal of 0\.72 km\)/);
});

/* ── live vs poster state ─────────────────────────────────────────────────────────────────────── */
function liveHarness(extra) {
  const THREE = fakeTHREE();
  const harness = { setups: [], THREE };
  const globals = { THREE, requestAnimationFrame: (f) => { f(); return 1; },
    aihydro: { scene3d(opts) {
      const c = fakeCtx(opts.canvas, THREE); opts.setup(c);
      if (opts.canvas.id === 'fishCanvas') { harness.opts = opts; harness.setups.push(c); }     /* the page also draws the synthetic scene */
      return Promise.resolve(c); } } };
  const r = run(T, { globals });
  return Object.assign(harness, r);
}

test('live state: poster hidden, 10x label shown, status live; a lost context brings the poster back and hides the label', async () => {
  const h = liveHarness();
  await settle();
  const { els } = h, canvas = h.setups[0].canvas;
  assert.equal(els.fishPoster.hidden, true);
  assert.equal(els.fishLabel.hidden, false, 'the 10x label is on a live scene');
  assert.equal(canvas.getAttribute('aria-hidden'), null);
  assert.match(els.fishStatus.textContent, /Heights are drawn 10 times too steep/);
  canvas.dispatch('webglcontextlost');
  assert.equal(els.fishPoster.hidden, false);
  assert.equal(els.fishPoster.style.display, '');
  assert.equal(els.fishLabel.hidden, true, 'no label without a scene');
  assert.equal(canvas.getAttribute('aria-hidden'), 'true');
  assert.match(els.fishStatus.textContent, /graphics context was lost/);
});

test('after a rebuild (the bridge runs setup again on a fresh canvas) the live state and the label come back', async () => {
  const h = liveHarness();
  await settle();
  h.setups[0].canvas.dispatch('webglcontextlost');
  const fresh = fakeCtx(h.opts.canvas, h.THREE);
  fresh.canvas = require('./fakedom').makeElement('fishCanvas', {});
  h.opts.setup(fresh);
  assert.equal(h.els.fishPoster.hidden, true);
  assert.equal(h.els.fishLabel.hidden, false, 'the 10x label is on the rebuilt scene too');
  assert.match(h.els.fishStatus.textContent, /Drag to orbit/);
  /* the old canvas's late events no longer matter */
  h.setups[0].canvas.dispatch('webglcontextlost');
  assert.equal(h.els.fishPoster.hidden, true);
  fresh.canvas.dispatch('webglcontextlost');
  assert.equal(h.els.fishPoster.hidden, false);
  assert.equal(h.els.fishLabel.hidden, true);
});

test('the bridge gives up (scene disposed, or its own fallback shown) before the first frame: no label, poster stays', async () => {
  for (const giveUp of [(c) => { c.scene = null; }, (c) => { c.canvas.style.display = 'none'; }]) {
    const THREE = fakeTHREE(); let later = null;
    const globals = { THREE, requestAnimationFrame: (f) => { later = later || []; later.push(f); return 1; },
      aihydro: { scene3d(opts) { const c = fakeCtx(opts.canvas, THREE); opts.setup(c); giveUp(c); return Promise.resolve(c); } } };
    const { els, getEl } = run(T, { globals });
    getEl('fishLabel').hidden = true;                      /* as in the markup; the fake DOM does not parse the attribute */
    await settle();
    for (let i = 0; i < 4 && later && later.length; i++) { const q = later.splice(0); q.forEach((f) => f()); }
    assert.equal((els.fishPoster || getEl('fishPoster')).hidden, false);
    assert.equal(getEl('fishLabel').hidden, true, 'label stays hidden');
  }
});
