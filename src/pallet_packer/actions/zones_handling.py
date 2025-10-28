"""
Actions for handling zones and obstacles in the pallet packing system.

This module contains functions for zone management, rotation, splitting,
and checking intersections with occupied zones and road zones.
"""

from src.reference_book import ReferenceBook
from src.pallet_packer.solution import Solution, ActionFailure
from src.rack import Rack, DoubleRack
from src.zone import SpecialRoadZone, OccupiedZone
import shapely
from copy import deepcopy
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# ROTATION FUNCTIONS
# =============================================================================

def rotate_everything_90_clockwise(
    _: ReferenceBook,
    solution: Solution
) -> None:
    available_zone = solution.available_zones[solution.available_zone_idx]
    
    # ✅ CRITICAL FIX: Use BOTTOM-LEFT corner as rotation point!
    # This ensures that after rotation back, everything returns to exact positions
    solution.rot_point = available_zone.bounds[:2]  # (min_x, min_y)
    
    angle = -90

    available_zone.rotate(solution.rot_point, angle)
    for occupied_zone in solution.current_occupied_zones:
        occupied_zone.rotate(solution.rot_point, angle)
    for road_zone in solution.current_road_zones:
        road_zone.rotate(solution.rot_point, angle)
    
    for column in solution.columns_in_zone:
        column.rotate(solution.rot_point, angle)

    solution.is_rotated = True

    solution.current_occupied_zones.sort(key=lambda x: x.bounds[0])
    solution.current_road_zones.sort(key=lambda x: x.bounds[0])
    
    logger.warning(f"[ZONES] Rotated everything 90° clockwise around BOTTOM-LEFT {solution.rot_point}")


def rotate_everything_90_counterclockwise(
    _: ReferenceBook,
    solution: Solution
) -> None:
    if solution.is_rotated:
        from src.rack import normalize_rack_orientation
        
        available_zone = solution.available_zones[solution.available_zone_idx]
        angle = 90

        # ✅ DEBUG: Log bounds BEFORE rotation back
        logger.warning("[DEBUG_ROTATION_BACK] ========================================")
        logger.warning("[DEBUG_ROTATION_BACK] BEFORE rotation counterclockwise:")
        logger.warning(f"[DEBUG_ROTATION_BACK] Zone bounds: {available_zone.bounds}")
        logger.warning(f"[DEBUG_ROTATION_BACK] Total saved_rack_groups: {len(solution.saved_rack_groups)}")
        
        for i, rg in enumerate(solution.saved_rack_groups):
            is_protective = False
            if rg.racks:
                first_rack = rg.racks[0]
                if isinstance(first_rack, DoubleRack) and hasattr(first_rack, 'is_protective'):
                    is_protective = first_rack.is_protective
            
            logger.warning(f"[DEBUG_ROTATION_BACK]   RackGroup {i}: "
                          f"protective={is_protective}, "
                          f"bounds={rg.bounds}, "
                          f"racks_count={len(rg.racks)}")
        
        # Rotate zone
        available_zone.rotate(solution.rot_point, angle)
        
        # Rotate obstacles
        for occupied_zone in solution.current_occupied_zones:
            occupied_zone.rotate(solution.rot_point, angle)
        for road_zone in solution.current_road_zones:
            road_zone.rotate(solution.rot_point, angle)
        
        # Rotate columns
        for column in solution.columns_in_zone:
            column.rotate(solution.rot_point, angle)
        
        # ✅ CRITICAL FIX: Don't rotate current_rack_group separately!
        # If it was saved, it will be rotated with saved_rack_groups below.
        # If it wasn't saved, we don't need to rotate it (it will be discarded).
        
        # Rotate ALL saved rack groups (including protective racks!)
        for rack_group in solution.saved_rack_groups:
            rack_group.rotate(angle, solution.rot_point)
            
            for rack in rack_group.racks:
                normalize_rack_orientation(rack)
                logger.warning(f"[ZONES] Normalized rack in saved_rack_groups")

        # ✅ DEBUG: Log bounds AFTER rotation back
        logger.warning("[DEBUG_ROTATION_BACK] AFTER rotation counterclockwise:")
        logger.warning(f"[DEBUG_ROTATION_BACK] Zone bounds: {available_zone.bounds}")
        
        for i, rg in enumerate(solution.saved_rack_groups):
            is_protective = False
            if rg.racks:
                first_rack = rg.racks[0]
                if isinstance(first_rack, DoubleRack) and hasattr(first_rack, 'is_protective'):
                    is_protective = first_rack.is_protective
            
            logger.warning(f"[DEBUG_ROTATION_BACK]   RackGroup {i}: "
                          f"protective={is_protective}, "
                          f"bounds={rg.bounds}, "
                          f"racks_count={len(rg.racks)}")
        
        logger.warning("[DEBUG_ROTATION_BACK] ========================================")

        solution.is_rotated = False
        logger.warning("[ZONES] Rotated everything 90° counterclockwise and normalized all racks")

