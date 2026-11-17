'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('vm');
const H = require('./helpers');
const { makeElement } = require('./fakedom');

/* HydroQuiz inside a fresh context with a minimal DOM. `parentOrigins` simulates
   location.ancestorOrigins; embedded=false simulates a standalone page (parent === window). */
function setup({ embedded = true, ancestorOrigins = ['vscode-webview://abc123'], referrer = '', artifact = { artifactId: 'art-1' } } = {}) {
  const posts = [];
  const document = {
    referrer,
    createElement: (tag) => makeElement('', { tag }),
    getElementById: () => null,
  };
  const win = { document, console, Math, JSON, URL, __aihydroArtifact: artifact, location: { ancestorOrigins }, parent: null };
  win.window = win;
  win.parent = embedded ? { postMessage: (m, o) => posts.push([m, o]) } : win;
  const ctx = vm.createContext(Object.assign(win, { document }));
  vm.runInContext(H.read('shared/quiz.js'), ctx);
  return { ctx, posts, HQ: vm.runInContext('HydroQuiz', ctx), document };
}

/* radios in one group are exclusive in a real DOM; the fake needs that said out loud */
function choose(radios, i) { radios.forEach((r, k) => { r.checked = k === i; }); }
function walk(el, fn) { fn(el); (el.children || []).forEach((c) => walk(c, fn)); }
function find(el, pred) { const out = []; walk(el, (n) => { if (pred(n)) out.push(n); }); return out; }
function allText(el) { let s = ''; walk(el, (n) => { if (n.textContent) s += ' ' + n.textContent; }); return s; }
const cls = (c) => (n) => (n.className || '').split(' ').includes(c);

const ITEMS = () => [
  { id: 'c1', type: 'choice', prompt: 'Which?', options: ['alpha', 'beta', 'gamma'], correct: 1,
    feedback: ['Wrong because of alpha.', null, 'Wrong because of gamma.'], explain: 'EXPLAIN-C1 beta is right.' },
  { id: 'n1', type: 'numeric', prompt: 'How many?', unit: 'mm', answer: () => 4.938, tol: { abs: 0.02 },
    hint: 'HINT-N1', explain: (a) => 'EXPLAIN-N1 ' + a.toFixed(2) },
];

test('parseNumber accepts plain, comma-decimal, thousands, unicode minus and units; rejects text', () => {
  const { HQ } = setup();
  const t = { '0.74': 0.74, ' 0,74 ': 0.74, '1 350': 1350, '1,350': 1350, '1,350.5': 1350.5, '−3.2': -3.2, '12 mm': 12, '45%': 45, '1e3': 1000, '.5': 0.5 };
  for (const [s, v] of Object.entries(t)) assert.equal(HQ.parseNumber(s), v, s);
  for (const bad of ['', 'abc', '--1', '1..2.3x', null, undefined, '3 apples 4']) assert.equal(HQ.parseNumber(bad), null, String(bad));
});

test('numeric grading: tolerance is absolute or relative, direction is reported, the answer comes from a function', () => {
  const { HQ } = setup();
  const item = { type: 'numeric', answer: () => 10, tol: { abs: 0.5 } };
  assert.equal(HQ.gradeNumeric(item, '10.4').status, 'correct');
  assert.equal(HQ.gradeNumeric(item, '10.6').status, 'incorrect');
  assert.equal(HQ.gradeNumeric(item, '10.6').direction, 'high');
  assert.equal(HQ.gradeNumeric(item, '9').direction, 'low');
  assert.equal(HQ.gradeNumeric(item, 'x').status, 'invalid');
  assert.equal(HQ.gradeNumeric({ type: 'numeric', answer: 200, tol: { rel: 0.01 } }, '201.9').status, 'correct');
  assert.equal(HQ.gradeNumeric({ type: 'numeric', answer: 200, tol: { rel: 0.01 } }, '202.1').status, 'incorrect');
  let calls = 0;
  const live = { type: 'numeric', answer: () => { calls++; return 3; } };
  HQ.gradeNumeric(live, '3'); HQ.gradeNumeric(live, '3');
  assert.equal(calls, 2, 'answer is recomputed at every check, never cached from a typed value');
});

