/* Plain-SVG sketch of GeoJSON points and polygon outlines on a longitude/latitude plot.
 *
 * Used where a module shows a Leaflet map through the AI-Hydro bridge: outside the preview there
 * is no bridge and no basemap, so the same features are drawn here with labelled axes. It draws
 * only the features it is given (no coastlines or other geometry is invented), scales longitude by
 * cos(latitude) so shapes are not distorted, and labels every point in text.
 * Single source of truth: shared/geosketch.js (inlined by scripts/build_modules.py).
 */
var HydroGeoSketch = (function () {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg';

  function mk(tag, attrs, text) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (text !== undefined) e.textContent = text;
    return e;
  }

  function niceStep(span) {
    var raw = span / 4, p = Math.pow(10, Math.floor(Math.log(raw) / Math.LN10)), m = raw / p;
    return (m < 1.5 ? 1 : m < 3.5 ? 2 : m < 7.5 ? 5 : 10) * p;
  }

  /* fc: GeoJSON FeatureCollection. Returns the <svg>. opts: {width, height, label} */
  function draw(container, fc, opts) {
    opts = opts || {};
    var W = opts.width || 640, H = opts.height || 340, pad = { l: 56, r: 24, t: 18, b: 40 };
    var pts = [], rings = [];
    fc.features.forEach(function (f) {
      var g = f.geometry;
      if (g.type === 'Point') pts.push({ c: g.coordinates, p: f.properties || {} });
      else if (g.type === 'Polygon') rings.push({ c: g.coordinates[0], p: f.properties || {} });
    });
    var all = pts.map(function (q) { return q.c; });
    rings.forEach(function (r) { all = all.concat(r.c); });
    var x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    all.forEach(function (c) { x0 = Math.min(x0, c[0]); x1 = Math.max(x1, c[0]); y0 = Math.min(y0, c[1]); y1 = Math.max(y1, c[1]); });
    var px = (x1 - x0 || 1) * 0.12, py = (y1 - y0 || 1) * 0.15;
    x0 -= px; x1 += px; y0 -= py; y1 += py;
    var kx = Math.cos(((y0 + y1) / 2) * Math.PI / 180);
    var pw = W - pad.l - pad.r, ph = H - pad.t - pad.b;
    var s = Math.min(pw / ((x1 - x0) * kx), ph / (y1 - y0));
    var ox = pad.l + (pw - (x1 - x0) * kx * s) / 2, oy = pad.t + (ph - (y1 - y0) * s) / 2;
    function X(lon) { return ox + (lon - x0) * kx * s; }
    function Y(lat) { return oy + (y1 - lat) * s; }

    var svg = mk('svg', { viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'class': 'geosketch', style: 'width:100%;height:auto;max-width:' + W + 'px;display:block;margin:0 auto;',
                          'aria-label': opts.label || 'Locations plotted by longitude and latitude' });
    svg.appendChild(mk('rect', { x: 0, y: 0, width: W, height: H, fill: '#0f0f1e', rx: 12 }));
    var sx = niceStep(x1 - x0), sy = niceStep(y1 - y0), v;
    for (v = Math.ceil(x0 / sx) * sx; v <= x1; v += sx) {
      svg.appendChild(mk('line', { x1: X(v), y1: pad.t, x2: X(v), y2: H - pad.b, stroke: 'rgba(125,211,252,0.15)' }));
      svg.appendChild(mk('text', { x: X(v), y: H - pad.b + 16, 'text-anchor': 'middle', 'font-size': 11, fill: '#94a3b8', 'font-family': 'JetBrains Mono,monospace' }, v.toFixed(sx < 1 ? 1 : 0) + '°'));
    }
    for (v = Math.ceil(y0 / sy) * sy; v <= y1; v += sy) {
      svg.appendChild(mk('line', { x1: pad.l, y1: Y(v), x2: W - pad.r, y2: Y(v), stroke: 'rgba(125,211,252,0.15)' }));
      svg.appendChild(mk('text', { x: pad.l - 6, y: Y(v) + 4, 'text-anchor': 'end', 'font-size': 11, fill: '#94a3b8', 'font-family': 'JetBrains Mono,monospace' }, v.toFixed(sy < 1 ? 1 : 0) + '°'));
    }
    svg.appendChild(mk('text', { x: W / 2, y: H - 6, 'text-anchor': 'middle', 'font-size': 11, fill: '#7dd3fc' }, 'longitude'));
    svg.appendChild(mk('text', { x: 14, y: H / 2, 'text-anchor': 'middle', 'font-size': 11, fill: '#7dd3fc', transform: 'rotate(-90 14 ' + H / 2 + ')' }, 'latitude'));
    rings.forEach(function (r) {
      svg.appendChild(mk('polygon', { points: r.c.map(function (c) { return X(c[0]) + ',' + Y(c[1]); }).join(' '),
        fill: 'rgba(0,163,255,0.18)', stroke: '#00DDFF', 'stroke-width': 2, 'stroke-dasharray': '6 3' }));
    });
    pts.forEach(function (q) {
      var cx = X(q.c[0]), cy = Y(q.c[1]), right = cx < W * 0.62;
      svg.appendChild(mk('circle', { cx: cx, cy: cy, r: 6, fill: q.p.color || q.p['marker-color'] || '#00DDFF', stroke: '#fff', 'stroke-width': 1.5 }));
      var lab = q.p.label || (q.p.name ? String(q.p.name).split(' \u00b7 ')[0] : '');
      if (lab) svg.appendChild(mk('text', { x: cx + (right ? 11 : -11), y: cy + 4, 'text-anchor': right ? 'start' : 'end', 'font-size': 12, 'font-weight': 700, fill: '#e2e8f0', 'font-family': 'JetBrains Mono,monospace' }, lab));
    });
    container.appendChild(svg);
    return svg;
  }
  return { draw: draw };
})();
