# D8 terrain routing: priority-flood fill, steepest-descent direction
# (drop / distance), flow accumulation, slope and TWI.  Twin of shared/d8.js.
# Priority-flood with epsilon (Barnes, Lehman & Mulla, 2014), seeded only at the
# outlet so every cell has a strictly descending path to it.
import heapq, math
D8_DIRS = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]  # N NE E SE S SW W NW


def d8_lowest_edge(dem):
    R, C = len(dem), len(dem[0])
    best = None
    for r in range(R):
        for c in range(C):
            if r in (0, R - 1) or c in (0, C - 1):
                if best is None or dem[r][c] < dem[best[0]][best[1]]:
                    best = (r, c)
    return best


def d8_fill(dem, outlet, epsilon=None):
    R, C = len(dem), len(dem[0])
    flat = [float(dem[r][c]) for r in range(R) for c in range(C)]
    eps = epsilon if epsilon is not None else 1e-5 * ((max(flat) - min(flat)) or 1.0)
    out, seen, heap, counter = flat[:], [False] * (R * C), [], 0
    o = outlet[0] * C + outlet[1]
    seen[o] = True
    heapq.heappush(heap, (out[o], counter, o)); counter += 1
    while heap:
        _, _, idx = heapq.heappop(heap)
        er, ec = divmod(idx, C)
        for dr, dc in D8_DIRS:
            nr, nc = er + dr, ec + dc
            if nr < 0 or nc < 0 or nr >= R or nc >= C:
                continue
            ni = nr * C + nc
            if seen[ni]:
                continue
            seen[ni] = True
            if out[ni] <= out[idx] + eps:
                out[ni] = out[idx] + eps
            heapq.heappush(heap, (out[ni], counter, ni)); counter += 1
    return out


def d8_directions(filled, R, C, cell, outlet):
    o = outlet[0] * C + outlet[1]
    rec = [-1] * (R * C)
    for r in range(R):
        for c in range(C):
            i = r * C + c
            if i == o:
                continue
            best, bi = 0.0, -1
            for dr, dc in D8_DIRS:
                nr, nc = r + dr, c + dc
                if nr < 0 or nc < 0 or nr >= R or nc >= C:
                    continue
                dist = cell * math.sqrt(2) if (dr and dc) else cell
                g = (filled[i] - filled[nr * C + nc]) / dist
                if g > best:
                    best, bi = g, nr * C + nc
            rec[i] = bi
    return rec


def d8_accumulation(filled, rec):
    order = sorted(range(len(filled)), key=lambda i: (-filled[i], i))
    acc = [1] * len(filled)
    for i in order:
        if rec[i] >= 0:
            acc[rec[i]] += acc[i]
    return acc


def d8_route(dem, cell, outlet=None, tan_floor=1e-3, epsilon=None):
    R, C = len(dem), len(dem[0])
    outlet = outlet or d8_lowest_edge(dem)
    filled = d8_fill(dem, outlet, epsilon)
    rec = d8_directions(filled, R, C, cell, outlet)
    acc = d8_accumulation(filled, rec)
    tanb, twi = [], []
    for i in range(R * C):
        if rec[i] < 0:
            t = tan_floor
        else:
            r, c = divmod(i, C); nr, nc = divmod(rec[i], C)
            dist = cell * math.sqrt(2) if (r != nr and c != nc) else cell
            t = max((filled[i] - filled[rec[i]]) / dist, tan_floor)
        tanb.append(t)
        twi.append(math.log(acc[i] * cell / t))  # a = A/w = acc*cell^2/cell
    return dict(R=R, C=C, cell=cell, outlet=outlet, filled=filled, rec=rec,
                acc=acc, tan_beta=tanb, twi=twi, tan_floor=tan_floor)


def d8_path(rec, start):
    path, i = [start], start
    for _ in range(len(rec)):
        if rec[i] < 0:
            break
        i = rec[i]; path.append(i)
    return path