test('before any attempt nothing in the DOM reveals an answer, explanation or hint', () => {
  const { HQ, document } = setup();
  const root = document.createElement('div');
  HQ.mount(root, { quizId: 'q', moduleId: 'm', items: ITEMS() });
  const text = allText(root);
  for (const secret of ['EXPLAIN-C1', 'EXPLAIN-N1', 'HINT-N1', 'Wrong because', '4.94']) assert.ok(!text.includes(secret), secret);
  find(root, (n) => n.tagName === 'LI').forEach((li) => assert.equal(li.getAttribute('data-state'), ''));
  find(root, (n) => n.tagName === 'INPUT' && n.getAttribute('type') === 'radio').forEach((r) => assert.equal(r.checked, false));
  const reveals = find(root, cls('hq-reveal'));
  assert.ok(reveals.every((b) => b.hasAttribute('hidden')), 'no "show explanation" before two misses');
});

test('wrong choice: feedback for that option only, never names the right answer; retry works; completion counts', () => {
  const { HQ, document } = setup();
  const root = document.createElement('div');
  const quiz = HQ.mount(root, { quizId: 'q', moduleId: 'm', items: ITEMS() });
  const radios = find(root, (n) => n.tagName === 'INPUT' && n.getAttribute('type') === 'radio');
  const item = find(root, (n) => n.getAttribute && n.getAttribute('data-hq-item') === 'c1')[0];
  const fb = find(item, cls('hq-feedback'))[0];
  const check = find(item, cls('hq-check'))[0], reveal = find(item, cls('hq-reveal'))[0];

  check.dispatch('click');                                  /* nothing chosen: a prompt, not an attempt */
  assert.ok(/choose an answer/i.test(fb.textContent));
  assert.equal(quiz.state().items[0].attempts, 0);

  choose(radios, 0); check.dispatch('click');        /* wrong */
  assert.equal(item.getAttribute('data-state'), 'incorrect');
  assert.ok(fb.textContent.includes('Wrong because of alpha'));
  assert.ok(!fb.textContent.includes('beta') && !fb.textContent.includes('EXPLAIN'), 'must not reveal the answer');
  assert.ok(reveal.hasAttribute('hidden'));
  assert.equal(check.textContent, 'Check again');

  choose(radios, 2); check.dispatch('click');        /* wrong again: explanation can now be requested */
  assert.ok(!reveal.hasAttribute('hidden'));
  assert.equal(quiz.state().correct, 0);

  choose(radios, 1); check.dispatch('click');        /* retry succeeds */
  assert.equal(item.getAttribute('data-state'), 'correct');
  assert.ok(fb.textContent.includes('EXPLAIN-C1'));
  assert.equal(quiz.state().correct, 1);
  assert.equal(quiz.state().items[0].attempts, 3);
});

test('revealing the explanation never counts as correct', () => {
  const { HQ, document } = setup();
  const root = document.createElement('div');
  const quiz = HQ.mount(root, { quizId: 'q', moduleId: 'm', items: ITEMS() });
  const item = find(root, (n) => n.getAttribute && n.getAttribute('data-hq-item') === 'c1')[0];
  const radios = find(item, (n) => n.tagName === 'INPUT');
  const check = find(item, cls('hq-check'))[0], reveal = find(item, cls('hq-reveal'))[0];
  radios[0].checked = true; check.dispatch('click'); check.dispatch('click');
  reveal.dispatch('click');
  assert.ok(find(item, cls('hq-feedback'))[0].textContent.includes('beta'));
  assert.equal(item.getAttribute('data-state'), 'revealed');
  assert.equal(quiz.state().correct, 0);
  assert.equal(quiz.state().items[0].revealed, true);
});

test('numeric item: Enter checks, wrong value gives a direction and the hint but not the number, retry succeeds', () => {
  const { HQ, document } = setup();
  const root = document.createElement('div');
  const quiz = HQ.mount(root, { quizId: 'q', moduleId: 'm', items: ITEMS() });
  const item = find(root, (n) => n.getAttribute && n.getAttribute('data-hq-item') === 'n1')[0];
  const input = find(item, (n) => n.tagName === 'INPUT')[0];
  const fb = find(item, cls('hq-feedback'))[0];
  assert.equal(input.getAttribute('inputmode'), 'decimal');
  const label = find(item, (n) => n.tagName === 'LABEL')[0];
  assert.equal(label.getAttribute('for'), input.getAttribute('id'), 'label is bound to the field');

  input.value = 'abc'; input.dispatch('keydown', { key: 'Enter' });
  assert.ok(/enter a number/i.test(fb.textContent)); assert.equal(quiz.state().items[1].attempts, 0);
  input.value = '9'; input.dispatch('keydown', { key: 'Enter' });
  assert.ok(/too high/.test(fb.textContent) && fb.textContent.includes('HINT-N1'));
  assert.ok(!fb.textContent.includes('4.94') && !fb.textContent.includes('EXPLAIN'));
  input.value = '4,95'; input.dispatch('keydown', { key: 'Enter' });
  assert.equal(item.getAttribute('data-state'), 'correct');
  assert.ok(fb.textContent.includes('EXPLAIN-N1 4.94'));
});

