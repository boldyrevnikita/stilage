from collections import deque
from copy import deepcopy

from src.pallet import Pallet
from src.reference_book import ReferenceBook
from src.solution import Solution
from src.zone import AvailableZone, OccupiedZone, SpecialRoadZone
from state_machine import StateMachine


class PalletPacker:
    @classmethod
    def pack_pallets(cls, pallets: list[Pallet],
                     available_zones: list[AvailableZone],
                     occupied_zones: list[OccupiedZone],
                     special_road_zones: list[SpecialRoadZone]
                     ) -> Solution | None:
        reference_book = ReferenceBook()
        solutions_queue: deque[Solution] = deque()
        ready_solutions: list[Solution] = []

        pallets = deepcopy(pallets)
        available_zones = deepcopy(available_zones)
        occupied_zones = deepcopy(occupied_zones)
        special_road_zones = deepcopy(special_road_zones)

        state_machine = StateMachine(reference_book)

        solutions_queue.append(Solution(
            available_zones=available_zones,
            occupied_zones=occupied_zones,
            road_zones=special_road_zones,
            pallets=pallets,
            state=state_machine.get_initial_state())
        )

        while solutions_queue:
            current_solution = solutions_queue.popleft()
            state_machine.apply_action(current_solution)
            new_solutions = state_machine.choose_next_action(current_solution)
            new_solutions = state_machine.remove_invalid_solutions(
                new_solutions)
            transitional_solutions, end_solutions = (
                state_machine.extract_end_solutions(new_solutions))

            ready_solutions.extend(end_solutions)
            solutions_queue.extend(transitional_solutions)

            solutions_queue = cls.__prune_solutions(solutions_queue)

        return cls.__get_best_solution(ready_solutions)

    @staticmethod
    def __prune_solutions(solutions: deque[Solution]
                          ) -> deque[Solution]:
        # TODO: Implement pruning logic
        return solutions

    @classmethod
    def __get_best_solution(cls, solutions: list[Solution]
                            ) -> Solution | None:
        max_score = -1
        best_solution = None

        for solution in solutions:
            score = cls.__calculate_solution_score(solution)
            if score > max_score:
                max_score = score
                best_solution = solution

        return best_solution

    @staticmethod
    def __calculate_solution_score(solution: Solution) -> int:
        score = 0
        for pallet_idx, pallet_count in solution.pallet_count.items():
            pallet = solution.pallets[pallet_idx]
            score += min(pallet_count, pallet.cargo.quantity)
        return score
