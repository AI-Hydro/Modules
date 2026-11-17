'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const vm = require('vm');
const H = require('./helpers');
const { run } = require('./fakedom');

/* A bare window with a counting setInterval, and shared/ready.js evaluated in it. */
function makeWindow(withBridge) {
  const counts = { set: 0, cleared: 0 }, timers = [];
  const win = {
    setInterval(fn) { counts.set++; timers.push(fn); return counts.set; },
    clearInterval() { counts.cleared++; },
    console,
  };
  win.window = win;
  if (withBridge) win.aihydro = {};
  vm.createContext(win);
  vm.runInContext(H.read('shared/ready.js'), win);
  return { win, counts, timers };
}

test('whenReady: any number of calls without the bridge create exactly one timer', () => {
  const { win, counts } = makeWindow(false);
  for (let i = 0; i < 500; i++) vm.runInContext('whenReady(function () {})', win);
  assert.equal(counts.set, 1);
});

test('whenReady: with the bridge already present no timer is created and every callback runs', async () => {
  const { win, counts } = makeWindow(true);
  win.n = 0;
  for (let i = 0; i < 50; i++) vm.runInContext('whenReady(function () { n++; })', win);
  await Promise.resolve(); await Promise.resolve();
  assert.equal(counts.set, 0);
  assert.equal(win.n, 50);
});

test('whenReady: callbacks wait for the bridge, then all run; polling stops', async () => {
  const { win, counts, timers } = makeWindow(false);
  win.n = 0;
  for (let i = 0; i < 20; i++) vm.runInContext('whenReady(function () { n++; })', win);
  timers[0]();                       /* poll: not there yet */
  assert.equal(win.n, 0);
  win.aihydro = {};
  timers[0]();                       /* poll: arrived */
  await Promise.resolve(); await Promise.resolve();
  assert.equal(win.n, 20);
  assert.equal(counts.cleared, 1);
  assert.equal(counts.set, 1);
});

test('whenReady: the poll gives up after about 10 s when no bridge ever arrives', () => {
  const { win, counts, timers } = makeWindow(false);
  vm.runInContext('whenReady(function () {})', win);
  for (let i = 0; i < 199; i++) timers[0]();
  assert.equal(counts.cleared, 0);
  timers[0]();
  assert.equal(counts.cleared, 1);
});

test('whenReady: after the time-out a later call re-arms ONE poll, so a late bridge is still picked up', async () => {
  const { win, counts, timers } = makeWindow(false);
  win.n = 0;
  vm.runInContext('whenReady(function () { n++; })', win);
  for (let i = 0; i < 200; i++) timers[0]();            /* gives up */
  assert.equal(counts.cleared, 1);
  for (let i = 0; i < 50; i++) vm.runInContext('whenReady(function () { n++; })', win);
  assert.equal(counts.set, 2, 'one new poll, not fifty');
  win.aihydro = {};
  timers[1]();
  await Promise.resolve(); await Promise.resolve();
  assert.equal(win.n, 51, 'the callback queued before the time-out runs too');
});

for (const id of fs.readdirSync(`${H.ROOT}/modules`).filter((d) => fs.existsSync(`${H.ROOT}/modules/${d}/module.html`))) {
  test(`${id}: loading the page without the bridge leaves at most one polling timer`, () => {
    const { counters } = run(H.moduleText(id));
    assert.ok(counters.setInterval <= 1, `${counters.setInterval} setInterval calls`);
  });
}

test('dem-to-twi: without the bridge exactly one poll runs and the 3-D scene is never requested', () => {
  const { ctx, counters } = run(H.moduleText('dem-to-twi'));
  assert.equal(ctx.window.aihydro, undefined);
  assert.equal(counters.setInterval, 1);
});

test('dem-to-twi: with the bridge present the 3-D scene is requested once, with no poll', async () => {
  const calls = [];
  const { counters } = run(H.moduleText('dem-to-twi'), { globals: { aihydro: { scene3d(o) { calls.push(o); } } } });
  await Promise.resolve(); await Promise.resolve(); await Promise.resolve();
  assert.equal(counters.setInterval, 0);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].dem.length, 5);
});
