from interfaces import Config, Solution
from instance import generate_instance
from distance import build_distance_matrix
from csp import solve_assignment
from search import optimize_routes


def main():
    config = Config(map_size=5, num_animals=4, seed=42)
    problem = generate_instance(config)
    dist = build_distance_matrix(problem)

    assignment = solve_assignment(problem, dist)
    if assignment is None:
        print("No feasible shelter assignment exists for this instance.")
        return

    routes = optimize_routes(problem, assignment, dist)
    solution = Solution(assignment, routes)

    if not problem.is_feasible(solution):
        print("Solution is infeasible.")
        return

    cost = problem.evaluate(solution, dist)
    print(f"distance:       {cost.distance}")
    print(f"severity delay: {cost.severity_delay}")
    print(f"overflow count: {cost.overflow_count}")
    print(f"total cost:     {cost.total}")


if __name__ == "__main__":
    main()