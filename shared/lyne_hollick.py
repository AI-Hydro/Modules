# Lyne–Hollick recursive digital filter, multi-pass with reflection; initial quickflow 0 for each pass.
# Each pass filters the baseflow of the PREVIOUS pass (forward / backward /
# forward; after Ladson et al., 2013), with the series reflected 30 steps at both ends.
#   f_t = alpha*f_{t-1} + (1+alpha)/2*(Q_t - Q_{t-1});  f_t = max(f_t, 0)
#   b_t = max(Q_t - f_t, 0)
# Single source of truth: shared/lyne_hollick.py (twin of lyne_hollick.js).
def lyne_hollick(Q, alpha=0.925, passes=3, reflect=30):
    Q = [float(v) for v in Q]
    n = len(Q)
    r = max(0, min(reflect, n - 1))
    cur = Q[1:r + 1][::-1] + Q + (Q[n - 1 - r:n - 1][::-1] if r else [])
    m, k = len(cur), (1.0 + alpha) / 2.0
    for p in range(passes):
        b, f = [0.0] * m, 0.0
        if p % 2 == 0:
            b[0] = cur[0]
            for i in range(1, m):
                f = max(alpha * f + k * (cur[i] - cur[i - 1]), 0.0)
                b[i] = max(cur[i] - f, 0.0)
        else:
            b[m - 1] = cur[m - 1]
            for i in range(m - 2, -1, -1):
                f = max(alpha * f + k * (cur[i] - cur[i + 1]), 0.0)
                b[i] = max(cur[i] - f, 0.0)
        cur = b
    return cur[r:r + n]


def baseflow_index(Q, base):
    sq = float(sum(Q))
    return float(sum(base)) / sq if sq > 0 else float("nan")