# =============================================================================
# ZONE NAVIGATION FUNCTIONS
# =============================================================================

def set_next_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Sets the next available zone as the current one."""
    if solution.available_zone_idx >= len(solution.available_zones) - 1:
        raise ActionFailure("No more available zones to process.")

    solution.available_zone_idx += 1
    
    # DEBUG: Новая зона
    new_zone = solution.available_zones[solution.available_zone_idx]
    logger.warning(f"[DEBUG_NEXT_ZONE] ========================================")
    logger.warning(f"[DEBUG_NEXT_ZONE] SWITCHING TO NEXT ZONE")
    logger.warning(f"[DEBUG_NEXT_ZONE] Zone index: {solution.available_zone_idx}/{len(solution.available_zones)}")
    logger.warning(f"[DEBUG_NEXT_ZONE] Zone bounds: {new_zone.bounds}")
    width = new_zone.bounds[2] - new_zone.bounds[0]
    height = new_zone.bounds[3] - new_zone.bounds[1]
    logger.warning(f"[DEBUG_NEXT_ZONE] Zone size: {width:.1f} x {height:.1f} mm")
    logger.warning(f"[DEBUG_NEXT_ZONE] ========================================")

def reset_zone_specific_data(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Resets zone-specific data when moving to a new zone.
    
    This includes:
    - Protective racks and columns
    - Free strips information
    - Last intersected road tracking
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    """
    # Clear column protection data
    solution.columns_in_zone = []
    solution.protective_racks = []
    solution.free_strips = []
    solution.current_strip_idx = 0
    
    # Clear tracking data
    solution.last_intersected_vertical_road = None
    solution.max_intersected_oz_y = None
    solution.intersected_special_zone = None
    
    # Ensure rotation state is reset
    if solution.is_rotated:
        logger.warning("[ZONES] ⚠️ WARNING: Zone transition while rotated! Resetting rotation flag.")
        solution.is_rotated = False
    
    logger.warning("[ZONES] ✅ Reset zone-specific data for new zone")


def set_zero_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Sets the current available zone index to zero and moves to the next pallet.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    """
    solution.available_zone_idx = 0
    logger.warning("[ZONES] Reset to zone 0")


# =============================================================================
# ZONE FITTING AND SPLITTING
# =============================================================================

def assert_current_rack_fits_available_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Checks if the current rack fits into the available zone.
    
    NEW: Also checks free strip boundaries if protective racks are active.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If rack doesn't fit in the zone or strip.
    """
    available_zone = solution.available_zones[solution.available_zone_idx]
    current_rack = solution.current_rack_group.get_current_rack()

    # Check zone boundaries
    if not shapely.contains(available_zone.contour, current_rack.contour):
        logger.warning(f"[ZONES] Rack doesn't fit in zone. Rack bounds: {current_rack.bounds}, "
                      f"Zone bounds: {available_zone.bounds}")
        raise ActionFailure("Current rack does not fit into the available zone.")
    
    # NEW: Check strip boundaries (Y-axis only)
    if solution.free_strips and solution.current_strip_idx < len(solution.free_strips):
        current_strip = solution.free_strips[solution.current_strip_idx]
        rack_bounds = current_rack.contour.bounds
        
        # Check Y boundaries with small tolerance
        if rack_bounds[1] < current_strip['y_min'] - 0.1 or rack_bounds[3] > current_strip['y_max'] + 0.1:
            logger.warning(f"[ZONES] Rack Y=[{rack_bounds[1]:.1f}, {rack_bounds[3]:.1f}] "
                          f"exceeds strip Y=[{current_strip['y_min']:.1f}, {current_strip['y_max']:.1f}]")
            raise ActionFailure("Current rack exceeds free strip boundary.")
    
    logger.warning("[ZONES] Rack fits in available zone and strip")


