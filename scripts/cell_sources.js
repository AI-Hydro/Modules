#!/usr/bin/env node
'use strict';
/* Print, as JSON, the text of every element with an id after a module's own scripts have run
   against the fake DOM in tests/js/fakedom.js. scripts/render_static_outputs.py uses it to get the
   final source of executable cells whose <pre class="aihydro-source"> is filled in by script
   (gauge snapshots, point calculators). Usage: node scripts/cell_sources.js modules/<id>/module.html */
const fs = require('fs');
const path = require('path');
const { run } = require(path.join(__dirname, '..', 'tests', 'js', 'fakedom.js'));

const html = fs.readFileSync(process.argv[2], 'utf8');
const { els } = run(html);
const out = {};
for (const id of Object.keys(els)) {
  const t = els[id].textContent;
  if (typeof t === 'string' && t.trim()) out[id] = t;
}
process.stdout.write(JSON.stringify(out));
