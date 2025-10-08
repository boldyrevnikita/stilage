"""
Solution module for pallet packing.

This module contains classes and enums related to the state machine
and solution representation for the pallet packing problem.
"""

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
    
    Each state has:
    - A process function to execute
    - A list of next states on success
    - A list of next states on failure
    """
    def __init__(self, process_function: callable,
                 next_success_state_name_list: list[str] = [],
                 next_failure_state_name_list: list[str] = []):
        self.process_function = process_function
        self.next_success_state_name_list = next_success_state_name_list
        self.next_failure_state_name_list = next_failure_state_name_list


class Solution:
    """Represents the current state of the pallet packing solution.
    
    NEW LOGIC FLOW (with column protection):
    ========================================
    
    Phase 1: Column Protection
    --------------------------
    1. Identify all columns (compact occupied zones) in the current zone
    2. Create protective double racks for ALL columns
       - Each protective rack spans the full width of the zone
       - Column is positioned between the two rack halves
       - Distance between halves is dynamically calculated based on column size
    3. Analyze free strips between protective racks
    
    Phase 2: Fill Free Strips
    -------------------------
    4. For each free strip between protective racks:
       - Place regular racks (single or double) in the strip
       - Use standard placement logic within strip boundaries
    
    Phase 3: Handle Special Road Zones
    ----------------------------------
    5. Process special road zones (bridges/shifts) for all racks
    
    OLD LOGIC (for reference):
    =========================
    - Start placing racks from zone corner
    - React to obstacles as they are encountered
    - Shorten, skip, or disable frames when hitting obstacles
    
    KEY DIFFERENCES:
    ===============
    - Proactive vs Reactive: All columns protected upfront vs handling obstacles on-the-fly
    - Continuous racks: Protective racks are never interrupted by columns
    - Zone subdivision: Zone is divided into free strips for independent filling
    """
    
    def __init__(self, 
                 available_zones: list[AvailableZone],
                 occupied_zones: list[OccupiedZone],
                 road_zones: list[SpecialRoadZone],
                 pallets: list[Pallet],
                 state: State,
                 available_zone_idx: int = -1,
                 pallet_idx: int = 0,
                 saved_rack_groups: list[RackGroup] | None = None,
                 current_rack_group: RackGroup = None,
                 action_status: ActionStatus = ActionStatus.NOT_STARTED,
                 pallet_count: dict[int, int] = defaultdict(int)):
        """Initializes a Solution instance.
        
        Args:
            available_zones (list[AvailableZone]): List of available zones for rack placement.
            occupied_zones (list[OccupiedZone]): List of occupied zones (obstacles).
            road_zones (list[SpecialRoadZone]): List of special road zones (must remain clear).
            pallets (list[Pallet]): List of pallets to be placed.
            state (State): Current state in the state machine.
            available_zone_idx (int): Index of the current available zone being processed.
            pallet_idx (int): Index of the current pallet type being processed.
            saved_rack_groups (list[RackGroup] | None): List of completed rack groups.
            current_rack_group (RackGroup): The rack group currently being built.
            action_status (ActionStatus): Status of the last action executed.
            pallet_count (dict[int, int]): Counter for pallets placed by cargo type ID.
        """
        # =====================================================================
        # ZONE AND OBSTACLE DATA
        # =====================================================================
        
        # Original zones (never modified, for reference)
        self.initial_available_zones = deepcopy(available_zones)
        
        # Current working zones (can be split/modified during processing)
        self.available_zones = deepcopy(available_zones)
        self.available_zone_idx = available_zone_idx
        
        # Rotation data
        self.rot_point: tuple[float, float] = (0.0, 0.0)
        self.is_rotated = False
        
        # All obstacles and roads in the warehouse
        self.occupied_zones = deepcopy(occupied_zones)
        self.road_zones = deepcopy(road_zones)
        
        # Obstacles/roads relevant to current zone (filtered subset)
        self.current_occupied_zones: list[OccupiedZone] = []
        self.current_road_zones: list[SpecialRoadZone] = []
        
        # Currently intersected obstacle/road (during placement)
        self.intersected_special_zone: OccupiedZone | SpecialRoadZone = None
        
        # =====================================================================
        # NEW: COLUMN PROTECTION (Phase 1)
        # =====================================================================
        
        # Columns identified in current zone (subset of current_occupied_zones)
        # These are compact, small obstacles that will be protected by double racks
        self.columns_in_zone: list[OccupiedZone] = []
        
        # Protective double racks created for columns
        # These racks span the full width of the zone and contain columns between halves
        self.protective_racks: list[DoubleRack] = []
        
        # Free strips between protective racks (for regular rack placement)
        # Format: [{'y_min': float, 'y_max': float, 'width': float, 'index': int}, ...]
        self.free_strips: list[dict] = []
        
        # Index of the free strip currently being filled
        self.current_strip_idx: int = 0
        
        # =====================================================================
        # PALLET DATA
        # =====================================================================
        
        # All pallets to be placed
        self.pallets = deepcopy(pallets)
        
        # Counter: how many pallets of each cargo type have been placed
        # Key: cargo_type_id, Value: count of pallets placed
        self.pallet_count = pallet_count
        
        # Index of current pallet type being processed
        self.pallet_idx = pallet_idx
        
        # =====================================================================
        # RACK DATA
        # =====================================================================
        
        # Completed rack groups (saved and finalized)
        self.saved_rack_groups = saved_rack_groups or []
        
        # Rack group currently being built
        self.current_rack_group = current_rack_group
        
        # Type of next rack to create (Rack or DoubleRack)
        self.next_rack_type: type[Rack] | type[DoubleRack] = None
        
        # =====================================================================
        # RACK CONFIGURATION (from reference book)
        # =====================================================================
        
        # Available beam types for current pallet
        self.beam_types = []
        
        # Selected upright type for current pallet
        self.upright_type = None
        
        # Index of current beam type being used
        self.beam_type_idx = 0
        
        # Extra space above pallet on each shelf
        self.pallet_extra_space = 0.0
        
        # Maximum number of shelves per frame
        self.max_shelfs = 0
        
        # Maximum number of shelves per bridge frame
        self.max_shelfs_bridge = 0
        
        # =====================================================================
        # STATE MACHINE DATA
        # =====================================================================
        
        # Current state in the state machine
        self.state = state
        
        # Status of the last action executed
        self.action_status = action_status
        
        # History of states (for debugging, optional)
        self.state_history = []
        
        # =====================================================================
        # TRACKING DATA (for special cases)
        # =====================================================================
        
        # Last vertical road zone intersected (to avoid re-processing)
        self.last_intersected_vertical_road = None
        
        # Maximum Y coordinate of intersected occupied zones (for positioning next rack)
        self.max_intersected_oz_y = None
    
    def __repr__(self) -> str:
        """Returns a string representation of the Solution.
        
        Returns:
            str: String representation with key statistics.
        """
        total_pallets_placed = sum(self.pallet_count.values())
        total_racks = sum(len(rg.racks) for rg in self.saved_rack_groups)
        
        return (f"Solution("
                f"zone_idx={self.available_zone_idx}, "
                f"pallet_idx={self.pallet_idx}, "
                f"racks={total_racks}, "
                f"pallets_placed={total_pallets_placed}, "
                f"protective_racks={len(self.protective_racks)}, "
                f"free_strips={len(self.free_strips)}, "
                f"state={self.state.__class__.__name__}"
                f")")
    
    def get_total_pallets_placed(self) -> int:
        """Calculates the total number of pallets placed in the solution.
        
        Returns:
            int: Total number of pallets placed across all rack groups.
        """
        return sum(self.pallet_count.values())
    
    def get_total_racks_count(self) -> int:
        """Calculates the total number of racks in the solution.
        
        Returns:
            int: Total number of racks (including both halves of double racks).
        """
        total = 0
        for rack_group in self.saved_rack_groups:
            for rack in rack_group.racks:
                if isinstance(rack, DoubleRack):
                    total += 2  # Count both halves
                else:
                    total += 1
        return total
    
    def get_total_rack_groups_count(self) -> int:
        """Returns the number of rack groups in the solution.
        
        Returns:
            int: Number of completed rack groups.
        """
        return len(self.saved_rack_groups)
    
    def get_zone_utilization(self) -> float:
        """Calculates the utilization percentage of available zones.
        
        Returns:
            float: Percentage of zone area used by racks (0.0 to 1.0).
        """
        total_zone_area = sum(zone.area for zone in self.initial_available_zones)
        if total_zone_area == 0:
            return 0.0
        
        total_rack_area = sum(rg.area for rg in self.saved_rack_groups)
        return total_rack_area / total_zone_area
    
    def get_protected_columns_count(self) -> int:
        """Returns the number of columns protected by protective racks.
        
        Returns:
            int: Number of protected columns.
        """
        return len(self.protective_racks)
    
    def is_column_protected(self, column: OccupiedZone) -> bool:
        """Checks if a specific column is protected by a protective rack.
        
        Args:
            column (OccupiedZone): The column to check.
        
        Returns:
            bool: True if the column is protected, False otherwise.
        """
        for protective_rack in self.protective_racks:
            if protective_rack.protected_column == column:
                return True
        return False
    
    def get_current_free_strip(self) -> dict | None:
        """Returns the currently active free strip.
        
        Returns:
            dict | None: Dictionary with strip data or None if no strips available.
        """
        if not self.free_strips or self.current_strip_idx >= len(self.free_strips):
            return None
        return self.free_strips[self.current_strip_idx]
    
    def get_remaining_pallets_count(self, cargo_type_id: int) -> int:
        """Returns the number of pallets remaining to be placed for a cargo type.
        
        Args:
            cargo_type_id (int): The cargo type ID to check.
        
        Returns:
            int: Number of pallets not yet placed.
        """
        for pallet in self.pallets:
            if pallet.cargo.cargo_type_id == cargo_type_id:
                placed = self.pallet_count.get(cargo_type_id, 0)
                return pallet.cargo.quantity - placed
        return 0
    
    def get_pallet_placement_progress(self) -> dict[int, float]:
        """Returns placement progress for each pallet type.
        
        Returns:
            dict[int, float]: Dictionary mapping cargo_type_id to progress percentage (0.0 to 1.0).
        """
        progress = {}
        for pallet in self.pallets:
            cargo_id = pallet.cargo.cargo_type_id
            total = pallet.cargo.quantity
            placed = self.pallet_count.get(cargo_id, 0)
            progress[cargo_id] = placed / total if total > 0 else 0.0
        return progress
    
    def clone(self) -> 'Solution':
        """Creates a deep copy of the solution.
        
        Returns:
            Solution: A new Solution instance with copied data.
        """
        return deepcopy(self)
    
    def get_statistics(self) -> dict:
        """Returns comprehensive statistics about the solution.
        
        Returns:
            dict: Dictionary containing various solution statistics.
        """
        return {
            'total_pallets_placed': self.get_total_pallets_placed(),
            'total_racks': self.get_total_racks_count(),
            'total_rack_groups': self.get_total_rack_groups_count(),
            'zone_utilization': self.get_zone_utilization(),
            'protected_columns': self.get_protected_columns_count(),
            'free_strips': len(self.free_strips),
            'current_strip_idx': self.current_strip_idx,
            'zones_processed': self.available_zone_idx + 1,
            'pallet_types_processed': self.pallet_idx + 1,
            'pallet_progress': self.get_pallet_placement_progress(),
            'is_rotated': self.is_rotated,
        }