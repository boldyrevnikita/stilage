from collections import deque
from copy import deepcopy
import sys

from src.pallet import Pallet
from src.pallet_packer.solution import Solution
from src.pallet_packer.state_machine import StateMachine
from src.reference_book import ReferenceBook
from src.utils import check_if_debugger_is_active
from src.zone import AvailableZone, OccupiedZone, SpecialRoadZone
from queue import Queue
from multiprocessing import Process, Manager, cpu_count, set_start_method
import time


class PalletPackerProcessor:
    """Processes pallet packing solutions."""
    def __init__(self, cache: Queue[Solution],
                 ready_solutions: list[Solution],
                 reference_book: ReferenceBook,
                 prune_steps: int,
                 prune_beams_keep: int,
                 min_solutions: int,
                 cache_size: int,
                 process_idx: int,
                 processes_idle: list[bool]):
        self.cache = cache
        self.ready_solutions = ready_solutions
        self.reference_book = reference_book
        self.state_machine = StateMachine(reference_book)
        self.prune_steps = prune_steps
        self.prune_beams_keep = prune_beams_keep
        self.min_solutions = min_solutions
        self.cache_size = cache_size
        self.process_idx = process_idx
        self.processes_idle = processes_idle

    def process(self):
        """Main processing loop for pallet packing solutions."""
        while True:
            if self.cache.empty():
                if all(self.processes_idle):
                    sys.exit(0)
                time.sleep(5)
                continue
            self.processes_idle[self.process_idx] = False
            current_solution = self.cache.get()
            self.run_main_cycle(current_solution)
            self.processes_idle[self.process_idx] = True

            if len(self.ready_solutions) >= self.min_solutions:
                if check_if_debugger_is_active():
                    print(f'Found {len(self.ready_solutions)} solutions')
                sys.exit(0)

    def run_main_cycle(self, current_solution: Solution):
        """Runs the main cycle of the pallet packing process
        Args:
            current_solution (Solution): The current solution to process.
        """
        solutions_queue: deque[Solution] = deque()

        solutions_queue.append(current_solution)

        step = 1
        while solutions_queue:
            current_solution = solutions_queue.popleft()
            self.state_machine.apply_action(current_solution)
            new_solutions = self.state_machine.choose_next_action(
                current_solution)
            new_solutions = self.state_machine.remove_invalid_solutions(
                new_solutions)
            transitional_solutions, end_solutions = (
                self.state_machine.extract_end_solutions(new_solutions))
            solutions_queue.extend(transitional_solutions)

            if end_solutions:
                self.ready_solutions.extend(end_solutions)

            if step % self.prune_steps == 0:
                solutions_queue, pruned_solutions = self.__prune_solutions(
                    solutions_queue,
                    self.prune_beams_keep)

                for solution in pruned_solutions:
                    if self.cache.qsize() >= self.cache_size:
                        self.cache.get()
                    self.cache.put(solution)

            step += 1

    def __prune_solutions(self, solutions: deque[Solution],
                          prune_beams_keep: int
                          ) -> tuple[deque[Solution], list[Solution]]:
        """Prunes the solutions based on their scores.
        Args:
            solutions (deque[Solution]): The deque of solutions to prune.
            prune_beams_keep (int): The number of top solutions to keep.
        Returns:
            tuple[deque[Solution], list[Solution]]: A tuple containing the
            pruned solutions and the kept solutions.
        """
        solutions = list(solutions)
        solutions.sort(
            key=PalletPacker.calculate_intermediate_solution_score,
            reverse=True
        )
        kept_solutions = solutions[:prune_beams_keep]
        pruned_solutions = solutions[prune_beams_keep:]
        solutions = deque(kept_solutions)
        return solutions, pruned_solutions


