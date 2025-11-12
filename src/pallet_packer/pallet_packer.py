"""
Pallet packer module for optimizing warehouse rack placement.

This module implements the main pallet packing algorithm using:
- State machine for sequential decision making
- Beam search for exploring multiple solution variants
- Multiprocessing for parallel processing
- Column protection strategy (NEW)
"""

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
import logging

logger = logging.getLogger(__name__)


class PalletPackerProcessor:
    """Processes pallet packing solutions using state machine and beam search.
    
    This processor:
    1. Takes solutions from a shared cache
    2. Applies state machine actions to each solution
    3. Generates multiple solution variants (branches)
    4. Prunes low-scoring solutions periodically
    5. Saves completed solutions to a shared list
    """
    
    def __init__(self, cache: Queue[Solution],
                 ready_solutions: list[Solution],
                 reference_book: ReferenceBook,
                 prune_steps: int,
                 prune_beams_keep: int,
                 min_solutions: int,
                 cache_size: int,
                 process_idx: int,
                 processes_idle: list[bool]):
        """Initializes a PalletPackerProcessor.
        
        Args:
            cache (Queue[Solution]): Shared queue of solutions to process.
            ready_solutions (list[Solution]): Shared list for completed solutions.
            reference_book (ReferenceBook): Reference book with configuration.
            prune_steps (int): Number of steps between pruning operations.
            prune_beams_keep (int): Number of top solutions to keep after pruning.
            min_solutions (int): Minimum number of solutions before stopping.
            cache_size (int): Maximum size of the solution cache.
            process_idx (int): Index of this process.
            processes_idle (list[bool]): Shared list tracking idle status of all processes.
        """
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
        """Main processing loop for pallet packing solutions.
        
        This method:
        1. Retrieves solutions from the cache
        2. Processes each solution through the state machine
        3. Saves completed solutions
        4. Exits when enough solutions are found or all processes are idle
        """
        logger.info(f"[PROCESSOR-{self.process_idx}] Started")
        
        while True:
            if self.cache.empty():
                if all(self.processes_idle):
                    logger.info(f"[PROCESSOR-{self.process_idx}] All processes idle, exiting")
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
                logger.info(f"[PROCESSOR-{self.process_idx}] Found {len(self.ready_solutions)} solutions, exiting")
                sys.exit(0)

    def run_main_cycle(self, current_solution: Solution):
        """Runs the main cycle of the pallet packing process.
        
        This method implements beam search with periodic pruning:
        1. Maintains a queue of solutions to process
        2. Applies state machine actions to generate new solution variants
        3. Filters invalid solutions
        4. Periodically prunes low-scoring solutions
        5. Saves completed solutions
        
        Args:
            current_solution (Solution): The current solution to process.
        """
        solutions_queue: deque[Solution] = deque()
        solutions_queue.append(current_solution)

        step = 1
        while solutions_queue:
            current_solution = solutions_queue.popleft()
            
            self.state_machine.apply_action(current_solution)
            
            new_solutions = self.state_machine.choose_next_action(current_solution)
            
            new_solutions = self.state_machine.remove_invalid_solutions(new_solutions)
            
            transitional_solutions, end_solutions = (
                self.state_machine.extract_end_solutions(new_solutions))
            
            solutions_queue.extend(transitional_solutions)

            if end_solutions:
                self.ready_solutions.extend(end_solutions)
                logger.info(f"[PROCESSOR-{self.process_idx}] Found {len(end_solutions)} completed solutions. "
                           f"Total: {len(self.ready_solutions)}")

            if step % self.prune_steps == 0:
                solutions_queue, pruned_solutions = self.__prune_solutions(
                    solutions_queue,
                    self.prune_beams_keep)

                for solution in pruned_solutions:
                    if self.cache.qsize() >= self.cache_size:
                        self.cache.get()
                    self.cache.put(solution)
                
                if pruned_solutions:
                    logger.debug(f"[PROCESSOR-{self.process_idx}] Pruned {len(pruned_solutions)} solutions at step {step}")

            step += 1

    def __prune_solutions(self, solutions: deque[Solution],
                          prune_beams_keep: int
                          ) -> tuple[deque[Solution], list[Solution]]:
        """Prunes the solutions based on their scores.
        
        Keeps only the top N solutions based on intermediate scoring,
        returning the rest for potential reprocessing.
        
        Args:
            solutions (deque[Solution]): The deque of solutions to prune.
            prune_beams_keep (int): The number of top solutions to keep.
        
        Returns:
            tuple[deque[Solution], list[Solution]]: A tuple containing the
            kept solutions (as deque) and the pruned solutions (as list).
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
    """Main class for packing pallets into warehouse racks.
    
    This class implements a multi-process beam search algorithm with:
    - Column protection (NEW): All columns are protected by double racks upfront
    - State machine: Sequential decision making
    - Beam search: Exploring multiple solution variants
    - Pruning: Keeping only promising solutions
    - Multiprocessing: Parallel processing for speed
    """
    
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
        """Packs pallets into racks using multiprocessing and beam search.
        
        NEW LOGIC:
        The algorithm now follows a three-phase approach:
        1. Phase 1 (Column Protection): Identify all columns and protect them
           with continuous double racks
        2. Phase 2 (Fill Free Strips): Fill the strips between protective racks
           with regular racks
        3. Phase 3 (Handle Road Zones): Process special road zones (bridges/shifts)
        
        Args:
            pallets (list[Pallet]): List of pallets to pack.
            available_zones (list[AvailableZone]): List of available zones.
            occupied_zones (list[OccupiedZone]): List of occupied zones (obstacles).
            special_road_zones (list[SpecialRoadZone]): List of special road zones.
            reference_book (ReferenceBook): Reference book for pallet packing.
                Defaults to a new ReferenceBook instance.
            prune_steps (int): Number of steps after which to prune solutions.
                Defaults to 100.
            prune_beams_keep (int): Number of top solutions to keep after pruning.
                Defaults to 2.
            min_solutions (int): Minimum number of solutions to find before stopping.
                Defaults to 5.
            cache_size (int): Maximum size of the solution cache.
                Defaults to 100.
        
        Returns:
            Solution | None: The best solution found or None if no solution is found.
        """
        logger.info("="*80)
        logger.info("STARTING PALLET PACKING WITH COLUMN PROTECTION")
        logger.info("="*80)
        logger.info(f"Input: {len(pallets)} pallet types, {len(available_zones)} zones, "
                   f"{len(occupied_zones)} obstacles, {len(special_road_zones)} road zones")
        logger.info(f"Parameters: prune_steps={prune_steps}, beams_keep={prune_beams_keep}, "
                   f"min_solutions={min_solutions}, processes={cpu_count()}")
        
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

            initial_solution = Solution(
                available_zones=available_zones,
                occupied_zones=occupied_zones,
                road_zones=special_road_zones,
                pallets=pallets,
                state=state_machine.get_initial_state()
            )
            
            cache.put(initial_solution)
            logger.info("Initial solution created and added to cache")

            for i in range(cpu_count()):
                logger.info(f'Starting process {i + 1}/{cpu_count()} for pallet packing')
                process = Process(
                    target=PalletPackerProcessor(
                        cache, ready_solutions,
                        reference_book, prune_steps,
                        prune_beams_keep,
                        min_solutions,
                        cache_size,
                        i, processes_idle
                    ).process
                )
                process.start()
                processes.append(process)

            for i, process in enumerate(processes):
                process.join()
                logger.info(f'Process {i + 1}/{cpu_count()} has finished')

            ready_solutions = list(ready_solutions)
            logger.info(f"All processes finished. Total solutions found: {len(ready_solutions)}")

        best_solution = cls.__get_best_solution(ready_solutions)
        
        if best_solution:
            stats = best_solution.get_statistics()
            logger.info("="*80)
            logger.info("BEST SOLUTION STATISTICS:")
            logger.info(f"  Total pallets placed: {stats['total_pallets_placed']}")
            logger.info(f"  Total racks: {stats['total_racks']}")
            logger.info(f"  Total rack groups: {stats['total_rack_groups']}")
            logger.info(f"  Zone utilization: {stats['zone_utilization']*100:.1f}%")
            logger.info(f"  Protected columns: {stats['protected_columns']}")
            logger.info(f"  Free strips created: {stats['free_strips']}")
            logger.info("="*80)
        else:
            logger.warning("No solution found!")
        
        return best_solution

    @classmethod
    def __get_best_solution(cls, solutions: list[Solution]
                            ) -> Solution | None:
        """Retrieves the best solution from the list of solutions based on
        the calculated score.
        
        Args:
            solutions (list[Solution]): The list of solutions to extract from.
        
        Returns:
            Solution | None: The best solution found or None if no solutions
            are available.
        """
        if not solutions:
            return None
        
        max_score = -1
        best_solution = None

        for solution in solutions:
            score = cls.__calculate_solution_score(solution)
            if score > max_score:
                max_score = score
                best_solution = solution
        
        logger.info(f"Best solution score: {max_score}")
        return best_solution

    @staticmethod
    def __calculate_solution_score(solution: Solution) -> int:
        """Calculates the score of a completed solution.
        
        The score is simply the total number of pallets that can be stored
        in all racks of the solution. Higher score = more storage capacity.
        
        Args:
            solution (Solution): The solution to calculate the score for.
        
        Returns:
            int: The score of the solution (total pallet capacity).
        """
        score = 0
        if solution is None or getattr(solution, 'saved_rack_groups', None) in (None, []):
            return 0
        
        for rack_group in solution.saved_rack_groups:
            for rack in rack_group.racks:
                score += rack.calculate_pallet_capacity()
        
        return score

    @staticmethod
    def calculate_intermediate_solution_score(solution: Solution) -> float:
        """Calculates the score of an intermediate (incomplete) solution.
        
        This score is used for beam search pruning. It combines:
        1. Area efficiency: How much of the available area is still free
        2. Pallet placement progress: How many pallets have been placed
        3. Column protection bonus (NEW): Reward for protecting columns
        
        Args:
            solution (Solution): The solution to calculate the score for.
        
        Returns:
            float: The score of the intermediate solution (0.0 to ~2.0).
        """
        score = 0.0
        start_area = 0.0
        current_area = 0.0
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

        if start_area > 0 and max_cargo_quantity > 0:
            area_score = (start_area - current_area) / start_area
            pallet_score = current_cargo_quantity / max_cargo_quantity
            score = area_score + pallet_score
        
        if hasattr(solution, 'protective_racks') and hasattr(solution, 'columns_in_zone'):
            protected_columns_count = len(solution.protective_racks)
            total_columns_count = len(solution.columns_in_zone)
            
            if total_columns_count > 0:
                protection_ratio = protected_columns_count / total_columns_count
                protection_bonus = protection_ratio * 0.1
                score += protection_bonus
        
        return score