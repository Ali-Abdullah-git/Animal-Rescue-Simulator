import heapq
import math

from interfaces import Problem

map_5x5 = [
    [2, 0, 0, 1, 3],
    [0, 1, 0, 1, 0],
    [0, 1, 0, 0, 0],
    [1, 1, 0, 1, 0],
    [3, 0, 0, 0, 5],
]

map_7x7 = [
    [2, 0, 0, 0, 1, 0, 5],
    [1, 1, 0, 1, 1, 0, 1],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 0, 1, 1, 0],
    [0, 0, 0, 0, 0, 1, 0],
    [1, 1, 0, 1, 0, 0, 0],
    [3, 0, 0, 0, 1, 0, 3],
]

map_9x9 = [
    [2, 0, 0, 1, 0, 0, 0, 1, 3],
    [0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 0, 0, 1, 0, 0, 0],
    [1, 1, 0, 1, 0, 1, 1, 1, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 5],
    [0, 1, 1, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 1, 0, 0, 0],
    [1, 1, 0, 1, 1, 1, 0, 1, 0],
    [3, 0, 0, 1, 0, 0, 0, 0, 3],
]

MAP_TEMPLATES = {5: map_5x5, 7: map_7x7, 9: map_9x9}

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def a_star(map_instance, start, goal):
    open_heap = [(heuristic(start, goal), 0, start)]
    best = {start: 0}
    parent = {start: None}
    closed = set()
    while open_heap:
        _, cost, node = heapq.heappop(open_heap)
        if node in closed:
            continue
        if node == goal:
            path = []
            while node is not None:
                path.append(node)
                node = parent[node]
            path.reverse()
            return cost, path
        closed.add(node)
        for nxt, step in map_instance.neighbors(node):
            new_cost = cost + step
            if new_cost < best.get(nxt, math.inf):
                best[nxt] = new_cost
                parent[nxt] = node
                heapq.heappush(open_heap, (new_cost + heuristic(nxt, goal), new_cost, nxt))
    return math.inf, None


def points_of_interest(problem):
    points = [problem.map_instance.base_node]
    points += [a.node for a in problem.animals]
    points += [s.node for s in problem.shelters]
    return list(dict.fromkeys(points))


def build_distance_matrix(problem):
    points = points_of_interest(problem)
    dist = {p: {} for p in points}
    for i, a in enumerate(points):
        dist[a][a] = 0
        for b in points[i + 1:]:
            cost, _ = a_star(problem.map_instance, a, b)
            dist[a][b] = cost
            dist[b][a] = cost
    return dist