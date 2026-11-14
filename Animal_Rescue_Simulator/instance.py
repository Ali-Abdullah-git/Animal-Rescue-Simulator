import math
import random

from maps import MAP_TEMPLATES
from interfaces import ROAD, SHELTER, Animal, Map, Problem, Shelter, Vehicle

SPECIES = ("dog", "cat", "bird")


def reachable_from(map_instance, start):
    seen = {start}
    stack = [start]
    while stack:
        node = stack.pop()
        for nxt, _ in map_instance.neighbors(node):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def load_grid(map_size):
    if map_size not in MAP_TEMPLATES:
        raise ValueError(f"Unsupported map_size: {map_size}")
    return MAP_TEMPLATES[map_size]


def find_shelter_cells(map_instance, grid):
    return [
        (r, c)
        for r in range(map_instance.rows)
        for c in range(map_instance.cols)
        if grid[r][c] == SHELTER
    ]


def generate_instance(config):
    rng = random.Random(config.seed)
    grid = load_grid(config.map_size)
    map_instance = Map(grid)

    reachable = reachable_from(map_instance, map_instance.base_node)

    if map_instance.overflow_node is None or map_instance.overflow_node not in reachable:
        raise ValueError("Overflow site is missing or unreachable from base")

    cells = find_shelter_cells(map_instance, grid)
    if not cells:
        raise ValueError("Map template has no shelter cells")
    if any(cell not in reachable for cell in cells):
        raise ValueError("A shelter cell is unreachable from base")

    road_cells = sorted(node for node in reachable if grid[node[0]][node[1]] == ROAD)
    if config.num_animals > len(road_cells):
        raise ValueError("More animals than reachable road cells")

    animal_nodes = rng.sample(road_cells, config.num_animals)
    animals = [
        Animal(i, rng.choice(SPECIES), rng.randint(1, 3), node, True)
        for i, node in enumerate(animal_nodes)
    ]

    accepted_sets = [
        {sp for sp in SPECIES if rng.random() < 0.5} for _ in cells
    ]
    for sp in SPECIES:
        if not any(sp in accepted for accepted in accepted_sets):
            rng.choice(accepted_sets).add(sp)

    max_cap = math.ceil(2 * config.num_animals / len(cells))
    capacities = [rng.randint(1, max_cap) for _ in cells]

    shelters = [
        Shelter(i, node, accepted_sets[i], capacities[i])
        for i, node in enumerate(cells)
    ]
    shelters.append(
        Shelter(len(shelters), map_instance.overflow_node, SPECIES, 0, is_overflow=True)
    )

    vehicles = [
        Vehicle(v, config.vehicle_capacity, map_instance.base_node)
        for v in range(config.num_vehicles)
    ]

    return Problem(map_instance, animals, shelters, vehicles, config)



















# import math
# import random

# from maps import MAP_TEMPLATES
# from interfaces import ROAD, SHELTER, Animal, Map, Problem, Shelter, Vehicle

# SPECIES = ("dog", "cat", "bird")


# def reachable_from(map_instance, start):
#     seen = {start}
#     stack = [start]
#     while stack:
#         node = stack.pop()
#         for nxt, _ in map_instance.neighbors(node):
#             if nxt not in seen:
#                 seen.add(nxt)
#                 stack.append(nxt)
#     return seen


# def generate_instance(config):
#     rng = random.Random(config.seed)
#     grid = MAP_TEMPLATES[config.map_size]
#     map_instance = Map(grid)

#     reachable = reachable_from(map_instance, map_instance.base_node)
#     road_cells = sorted(n for n in reachable if grid[n[0]][n[1]] == ROAD)
#     if config.num_animals > len(road_cells):
#         raise ValueError("More animals than reachable road cells")

#     animal_nodes = rng.sample(road_cells, config.num_animals)
#     animals = [
#         Animal(i, rng.choice(SPECIES), rng.randint(1, 3), node, True)
#         for i, node in enumerate(animal_nodes)
#     ]

#     shelter_cells = [
#         (r, c)
#         for r in range(map_instance.rows)
#         for c in range(map_instance.cols)
#         if grid[r][c] == SHELTER
#     ]
#     if len(shelter_cells) != config.num_shelters:
#         raise ValueError("config.num_shelters does not match the map template")

#     accepted_sets = [{sp for sp in SPECIES if rng.random() < 0.5} for _ in shelter_cells]
#     for sp in SPECIES:
#         if not any(sp in acc for acc in accepted_sets):
#             rng.choice(accepted_sets).add(sp)

#     per_shelter = math.ceil(config.num_animals / len(shelter_cells))
#     shelters = [
#         Shelter(i, node, accepted_sets[i], per_shelter + rng.randint(0, 1))
#         for i, node in enumerate(shelter_cells)
#     ]

#     overflow = Shelter(
#         len(shelters), map_instance.overflow_node, SPECIES, 0, is_overflow=True
#     )
#     shelters.append(overflow)

#     vehicles = [
#         Vehicle(v, config.vehicle_capacity, map_instance.base_node)
#         for v in range(config.num_vehicles)
#     ]

#     return Problem(map_instance, animals, shelters, vehicles, config)