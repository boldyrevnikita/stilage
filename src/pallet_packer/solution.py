from enum import Enum
from src.zone import AvailableZone, OccupiedZone, SpecialRoadZone
from src.pallet import Pallet
from src.rack import RackGroup, Rack, DoubleRack
from copy import deepcopy
from collections import defaultdict


class ActionFailure(Exception):
    """Exception raised when an action fails during the pallet
    packing process."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ActionStatus(Enum):
    """Enumeration for the status of an action in the pallet packing process.
    """
    NOT_STARTED = 1
    SUCCESS = 2
    FAILED = 3


class State:
    """Represents a state in the state machine for pallet packing actions.
    """
    def __init__(self, process_function: callable,
                 next_success_state_name_list: list[str] = [],
                 next_failure_state_name_list: list[str] = []):
        self.process_function = process_function
        self.next_success_state_name_list = next_success_state_name_list
        self.next_failure_state_name_list = next_failure_state_name_list


class Solution:
    """Represents the current state of the pallet packing solution.
    """
    def __init__(self, available_zones: list[AvailableZone],
                 occupied_zones: list[OccupiedZone],
                 road_zones: list[SpecialRoadZone],
                 pallets: list[Pallet],
                 state: State,
                 available_zone_idx: int = -1,
                 pallet_idx: int = 0,
                 saved_rack_groups: list[RackGroup] = [],
                 current_rack_group: RackGroup = None,
                 action_status: ActionStatus = (
                     ActionStatus.NOT_STARTED),
                 pallet_count: dict[int, int] = defaultdict(int)):
        self.initial_available_zones = deepcopy(available_zones)

        self.available_zones = deepcopy(available_zones)
        self.available_zone_idx = available_zone_idx
        self.rot_point: tuple[float, float] = (0.0, 0.0)
        self.pallets = deepcopy(pallets)
        self.pallet_count = pallet_count
        self.pallet_idx = pallet_idx

        self.occupied_zones = deepcopy(occupied_zones)
        self.road_zones = deepcopy(road_zones)
        self.current_occupied_zones: list[OccupiedZone] = []
        self.current_road_zones: list[SpecialRoadZone] = []
        self.intersected_special_zone: OccupiedZone | SpecialRoadZone = None

        self.saved_rack_groups = saved_rack_groups
        self.current_rack_group = current_rack_group

        self.state = state
        self.action_status = action_status

        # Beam and Upright types
        self.beam_types = []
        self.upright_type = None
        self.beam_type_idx = 0
        self.pallet_extra_space = 0.0
        self.max_shelfs = 0
        self.max_shelfs_bridge = 0

        self.state_history = []
        self.is_rotated = False
        self.next_rack_type: Rack | DoubleRack = None
        self.last_intersected_vertical_road = None
        self.max_intersected_oz_y = None
