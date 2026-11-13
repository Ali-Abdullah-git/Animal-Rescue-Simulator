import math

ReadMap = {"Road": 0, "Wall": 1, "Base": 2, "Shelter": 3, "Animal": 4, "Overflow": 5}
ROAD = ReadMap["Road"]
WALL = ReadMap["Wall"]
BASE = ReadMap["Base"]
SHELTER = ReadMap["Shelter"]
OVERFLOW = ReadMap["Overflow"]

PICKUP = "PICKUP"
DROP = "DROP"
RETURN = "RETURN"


class Config:
    def __init__(self, map_size=5, num_vehicles=1, capacity_mode="GENERIC", w_dist=1.0, w_sev=1.0, w_over=1000.0, seed=42, num_animals=4, vehicle_capacity=5, pickup_time=1.0, drop_time=1.0):
        self.map_size = map_size
        self.num_vehicles = num_vehicles
        self.capacity_mode = capacity_mode
        self.w_dist = w_dist
        self.w_sev = w_sev
        self.w_over = w_over
        self.seed = seed
        self.num_animals = num_animals
        self.vehicle_capacity = vehicle_capacity
        self.pickup_time = pickup_time
        self.drop_time = drop_time


class Map:
    def __init__(self, grid):
        self.grid = [row[:] for row in grid]
        self.rows = len(self.grid)
        self.cols = len(self.grid[0])
        self.base_node = self._find_first(BASE)
        self.overflow_node = self._find_first(OVERFLOW)
        self.nodes = []
        self.edges = {}
        self._build_graph()

    def _find_first(self, value):
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == value:
                    return (r, c)
        return None

    def _get_step_cost(self, node):
        return 1

    def _build_graph(self):
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] != WALL:
                    self.nodes.append((r, c))
        for node in self.nodes:
            self.edges[node] = []
            for dr, dc in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                neighbor = (node[0] + dr, node[1] + dc)
                if 0 <= neighbor[0] < self.rows and 0 <= neighbor[1] < self.cols and self.grid[neighbor[0]][neighbor[1]] != WALL:
                    self.edges[node].append((neighbor, self._get_step_cost(neighbor)))

    def node_count(self):
        return len(self.nodes)

    def neighbors(self, node):
        return self.edges.get(node, [])


class Animal:
    def __init__(self, id, species, severity, node, needs_shelter=True):
        self.id = id
        self.species = species
        self.severity = severity
        self.node = node
        self.needs_shelter = needs_shelter


class Shelter:
    def __init__(self, id, node, accepted_species, capacity, is_overflow=False):
        self.id = id
        self.node = node
        self.accepted_species = frozenset(accepted_species)
        self.is_overflow = is_overflow
        self.initial_capacity = capacity
        self.remaining_capacity = capacity

    def accepts_species(self, species):
        return self.is_overflow or species in self.accepted_species

    def can_accept(self, animal):
        return self.accepts_species(animal.species) and self.remaining(animal) > 0

    def remaining(self, animal):
        if self.is_overflow:
            return math.inf
        return self.remaining_capacity

    def place(self, animal):
        if not self.is_overflow:
            self.remaining_capacity -= 1

    def release(self, animal):
        if not self.is_overflow:
            self.remaining_capacity += 1

    def reset(self):
        self.remaining_capacity = self.initial_capacity

    def clone(self):
        cloned = Shelter(self.id, self.node, self.accepted_species, self.initial_capacity, self.is_overflow)
        cloned.remaining_capacity = self.remaining_capacity
        return cloned


class Vehicle:
    def __init__(self, id, capacity, base_node):
        self.id = id
        self.capacity = capacity
        self.base_node = base_node


class Event:
    def __init__(self, kind, animal_id=None):
        self.kind = kind
        self.animal_id = animal_id


