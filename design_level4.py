"""离线设计工具：反向放置折线，输出可解的24×16关卡数据。"""
import json
import random

ROWS, COLS = 24, 16
DIRECTIONS = [(0, 1), (0, -1), (1, 0), (-1, 0)]
COLORS = [(255, 135, 142), (116, 205, 91), (128, 226, 196),
          (249, 177, 98), (255, 199, 55), (154, 137, 239),
          (102, 202, 194), (255, 128, 175), (97, 194, 229)]


def inside(p):
    return 0 <= p[0] < ROWS and 0 <= p[1] < COLS


def ray(head, direction):
    r, c = head
    dr, dc = direction
    r, c = r + dr, c + dc
    while inside((r, c)):
        yield r, c
        r, c = r + dr, c + dc


def design(seed):
    rng = random.Random(seed)
    occupied = set()
    arrows = []
    for attempt in range(16000):
        head = rng.randrange(ROWS), rng.randrange(COLS)
        direction = rng.choice(DIRECTIONS)
        if head in occupied or any(p in occupied for p in ray(head, direction)):
            continue
        dr, dc = direction
        first = head[0] - dr, head[1] - dc
        if not inside(first) or first in occupied:
            continue
        points = [head, first]
        target = rng.randint(5, 11)
        for _ in range(target - 2):
            choices = []
            for dy, dx in DIRECTIONS:
                p = points[-1][0] + dy, points[-1][1] + dx
                if inside(p) and p not in occupied and p not in points:
                    choices.append(p)
            if not choices:
                break
            points.append(rng.choice(choices))
        if len(points) < 4:
            continue
        # 自身不能堵住头部出射路径。
        if set(points[1:]) & set(ray(head, direction)):
            continue
        points.reverse()
        path = [points[0]]
        for a, b, c in zip(points, points[1:], points[2:]):
            if (b[0]-a[0], b[1]-a[1]) != (c[0]-b[0], c[1]-b[1]):
                path.append(b)
        path.append(points[-1])
        occupied.update(points)
        arrows.append({'path': path, 'color': COLORS[len(arrows) % len(COLORS)]})
    owners = {p: i for i, a in enumerate(arrows) for p in expand(a['path'])}
    dependencies = []
    for i, a in enumerate(arrows):
        prev, head = a['path'][-2:]
        d = ((head[0]>prev[0])-(head[0]<prev[0]), (head[1]>prev[1])-(head[1]<prev[1]))
        dependencies.append({owners[p] for p in ray(head,d) if p in owners and owners[p]!=i})
    depth = {}
    for i in reversed(range(len(arrows))):
        depth[i] = 1 + max((depth[j] for j in dependencies[i]), default=0)
    safe = sum(not d for d in dependencies)
    return arrows, (len(arrows), len(occupied), safe, max(depth.values()))


def expand(path):
    for a, b in zip(path, path[1:]):
        dr = (b[0]>a[0])-(b[0]<a[0])
        dc = (b[1]>a[1])-(b[1]<a[1])
        p = a
        yield p
        while p != b:
            p = p[0]+dr, p[1]+dc
            yield p


def refine(arrows):
    """在同一组折线路径上搜索更长的解锁依赖链。"""
    owners = {p: i for i, a in enumerate(arrows) for p in expand(a['path'])}
    options = []
    for i, a in enumerate(arrows):
        pair = []
        for path in (a['path'], list(reversed(a['path']))):
            prev, head = path[-2:]
            d = ((head[0]>prev[0])-(head[0]<prev[0]), (head[1]>prev[1])-(head[1]<prev[1]))
            seen = {owners[p] for p in ray(head, d) if p in owners}
            pair.append(None if i in seen else seen)
        options.append(pair)

    def score(flags):
        deps = [options[i][flag] for i, flag in enumerate(flags)]
        if any(d is None for d in deps):
            return -10000
        left = set(range(len(deps)))
        depth = {}
        initial = sum(not d for d in deps)
        while left:
            safe = [i for i in left if not (deps[i] & left)]
            if not safe:
                return -10000
            for i in safe:
                depth[i] = 1 + max((depth[j] for j in deps[i]), default=0)
                left.remove(i)
        return max(depth.values()) * 6 - initial * 8

    rng = random.Random(24016)
    flags = [0] * len(arrows)
    best = flags[:]
    current = best_score = score(flags)
    for _ in range(6000):
        i = rng.randrange(len(flags))
        trial = flags[:]
        trial[i] = 1 - trial[i]
        value = score(trial)
        if value >= current or (value > -10000 and rng.random() < .03):
            flags, current = trial, value
        if current > best_score:
            best, best_score = flags[:], current
    for i, flag in enumerate(best):
        if flag:
            arrows[i]['path'].reverse()
    return arrows


def solvable(arrows):
    owners = {p: i for i, a in enumerate(arrows) for p in expand(a['path'])}
    deps = []
    for i, a in enumerate(arrows):
        prev, head = a['path'][-2:]
        direction = ((head[0]>prev[0])-(head[0]<prev[0]),
                     (head[1]>prev[1])-(head[1]<prev[1]))
        seen = {owners[p] for p in ray(head, direction) if p in owners}
        if i in seen:
            return False
        deps.append(seen)
    left = set(range(len(arrows)))
    while left:
        safe = {i for i in left if not deps[i] & left}
        if not safe:
            return False
        left -= safe
    return True


def densify(arrows):
    """补入空白区域的短折线，并延长尾部吸收孤立空点。"""
    rng = random.Random(384)
    for phase in range(3):
        occupied = set().union(*(set(expand(a['path'])) for a in arrows))
        for _ in range(4500):
            free = sorted(set((r, c) for r in range(ROWS) for c in range(COLS)) - occupied)
            if not free:
                break
            points = [rng.choice(free)]
            for step in range(rng.randint(2, 6)):
                choices = [(points[-1][0]+dr, points[-1][1]+dc) for dr, dc in DIRECTIONS]
                choices = [p for p in choices if inside(p) and p not in occupied and p not in points]
                if not choices:
                    break
                points.append(rng.choice(choices))
            if len(points) < 2:
                continue
            candidate = {'path': points, 'color': COLORS[len(arrows) % len(COLORS)]}
            if solvable(arrows + [candidate]):
                arrows.append(candidate)
                occupied.update(points)
        # 短线插入后，尝试把余下空点接到相邻箭头尾部。
        changed = True
        while changed:
            changed = False
            for arrow in arrows:
                tail = arrow['path'][0]
                directions = DIRECTIONS[:]
                rng.shuffle(directions)
                for dr, dc in directions:
                    p = tail[0]+dr, tail[1]+dc
                    if not inside(p) or p in occupied:
                        continue
                    arrow['path'].insert(0, p)
                    if solvable(arrows):
                        occupied.add(p)
                        changed = True
                        break
                    arrow['path'].pop(0)
    return arrows


if __name__ == '__main__':
    candidates = [design(seed) for seed in range(16)]
    arrows, metrics = max(candidates, key=lambda item: item[1][3]*4 + item[1][0] - item[1][2]*3)
    print(json.dumps({'arrows': refine(densify(refine(arrows))), 'metrics_before_refine': metrics}))