class PalletPacker:
    """Class for packing pallets into racks (placing racks)."""
    @classmethod
    def pack_pallets(cls, pallets: list[Pallet],
                     available_zones: list[AvailableZone],
                     occupied_zones: list[OccupiedZone],
                     special_road_zones: list[SpecialRoadZone],
                     reference_book: ReferenceBook = ReferenceBook(),
                     prune_steps: int = 100,
                     prune_beams_keep: int = 2,
                     min_solutions: int = 5,
                     cache_size: int = 100
                     ) -> Solution | None:
        """Packs pallets into racks using multiprocessing.
        Args:
            pallets (list[Pallet]): List of pallets to pack.
            available_zones (list[AvailableZone]): List of available zones.
            occupied_zones (list[OccupiedZone]): List of occupied zones.
            special_road_zones (list[SpecialRoadZone]): List of special
                road zones.
            reference_book (ReferenceBook): Reference book for pallet packing.
            prune_steps (int): Number of steps after which to prune solutions.
            prune_beams_keep (int): Number of top solutions to keep
                after pruning.
            min_solutions (int): Minimum number of solutions to find
                before stopping.
            cache_size (int): Maximum size of the solution cache.
        Returns:
            Solution | None: The best solution found or
                None if no solution is found.
        """
        set_start_method('spawn', force=True)
        processes: list[Process] = []

        with Manager() as manager:
            cache = manager.Queue()
            ready_solutions = manager.list()
            processes_idle = manager.list([True] * cpu_count())

            pallets = deepcopy(pallets)
            available_zones = deepcopy(available_zones)
            occupied_zones = deepcopy(occupied_zones)
            special_road_zones = deepcopy(special_road_zones)

            state_machine = StateMachine(reference_book)

            cache.put(Solution(
                available_zones=available_zones,
                occupied_zones=occupied_zones,
                road_zones=special_road_zones,
                pallets=pallets,
                state=state_machine.get_initial_state())
            )

            for i in range(cpu_count()):
                print(f'Starting process {i + 1} for pallet packing')
                process = Process(
                    target=PalletPackerProcessor(cache, ready_solutions,
                                                 reference_book, prune_steps,
                                                 prune_beams_keep,
                                                 min_solutions,
                                                 cache_size,
                                                 i, processes_idle).process
                )
                process.start()
                processes.append(process)

            for i, process in enumerate(processes):
                process.join()
                print(f'Process {i + 1} has finished')

            ready_solutions = list(ready_solutions)

        return cls.__get_best_solution(ready_solutions)

    @classmethod
    def __get_best_solution(cls, solutions: list[Solution]
                            ) -> Solution | None:
        """
        Retrieves the best solution from the list of solutions based on
        the calculated score.
        Args:
            solutions (list[Solution]): The list of solutions to extract from.
        Returns:
            Solution | None: The best solution found or None if no solutions
            are available.
        """
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
        """Calculates the score of a solution based on the number of pallets
        packed and the area used.
        Args:
            solution (Solution): The solution to calculate the score for.
        Returns:
            int: The score of the solution.
        """
        score = 0
        if solution is None or getattr(solution, 'saved_rack_groups', None) in (None, []):
            return 0
        for rack_group in solution.saved_rack_groups:
            for rack in rack_group.racks:
                score += rack.calculate_pallet_capacity()
        return score

    @staticmethod
    def calculate_intermediate_solution_score(solution: Solution) -> int:
        """Calculates the score of an intermediate solution based on the area
        used and the number of pallets packed.
        Args:
            solution (Solution): The solution to calculate the score for.
        Returns:
            int: The score of the intermediate solution.
        """
        score = 0
        start_area = 0
        current_area = 0
        max_cargo_quantity = 0
        current_cargo_quantity = 0

        for available_zone in solution.initial_available_zones:
            start_area += available_zone.area
        for available_zone in solution.available_zones:
            current_area += available_zone.area

        if solution.current_rack_group is not None:
            current_area -= solution.current_rack_group.area

        for pallet in solution.pallets:
            max_cargo_quantity += pallet.cargo.quantity
            current_cargo_quantity += solution.pallet_count[
                pallet.cargo.cargo_type_id]

        score = (current_area / start_area + current_cargo_quantity
                 / max_cargo_quantity)

        return score
