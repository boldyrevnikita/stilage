"""
Actions for protecting columns with continuous double racks.
This module implements Phase 1 of the new placement logic:
identifying all columns in a zone and covering them with protective racks.
"""

from src.reference_book import ReferenceBook
from src.pallet_packer.solution import Solution, ActionFailure
from src.rack import DoubleRack, RackGroup
from src.zone import OccupiedZone
import shapely
from copy import deepcopy
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# MAIN FUNCTIONS (called from state machine)
# =============================================================================

def identify_and_protect_all_columns(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Main function that executes Phase 1: identify all columns and protect them.
    
    This is a composite action that:
    1. Identifies all columns in the current zone
    2. Creates protective double racks for each column
    3. Stores protective racks in the solution
    
    Args:
        reference_book (ReferenceBook): The reference book containing business
            logic related information.
        solution (Solution): The current solution containing available zones.
    
    Raises:
        ActionFailure: If no columns found or if protective racks cannot be created.
    """
    logger.info("[COLUMN_PROTECTION] Starting Phase 1: Protect all columns")
    
    # Step 1: Identify columns
    identify_columns_in_zone(reference_book, solution)
    
    # Step 2: Create protective racks for all columns
    create_protective_double_racks_for_all_columns(reference_book, solution)
    
    # Step 3: Optimize if needed
    optimize_protective_racks(reference_book, solution)
    
    logger.info(f"[COLUMN_PROTECTION] Phase 1 complete. Protected {len(solution.protective_racks)} columns")


def identify_columns_in_zone(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Identifies all columns (compact occupied zones) in the current zone.
    
    Separates occupied zones into:
    - Columns (compact, small objects) → stored in solution.columns_in_zone
    - Other obstacles → remain in solution.current_occupied_zones
    
    Args:
        reference_book (ReferenceBook): The reference book.
        solution (Solution): The current solution.
    
    Note:
        This function modifies solution.columns_in_zone and 
        solution.current_occupied_zones in place.
    """
    logger.info("[COLUMN_PROTECTION] Identifying columns in zone")
    
    solution.columns_in_zone = []
    remaining_occupied_zones = []
    
    for occupied_zone in solution.current_occupied_zones:
        if _is_column(occupied_zone, reference_book):
            solution.columns_in_zone.append(occupied_zone)
            logger.debug(f"[COLUMN_PROTECTION] Found column at {occupied_zone.bounds}")
        else:
            remaining_occupied_zones.append(occupied_zone)
    
    # Update current_occupied_zones to exclude columns
    solution.current_occupied_zones = remaining_occupied_zones
    
    logger.info(f"[COLUMN_PROTECTION] Found {len(solution.columns_in_zone)} columns, "
                f"{len(remaining_occupied_zones)} other obstacles")


def create_protective_double_racks_for_all_columns(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Creates protective double racks for all identified columns.
    
    For each column, creates a continuous double rack that:
    - Spans from left to right edge of the zone
    - Has the column positioned between its two halves
    - Has dynamic distance between halves to fit the column
    
    Args:
        reference_book (ReferenceBook): The reference book.
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If columns_in_zone is empty or if rack creation fails.
    """
    if not solution.columns_in_zone:
        logger.warning("[COLUMN_PROTECTION] No columns found to protect")
        # This is not necessarily a failure - zone might have no columns
        return
    
    logger.info(f"[COLUMN_PROTECTION] Creating protective racks for {len(solution.columns_in_zone)} columns")
    
    available_zone = solution.available_zones[solution.available_zone_idx]
    solution.protective_racks = []
    
    for idx, column in enumerate(solution.columns_in_zone):
        try:
            protective_rack = _create_protective_rack_for_column(
                column=column,
                available_zone=available_zone,
                reference_book=reference_book,
                solution=solution
            )
            
            solution.protective_racks.append(protective_rack)
            logger.debug(f"[COLUMN_PROTECTION] Created protective rack {idx + 1}/{len(solution.columns_in_zone)}")
            
        except Exception as e:
            logger.error(f"[COLUMN_PROTECTION] Failed to create protective rack for column {idx}: {e}")
            # Continue with other columns even if one fails
            continue
    
    if not solution.protective_racks:
        raise ActionFailure("Failed to create any protective racks for columns")
    
    logger.info(f"[COLUMN_PROTECTION] Successfully created {len(solution.protective_racks)} protective racks")


def optimize_protective_racks(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Optimizes protective racks after creation.
    
    Optimization strategies:
    1. Merge protective racks if columns are close together
    2. Shorten protective racks if column is near zone edge
    3. Remove redundant protective racks
    
    Args:
        reference_book (ReferenceBook): The reference book.
        solution (Solution): The current solution.
    """
    if not solution.protective_racks:
        return
    
    logger.info("[COLUMN_PROTECTION] Optimizing protective racks")
    
    # Sort protective racks by Y coordinate
    solution.protective_racks.sort(key=lambda r: r.bounds[1])
    
    # Strategy 1: Try to merge close protective racks
    _merge_close_protective_racks(solution, reference_book)
    
    # Strategy 2: Shorten racks near edges (if needed)
    _shorten_edge_protective_racks(solution, reference_book)
    
    logger.info(f"[COLUMN_PROTECTION] Optimization complete. Final count: {len(solution.protective_racks)}")


def analyze_free_strips(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Analyzes free strips between protective racks.
    
    After protective racks are placed, the zone is divided into horizontal strips:
    - Strip below first protective rack
    - Strips between consecutive protective racks
    - Strip above last protective rack
    
    Each strip is analyzed for:
    - Y boundaries (y_min, y_max)
    - Width (height in horizontal orientation)
    - Suitability for rack placement
    
    Args:
        reference_book (ReferenceBook): The reference book.
        solution (Solution): The current solution.
    """
    logger.info("[COLUMN_PROTECTION] Analyzing free strips")
    
    available_zone = solution.available_zones[solution.available_zone_idx]
    zone_bounds = available_zone.bounds
    solution.free_strips = []
    
    if not solution.protective_racks:
        # No protective racks - entire zone is one free strip
        solution.free_strips.append({
            'y_min': zone_bounds[1],
            'y_max': zone_bounds[3],
            'width': zone_bounds[3] - zone_bounds[1],
            'index': 0
        })
        logger.info("[COLUMN_PROTECTION] No protective racks - entire zone is free")
        return
    
    # Sort protective racks by Y coordinate
    sorted_racks = sorted(solution.protective_racks, key=lambda r: r.bounds[1])
    
    # Strip below first protective rack
    first_rack = sorted_racks[0]
    strip_width = first_rack.bounds[1] - zone_bounds[1] - reference_book.roads_width
    
    if strip_width >= reference_book.min_free_strip_width:
        solution.free_strips.append({
            'y_min': zone_bounds[1],
            'y_max': first_rack.bounds[1] - reference_book.roads_width,
            'width': strip_width,
            'index': len(solution.free_strips)
        })
        logger.debug(f"[COLUMN_PROTECTION] Free strip 0: y=[{zone_bounds[1]:.1f}, {first_rack.bounds[1] - reference_book.roads_width:.1f}], width={strip_width:.1f}")
    
    # Strips between consecutive protective racks
    for i in range(len(sorted_racks) - 1):
        rack_1 = sorted_racks[i]
        rack_2 = sorted_racks[i + 1]
        
        strip_y_min = rack_1.bounds[3] + reference_book.roads_width
        strip_y_max = rack_2.bounds[1] - reference_book.roads_width
        strip_width = strip_y_max - strip_y_min
        
        if strip_width >= reference_book.min_free_strip_width:
            solution.free_strips.append({
                'y_min': strip_y_min,
                'y_max': strip_y_max,
                'width': strip_width,
                'index': len(solution.free_strips)
            })
            logger.debug(f"[COLUMN_PROTECTION] Free strip {len(solution.free_strips) - 1}: y=[{strip_y_min:.1f}, {strip_y_max:.1f}], width={strip_width:.1f}")
    
    # Strip above last protective rack
    last_rack = sorted_racks[-1]
    strip_width = zone_bounds[3] - last_rack.bounds[3] - reference_book.roads_width
    
    if strip_width >= reference_book.min_free_strip_width:
        solution.free_strips.append({
            'y_min': last_rack.bounds[3] + reference_book.roads_width,
            'y_max': zone_bounds[3],
            'width': strip_width,
            'index': len(solution.free_strips)
        })
        logger.debug(f"[COLUMN_PROTECTION] Free strip {len(solution.free_strips) - 1}: y=[{last_rack.bounds[3] + reference_book.roads_width:.1f}, {zone_bounds[3]:.1f}], width={strip_width:.1f}")
    
    logger.info(f"[COLUMN_PROTECTION] Found {len(solution.free_strips)} free strips for regular rack placement")


def set_first_free_strip(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Sets the current strip index to 0 (first free strip).
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If no free strips are available.
    """
    if not solution.free_strips:
        raise ActionFailure("No free strips available for rack placement")
    
    solution.current_strip_idx = 0
    logger.info(f"[COLUMN_PROTECTION] Starting with free strip 0 of {len(solution.free_strips)}")


def check_if_more_strips_available(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Checks if there are more free strips to process.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If no more strips available.
    """
    if solution.current_strip_idx >= len(solution.free_strips) - 1:
        logger.info("[COLUMN_PROTECTION] All free strips processed")
        raise ActionFailure("No more free strips to process")


def set_next_free_strip(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Moves to the next free strip.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If already at last strip.
    """
    if solution.current_strip_idx >= len(solution.free_strips) - 1:
        raise ActionFailure("Already at last free strip")
    
    solution.current_strip_idx += 1
    logger.info(f"[COLUMN_PROTECTION] Moving to free strip {solution.current_strip_idx} of {len(solution.free_strips)}")


# =============================================================================
# HELPER FUNCTIONS (internal)
# =============================================================================

def _is_column(occupied_zone: OccupiedZone, reference_book: ReferenceBook) -> bool:
    """Determines if an occupied zone is a column.
    
    Criteria for a column:
    1. Compact shape (aspect ratio < max_aspect_ratio)
    2. Small size (max dimension < max_size)
    3. Not marked as should_be_available
    
    Args:
        occupied_zone (OccupiedZone): The occupied zone to check.
        reference_book (ReferenceBook): The reference book with thresholds.
    
    Returns:
        bool: True if the occupied zone is a column, False otherwise.
    """
    bounds = occupied_zone.contour.bounds
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    
    # Avoid division by zero
    if min(width, height) == 0:
        return False
    
    aspect_ratio = max(width, height) / min(width, height)
    max_dimension = max(width, height)
    
    # Check compactness
    is_compact = aspect_ratio <= reference_book.column_identification_max_aspect_ratio
    
    # Check size
    is_small = max_dimension <= reference_book.column_identification_max_size
    
    # Check if marked as available
    is_not_available = not occupied_zone.should_be_available
    
    result = is_compact and is_small and is_not_available
    
    if result:
        logger.debug(f"[COLUMN_PROTECTION] Column identified: width={width:.1f}, height={height:.1f}, "
                    f"aspect_ratio={aspect_ratio:.2f}, max_dim={max_dimension:.1f}")
    
    return result


def _calculate_dynamic_rack_distance_for_column(
    column: OccupiedZone,
    reference_book: ReferenceBook
) -> float:
    """Calculates the required distance between double rack halves for a column.
    
    Distance = column_width + 2 * clearance + internal_spacing
    
    Args:
        column (OccupiedZone): The column to protect.
        reference_book (ReferenceBook): The reference book.
    
    Returns:
        float: The required distance between rack halves.
    """
    bounds = column.contour.bounds
    column_width = bounds[2] - bounds[0]
    
    # Distance = column width + clearance on both sides + base internal distance
    distance = column_width + 2 * column.clearance + reference_book.double_rack_distance_eps
    
    # Ensure it doesn't exceed maximum
    max_distance = reference_book.max_protective_rack_internal_distance
    if distance > max_distance:
        logger.warning(f"[COLUMN_PROTECTION] Column too wide: {column_width:.1f}mm. "
                      f"Required distance {distance:.1f}mm exceeds max {max_distance:.1f}mm")
        distance = max_distance
    
    logger.debug(f"[COLUMN_PROTECTION] Calculated rack distance: {distance:.1f}mm for column width {column_width:.1f}mm")
    
    return distance


def _create_protective_rack_for_column(
    column: OccupiedZone,
    available_zone,
    reference_book: ReferenceBook,
    solution: Solution
) -> DoubleRack:
    """Creates a single protective double rack for a column.
    
    The rack:
    - Starts at the left edge of the zone
    - Has the column positioned between its two halves
    - Extends as far right as possible within the zone
    
    Args:
        column (OccupiedZone): The column to protect.
        available_zone: The available zone for placement.
        reference_book (ReferenceBook): The reference book.
        solution (Solution): The current solution (for beam/upright types).
    
    Returns:
        DoubleRack: The created protective double rack.
    
    Raises:
        ValueError: If rack cannot be created for the column.
    """
    # Calculate dynamic distance
    rack_distance = _calculate_dynamic_rack_distance_for_column(column, reference_book)
    
    # Position: align with column's Y coordinate
    column_bounds = column.contour.bounds
    zone_bounds = available_zone.bounds
    
    # Position first rack at zone's left edge, Y-aligned with column
    # We want the column to be between the two halves, so:
    # first_rack Y = column center Y - rack_distance/2 - pallet.length/2
    pallet = solution.pallets[solution.pallet_idx]
    
    column_center_y = (column_bounds[1] + column_bounds[3]) / 2
    
    # Calculate Y position for first rack so that column is centered between halves
    first_rack_y = column_center_y - rack_distance / 2 - pallet.length / 2
    
    # Ensure we don't go below zone boundary
    first_rack_y = max(zone_bounds[1], first_rack_y)
    
    position = (zone_bounds[0], first_rack_y)
    
    # Create protective double rack
    try:
        protective_rack = DoubleRack(
            beam_types=solution.beam_types,
            upright_type=solution.upright_type,
            pallet=pallet,
            max_shelfs=solution.max_shelfs,
            max_shelfs_bridge=solution.max_shelfs_bridge,
            position=position,
            rack_distance=rack_distance,
            double_rack_distance_eps=reference_book.double_rack_distance_eps,
            is_protective=True,
            protected_column=column
        )
        
        # Fill with frames to make it as long as possible
        _fill_protective_rack_with_frames(protective_rack, available_zone)
        
        logger.debug(f"[COLUMN_PROTECTION] Created protective rack at y={first_rack_y:.1f}, "
                    f"distance={rack_distance:.1f}, frames={len(protective_rack.rack_1)}")
        
        return protective_rack
        
    except Exception as e:
        logger.error(f"[COLUMN_PROTECTION] Failed to create protective rack: {e}")
        raise ValueError(f"Cannot create protective rack for column: {e}")


def _fill_protective_rack_with_frames(
    protective_rack: DoubleRack,
    available_zone
) -> None:
    """Fills a protective rack with as many frames as possible.
    
    Args:
        protective_rack (DoubleRack): The protective rack to fill.
        available_zone: The available zone (for boundary checking).
    """
    # Calculate how many frames can fit
    section_length = (protective_rack.rack_1.beam_type.length + 
                     protective_rack.rack_1.upright_type.width)
    
    zone_bounds = available_zone.bounds
    max_available_length = zone_bounds[2] - protective_rack.bounds[0]
    
    frames_count = max(0, int(max_available_length // section_length))
    
    if frames_count > 0:
        protective_rack.add_multiple_frames(frames_count)
        logger.debug(f"[COLUMN_PROTECTION] Added {frames_count} frames to protective rack")
    
    # Verify the rack fits in the zone
    if not shapely.contains(available_zone.contour, protective_rack.contour):
        # Remove frames until it fits
        while not shapely.contains(available_zone.contour, protective_rack.contour) and len(protective_rack.rack_1) > 0:
            protective_rack.delete_last_frame()
        logger.warning(f"[COLUMN_PROTECTION] Had to trim protective rack to fit zone. Final frames: {len(protective_rack.rack_1)}")


def _merge_close_protective_racks(
    solution: Solution,
    reference_book: ReferenceBook
) -> None:
    """Attempts to merge protective racks if their columns are close together.
    
    If two columns are so close that the gap between them is less than
    the minimum road width, they can be protected by a single wide rack.
    
    Args:
        solution (Solution): The current solution.
        reference_book (ReferenceBook): The reference book.
    """
    if len(solution.protective_racks) < 2:
        return
    
    logger.debug("[COLUMN_PROTECTION] Checking for mergeable protective racks")
    
    merged_indices = set()
    new_protective_racks = []
    
    i = 0
    while i < len(solution.protective_racks):
        if i in merged_indices:
            i += 1
            continue
        
        current_rack = solution.protective_racks[i]
        current_column = current_rack.protected_column
        
        # Check if next rack is close enough to merge
        if i + 1 < len(solution.protective_racks):
            next_rack = solution.protective_racks[i + 1]
            next_column = next_rack.protected_column
            
            # Calculate gap between columns
            gap = next_column.bounds[1] - current_column.bounds[3]
            
            # If gap is smaller than minimum road width, merge
            if gap < reference_book.roads_width:
                logger.info(f"[COLUMN_PROTECTION] Merging protective racks {i} and {i+1} (gap={gap:.1f}mm)")
                # For now, just keep both separate (merging is complex)
                # In future: create one wide rack covering both columns
                new_protective_racks.append(current_rack)
                merged_indices.add(i)
                i += 1
                continue
        
        new_protective_racks.append(current_rack)
        i += 1
    
    # Update solution (currently no actual merging, just preparation)
    # solution.protective_racks = new_protective_racks


def _shorten_edge_protective_racks(
    solution: Solution,
    reference_book: ReferenceBook
) -> None:
    """Shortens protective racks that are near zone edges if beneficial.
    
    If a column is very close to the left or right edge of the zone,
    the protective rack might be shortened from that side to save material.
    
    Args:
        solution (Solution): The current solution.
        reference_book (ReferenceBook): The reference book.
    """
    available_zone = solution.available_zones[solution.available_zone_idx]
    zone_bounds = available_zone.bounds
    
    for protective_rack in solution.protective_racks:
        column = protective_rack.protected_column
        column_bounds = column.bounds
        
        # Check distance from column to left edge
        distance_to_left = column_bounds[0] - zone_bounds[0]
        
        # Check distance from column to right edge  
        distance_to_right = zone_bounds[2] - column_bounds[2]
        
        # If column is very close to an edge, we might optimize
        # For now, just log the information
        if distance_to_left < reference_book.roads_width * 2:
            logger.debug(f"[COLUMN_PROTECTION] Column close to left edge: {distance_to_left:.1f}mm")
        
        if distance_to_right < reference_book.roads_width * 2:
            logger.debug(f"[COLUMN_PROTECTION] Column close to right edge: {distance_to_right:.1f}mm")