"""
Actions for handling zones and obstacles in the pallet packing system.

This module contains functions for zone management, rotation, splitting,
and checking intersections with occupied zones and road zones.
"""

from src.reference_book import ReferenceBook
from src.pallet_packer.solution import Solution, ActionFailure
from src.rack import Rack
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
    """Rotates the available zone's contour 90 degrees clockwise.

    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution containing available zones.
    """
    available_zone = solution.available_zones[solution.available_zone_idx]
    solution.rot_point = available_zone.bounds[:2]
    angle = -90

    available_zone.rotate(solution.rot_point, angle)
    for occupied_zone in solution.current_occupied_zones:
        occupied_zone.rotate(solution.rot_point, angle)
    for road_zone in solution.current_road_zones:
        road_zone.rotate(solution.rot_point, angle)
    
    # NEW: Also rotate columns and protective racks
    for column in solution.columns_in_zone:
        column.rotate(solution.rot_point, angle)
    for protective_rack in solution.protective_racks:
        protective_rack.rotate(angle, solution.rot_point)

    solution.is_rotated = True

    solution.current_occupied_zones.sort(key=lambda x: x.bounds[0])
    solution.current_road_zones.sort(key=lambda x: x.bounds[0])
    
    logger.debug("[ZONES] Rotated everything 90 degrees clockwise")


def rotate_everything_90_counterclockwise(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Rotates the available zone's contour 90 degrees counterclockwise.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    """
    if solution.is_rotated:
        available_zone = solution.available_zones[solution.available_zone_idx]
        angle = 90

        available_zone.rotate(solution.rot_point, angle)
        for occupied_zone in solution.current_occupied_zones:
            occupied_zone.rotate(solution.rot_point, angle)
        for road_zone in solution.current_road_zones:
            road_zone.rotate(solution.rot_point, angle)
        
        # NEW: Also rotate columns and protective racks
        for column in solution.columns_in_zone:
            column.rotate(solution.rot_point, angle)
        for protective_rack in solution.protective_racks:
            protective_rack.rotate(angle, solution.rot_point)
        
        solution.current_rack_group.rotate(angle, solution.rot_point)

        solution.is_rotated = False

        solution.current_occupied_zones.sort(
            key=lambda x: (x.bounds[0], x.bounds[2]))
        solution.current_road_zones.sort(
            key=lambda x: (x.bounds[0], x.bounds[2]))
        
        logger.debug("[ZONES] Rotated everything 90 degrees counterclockwise")


# =============================================================================
# ZONE NAVIGATION FUNCTIONS
# =============================================================================

def set_next_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Sets the next available zone as the current one.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If no more zones available.
    """
    if solution.available_zone_idx >= len(solution.available_zones) - 1:
        raise ActionFailure("No more available zones to process.")

    solution.available_zone_idx += 1
    logger.info(f"[ZONES] Moving to zone {solution.available_zone_idx + 1}/{len(solution.available_zones)}")


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
    logger.debug("[ZONES] Reset to zone 0")


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
    
    logger.debug("[ZONES] Rack fits in available zone and strip")


def split_available_zone(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Splits the available zone into two parts.
    
    Args:
        reference_book (ReferenceBook): The reference book.
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If no racks are placed (nothing to split around).
    """
    if len(solution.current_rack_group.racks) == 0:
        raise ActionFailure("No racks are placed.")

    current_rack_group = solution.current_rack_group
    available_zone = solution.available_zones[solution.available_zone_idx]
    split_point = list(current_rack_group.bounds[2:])
    split_point[0] += reference_book.roads_width
    split_point[1] += reference_book.roads_width
    split_point[0] = min(available_zone.bounds[2], split_point[0]) - 1
    split_point[1] = min(available_zone.bounds[3], split_point[1]) - 1

    if available_zone.contains_point(split_point):
        new_zones = available_zone.split_zone(split_point)
        solution.available_zones.extend(new_zones)
        logger.info(f"[ZONES] Split zone at point {split_point}. Created {len(new_zones)} new zones")

    solution.available_zones.pop(solution.available_zone_idx)
    solution.available_zone_idx -= 1
    logger.debug(f"[ZONES] Total zones now: {len(solution.available_zones)}")


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
    logger.debug(f"[ZONES] Sorted {len(solution.available_zones)} zones by area and height")


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
            logger.debug(f"[ZONES] Found occupied zone in zone: bounds={occupied_zone.bounds}")

    # Process road zones
    for road_zone in solution.road_zones:
        if shapely.intersects(road_zone.contour, available_zone.contour):
            solution.current_road_zones.append(deepcopy(road_zone))
            logger.debug(f"[ZONES] Found road zone in zone: bounds={road_zone.bounds}")

    # Sort for consistent processing order
    solution.current_occupied_zones.sort(key=lambda x: (x.bounds[0], x.bounds[2]))
    solution.current_road_zones.sort(key=lambda x: (x.bounds[0], x.bounds[2]))
    
    logger.info(f"[ZONES] Zone obstacles: {len(solution.current_occupied_zones)} obstacles, "
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
            logger.debug(f"[ZONES] Skipping protected column at {occupied_zone.bounds}")
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
            logger.debug(f"[ZONES] Rack intersects occupied zone at {occupied_zone.bounds}")
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
    
    logger.debug("[ZONES] Both racks intersect occupied zone")


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

            logger.debug(f"[ZONES] Rack intersects road zone at {road_zone.bounds}")
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
        logger.debug(f"[ZONES] Rack intersects with zone at {intersected_special_zone.bounds}")
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
    logger.debug("[ZONES] Placed road zones on right and top edges")


def move_second_rack_higher_over_oz(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Moves the second rack higher over the occupied zone.
    
    Args:
        reference_book (ReferenceBook): The reference book.
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If internal distance becomes too large.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    current_occupied_zone = solution.intersected_special_zone

    y_shift = (current_occupied_zone.contour.bounds[3] -
               current_rack.rack_2.contour.bounds[1]) + 1

    tail = y_shift % 50
    if tail != 0:
        y_shift += 50 - tail

    final_double_rack_internal_distance = y_shift + current_rack.rack_distance
    
    # Use different max distance for protective racks
    if current_rack.is_protective:
        max_distance = reference_book.max_protective_rack_internal_distance
    else:
        max_distance = reference_book.max_double_rack_internal_distance
    
    if final_double_rack_internal_distance > max_distance:
        logger.warning(f"[ZONES] Internal distance {final_double_rack_internal_distance:.1f} "
                      f"exceeds max {max_distance:.1f}")
        raise ActionFailure("Internal double rack distance is too big.")

    current_rack.move_second_rack_higher(y_shift)
    logger.debug(f"[ZONES] Moved second rack higher by {y_shift:.1f}mm")


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
        logger.info(f"[ZONES] Removed {removed_count} unavailable rack parts")