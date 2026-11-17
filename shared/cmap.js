/* Perceptually uniform, colour-vision-deficiency-safe sequential colour map (viridis, 17 anchors
 * sampled from matplotlib's viridis, CC0) plus a plain-canvas shaded-relief renderer.
 * Replaces red-green maps: lightness rises monotonically with the value, so the map reads in
 * greyscale and for every common form of colour blindness.
 * Single source of truth: shared/cmap.js (inlined by scripts/build_modules.py).
 */
var HydroCmap = (function () {
  'use strict';
  var STOPS = [[68,1,84], [72,24,106], [71,45,123], [66,64,134], [59,82,139], [51,99,141], [44,114,142], [38,130,142], [33,145,140], [31,160,136], [40,174,128], [63,188,115], [94,201,98], [132,212,75], [173,220,48], [216,226,25], [253,231,37]];
  function rgb(t) {
    t = Math.max(0, Math.min(1, t));
    var x = t * (STOPS.length - 1), i = Math.min(STOPS.length - 2, Math.floor(x)), f = x - i, a = STOPS[i], b = STOPS[i + 1];
    return [Math.round(a[0] + (b[0] - a[0]) * f), Math.round(a[1] + (b[1] - a[1]) * f), Math.round(a[2] + (b[2] - a[2]) * f)];
  }
  function css(t) { var c = rgb(t); return 'rgb(' + c[0] + ',' + c[1] + ',' + c[2] + ')'; }
  /* CSS linear-gradient for a legend bar */
  function gradient(dir) {
    return 'linear-gradient(' + (dir || 'to right') + ', ' + STOPS.map(function (s, i) { return 'rgb(' + s.join(',') + ') ' + (100 * i / (STOPS.length - 1)).toFixed(1) + '%'; }).join(', ') + ')';
  }
  /* Shaded relief of a DEM (array of rows) on a 2-D canvas; cell and zUnit are in the DEM's units. */
  function relief(canvas, dem, o) {
    o = o || {};
    var R = dem.length, C = dem[0].length, ctx = canvas.getContext('2d');
    var cw = canvas.width / C, ch = canvas.height / R, cell = o.cell || 30;
    var lo = Infinity, hi = -Infinity, r, c;
    for (r = 0; r < R; r++) for (c = 0; c < C; c++) { if (dem[r][c] < lo) lo = dem[r][c]; if (dem[r][c] > hi) hi = dem[r][c]; }
    var L = [-0.55, -0.55, 0.63];   /* light from the north-west, 45 degrees up */
    for (r = 0; r < R; r++) for (c = 0; c < C; c++) {
      var zx = (dem[r][Math.min(C - 1, c + 1)] - dem[r][Math.max(0, c - 1)]) / (2 * cell);
      var zy = (dem[Math.min(R - 1, r + 1)][c] - dem[Math.max(0, r - 1)][c]) / (2 * cell);
      var n = Math.sqrt(zx * zx + zy * zy + 1), shade = Math.max(0, (-zx * L[0] - zy * L[1] + L[2]) / n);
      var base = rgb((dem[r][c] - lo) / ((hi - lo) || 1)), k = 0.35 + 0.9 * shade;
      ctx.fillStyle = 'rgb(' + Math.min(255, Math.round(base[0] * k)) + ',' + Math.min(255, Math.round(base[1] * k)) + ',' + Math.min(255, Math.round(base[2] * k)) + ')';
      ctx.fillRect(c * cw, r * ch, cw + 0.5, ch + 0.5);
    }
    if (o.streams) {
      ctx.fillStyle = 'rgba(0,255,255,0.9)';
      for (r = 0; r < R; r++) for (c = 0; c < C; c++) if (o.streams(r, c)) ctx.fillRect(c * cw + cw * 0.25, r * ch + ch * 0.25, cw * 0.5, ch * 0.5);
    }
    if (o.outlet) {
      ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc((o.outlet.c + 0.5) * cw, (o.outlet.r + 0.5) * ch, Math.max(3, cw * 0.5), 0, Math.PI * 2); ctx.fill();
    }
  }
  return { rgb: rgb, css: css, gradient: gradient, relief: relief, STOPS: STOPS };
})();
