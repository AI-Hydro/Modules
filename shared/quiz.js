/* HydroQuiz: the one checkpoint engine used by every module.
 *
 * Behaviour (the contract the tests pin):
 *  - nothing about the answer is in the DOM before the first attempt (no pre-marked option, no
 *    explanation text); the specification lives in the module's script, not the markup;
 *  - every item can be answered again and again; a wrong attempt gets feedback for THAT answer but
 *    never names the right one; after two wrong attempts a "Show explanation" button appears;
 *  - a correct attempt shows the explanation; revealing an answer does not count as correct;
 *  - fully keyboard operable (native radio group or text field + a Check button; Enter checks a
 *    numeric answer) and announced through role=status live regions;
 *  - numeric items take their answer from a function over the lesson's own data or code, so the
 *    expected value can never be typed in by hand and drift from the lesson;
 *  - completion goes to the AI-Hydro host as `artifact/quizComplete` with an explicit target
 *    origin (the embedding window's origin), never '*'. If that origin cannot be determined, or
 *    the page is standalone, nothing is posted.
 *
 * Item specification:
 *   (prompt may be a function, so numbers quoted in the question come from the lesson's data too)
 *   { id, type:'choice', prompt, options:[text,...], correct:index|function,
 *     feedback:[text|null,...],            // shown when that option is chosen and wrong
 *     explain:text|function }              // shown when correct (and on "Show explanation")
 *   { id, type:'numeric', prompt, answer:number|function, tol:{abs,rel}, unit, format:function,
 *     hint:text|function, explain:text|function(answer) }
 *
 * Single source of truth: shared/quiz.js (inlined by scripts/build_modules.py).
 */
