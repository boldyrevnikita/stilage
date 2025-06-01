from src.reference_book import ReferenceBook
from src.pallet import Pallet
from src.zone import AvailableZone, OccupiedZone, SpecialRoadZone
from collections import deque
from rack import RackGroup
from enum import Enum
from copy import deepcopy


class PalletPackerSolution:
    def __init__(self, available_zones: list[AvailableZone],
                 current_available_zone: AvailableZone = None,
                 saved_rack_groups: list[RackGroup] = [],
                 current_rack_group: RackGroup = None,
                 next_action: Actions = None,
                 task_completion_status: TaskCompletionStatus = (
                     TaskCompletionStatus.NOTHING_PLANNED),
                 cargo_count: dict[int, int] = {}):
        self.available_zones = deepcopy(available_zones)
        self.current_available_zone = current_available_zone
        self.saved_rack_groups = saved_rack_groups
        self.current_rack_group = current_rack_group
        self.next_action = next_action
        self.task_completion_status = task_completion_status
        self.cargo_count = cargo_count

    def set_action(self, action: Actions) -> None:
        self.next_action = action
        self.task_completion_status = TaskCompletionStatus.NOT_STARTED


class PalletPacker:
    @classmethod
    def pack_pallets(cls, pallets: list[Pallet],
                     available_zones: list[AvailableZone],
                     occupied_zones: list[OccupiedZone],
                     special_road_zones: list[SpecialRoadZone]
                     ) -> PalletPackerSolution:
        reference_book = ReferenceBook()
        solutions_queue = deque()
        ready_solutions = []

        pallets = deepcopy(pallets)
        available_zones = deepcopy(available_zones)
        occupied_zones = deepcopy(occupied_zones)
        special_road_zones = deepcopy(special_road_zones)

        pallets.sort(key=lambda x: (x.weight, x.height, x.width))
        available_zones.sort(key=lambda x: (x.area, x.height))

        solutions_queue.append(PalletPackerSolution())

        while solutions_queue:
            current_solution = solutions_queue.popleft()
            cls.__apply_action(current_solution)
            new_solutions = cls.__choose_next_action(current_solution)

            for solution in new_solutions:
                cls.__validate_next_action(solution)
                pass

            solutions_queue = cls.__prune_solutions(solutions_queue)

        return cls.__get_best_solution(ready_solutions)

    @staticmethod
    def __apply_action(current_solution: PalletPackerSolution) -> None:
        if (current_solution.task_completion_status
                is TaskCompletionStatus.NOTHING_PLANNED):
            return
        action = current_solution.next_action
        if action is Actions.CREATE_HORIZONTAL_GROUP:
            pass
        elif action is Actions.CREATE_VERTICAL_GROUP:
            pass
        elif action is Actions.ADD_SINGLE_RACK:
            pass
        elif action is Actions.ADD_CONNECTED_RACK:
            pass
        elif action is Actions.JUMP_OVER_OBSTACLE:
            pass
        elif action is Actions.GET_AROUND_OBSTACLE:
            pass
        elif action is Actions.HANDLE_SPECIAL_ROAD:
            pass
        else:
            raise ValueError(f"Unknown action: {action}")
        current_solution.next_action = None

    @staticmethod
    def __choose_next_action(current_solution: PalletPackerSolution
                             ) -> list[PalletPackerSolution]:
        if (current_solution.task_completion_status
                is TaskCompletionStatus.NOTHING_PLANNED):
            sollution1, sollution2 = (deepcopy(current_solution),
                                      deepcopy(current_solution))
            sollution1.set_action(Actions.CREATE_HORIZONTAL_GROUP)
            sollution2.set_action(Actions.CREATE_VERTICAL_GROUP)
            return [sollution1, sollution2]
        elif (current_solution.task_completion_status
              == TaskCompletionStatus.NOT_STARTED):
            return [current_solution]

    @staticmethod
    def __validate_next_action(current_solution: PalletPackerSolution) -> None:
        if (current_solution.task_completion_status
                != TaskCompletionStatus.NOT_STARTED):
            return

    @staticmethod
    def __prune_solutions(solutions: deque[PalletPackerSolution]
                          ) -> deque[PalletPackerSolution]:
        # TODO: Implement pruning logic
        return solutions

    @staticmethod
    def __get_best_solution(solutions: list[PalletPackerSolution]
                            ) -> PalletPackerSolution:
        pass