def split_available_zone(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Splits the available zone into two parts.
    
    ✅ NEW LOGIC WITH PROTECTIVE RACKS:
    When protective racks exist, split is calculated based on REGULAR racks only,
    not protective racks. This is because:
    - Protective racks span the full width of the zone (X-axis)
    - Regular racks are placed in strips between protective racks
    - We need to split based on where regular racks end, not protective racks
    """
    available_zone = solution.available_zones[solution.available_zone_idx]
    MIN_ZONE_SIZE = 5000.0  # Minimum 5 meters to ensure usable zones
    
    # ✅ NEW: Calculate split point from ALL saved rack groups, excluding protective
    if not solution.saved_rack_groups:
        logger.warning("[ZONES] No saved rack groups, skipping split")
        solution.available_zones.pop(solution.available_zone_idx)
        solution.available_zone_idx -= 1
        return
    
    # Find maximum X and Y from regular (non-protective) racks
    max_x = available_zone.bounds[0]  # Start from zone left edge
    max_y = available_zone.bounds[1]  # Start from zone bottom edge
    
    has_regular_racks = False
    
    # ✅ CRITICAL FIX: Only use saved_rack_groups
    # Don't check current_rack_group - it's either None or already in saved_rack_groups
    for rack_group in solution.saved_rack_groups:
        # Check if this rack group contains protective racks
        is_protective_group = False
        
        if rack_group.racks:
            first_rack = rack_group.racks[0]
            if isinstance(first_rack, DoubleRack):
                if hasattr(first_rack, 'is_protective') and first_rack.is_protective:
                    is_protective_group = True
        
        if not is_protective_group:
            # This is a REGULAR rack group - use it for split calculation
            has_regular_racks = True
            max_x = max(max_x, rack_group.bounds[2])
            max_y = max(max_y, rack_group.bounds[3])
            logger.warning(f"[ZONES] Including regular rack: bounds={rack_group.bounds}")
        else:
            logger.warning(f"[ZONES] Excluding protective rack from split calculation")
    
    # If no regular racks were placed, skip split
    if not has_regular_racks:
        logger.warning("[ZONES] ⚠️ No regular racks placed, only protective racks exist")
        logger.warning("[ZONES] Skipping split - zone is fully processed")
        solution.available_zones.pop(solution.available_zone_idx)
        solution.available_zone_idx -= 1
        return
    
    # Calculate split point based on regular racks
    split_point = [max_x, max_y]
    split_point[0] += reference_book.roads_width
    split_point[1] += reference_book.roads_width
    split_point[0] = min(available_zone.bounds[2], split_point[0]) - 1
    split_point[1] = min(available_zone.bounds[3], split_point[1]) - 1

    # Check if split will produce any viable zones
    right_zone_width = available_zone.bounds[2] - split_point[0]
    top_zone_height = available_zone.bounds[3] - split_point[1]
    
    logger.warning(f"[ZONES] ========================================")
    logger.warning(f"[ZONES] SPLIT ANALYSIS (excluding protective racks)")
    logger.warning(f"[ZONES]   Available zone: {available_zone.bounds}")
    logger.warning(f"[ZONES]   Regular racks max X: {max_x:.1f}mm")
    logger.warning(f"[ZONES]   Regular racks max Y: {max_y:.1f}mm")
    logger.warning(f"[ZONES]   Split point: ({split_point[0]:.1f}, {split_point[1]:.1f})")
    logger.warning(f"[ZONES]   Right zone width: {right_zone_width:.1f}mm")
    logger.warning(f"[ZONES]   Top zone height: {top_zone_height:.1f}mm")
    logger.warning(f"[ZONES]   Min required: {MIN_ZONE_SIZE:.1f}mm")
    logger.warning(f"[ZONES] ========================================")
    
    # Only split if at least one resulting zone will be large enough
    if right_zone_width >= MIN_ZONE_SIZE or top_zone_height >= MIN_ZONE_SIZE:
        if available_zone.contains_point(split_point):
            new_zones = available_zone.split_zone(split_point)
            
            added_count = 0
            for zone in new_zones:
                zone_w = zone.bounds[2] - zone.bounds[0]
                zone_h = zone.bounds[3] - zone.bounds[1]
                
                if zone_w >= MIN_ZONE_SIZE and zone_h >= MIN_ZONE_SIZE:
                    solution.available_zones.append(zone)
                    added_count += 1
                    logger.warning(f"[ZONES] ✅ Added new zone: {zone_w:.1f} x {zone_h:.1f} mm")
                else:
                    logger.warning(f"[ZONES] ❌ Rejected small zone: {zone_w:.1f} x {zone_h:.1f} mm")
            
            logger.warning(f"[ZONES] Split created {added_count} viable zones")
        else:
            logger.warning(f"[ZONES] ⚠️ Split point outside zone bounds, skipping split")
    else:
        logger.warning(f"[ZONES] ⚠️ Split skipped - no resulting zones meet minimum size")

    solution.available_zones.pop(solution.available_zone_idx)
    solution.available_zone_idx -= 1

def sort_available_zones_by_area_and_height(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Sorts the available zones by area and height.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    """
    solution.available_zones.sort(key=lambda x: (-x.height, -x.area))
    logger.warning(f"[ZONES] Sorted {len(solution.available_zones)} zones by area and height")


# =============================================================================
# OCCUPIED ZONE INTERSECTION CHECKS
# =============================================================================

def set_current_occupied_zones_and_road_zones(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Retrieves the corresponding occupied zones and road zones for the current
    available zone.
    
    Note:
    Column identification and separation is handled by column_protection module,
    not here. This function collects ALL occupied zones in the zone.
    
    Args:
        reference_book (ReferenceBook): The reference book.
        solution (Solution): The current solution.
    """
    available_zone = solution.available_zones[solution.available_zone_idx]
    
    # Reset lists - columns_in_zone will be filled by column_protection
    solution.columns_in_zone = []
    solution.current_occupied_zones = []
    solution.current_road_zones = []
    
    # NEW: Clear protective racks and strips when switching zones
    solution.protective_racks = []
    solution.free_strips = []
    solution.current_strip_idx = 0
    
    # ✅ CRITICAL FIX: Clear current_rack_group to avoid duplication in split
    # When we switch zones, current_rack_group should be either:
    # - Already saved in saved_rack_groups (so we don't need it)
    # - Or it should be discarded (incomplete work from previous zone)
    solution.current_rack_group = None
    
    logger.warning(f"[ZONES] Cleared protective racks, strips, and current_rack_group for new zone")

    # Process occupied zones - add ALL obstacles to current_occupied_zones
    for occupied_zone in solution.occupied_zones:
        intersects_with_clearance = (
            shapely.intersects(
                available_zone.contour, occupied_zone.contour_with_clearance))
        intersects_with_roads_width = (
            shapely.intersects(
                available_zone.contour, occupied_zone.contour_with_roads_width))

        if intersects_with_clearance or intersects_with_roads_width:
            solution.current_occupied_zones.append(deepcopy(occupied_zone))
            logger.warning(f"[ZONES] Found occupied zone in zone: bounds={occupied_zone.bounds}")

    # Process road zones
    for road_zone in solution.road_zones:
        if shapely.intersects(road_zone.contour, available_zone.contour):
            solution.current_road_zones.append(deepcopy(road_zone))
            logger.warning(f"[ZONES] Found road zone in zone: bounds={road_zone.bounds}")

    # Sort for consistent processing order
    solution.current_occupied_zones.sort(key=lambda x: (x.bounds[0], x.bounds[2]))
    solution.current_road_zones.sort(key=lambda x: (x.bounds[0], x.bounds[2]))
    
    logger.warning(f"[ZONES] Zone obstacles: {len(solution.current_occupied_zones)} obstacles, "
               f"{len(solution.current_road_zones)} road zones")


def assert_current_rack_intersecting_occupied_zones(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that the current rack intersects with at least one occupied zone.
    
    NEW BEHAVIOR:
    Skips columns that are already protected by protective racks.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If rack doesn't intersect with any (unprotected) occupied zone.
    """
    current_rack = solution.current_rack_group.get_current_rack()

    # NEW: Get list of protected columns
    protected_columns = [pr.protected_column for pr in solution.protective_racks 
                        if pr.protected_column is not None]

    for occupied_zone in solution.current_occupied_zones:
        # NEW: Skip if this zone is a protected column
        if occupied_zone in protected_columns:
            logger.warning(f"[ZONES] Skipping protected column at {occupied_zone.bounds}")
            continue
        
        first_condition = current_rack.intersects(occupied_zone.contour)
        second_condition = (
            current_rack.intersects(occupied_zone.contour_with_roads_width)
            and current_rack.bounds[3] < occupied_zone.contour.bounds[1]
            and current_rack.bounds[2] > occupied_zone.contour.bounds[0]
            and occupied_zone.contour.bounds[2] > current_rack.bounds[0]
        )

        if first_condition or second_condition:
            solution.intersected_special_zone = occupied_zone
            if solution.max_intersected_oz_y is None:
                solution.max_intersected_oz_y = occupied_zone.bounds[3]
            else:
                solution.max_intersected_oz_y = max(
                    occupied_zone.bounds[3],
                    solution.max_intersected_oz_y)
            logger.warning(f"[ZONES] Rack intersects occupied zone at {occupied_zone.bounds}")
            return

    raise ActionFailure("Current rack does not intersect with any occupied zone.")


def assert_both_racks_intersecting_occupied_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that both racks of the double rack intersect with the occupied zone.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If not both racks intersect.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    current_occupied_zone = solution.intersected_special_zone

    is_first_rack_intersecting = (
        shapely.intersects(
            current_occupied_zone.contour,
            current_rack.rack_1.contour))
    is_second_rack_intersecting = (
        shapely.intersects(
            current_occupied_zone.contour,
            current_rack.rack_2.contour))

    if not is_first_rack_intersecting:
        raise ActionFailure("First rack does not intersect with the occupied zone.")
    if not is_second_rack_intersecting:
        raise ActionFailure("Second rack does not intersect with the occupied zone.")
    
    logger.warning("[ZONES] Both racks intersect occupied zone")


def assert_first_rack_intersecting_occupied_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that the first rack of the double rack intersects with the occupied zone.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If first rack doesn't intersect.
    """
    is_first_rack_intersecting = (
        shapely.intersects(
            solution.intersected_special_zone.contour,
            solution.current_rack_group.get_current_rack().rack_1.contour))
    if not is_first_rack_intersecting:
        raise ActionFailure("First rack does not intersect with the occupied zone.")


def assert_second_rack_intersecting_occupied_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that the second rack of the double rack intersects with the occupied zone.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If second rack doesn't intersect.
    """
    is_second_rack_intersecting = (
        shapely.intersects(
            solution.intersected_special_zone.contour,
            solution.current_rack_group.get_current_rack().rack_2.contour))
    if not is_second_rack_intersecting:
        raise ActionFailure("Second rack does not intersect with the occupied zone.")


def assert_last_rack_shelf_covers_occupied_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that the last shelf of the current rack covers the occupied zone.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If last shelf doesn't cover the zone.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    current_occupied_zone = solution.intersected_special_zone

    is_last_shelf_covers = (
        shapely.covers(
            current_rack.last_shelf_contour,
            current_occupied_zone.contour))

    if not is_last_shelf_covers:
        raise ActionFailure(
            "Last shelf of the current rack does not cover the occupied zone.")


def assert_last_shelf_of_first_rack_covers_occupied_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that the last shelf of the first rack covers the occupied zone.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If last shelf of first rack doesn't cover.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    current_occupied_zone = solution.intersected_special_zone

    is_last_shelf_covers = (
        shapely.covers(
            current_rack.rack_1.last_shelf_contour,
            current_occupied_zone.contour))

    if not is_last_shelf_covers:
        raise ActionFailure(
            "Last shelf of the first rack does not cover the occupied zone.")


def assert_last_shelf_of_second_rack_covers_occupied_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that the last shelf of the second rack covers the occupied zone.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If last shelf of second rack doesn't cover.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    current_occupied_zone = solution.intersected_special_zone

    is_last_shelf_covers = (
        shapely.covers(
            current_rack.rack_2.last_shelf_contour,
            current_occupied_zone.contour))

    if not is_last_shelf_covers:
        raise ActionFailure(
            "Last shelf of the second rack does not cover the occupied zone.")


# =============================================================================
# ROAD ZONE INTERSECTION CHECKS
# =============================================================================

def assert_current_rack_intersecting_road_zones(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that the current rack intersects with at least one road zone.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If rack doesn't intersect any road zone.
    """
    current_rack = solution.current_rack_group.get_current_rack()

    for road_zone in solution.current_road_zones:
        if current_rack.last_frame_intersects(road_zone.contour):
            if road_zone is solution.last_intersected_vertical_road:
                continue

            solution.intersected_special_zone = road_zone
            if not road_zone.is_horizontal():
                solution.last_intersected_vertical_road = road_zone

            logger.warning(f"[ZONES] Rack intersects road zone at {road_zone.bounds}")
            return

    raise ActionFailure("Current rack does not intersect with any road zone.")


def assert_intersected_road_horizontal(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that the intersected road zone is horizontal.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If road is not horizontal.
    """
    if not solution.intersected_special_zone.is_horizontal():
        raise ActionFailure("Intersected road zone is not horizontal.")


def assert_current_shelf_length_enough_for_road(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Checks if the current shelf length is enough for the road width.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If shelf length is insufficient.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    current_road = solution.intersected_special_zone

    if current_rack.get_current_shelf_length() < current_road.width:
        raise ActionFailure("Current shelf length is not enough for the road width.")


def assert_current_zone_height_enough_for_rack_bridge(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that the current zone height is enough for the rack bridge.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If zone height is insufficient for bridge.
    """
    if solution.max_shelfs_bridge <= 0:
        raise ActionFailure(
            "Current available zone is too low for current rack bridge.")


# =============================================================================
# COMBINED INTERSECTION CHECKS
# =============================================================================

def assert_current_rack_not_intersecting_oz_or_rz(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that the current rack does not intersect with any occupied or road zones.
    
    NEW BEHAVIOR:
    Also checks that rack doesn't intersect with protective racks.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If rack intersects with any zone.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    intersected_special_zone = None
    min_left_bound = None

    # Check occupied zones
    for occupied_zone in solution.current_occupied_zones:
        if shapely.intersects(
                occupied_zone.contour_with_roads_width, current_rack.contour):
            current_left_bound = \
                occupied_zone.contour_with_roads_width.bounds[0]
            if (intersected_special_zone is None or
                    min_left_bound > current_left_bound):
                intersected_special_zone = occupied_zone
                min_left_bound = current_left_bound

    # Check road zones
    for road_zone in solution.current_road_zones:
        if shapely.intersects(road_zone.contour, current_rack.contour):
            current_left_bound = road_zone.bounds[0]
            if (intersected_special_zone is None or
                    min_left_bound > current_left_bound):
                intersected_special_zone = road_zone
                min_left_bound = current_left_bound
    
    # NEW: Check protective racks
    for protective_rack in solution.protective_racks:
        if shapely.intersects(protective_rack.contour, current_rack.contour):
            logger.warning(f"[ZONES] Rack intersects with protective rack")
            solution.intersected_special_zone = protective_rack.protected_column
            raise ActionFailure("Current rack intersects with a protective rack.")

    if intersected_special_zone is not None:
        solution.intersected_special_zone = intersected_special_zone
        logger.warning(f"[ZONES] Rack intersects with zone at {intersected_special_zone.bounds}")
        raise ActionFailure("Current rack intersects with an occupied or road zone.")


# =============================================================================
# SPECIAL HANDLING FUNCTIONS
# =============================================================================

def place_road_zone_on_right_size(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Places the road zone on the right size.
    
    Args:
        reference_book (ReferenceBook): The reference book.
        solution (Solution): The current solution.
    """
    available_zone = solution.available_zones[solution.available_zone_idx]

    # Right road
    x_0, y_0, x_1, y_1 = available_zone.bounds
    x_0 = x_1 - reference_book.roads_width / 2
    x_1 = x_0

    new_road_zone = SpecialRoadZone(
        [(x_0, y_0), (x_1, y_1)],
        reference_book.roads_width,
    )

    solution.current_road_zones.append(new_road_zone)

    # Upper road
    x_0, y_0, x_1, y_1 = available_zone.bounds
    y_0 = (y_1 - solution.pallets[solution.pallet_idx].length
           - reference_book.roads_width / 2)
    y_1 = y_0

    new_road_zone = SpecialRoadZone(
        [(x_0, y_0), (x_1, y_1)],
        reference_book.roads_width,
    )

    solution.current_road_zones.append(new_road_zone)
    logger.warning("[ZONES] Placed road zones on right and top edges")


def move_second_rack_higher_over_oz(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Moves the second rack higher over the occupied zone.
    
    CRITICAL: This function should NEVER be called for protective racks!
    Protective racks have a fixed rack_distance that must not be modified.
    
    Args:
        reference_book (ReferenceBook): The reference book.
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If rack is protective or if internal distance becomes too large.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    current_occupied_zone = solution.intersected_special_zone

    # CRITICAL CHECK: Prevent moving protective racks!
    if isinstance(current_rack, DoubleRack) and current_rack.is_protective:
        logger.error(f"[ZONES] ❌ FORBIDDEN: Attempted to move protective rack!")
        logger.error(f"[ZONES]   Protective racks must maintain fixed rack_distance={current_rack.rack_distance:.1f}mm")
        logger.error(f"[ZONES]   Protected column: {current_rack.protected_column.bounds if current_rack.protected_column else 'None'}")
        raise ActionFailure(
            "Cannot move second rack higher: this is a protective rack with fixed distance."
        )

    y_shift = (current_occupied_zone.contour.bounds[3] -
               current_rack.rack_2.contour.bounds[1]) + 1

    tail = y_shift % 50
    if tail != 0:
        y_shift += 50 - tail

    final_double_rack_internal_distance = y_shift + current_rack.rack_distance
    
    # Use correct max distance
    max_distance = reference_book.max_double_rack_internal_distance
    
    if final_double_rack_internal_distance > max_distance:
        logger.warning(f"[ZONES] Internal distance {final_double_rack_internal_distance:.1f} "
                      f"exceeds max {max_distance:.1f}")
        raise ActionFailure("Internal double rack distance is too big.")

    current_rack.move_second_rack_higher(y_shift)
    logger.warning(f"[ZONES] Moved second rack higher by {y_shift:.1f}mm "
                f"(new distance: {current_rack.rack_distance:.1f}mm)")


def remove_unavailable_rack_parts(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Removes unavailable rack parts.
    
    Args:
        reference_book (ReferenceBook): The reference book.
        solution (Solution): The current solution.
    """
    current_rack_group = solution.current_rack_group
    available_zone = solution.available_zones[solution.available_zone_idx]

    removed_count = 0
    for i, rack in enumerate(current_rack_group.racks):
        if isinstance(rack, Rack):
            continue
        bounds = rack.bounds
        upper_point = (bounds[0] + 1, bounds[3] + reference_book.roads_width)
        if not available_zone.contains_point(upper_point):
            current_rack_group.racks[i] = rack.rack_2
            removed_count += 1
    
    if removed_count > 0:
        logger.warning(f"[ZONES] Removed {removed_count} unavailable rack parts")


def check_if_vertical_allowed(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Checks if vertical rack placement is allowed in the current zone.
    
    Vertical placement is allowed when:
    - orientation == 2 (only vertical)
    - orientation == 0 (any orientation)
    
    Args:
        _: The reference book (not used).
        solution: The current solution.
    
    Raises:
        ActionFailure: If vertical placement is not allowed (orientation == 1).
    """
    available_zone = solution.available_zones[solution.available_zone_idx]
    
    if available_zone.orientation == 1:  # Only horizontal allowed
        logger.warning(f"[ORIENTATION] ✗ Vertical placement NOT allowed (orientation=1 - horizontal only)")
        raise ActionFailure("Vertical rack placement is not allowed in this zone")
    
    # orientation == 2 (vertical) or orientation == 0 (any) → SUCCESS
    logger.warning(f"[ORIENTATION] ✓ Vertical placement allowed (orientation={available_zone.orientation})")


def check_if_horizontal_allowed(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Checks if horizontal rack placement is allowed in the current zone.
    
    Horizontal placement is allowed when:
    - orientation == 1 (only horizontal)
    - orientation == 0 (any orientation)
    
    Args:
        _: The reference book (not used).
        solution: The current solution.
    
    Raises:
        ActionFailure: If horizontal placement is not allowed (orientation == 2).
    """
    available_zone = solution.available_zones[solution.available_zone_idx]
    
    if available_zone.orientation == 2:  # Only vertical allowed
        logger.warning(f"[ORIENTATION] ✗ Horizontal placement NOT allowed (orientation=2 - vertical only)")
        raise ActionFailure("Horizontal rack placement is not allowed in this zone")
    
    # orientation == 1 (horizontal) or orientation == 0 (any) → SUCCESS
    logger.warning(f"[ORIENTATION] ✓ Horizontal placement allowed (orientation={available_zone.orientation})")