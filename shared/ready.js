/* Bridge readiness: ONE shared promise for the whole page.
 *
 * window.aihydro is injected by the AI-Hydro preview bridge, sometimes after the module's own
 * scripts have run. Every call to whenReady() waits on the same promise, so at most one 50 ms
 * poll exists per page no matter how many handlers call it (the old per-call setInterval leaked
 * one timer per call when no bridge was present). The poll stops after about 10 s: outside the
 * preview (a plain browser) the bridge never arrives and the callbacks never run, which is the
 * intended standalone behaviour. Modules must render without the bridge.
 *
 * Single source of truth: shared/ready.js (inlined by scripts/build_modules.py).
 */
function aihydroReady() {
  var st = window.__aihydroReadyState || (window.__aihydroReadyState = {});
  if (!st.promise) st.promise = new Promise(function (resolve) { st.resolve = resolve; });
  if (window.aihydro) { st.resolve(window.aihydro); return st.promise; }
  if (!st.timer) {                       /* at most one poll; a later call re-arms it after a time-out */
    var tries = 0;
    st.timer = setInterval(function () {
      if (window.aihydro) { clearInterval(st.timer); st.timer = null; st.resolve(window.aihydro); }
      else if (++tries >= 200) { clearInterval(st.timer); st.timer = null; }
    }, 50);
  }
  return st.promise;
}
function whenReady(fn) {
  aihydroReady().then(function () { fn(); });
}
