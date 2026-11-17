#!/usr/bin/env node
'use strict';
/* Print every module's checkpoint as the learner sees it (prompts, options) plus the computed right
   answers, as JSON. tests/test_quiz_answers.py recomputes the answers independently in Python. */
const fs = require('fs');
const vm = require('vm');
const H = require('./helpers');
const { run } = require('./fakedom');

const out = {};
for (const id of fs.readdirSync(`${H.ROOT}/modules`).filter((d) => fs.existsSync(`${H.ROOT}/modules/${d}/module.html`))) {
  const { ctx } = run(H.moduleText(id));
  const inst = vm.runInContext('typeof HydroQuiz === "undefined" ? {} : HydroQuiz.instances', ctx);
  const names = Object.keys(inst);
  if (names.length) out[id] = { quizId: names[0], items: inst[names[0]].describe() };
}
process.stdout.write(JSON.stringify(out));
