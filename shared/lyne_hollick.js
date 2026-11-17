/* Lyne–Hollick recursive digital filter, standard multi-pass form.
 *
 * Each pass filters the baseflow produced by the PREVIOUS pass (not the raw
 * series), alternating forward / backward / forward (Ladson et al., 2013; the
 * same convention as CAMELS). The series is reflected at both ends before
 * filtering so the recursion has a spin-up and the edges are not biased.
 *
 *   f_t = alpha * f_{t-1} + (1 + alpha) / 2 * (Q_t - Q_{t-1})     (quickflow)
 *   f_t = max(f_t, 0)                                              (carried on)
 *   b_t = max(Q_t - f_t, 0)                                        (baseflow)
 *
 * Single source of truth: shared/lyne_hollick.js (and its twin lyne_hollick.py).
 * scripts/build_modules.py inlines this text into every module that uses it.
 */
function lyneHollick(Q, alpha, passes, reflect) {
  if (alpha === undefined) alpha = 0.925;
  if (passes === undefined) passes = 3;
  if (reflect === undefined) reflect = 30;
  var n = Q.length;
  var r = Math.max(0, Math.min(reflect, n - 1));
  var ext = [], i;
  for (i = r; i >= 1; i--) ext.push(Q[i]);
  for (i = 0; i < n; i++) ext.push(Q[i]);
  for (i = 1; i <= r; i++) ext.push(Q[n - 1 - i]);
  var m = ext.length, cur = ext;
  var k = (1 + alpha) / 2;
  for (var p = 0; p < passes; p++) {
    var b = new Array(m), f = 0;
    if (p % 2 === 0) {
      b[0] = cur[0];
      for (i = 1; i < m; i++) {
        f = alpha * f + k * (cur[i] - cur[i - 1]);
        if (f < 0) f = 0;
        b[i] = Math.max(cur[i] - f, 0);
      }
    } else {
      b[m - 1] = cur[m - 1];
      for (i = m - 2; i >= 0; i--) {
        f = alpha * f + k * (cur[i] - cur[i + 1]);
        if (f < 0) f = 0;
        b[i] = Math.max(cur[i] - f, 0);
      }
    }
    cur = b;
  }
  return cur.slice(r, r + n);
}
function baseflowIndex(Q, base) {
  var sq = 0, sb = 0;
  for (var i = 0; i < Q.length; i++) { sq += Q[i]; sb += base[i]; }
  return sq > 0 ? sb / sq : NaN;
}
