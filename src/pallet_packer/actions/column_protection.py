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
    """Main function that executes Phase 1: identify all columns and protect them."""
    logger.warning("[COLUMN_PROTECTION] ========================================")
    logger.warning("[COLUMN_PROTECTION] Starting Phase 1: Protect all columns")
    logger.warning("[COLUMN_PROTECTION] ========================================")
    
    # Step 1: Identify columns
    identify_columns_in_zone(reference_book, solution)
    
    # Step 2: Create protective racks for all columns
    create_protective_double_racks_for_all_columns(reference_book, solution)
    
    # Step 3: Optimize if needed
    optimize_protective_racks(reference_book, solution)
    
    # Step 4: Save protective racks as regular rack_groups
    _save_protective_racks_as_rack_groups(reference_book, solution)
    
    logger.warning(f"[COLUMN_PROTECTION] Phase 1 complete. Protected {len(solution.protective_racks)} columns")
    logger.warning("[COLUMN_PROTECTION] ========================================")


def _save_protective_racks_as_rack_groups(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Saves all protective racks as regular rack groups in the solution."""
    if not solution.protective_racks:
        logger.warning("[COLUMN_PROTECTION] No protective racks to save")
        return
    
    available_zone = solution.available_zones[solution.available_zone_idx]
    zone_bounds = available_zone.bounds
    
    logger.warning("[COLUMN_PROTECTION] Saving protective racks as rack groups")
    
    saved_count = 0
    for idx, protective_rack in enumerate(solution.protective_racks):
        try:
            # Create a RackGroup for this protective rack
            rack_group = RackGroup(
                beam_types=solution.beam_types,
                upright_type=solution.upright_type,
                pallet=solution.pallets[solution.pallet_idx],
                max_shelfs=solution.max_shelfs,
                max_shelfs_bridge=solution.max_shelfs_bridge,
                position=(zone_bounds[0], protective_rack.bounds[1]),
                roads_width=reference_book.roads_width,
                pallet_extra_space=solution.pallet_extra_space,
                frame_height_eps=reference_book.frame_height_eps
            )
            
            # Add the protective rack to the group
            rack_group.racks.append(protective_rack)
            
            # IMPORTANT: Update RackGroup bounds if method exists
            if hasattr(rack_group, '_update_bounds'):
                rack_group._update_bounds()
            
            # Save to solution
            solution.saved_rack_groups.append(rack_group)
            saved_count += 1
            
        except Exception as e:
            logger.error(f"[COLUMN_PROTECTION] Failed to save rack {idx+1}: {e}")
            continue
    
    logger.warning(f"[COLUMN_PROTECTION] Saved {saved_count}/{len(solution.protective_racks)} protective racks")


def identify_columns_in_zone(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Identifies all columns (compact occupied zones) in the current zone."""
    solution.columns_in_zone = []
    remaining_occupied_zones = []
    
    for occupied_zone in solution.current_occupied_zones:
        if _is_column(occupied_zone, reference_book):
            solution.columns_in_zone.append(occupied_zone)
        else:
            remaining_occupied_zones.append(occupied_zone)
    
    # Update current_occupied_zones to exclude columns
    solution.current_occupied_zones = remaining_occupied_zones
    
    logger.warning(f"[COLUMN_PROTECTION] Found {len(solution.columns_in_zone)} columns, "
                f"{len(remaining_occupied_zones)} other obstacles")


def create_protective_double_racks_for_all_columns(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Creates protective double racks for all identified columns."""
    if not solution.columns_in_zone:
        logger.warning("[COLUMN_PROTECTION] No columns found to protect - skipping")
        return
    
    logger.warning(f"[COLUMN_PROTECTION] Creating protective racks for {len(solution.columns_in_zone)} columns")
    
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
            
        except Exception as e:
            logger.error(f"[COLUMN_PROTECTION] Failed to create rack {idx}: {e}")
            continue
    
    if not solution.protective_racks:
        raise ActionFailure("Failed to create any protective racks for columns")
    
    logger.warning(f"[COLUMN_PROTECTION] Created {len(solution.protective_racks)} protective racks")


def optimize_protective_racks(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Optimizes protective racks after creation."""
    if not solution.protective_racks:
        return
    
    # Sort protective racks by Y coordinate
    solution.protective_racks.sort(key=lambda r: r.bounds[1])
    
    # Strategy 1: Try to merge close protective racks
    _merge_close_protective_racks(solution, reference_book)
    
    # Strategy 2: Shorten racks near edges (if needed)
    _shorten_edge_protective_racks(solution, reference_book)


def analyze_free_strips(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Analyzes free strips between protective racks."""
    logger.warning("[COLUMN_PROTECTION] ========================================")
    logger.warning("[COLUMN_PROTECTION] Analyzing free strips")
    logger.warning("[COLUMN_PROTECTION] ========================================")
    
    available_zone = solution.available_zones[solution.available_zone_idx]
    zone_bounds = available_zone.bounds
    solution.free_strips = []
    
    if not solution.protective_racks:
        strip_width = zone_bounds[3] - zone_bounds[1]
        solution.free_strips.append({
            'y_min': zone_bounds[1],
            'y_max': zone_bounds[3],
            'width': strip_width,
            'index': 0
        })
        logger.warning(f"[COLUMN_PROTECTION] No racks - entire zone is free: {strip_width:.1f}mm")
        return
    
    # Deduplicate by Y coordinates
    unique_racks = []
    seen_bounds = set()
    for rack in solution.protective_racks:
        bounds_tuple = (round(rack.bounds[1], 1), round(rack.bounds[3], 1))
        if bounds_tuple not in seen_bounds:
            unique_racks.append(rack)
            seen_bounds.add(bounds_tuple)
    
    logger.warning(f"[COLUMN_PROTECTION] Deduplication: {len(solution.protective_racks)} total → {len(unique_racks)} unique")
    
    # Sort unique protective racks by Y coordinate
    sorted_racks = sorted(unique_racks, key=lambda r: r.bounds[1])
    
    # Strip below first rack
    first_rack = sorted_racks[0]
    strip_y_min = zone_bounds[1]
    strip_y_max = first_rack.bounds[1] - reference_book.roads_width
    strip_width = strip_y_max - strip_y_min
    
    if strip_width >= reference_book.min_free_strip_width:
        solution.free_strips.append({
            'y_min': strip_y_min,
            'y_max': strip_y_max,
            'width': strip_width,
            'index': len(solution.free_strips)
        })
    
    # Strips between consecutive racks
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
    
    # Strip above last rack
    last_rack = sorted_racks[-1]
    strip_y_min = last_rack.bounds[3] + reference_book.roads_width
    strip_y_max = zone_bounds[3]
    strip_width = strip_y_max - strip_y_min
    
    if strip_width >= reference_book.min_free_strip_width:
        solution.free_strips.append({
            'y_min': strip_y_min,
            'y_max': strip_y_max,
            'width': strip_width,
            'index': len(solution.free_strips)
        })
    
    logger.warning(f"[COLUMN_PROTECTION] Found {len(solution.free_strips)} free strips")
    if solution.free_strips:
        total_free = sum(s['width'] for s in solution.free_strips)
        logger.warning(f"[COLUMN_PROTECTION] Total free: {total_free:.1f}mm of {zone_bounds[3]-zone_bounds[1]:.1f}mm")


def set_first_free_strip(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Sets the current strip index to 0 (first free strip)."""
    if not solution.free_strips:
        logger.warning("[COLUMN_PROTECTION] No free strips available!")
        raise ActionFailure("No free strips available for rack placement")
    
    solution.current_strip_idx = 0
    strip = solution.free_strips[0]
    logger.warning(f"[COLUMN_PROTECTION] Set first strip: Y=[{strip['y_min']:.1f}, {strip['y_max']:.1f}], "
                f"width={strip['width']:.1f}mm")


def check_if_more_strips_available(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Checks if there are more free strips to process.
    
    ✅ CRITICAL: This function MUST return FAILURE (raise ActionFailure) 
    when all strips are processed, so the state machine proceeds to 
    rotate_everything_90_counterclockwise and then split_available_zone.
    """
    if solution.current_strip_idx >= len(solution.free_strips) - 1:
        logger.warning("[COLUMN_PROTECTION] All strips processed")
        # ✅ This MUST be ActionFailure to trigger rotation back!
        raise ActionFailure("No more free strips to process")
    
    logger.warning(f"[COLUMN_PROTECTION] More strips available: "
                  f"{len(solution.free_strips) - solution.current_strip_idx - 1} remaining")


def set_next_free_strip(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Moves to the next free strip."""
    if solution.current_strip_idx >= len(solution.free_strips) - 1:
        logger.error("[COLUMN_PROTECTION] Already at last strip!")
        raise ActionFailure("Already at last free strip")
    
    solution.current_strip_idx += 1
    strip = solution.free_strips[solution.current_strip_idx]
    logger.warning(f"[COLUMN_PROTECTION] Set next strip {solution.current_strip_idx}: "
                f"Y=[{strip['y_min']:.1f}, {strip['y_max']:.1f}], width={strip['width']:.1f}mm")


# =============================================================================
# HELPER FUNCTIONS (internal)
# =============================================================================

def _is_column(occupied_zone: OccupiedZone, reference_book: ReferenceBook) -> bool:
    """Determines if an occupied zone is a column."""
    bounds = occupied_zone.contour.bounds
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    
    if min(width, height) == 0:
        return False
    
    aspect_ratio = max(width, height) / min(width, height)
    max_dimension = max(width, height)
    
    is_compact = aspect_ratio <= reference_book.column_identification_max_aspect_ratio
    is_small = max_dimension <= reference_book.column_identification_max_size
    is_not_available = not occupied_zone.should_be_available
    
    return is_compact and is_small and is_not_available


def _calculate_dynamic_rack_distance_for_column(
    column: OccupiedZone,
    reference_book: ReferenceBook
) -> float:
    """Calculates the required distance between double rack halves for a column.
    
    Uses a fixed distance of 1000mm to match the maximum available jumper
    from the rack configuration (jumper_1000).
    """
    distance = 1000.0
    return distance


def _create_protective_rack_for_column(
    column: OccupiedZone,
    available_zone,
    reference_book: ReferenceBook,
    solution: Solution
) -> DoubleRack:
    """Creates a single protective double rack for a column."""
    column_bounds = column.contour.bounds
    zone_bounds = available_zone.bounds
    pallet = solution.pallets[solution.pallet_idx]
    
    # Calculate rack distance
    rack_distance = _calculate_dynamic_rack_distance_for_column(column, reference_book)
    
    # Calculate actual rack height
    actual_gap = rack_distance - reference_book.double_rack_distance_eps
    total_rack_height = 2 * pallet.length + actual_gap
    
    # Calculate available space
    zone_height = zone_bounds[3] - zone_bounds[1]
    available_height = zone_height - 2 * reference_book.roads_width
    
    if total_rack_height > available_height:
        logger.error(f"[COLUMN_PROTECTION] Rack too tall: {total_rack_height:.1f} > {available_height:.1f}")
        raise ValueError(f"Rack too tall: {total_rack_height:.1f} > {available_height:.1f}")
    
    # Center rack relative to column
    column_center_y = (column_bounds[1] + column_bounds[3]) / 2
    first_rack_y = column_center_y - (total_rack_height / 2)
    
    # Apply zone constraints
    min_first_rack_y = zone_bounds[1] + reference_book.roads_width
    max_first_rack_y = zone_bounds[3] - reference_book.roads_width - total_rack_height
    first_rack_y = max(min_first_rack_y, min(first_rack_y, max_first_rack_y))
    
    position = (zone_bounds[0], first_rack_y)
    
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
        
        rack_bounds = protective_rack.bounds
        
        # Verify boundaries
        min_allowed_y = zone_bounds[1] + reference_book.roads_width
        max_allowed_y = zone_bounds[3] - reference_book.roads_width
        
        if rack_bounds[1] < min_allowed_y:
            logger.error(f"[COLUMN_PROTECTION] Rack too low: {rack_bounds[1]:.1f} < {min_allowed_y:.1f}")
            raise ValueError("Rack violates bottom road")
        
        if rack_bounds[3] > max_allowed_y:
            logger.error(f"[COLUMN_PROTECTION] Rack too high: {rack_bounds[3]:.1f} > {max_allowed_y:.1f}")
            raise ValueError("Rack violates top road")
        
        rack1_end = protective_rack.rack_1.bounds[3]
        rack2_start = protective_rack.rack_2.bounds[1]
        
        if column_bounds[1] < rack1_end or column_bounds[3] > rack2_start:
            logger.error(f"[COLUMN_PROTECTION] Column not in gap!")
        
        # Fill with frames
        _fill_protective_rack_with_frames(protective_rack, available_zone)
        
        return protective_rack
        
    except Exception as e:
        logger.error(f"[COLUMN_PROTECTION] Failed: {e}")
        raise ValueError(f"Cannot create rack: {e}")


def _fill_protective_rack_with_frames(
    protective_rack: DoubleRack,
    available_zone
) -> None:
    """Fills a protective rack with as many frames as possible."""
    section_length = (protective_rack.rack_1.beam_type.length + 
                     protective_rack.rack_1.upright_type.width)
    
    zone_bounds = available_zone.bounds
    max_available_length = zone_bounds[2] - protective_rack.bounds[0]
    
    frames_count = max(0, int(max_available_length // section_length))
    
    if frames_count > 0:
        protective_rack.add_multiple_frames(frames_count)
    
    # Verify fit
    if not shapely.contains(available_zone.contour, protective_rack.contour):
        original = len(protective_rack.rack_1)
        while not shapely.contains(available_zone.contour, protective_rack.contour) and len(protective_rack.rack_1) > 0:
            protective_rack.delete_last_frame()


def _merge_close_protective_racks(
    solution: Solution,
    reference_book: ReferenceBook
) -> None:
    """Attempts to merge protective racks if their columns are close together."""
    if len(solution.protective_racks) < 2:
        return
    
    for i in range(len(solution.protective_racks) - 1):
        current_rack = solution.protective_racks[i]
        next_rack = solution.protective_racks[i + 1]
        
        current_column = current_rack.protected_column
        next_column = next_rack.protected_column
        
        gap = next_column.bounds[1] - current_column.bounds[3]
        
        if gap < reference_book.roads_width:
            logger.warning(f"[COLUMN_PROTECTION] Close racks {i}/{i+1}: gap={gap:.1f}mm")


def _shorten_edge_protective_racks(
    solution: Solution,
    reference_book: ReferenceBook
) -> None:
    """Shortens protective racks that are near zone edges if beneficial."""
    available_zone = solution.available_zones[solution.available_zone_idx]
    zone_bounds = available_zone.bounds
    
    for idx, protective_rack in enumerate(solution.protective_racks):
        column = protective_rack.protected_column
        column_bounds = column.bounds
        
        distance_to_left = column_bounds[0] - zone_bounds[0]
        distance_to_right = zone_bounds[2] - column_bounds[2]
        
        if distance_to_left < reference_book.roads_width * 2:
            logger.warning(f"[COLUMN_PROTECTION] Rack {idx} near left: {distance_to_left:.1f}mm")
        
        if distance_to_right < reference_book.roads_width * 2:
            logger.warning(f"[COLUMN_PROTECTION] Rack {idx} near right: {distance_to_right:.1f}mm")