var HydroQuiz = (function () {
  'use strict';

  var instances = {};
  var lastReport = null;

  function resolve(v, arg) { return typeof v === 'function' ? v(arg) : v; }

  /* "0.74", "0,74", "1 350", "1,350", "−3", "12 mm", "45%" -> number; anything else -> null */
  function parseNumber(text) {
    var s = String(text == null ? '' : text).replace(/−/g, '-').replace(/[  ]/g, ' ').trim();
    var m = /^([+-]?[0-9][0-9 ,.]*(?:e[+-]?[0-9]+)?|[+-]?\.[0-9]+)\s*(?:%|[A-Za-z°µμ\/²³·^ -]*)$/i.exec(s);
    if (!m) return null;
    var n = m[1].replace(/ /g, '');
    if (n.indexOf('.') >= 0 && n.indexOf(',') >= 0) n = n.replace(/,/g, '');
    else if (/^[+-]?[0-9]{1,3}(,[0-9]{3})+$/.test(n)) n = n.replace(/,/g, '');
    else n = n.replace(',', '.');
    if (!/^[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:e[+-]?[0-9]+)?$/i.test(n)) return null;
    var v = parseFloat(n);
    return isFinite(v) ? v : null;
  }

  function tolerance(item, ans) {
    var t = item.tol || {};
    var abs = typeof t.abs === 'number' ? t.abs : 0;
    var rel = typeof t.rel === 'number' ? t.rel : (typeof t.abs === 'number' ? 0 : 0.02);
    return Math.max(abs, rel * Math.abs(ans));
  }

  function gradeChoice(item, idx) {
    if (idx === null || idx === undefined || idx < 0) return { status: 'empty' };
    return { status: idx === resolve(item.correct) ? 'correct' : 'incorrect', choice: idx };
  }

  function gradeNumeric(item, text) {
    var v = parseNumber(text);
    if (v === null) return { status: 'invalid' };
    var ans = resolve(item.answer);
    var tol = tolerance(item, ans);
    var ok = Math.abs(v - ans) <= tol;
    return { status: ok ? 'correct' : 'incorrect', value: v, answer: ans, tol: tol, direction: v > ans ? 'high' : 'low' };
  }

  function fmt(item, v) {
    if (item.format) return item.format(v);
    var s = Math.abs(v) >= 1000 ? String(Math.round(v)) : String(parseFloat(v.toPrecision(4)));
    return s + (item.unit ? ' ' + item.unit : '');
  }

  function feedbackText(item, res) {
    if (res.status === 'correct') {
      var ex = item.type === 'numeric' ? resolve(item.explain, res.answer) : resolve(item.explain);
      return '✓ Correct. ' + (ex || '');
    }
    if (item.type === 'numeric') {
      var hint = resolve(item.hint, res.answer);
      return '✗ Not quite: your value is too ' + res.direction + '. ' + (hint || 'Recompute it from the numbers in the lesson and try again.');
    }
    var fb = item.feedback && item.feedback[res.choice];
    return '✗ Not quite. ' + (fb || 'Re-read the section above and try again.');
  }

  function revealText(item) {
    if (item.type === 'numeric') {
      var a = resolve(item.answer);
      return 'Answer: ' + fmt(item, a) + '. ' + (resolve(item.explain, a) || '');
    }
    var c = resolve(item.correct);
    return 'Answer: ' + item.options[c] + '. ' + (resolve(item.explain) || '');
  }

  /* A numeric constant read from the text of a code cell (e.g. `C = 0.35`), so an answer is
     computed from the very numbers the learner reads in the cell. */
  function sourceConstant(cellId, name) {
    var pre = document.querySelector('[data-aihydro-cell-id="' + cellId + '"] .aihydro-source');
    var m = pre && new RegExp('^\\s*' + name + '\\s*=\\s*([-+0-9._eE]+)', 'm').exec(pre.textContent);
    if (!m) throw new Error('constant ' + name + ' not found in cell ' + cellId);
    return parseFloat(m[1].replace(/_/g, ''));
  }

  /* The window that embeds this page, as an origin string, or null (standalone / unknown). */
  function parentOrigin(win) {
    win = win || window;
    try { if (!win.parent || win.parent === win) return null; } catch (e) { return null; }
    var o = null;
    try { var a = win.location && win.location.ancestorOrigins; if (a && a.length) o = a[0]; } catch (e) { o = null; }
    if (!o || o === 'null') {
      try { o = win.document.referrer ? new URL(win.document.referrer).origin : null; } catch (e) { o = null; }
    }
    return o && o !== 'null' ? o : null;
  }

  /* artifact/quizComplete exactly as the AI-Hydro bridge sends it, but to a named origin. */
  function postComplete(quizId, passed, score, total, win) {
    win = win || window;
    var origin = parentOrigin(win);
    lastReport = { quizId: quizId, passed: passed, score: score, total: total, origin: origin, posted: false };
    if (!origin) return false;
    var base = win.__aihydroArtifact || {};
    var msg = { source: 'aihydro-artifact' };
    for (var k in base) msg[k] = base[k];
    msg.type = 'artifact/quizComplete';
    msg.quizId = quizId; msg.passed = passed; msg.score = score; msg.total = total;
    try { win.parent.postMessage(msg, origin); lastReport.posted = true; } catch (e) { return false; }
    return true;
  }

  function el(tag, props, kids) {
    var e = document.createElement(tag);
    if (props) for (var k in props) {
      if (k === 'class') e.className = props[k];
      else if (k === 'text') e.textContent = props[k];
      else e.setAttribute(k, props[k]);
    }
    (kids || []).forEach(function (c) { if (c) e.appendChild(c); });
    return e;
  }

  function mount(root, spec) {
    var quizId = spec.quizId;
    var items = spec.items;
    var rec = {};            // id -> { attempts, correct, revealed, node refs }
    var list = el('ol', { 'class': 'hq-list' });
    var summary = el('p', { 'class': 'hq-summary', role: 'status', 'aria-live': 'polite' });

    root.setAttribute('class', 'hq');
    root.setAttribute('data-hq-quiz', quizId);

    function counts() {
      var n = 0;
      items.forEach(function (it) { if (rec[it.id].correct) n++; });
      return n;
    }
    function updateSummary() {
      var n = counts(), total = items.length;
      summary.textContent = n === total
        ? 'All ' + total + ' correct ✓ Checkpoint complete.'
        : n + ' of ' + total + ' correct. Wrong answers can be changed and checked again.';
      summary.setAttribute('data-complete', n === total ? '1' : '0');
    }

    items.forEach(function (it, qi) {
      var r = rec[it.id] = { attempts: 0, correct: false, revealed: false, radios: [], input: null };
      var uid = quizId + '-' + it.id;
      var fb = el('div', { 'class': 'hq-feedback', id: uid + '-fb', role: 'status', 'aria-live': 'polite' });
      var check = el('button', { 'class': 'hq-check', type: 'button', text: 'Check answer' });
      var reveal = el('button', { 'class': 'hq-reveal', type: 'button', text: 'Show explanation', hidden: 'hidden' });
      var legend = el('legend', { 'class': 'hq-prompt', text: (qi + 1) + ' · ' + resolve(it.prompt) });
      var body;

      if (it.type === 'numeric') {
        var input = el('input', { 'class': 'hq-input', type: 'text', inputmode: 'decimal', autocomplete: 'off',
                                  id: uid + '-in', 'aria-describedby': uid + '-fb' });
        r.input = input;
        input.addEventListener('keydown', function (ev) { if (ev.key === 'Enter') { ev.preventDefault(); doCheck(); } });
        body = el('div', { 'class': 'hq-numeric' }, [
          el('label', { 'class': 'hq-numlabel', 'for': uid + '-in', text: 'Your answer' + (it.unit ? ' (' + it.unit + ')' : '') }),
          input
        ]);
      } else {
        body = el('div', { 'class': 'hq-options' });
        it.options.forEach(function (text, oi) {
          var radio = el('input', { type: 'radio', name: uid, value: String(oi), 'aria-describedby': uid + '-fb' });
          r.radios.push(radio);
          body.appendChild(el('label', { 'class': 'hq-opt' }, [radio, el('span', { text: text })]));
        });
      }

      function selected() {
        for (var i = 0; i < r.radios.length; i++) if (r.radios[i].checked) return i;
        return -1;
      }
      function doCheck() {
        var res = it.type === 'numeric' ? gradeNumeric(it, r.input.value) : gradeChoice(it, selected());
        if (res.status === 'empty' || res.status === 'invalid') {
          fb.textContent = res.status === 'empty' ? 'Choose an answer first, then check it.' : 'Enter a number (for example 0.74), then check it.';
          item.setAttribute('data-state', 'pending');
          return;
        }
        r.attempts++;
        r.correct = res.status === 'correct';
        item.setAttribute('data-state', r.correct ? 'correct' : 'incorrect');
        fb.textContent = feedbackText(it, res);
        check.textContent = 'Check again';
        if (!r.correct && r.attempts >= 2) reveal.removeAttribute('hidden');
        updateSummary();
        postComplete(quizId, counts() === items.length, counts(), items.length);
        if (spec.onChange) spec.onChange(api.state());
      }
      check.addEventListener('click', doCheck);
      reveal.addEventListener('click', function () {
        r.revealed = true;
        item.setAttribute('data-state', r.correct ? 'correct' : 'revealed');
        fb.textContent = revealText(it);
      });
      r.check = doCheck;

      var fieldset = el('fieldset', { 'class': 'hq-fieldset' }, [
        legend, body,
        el('div', { 'class': 'hq-actions' }, [check, reveal]),
        fb
      ]);
      var item = el('li', { 'class': 'hq-item', 'data-hq-item': it.id, 'data-state': '' }, [fieldset]);
      list.appendChild(item);
    });

    root.appendChild(list);
    root.appendChild(summary);
    updateSummary();

    var api = {
      quizId: quizId,
      state: function () {
        var n = counts();
        return { quizId: quizId, correct: n, total: items.length, passed: n === items.length,
                 items: items.map(function (it) { return { id: it.id, attempts: rec[it.id].attempts, correct: rec[it.id].correct, revealed: rec[it.id].revealed }; }) };
      },
      /* test/programmatic hooks: answer an item then check it */
      answer: function (id, value) {
        var r = rec[id];
        if (r.input) r.input.value = String(value);
        else if (r.radios[value]) r.radios[value].checked = true;
      },
      check: function (id) { rec[id].check(); },
      /* every item as the learner sees it plus the computed right answer, for tests that cross-check them independently */
      describe: function () {
        return items.map(function (it) {
          return { id: it.id, type: it.type, prompt: resolve(it.prompt), options: it.options || null,
                   expected: resolve(it.type === 'numeric' ? it.answer : it.correct),
                   explain: it.type === 'numeric' ? resolve(it.explain, resolve(it.answer)) : resolve(it.explain) };
        });
      },
      /* the computed right answer (index or number), for tests that cross-check it independently */
      expected: function (id) {
        for (var i = 0; i < items.length; i++) if (items[i].id === id) return resolve(items[i].type === 'numeric' ? items[i].answer : items[i].correct);
        return undefined;
      }
    };
    instances[quizId] = api;
    return api;
  }

  return { mount: mount, parseNumber: parseNumber, gradeChoice: gradeChoice, gradeNumeric: gradeNumeric,
           sourceConstant: sourceConstant, parentOrigin: parentOrigin, postComplete: postComplete, feedbackText: feedbackText,
           revealText: revealText, tolerance: tolerance, instances: instances,
           lastReport: function () { return lastReport; } };
})();