test('accessibility structure: fieldset + legend per item, live status regions, native radios in a named group', () => {
  const { HQ, document } = setup();
  const root = document.createElement('div');
  HQ.mount(root, { quizId: 'q', moduleId: 'm', items: ITEMS() });
  assert.equal(find(root, (n) => n.tagName === 'FIELDSET').length, 2);
  assert.equal(find(root, (n) => n.tagName === 'LEGEND').length, 2);
  const live = find(root, (n) => n.getAttribute && n.getAttribute('aria-live') === 'polite');
  assert.ok(live.length >= 3, 'a status region per item plus the summary');
  const radios = find(root, (n) => n.tagName === 'INPUT' && n.getAttribute('type') === 'radio');
  assert.equal(new Set(radios.map((r) => r.getAttribute('name'))).size, 1, 'one radio group per question');
  find(root, (n) => n.tagName === 'BUTTON').forEach((b) => assert.equal(b.getAttribute('type'), 'button'));
});

test('completion is posted as artifact/quizComplete to the embedding window origin, never "*"', () => {
  const { HQ, document, posts } = setup();
  const root = document.createElement('div');
  const quiz = HQ.mount(root, { quizId: 'q', moduleId: 'm', items: ITEMS() });
  quiz.answer('c1', 1); quiz.check('c1');
  quiz.answer('n1', '4.94'); quiz.check('n1');
  assert.ok(posts.length >= 2);
  const [msg, origin] = posts[posts.length - 1];
  assert.equal(origin, 'vscode-webview://abc123');
  assert.notEqual(origin, '*');
  assert.deepEqual([msg.source, msg.type, msg.quizId, msg.passed, msg.score, msg.total, msg.artifactId],
                   ['aihydro-artifact', 'artifact/quizComplete', 'q', true, 2, 2, 'art-1']);
  assert.equal(posts[0][0].passed, false, 'an incomplete quiz reports passed: false');
  assert.ok(posts.every((p) => p[1] !== '*'));
});

test('nothing is posted from a standalone page or when the embedding origin cannot be determined', () => {
  for (const cfg of [{ embedded: false }, { ancestorOrigins: [] }, { ancestorOrigins: ['null'] }, { ancestorOrigins: null, referrer: 'vscode-webview://x/index.html' }]) {
    const { HQ, document, posts } = setup(cfg);
    const root = document.createElement('div');
    const quiz = HQ.mount(root, { quizId: 'q', moduleId: 'm', items: ITEMS() });
    quiz.answer('c1', 1); quiz.check('c1');
    assert.equal(posts.length, 0, JSON.stringify(cfg));
    assert.equal(HQ.lastReport().posted, false);
  }
  const { HQ, document, posts } = setup({ ancestorOrigins: null, referrer: 'https://example.org/preview/page.html' });
  const quiz = HQ.mount(document.createElement('div'), { quizId: 'q', moduleId: 'm', items: ITEMS() });
  quiz.answer('c1', 1); quiz.check('c1');
  assert.equal(posts[0][1], 'https://example.org', 'referrer origin is the fallback');
});

test('prompt, correct answer and explanation may be functions evaluated at use time', () => {
  const { HQ, document } = setup();
  let k = 1;
  const quiz = HQ.mount(document.createElement('div'), { quizId: 'q', moduleId: 'm', items: [
    { id: 'f', type: 'choice', prompt: () => 'P' + k, options: ['a', 'b'], correct: () => k, explain: () => 'E' + k }] });
  assert.equal(quiz.expected('f'), 1);
  k = 0;
  assert.equal(quiz.expected('f'), 0);
});
