/* D8 terrain routing on a regular grid: priority-flood fill, steepest-descent
 * flow direction (drop / distance), flow accumulation, slope and TWI.
 *
 *   dem      : array of rows (dem[row][col]), elevations in metres
 *   cell     : cell size in metres
 *   outlet   : {r, c}; defaults to the lowest cell on the grid edge
 *
 * Fill follows Barnes, Lehman & Mulla (2014) "Priority-flood" with epsilon
 * increments, seeded ONLY at the outlet so that every cell has a strictly
 * descending path to it. Ties break by insertion order (deterministic; the
 * Python twin shared/d8.py uses the identical rule).
 * Single source of truth: shared/d8.js (twin: d8.py).
 */
var D8_DIRS = [[-1,0],[-1,1],[0,1],[1,1],[1,0],[1,-1],[0,-1],[-1,-1]]; /* N NE E SE S SW W NW */

function d8LowestEdge(dem) {
  var R = dem.length, C = dem[0].length, best = null, r, c;
  for (r = 0; r < R; r++) for (c = 0; c < C; c++) {
    if (r !== 0 && c !== 0 && r !== R - 1 && c !== C - 1) continue;
    if (best === null || dem[r][c] < dem[best.r][best.c]) best = { r: r, c: c };
  }
  return best;
}

function d8Fill(dem, outlet, epsilon) {
  var R = dem.length, C = dem[0].length, N = R * C;
  var lo = Infinity, hi = -Infinity, r, c, k;
  for (r = 0; r < R; r++) for (c = 0; c < C; c++) {
    if (dem[r][c] < lo) lo = dem[r][c];
    if (dem[r][c] > hi) hi = dem[r][c];
  }
  var eps = epsilon === undefined ? 1e-5 * ((hi - lo) || 1) : epsilon;
  var out = new Array(N), seen = new Uint8Array(N);
  for (r = 0; r < R; r++) for (c = 0; c < C; c++) out[r * C + c] = dem[r][c];
  var heap = [], counter = 0;
  function less(a, b) { return a[0] < b[0] || (a[0] === b[0] && a[1] < b[1]); }
  function push(e) {
    var i = heap.length; heap.push(e);
    while (i > 0) { var p = (i - 1) >> 1; if (less(heap[i], heap[p])) { var t = heap[i]; heap[i] = heap[p]; heap[p] = t; i = p; } else break; }
  }
  function pop() {
    var top = heap[0], last = heap.pop();
    if (heap.length) {
      heap[0] = last; var i = 0;
      for (;;) {
        var l = 2 * i + 1, rr = l + 1, m = i;
        if (l < heap.length && less(heap[l], heap[m])) m = l;
        if (rr < heap.length && less(heap[rr], heap[m])) m = rr;
        if (m === i) break;
        var t = heap[i]; heap[i] = heap[m]; heap[m] = t; i = m;
      }
    }
    return top;
  }
  var o = outlet.r * C + outlet.c;
  seen[o] = 1; push([out[o], counter++, o]);
  while (heap.length) {
    var e = pop(), idx = e[2], er = (idx / C) | 0, ec = idx % C;
    for (k = 0; k < 8; k++) {
      var nr = er + D8_DIRS[k][0], nc = ec + D8_DIRS[k][1];
      if (nr < 0 || nc < 0 || nr >= R || nc >= C) continue;
      var ni = nr * C + nc;
      if (seen[ni]) continue;
      seen[ni] = 1;
      if (out[ni] <= out[idx] + eps) out[ni] = out[idx] + eps;
      push([out[ni], counter++, ni]);
    }
  }
  return out; /* flat row-major */
}

/* receiver index per cell (-1 for the outlet), steepest drop/distance */
function d8Directions(filled, R, C, cell, outlet) {
  var rec = new Array(R * C), o = outlet.r * C + outlet.c, r, c, k;
  for (r = 0; r < R; r++) for (c = 0; c < C; c++) {
    var i = r * C + c;
    if (i === o) { rec[i] = -1; continue; }
    var best = 0, bi = -1;
    for (k = 0; k < 8; k++) {
      var nr = r + D8_DIRS[k][0], nc = c + D8_DIRS[k][1];
      if (nr < 0 || nc < 0 || nr >= R || nc >= C) continue;
      var dist = (D8_DIRS[k][0] !== 0 && D8_DIRS[k][1] !== 0) ? cell * Math.SQRT2 : cell;
      var g = (filled[i] - filled[nr * C + nc]) / dist;
      if (g > best) { best = g; bi = nr * C + nc; }
    }
    rec[i] = bi;
  }
  return rec;
}

/* number of cells draining through each cell (the cell itself included) */
function d8Accumulation(filled, rec) {
  var N = filled.length, order = [], i;
  for (i = 0; i < N; i++) order.push(i);
  order.sort(function (a, b) { return filled[b] - filled[a] || a - b; });
  var acc = new Array(N).fill(1);
  for (var j = 0; j < N; j++) { i = order[j]; if (rec[i] >= 0) acc[rec[i]] += acc[i]; }
  return acc;
}

/* tan(beta): steepest downslope gradient, floored (see TAN_FLOOR note) */
function d8TanBeta(filled, rec, R, C, cell, floor) {
  var t = new Array(R * C);
  for (var i = 0; i < R * C; i++) {
    if (rec[i] < 0) { t[i] = floor; continue; }
    var r = (i / C) | 0, c = i % C, nr = (rec[i] / C) | 0, nc = rec[i] % C;
    var dist = (r !== nr && c !== nc) ? cell * Math.SQRT2 : cell;
    t[i] = Math.max((filled[i] - filled[rec[i]]) / dist, floor);
  }
  return t;
}

function d8Route(dem, cell, opts) {
  opts = opts || {};
  var R = dem.length, C = dem[0].length;
  var outlet = opts.outlet || d8LowestEdge(dem);
  var floor = opts.tanFloor === undefined ? 1e-3 : opts.tanFloor;
  var filled = d8Fill(dem, outlet, opts.epsilon);
  var rec = d8Directions(filled, R, C, cell, outlet);
  var acc = d8Accumulation(filled, rec);
  var tanb = d8TanBeta(filled, rec, R, C, cell, floor);
  var twi = new Array(R * C);
  for (var i = 0; i < R * C; i++) twi[i] = Math.log((acc[i] * cell) / tanb[i]); /* a = A/w = acc*cell^2/cell */
  return { R: R, C: C, cell: cell, outlet: outlet, filled: filled, rec: rec, acc: acc, tanBeta: tanb, twi: twi, tanFloor: floor };
}

/* path from a cell to the outlet (guarded: cannot loop forever) */
function d8Path(rec, start, maxSteps) {
  var path = [start], i = start, guard = maxSteps || rec.length;
  while (rec[i] >= 0 && guard-- > 0) { i = rec[i]; path.push(i); }
  return path;
}

/* cells whose D8 path passes through target (target included) */
function d8Upstream(rec, target) {
  var N = rec.length, kids = new Array(N), i;
  for (i = 0; i < N; i++) kids[i] = [];
  for (i = 0; i < N; i++) if (rec[i] >= 0) kids[rec[i]].push(i);
  var out = [target], stack = [target];
  while (stack.length) { var u = stack.pop(); for (var j = 0; j < kids[u].length; j++) { out.push(kids[u][j]); stack.push(kids[u][j]); } }
  return out;
}
