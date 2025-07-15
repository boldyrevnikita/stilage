from collections import deque
from copy import deepcopy

from src.pallet import Pallet
from src.pallet_packer.solution import Solution
from src.pallet_packer.state_machine import StateMachine
from src.reference_book import ReferenceBook
from src.utils import check_if_debugger_is_active
from src.zone import AvailableZone, OccupiedZone, SpecialRoadZone


class PalletPacker:
    @classmethod
    def pack_pallets(cls, pallets: list[Pallet],
                     available_zones: list[AvailableZone],
                     occupied_zones: list[OccupiedZone],
                     special_road_zones: list[SpecialRoadZone],
                     reference_book: ReferenceBook = ReferenceBook(),
                     prune_steps: int = 500,
                     prune_beams_keep: int = 2
                     #  prune_steps: int = 1,
                     #  prune_beams_keep: int = 1
                     ) -> Solution | None:
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

        step = 1
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

            if step % prune_steps == 0:
                solutions_queue = cls.__prune_solutions(solutions_queue,
                                                        prune_beams_keep)

            step += 1

            if check_if_debugger_is_active():
                print(f"Queue size: {len(solutions_queue)}")
                print(f"Ready solutions: {len(ready_solutions)}")
                print("Current function name: "
                      f"{current_solution.state.process_function.__name__}")
                print()

        return cls.__get_best_solution(ready_solutions)

    @staticmethod
    def __prune_solutions(solutions: deque[Solution],
                          prune_beams_keep: int
                          ) -> deque[Solution]:
        solutions = list(solutions)
        solutions.sort(
            key=PalletPacker.__calculate_intermediate_solution_score,
            reverse=True
        )
        solutions = solutions[:prune_beams_keep]
        solutions = deque(solutions)
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
        for rack_group in solution.saved_rack_groups:
            for rack in rack_group.racks:
                score += rack.calculate_pallet_capacity()
        return score

    @staticmethod
    def __calculate_intermediate_solution_score(solution: Solution) -> int:
        score = 0
        start_area = 0
        current_area = 0
        max_cargo_quantity = 0
        current_cargo_quantity = 0

        for available_zone in solution.initial_available_zones:
            start_area += available_zone.area
        for available_zone in solution.available_zones:
            current_area += available_zone.area
        current_area -= solution.current_rack_group.area

        for pallet in solution.pallets:
            max_cargo_quantity += pallet.cargo.quantity
            current_cargo_quantity += solution.pallet_count[
                pallet.cargo.cargo_type_id]

        score = (current_area / start_area + current_cargo_quantity
                 / max_cargo_quantity)

        return score