class Problem:
    def __init__(self, map_instance, animals, shelters, vehicles, config):
        self.map_instance = map_instance
        self.animals = animals
        self.shelters = shelters
        self.vehicles = vehicles
        self.config = config
        self.animal_map = {a.id: a for a in animals}
        self.shelter_map = {s.id: s for s in shelters}

    def walk(self, route, assignment, dist):
        base = self.map_instance.base_node
        loc = base
        clock = 0.0
        distance = 0.0
        delay = 0.0
        for event in route:
            if event.kind == PICKUP:
                target = self.animal_map[event.animal_id].node
            elif event.kind == DROP:
                target = self.shelter_map[assignment[event.animal_id]].node
            else:
                target = base
            step = dist[loc][target]
            clock += step
            distance += step
            loc = target
            if event.kind == PICKUP:
                clock += self.config.pickup_time
            elif event.kind == DROP:
                clock += self.config.drop_time
                delay += self.animal_map[event.animal_id].severity * clock
        return distance, delay

    def route_cost(self, route, assignment, dist):
        distance, delay = self.walk(route, assignment, dist)
        return self.config.w_dist * distance + self.config.w_sev * delay

    def evaluate(self, solution, dist):
        distance = 0.0
        delay = 0.0
        for route in solution.routes:
            d, s = self.walk(route, solution.assignment, dist)
            distance += d
            delay += s
        overflow = sum(1 for sid in solution.assignment.values() if self.shelter_map[sid].is_overflow)
        total = self.config.w_dist * distance + self.config.w_sev * delay + self.config.w_over * overflow
        return CostBreakdown(distance, delay, overflow, total)

    def is_feasible(self, solution):
        needing = {a.id for a in self.animals if a.needs_shelter}
        if set(solution.assignment) != needing:
            return False
        counts = {}
        for aid, sid in solution.assignment.items():
            shelter = self.shelter_map.get(sid)
            if shelter is None or not shelter.accepts_species(self.animal_map[aid].species):
                return False
            if not shelter.is_overflow:
                counts[sid] = counts.get(sid, 0) + 1
                if counts[sid] > shelter.initial_capacity:
                    return False
        if len(solution.routes) != len(self.vehicles):
            return False
        delivered = []
        for vehicle, route in zip(self.vehicles, solution.routes):
            if not route or route[-1].kind != RETURN:
                return False
            load = 0
            on_board = set()
            picked = set()
            for event in route[:-1]:
                if event.kind == PICKUP:
                    if event.animal_id not in needing or event.animal_id in picked:
                        return False
                    if load >= vehicle.capacity:
                        return False
                    picked.add(event.animal_id)
                    on_board.add(event.animal_id)
                    load += 1
                elif event.kind == DROP:
                    if event.animal_id not in on_board:
                        return False
                    on_board.remove(event.animal_id)
                    load -= 1
                    delivered.append(event.animal_id)
                else:
                    return False
            if on_board:
                return False
        return len(delivered) == len(needing) and set(delivered) == needing


class Solution:
    def __init__(self, assignment=None, routes=None):
        self.assignment = dict(assignment) if assignment is not None else {}
        self.routes = [list(route) for route in routes] if routes is not None else []

    def copy(self):
        return Solution(self.assignment, self.routes)


class CostBreakdown:
    def __init__(self, distance=0.0, severity_delay=0.0, overflow_count=0, total=0.0):
        self.distance = distance
        self.severity_delay = severity_delay
        self.overflow_count = overflow_count
        self.total = total


















# import random
# import math

# ReadMap = {"Road": 0, "Wall": 1, "Base": 2, "Shelter": 3, "Animal": 4, "Overflow": 5}
# ROAD = ReadMap["Road"]
# WALL = ReadMap["Wall"]
# BASE = ReadMap["Base"]
# SHELTER = ReadMap["Shelter"]
# OVERFLOW = ReadMap["Overflow"]

# class Config:
#     def __init__(self, num_vehicles=1, capacity_mode="GENERIC", w_dist=1.0, w_sev=1.0, w_over=1000.0, seed=42, num_animals=8, num_shelters=3, vehicle_capacity=5):
#         self.num_vehicles = num_vehicles
#         self.capacity_mode = capacity_mode
#         self.w_dist = w_dist
#         self.w_sev = w_sev
#         self.w_over = w_over
#         self.seed = seed
#         self.num_animals = num_animals
#         self.num_shelters = num_shelters
#         self.vehicle_capacity = vehicle_capacity


# class Map:
#     def __init__(self, grid):
#         self.grid = [row[:] for row in grid]
#         self.rows = len(self.grid)
#         self.cols = len(self.grid[0])
#         self.base_node = self._find_first(BASE)
#         self.overflow_node = self._find_first(OVERFLOW)
#         self.nodes = []
#         self.edges = {}
#         self._build_graph()

#     def _find_first(self, value):
#         for r in range(self.rows):
#             for c in range(self.cols):
#                 if self.grid[r][c] == value:
#                     return (r, c)
#         return None

#     def _get_step_cost(self, node):
#         return 1

#     def _build_graph(self):
#         for r in range(self.rows):
#             for c in range(self.cols):
#                 if self.grid[r][c] != WALL:
#                     self.nodes.append((r, c))
#         for node in self.nodes:
#             self.edges[node] = []
#             for dr, dc in ((1, 0), (0, 1), (-1, 0), (0, -1)):
#                 neighbor = (node[0] + dr, node[1] + dc)
#                 if 0 <= neighbor[0] < self.rows and 0 <= neighbor[1] < self.cols and self.grid[neighbor[0]][neighbor[1]] != WALL:
#                     self.edges[node].append((neighbor, self._get_step_cost(neighbor)))

#     def node_count(self):
#         return len(self.nodes)

#     def neighbors(self, node):
#         return self.edges.get(node, [])


# class Animal:
#     def __init__(self, id, species, severity, node, needs_shelter=True):
#         self.id = id
#         self.species = species
#         self.severity = severity
#         self.node = node
#         self.needs_shelter = needs_shelter


# class Shelter:
#     def __init__(self, id, node, accepted_species, capacity, is_overflow=False):
#         self.id = id
#         self.node = node
#         self.accepted_species = frozenset(accepted_species)
#         self.is_overflow = is_overflow
#         self.initial_capacity = capacity
#         self.remaining_capacity = capacity

#     def accepts_species(self, species):
#         return self.is_overflow or species in self.accepted_species

#     def can_accept(self, animal):
#         return self.accepts_species(animal.species) and self.remaining(animal) > 0

#     def remaining(self, animal):
#         if self.is_overflow:
#             return math.inf
#         return self.remaining_capacity

#     def place(self, animal):
#         if not self.is_overflow:
#             self.remaining_capacity -= 1

#     def release(self, animal):
#         if not self.is_overflow:
#             self.remaining_capacity += 1

#     def reset(self):
#         self.remaining_capacity = self.initial_capacity

#     def clone(self):
#         cloned = Shelter(self.id, self.node, self.accepted_species, self.initial_capacity, self.is_overflow)
#         cloned.remaining_capacity = self.remaining_capacity
#         return cloned


# class Vehicle:
#     def __init__(self, id, capacity, base_node):
#         self.id = id
#         self.capacity = capacity
#         self.base_node = base_node


# class Problem:
#     def __init__(self, map_instance, animals, shelters, vehicles, config):
#         self.map_instance = map_instance
#         self.animals = animals
#         self.shelters = shelters
#         self.vehicles = vehicles
#         self.config = config
#         self.animal_map = {a.id: a for a in animals}
#         self.shelter_map = {s.id: s for s in shelters}

#     def walk(self, route, assignment, dist):
#         time_now = 0.0
#         distance = 0.0
#         delay = 0.0
#         base = self.map_instance.base_node
#         for trip in route:
#             loc = base
#             for aid in trip.pickup_order:
#                 animal = self.animal_map[aid]
#                 d = dist[loc][animal.node]
#                 time_now += d
#                 distance += d
#                 delay += animal.severity * time_now
#                 loc = animal.node
#             for aid in trip.drop_order:
#                 shelter = self.shelter_map[assignment[aid]]
#                 d = dist[loc][shelter.node]
#                 time_now += d
#                 distance += d
#                 loc = shelter.node
#             d = dist[loc][base]
#             time_now += d
#             distance += d
#         return distance, delay

#     def route_cost(self, route, assignment, dist):
#         distance, delay = self.walk(route, assignment, dist)
#         return self.config.w_dist * distance + self.config.w_sev * delay

#     def evaluate(self, solution, dist):
#         distance = 0.0
#         delay = 0.0
#         for route in solution.routes:
#             d, s = self.walk(route, solution.assignment, dist)
#             distance += d
#             delay += s
#         overflow = sum(1 for sid in solution.assignment.values() if self.shelter_map[sid].is_overflow)
#         total = self.config.w_dist * distance + self.config.w_sev * delay + self.config.w_over * overflow
#         return CostBreakdown(distance, delay, overflow, total)

#     def is_feasible(self, solution):
#         counts = {}
#         for aid, sid in solution.assignment.items():
#             shelter = self.shelter_map[sid]
#             if not shelter.accepts_species(self.animal_map[aid].species):
#                 return False
#             if not shelter.is_overflow:
#                 counts[sid] = counts.get(sid, 0) + 1
#                 if counts[sid] > shelter.initial_capacity:
#                     return False
#         needing = {a.id for a in self.animals if a.needs_shelter}
#         if needing - set(solution.assignment):
#             return False
#         picked, dropped = set(), set()
#         for v_index, route in enumerate(solution.routes):
#             capacity = self.vehicles[v_index].capacity
#             for trip in route:
#                 if len(trip.drop_order) > capacity:
#                     return False
#                 if not set(trip.drop_order) <= set(trip.pickup_order):
#                     return False
#                 picked.update(trip.pickup_order)
#                 dropped.update(trip.drop_order)
#         return picked == set(self.animal_map) and dropped == needing


# class Solution:
#     def __init__(self, assignment=None, routes=None):
#         self.assignment = assignment if assignment is not None else {}
#         self.routes = routes if routes is not None else []


# class CostBreakdown:
#     def __init__(self, distance=0.0, severity_delay=0.0, overflow_count=0, total=0.0):
#         self.distance = distance
#         self.severity_delay = severity_delay
#         self.overflow_count = overflow_count
#         self.total = total