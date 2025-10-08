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
    print("=" * 80)
    print("COLUMN PROTECTION: FUNCTION CALLED!")
    print("=" * 80)
    logger.info("[COLUMN_PROTECTION NEW LOGS] ========================================")
    logger.info("[COLUMN_PROTECTION] Starting Phase 1: Protect all columns")
    logger.info("[COLUMN_PROTECTION] ========================================")
    
    # Step 1: Identify columns
    identify_columns_in_zone(reference_book, solution)
    
    # Step 2: Create protective racks for all columns
    create_protective_double_racks_for_all_columns(reference_book, solution)
    
    # Step 3: Optimize if needed
    optimize_protective_racks(reference_book, solution)
    
    logger.info(f"[COLUMN_PROTECTION] Phase 1 complete. Protected {len(solution.protective_racks)} columns")
    logger.info("[COLUMN_PROTECTION] ========================================")


def identify_columns_in_zone(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Identifies all columns (compact occupied zones) in the current zone."""
    logger.info("[COLUMN_PROTECTION] Identifying columns in zone")
    logger.info(f"[COLUMN_PROTECTION] Initial obstacles: {len(solution.current_occupied_zones)}")
    logger.info(f"[COLUMN_PROTECTION] Thresholds: max_size={reference_book.column_identification_max_size:.1f}mm, "
                f"max_aspect={reference_book.column_identification_max_aspect_ratio:.2f}")
    
    solution.columns_in_zone = []
    remaining_occupied_zones = []
    
    for idx, occupied_zone in enumerate(solution.current_occupied_zones):
        bounds = occupied_zone.contour.bounds
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        
        if _is_column(occupied_zone, reference_book):
            solution.columns_in_zone.append(occupied_zone)
            logger.info(f"[COLUMN_PROTECTION] ✓ Column {len(solution.columns_in_zone)}: "
                       f"y_bounds=[{bounds[1]:.1f}, {bounds[3]:.1f}], "
                       f"width={width:.1f}, height={height:.1f}")
        else:
            remaining_occupied_zones.append(occupied_zone)
            logger.info(f"[COLUMN_PROTECTION] ✗ Not a column {idx}: "
                        f"width={width:.1f}, height={height:.1f}")
    
    # Update current_occupied_zones to exclude columns
    solution.current_occupied_zones = remaining_occupied_zones
    
    logger.info(f"[COLUMN_PROTECTION] ========================================")
    logger.info(f"[COLUMN_PROTECTION] RESULT: {len(solution.columns_in_zone)} columns, "
                f"{len(remaining_occupied_zones)} other obstacles")
    logger.info(f"[COLUMN_PROTECTION] ========================================")


def create_protective_double_racks_for_all_columns(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Creates protective double racks for all identified columns."""
    if not solution.columns_in_zone:
        logger.warning("[COLUMN_PROTECTION] No columns found to protect - skipping")
        return
    
    logger.info(f"[COLUMN_PROTECTION] Creating protective racks for {len(solution.columns_in_zone)} columns")
    
    available_zone = solution.available_zones[solution.available_zone_idx]
    zone_bounds = available_zone.bounds
    logger.info(f"[COLUMN_PROTECTION] Zone bounds: x=[{zone_bounds[0]:.1f}, {zone_bounds[2]:.1f}], "
                f"y=[{zone_bounds[1]:.1f}, {zone_bounds[3]:.1f}]")
    logger.info(f"[COLUMN_PROTECTION] Zone size: width={zone_bounds[2]-zone_bounds[0]:.1f}, "
                f"height={zone_bounds[3]-zone_bounds[1]:.1f}")
    logger.info(f"[COLUMN_PROTECTION] Roads width: {reference_book.roads_width:.1f}mm")
    
    solution.protective_racks = []
    
    for idx, column in enumerate(solution.columns_in_zone):
        column_bounds = column.contour.bounds
        logger.info(f"[COLUMN_PROTECTION] ========================================")
        logger.info(f"[COLUMN_PROTECTION] Creating rack {idx+1}/{len(solution.columns_in_zone)}")
        logger.info(f"[COLUMN_PROTECTION] Column Y: [{column_bounds[1]:.1f}, {column_bounds[3]:.1f}]")
        logger.info(f"[COLUMN_PROTECTION] Column center Y: {(column_bounds[1]+column_bounds[3])/2:.1f}")
        
        try:
            protective_rack = _create_protective_rack_for_column(
                column=column,
                available_zone=available_zone,
                reference_book=reference_book,
                solution=solution
            )
            
            solution.protective_racks.append(protective_rack)
            rack_bounds = protective_rack.bounds
            logger.info(f"[COLUMN_PROTECTION] ✓ Rack {idx+1} CREATED:")
            logger.info(f"[COLUMN_PROTECTION]   Y bounds: [{rack_bounds[1]:.1f}, {rack_bounds[3]:.1f}]")
            logger.info(f"[COLUMN_PROTECTION]   Height: {rack_bounds[3]-rack_bounds[1]:.1f}mm")
            logger.info(f"[COLUMN_PROTECTION]   Frames: {len(protective_rack.rack_1)}")
            
        except Exception as e:
            logger.error(f"[COLUMN_PROTECTION] ✗ Failed to create rack {idx}: {e}")
            continue
    
    if not solution.protective_racks:
        raise ActionFailure("Failed to create any protective racks for columns")
    
    logger.info(f"[COLUMN_PROTECTION] ========================================")
    logger.info(f"[COLUMN_PROTECTION] Created {len(solution.protective_racks)} protective racks")
    logger.info(f"[COLUMN_PROTECTION] ========================================")


def optimize_protective_racks(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Optimizes protective racks after creation."""
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
    """Analyzes free strips between protective racks."""
    logger.info("[COLUMN_PROTECTION] ========================================")
    logger.info("[COLUMN_PROTECTION] ANALYZING FREE STRIPS")
    logger.info("[COLUMN_PROTECTION] ========================================")
    
    available_zone = solution.available_zones[solution.available_zone_idx]
    zone_bounds = available_zone.bounds
    solution.free_strips = []
    
    logger.info(f"[COLUMN_PROTECTION] Zone Y: [{zone_bounds[1]:.1f}, {zone_bounds[3]:.1f}]")
    logger.info(f"[COLUMN_PROTECTION] Zone height: {zone_bounds[3]-zone_bounds[1]:.1f}mm")
    logger.info(f"[COLUMN_PROTECTION] Min strip width: {reference_book.min_free_strip_width:.1f}mm")
    logger.info(f"[COLUMN_PROTECTION] Roads width: {reference_book.roads_width:.1f}mm")
    
    if not solution.protective_racks:
        strip_width = zone_bounds[3] - zone_bounds[1]
        solution.free_strips.append({
            'y_min': zone_bounds[1],
            'y_max': zone_bounds[3],
            'width': strip_width,
            'index': 0
        })
        logger.info(f"[COLUMN_PROTECTION] No racks - entire zone is free: {strip_width:.1f}mm")
        return
    
    logger.info(f"[COLUMN_PROTECTION] ========================================")
    logger.info(f"[COLUMN_PROTECTION] ALL PROTECTIVE RACKS ({len(solution.protective_racks)})")
    logger.info(f"[COLUMN_PROTECTION] ========================================")
    
    # Sort protective racks by Y coordinate
    sorted_racks = sorted(solution.protective_racks, key=lambda r: r.bounds[1])
    
    # Log ALL protective racks
    for idx, rack in enumerate(sorted_racks):
        rack_height = rack.bounds[3] - rack.bounds[1]
        logger.info(f"[COLUMN_PROTECTION] Rack {idx}: "
                   f"Y=[{rack.bounds[1]:.1f}, {rack.bounds[3]:.1f}], "
                   f"height={rack_height:.1f}mm, "
                   f"frames={len(rack.rack_1)}")
    
    logger.info(f"[COLUMN_PROTECTION] ========================================")
    logger.info(f"[COLUMN_PROTECTION] CALCULATING STRIPS")
    logger.info(f"[COLUMN_PROTECTION] ========================================")
    
    # Strip below first rack
    first_rack = sorted_racks[0]
    strip_y_min = zone_bounds[1]
    strip_y_max = first_rack.bounds[1] - reference_book.roads_width
    strip_width = strip_y_max - strip_y_min
    
    logger.info(f"[COLUMN_PROTECTION] Strip BELOW first rack:")
    logger.info(f"[COLUMN_PROTECTION]   Zone bottom: {zone_bounds[1]:.1f}")
    logger.info(f"[COLUMN_PROTECTION]   First rack Y_min: {first_rack.bounds[1]:.1f}")
    logger.info(f"[COLUMN_PROTECTION]   Roads width: {reference_book.roads_width:.1f}")
    logger.info(f"[COLUMN_PROTECTION]   Strip Y: [{strip_y_min:.1f}, {strip_y_max:.1f}]")
    logger.info(f"[COLUMN_PROTECTION]   Strip width: {strip_width:.1f}mm")
    
    if strip_width >= reference_book.min_free_strip_width:
        solution.free_strips.append({
            'y_min': strip_y_min,
            'y_max': strip_y_max,
            'width': strip_width,
            'index': len(solution.free_strips)
        })
        logger.info(f"[COLUMN_PROTECTION]   ✓ ADDED strip {len(solution.free_strips)-1}")
    else:
        logger.warning(f"[COLUMN_PROTECTION]   ✗ REJECTED: {strip_width:.1f} < {reference_book.min_free_strip_width:.1f}")
    
    # Strips between consecutive racks
    for i in range(len(sorted_racks) - 1):
        rack_1 = sorted_racks[i]
        rack_2 = sorted_racks[i + 1]
        
        strip_y_min = rack_1.bounds[3] + reference_book.roads_width
        strip_y_max = rack_2.bounds[1] - reference_book.roads_width
        strip_width = strip_y_max - strip_y_min
        
        logger.info(f"[COLUMN_PROTECTION] Strip BETWEEN rack {i} and rack {i+1}:")
        logger.info(f"[COLUMN_PROTECTION]   Rack {i} Y_max: {rack_1.bounds[3]:.1f}")
        logger.info(f"[COLUMN_PROTECTION]   Rack {i+1} Y_min: {rack_2.bounds[1]:.1f}")
        logger.info(f"[COLUMN_PROTECTION]   Roads width: {reference_book.roads_width:.1f}")
        logger.info(f"[COLUMN_PROTECTION]   Calculation: {rack_1.bounds[3]:.1f} + {reference_book.roads_width:.1f} to {rack_2.bounds[1]:.1f} - {reference_book.roads_width:.1f}")
        logger.info(f"[COLUMN_PROTECTION]   Strip Y: [{strip_y_min:.1f}, {strip_y_max:.1f}]")
        logger.info(f"[COLUMN_PROTECTION]   Strip width: {strip_width:.1f}mm")
        
        if strip_width >= reference_book.min_free_strip_width:
            solution.free_strips.append({
                'y_min': strip_y_min,
                'y_max': strip_y_max,
                'width': strip_width,
                'index': len(solution.free_strips)
            })
            logger.info(f"[COLUMN_PROTECTION]   ✓ ADDED strip {len(solution.free_strips)-1}")
        else:
            logger.warning(f"[COLUMN_PROTECTION]   ✗ REJECTED: {strip_width:.1f} < {reference_book.min_free_strip_width:.1f}")
    
    # Strip above last rack
    last_rack = sorted_racks[-1]
    strip_y_min = last_rack.bounds[3] + reference_book.roads_width
    strip_y_max = zone_bounds[3]
    strip_width = strip_y_max - strip_y_min
    
    logger.info(f"[COLUMN_PROTECTION] Strip ABOVE last rack:")
    logger.info(f"[COLUMN_PROTECTION]   Last rack Y_max: {last_rack.bounds[3]:.1f}")
    logger.info(f"[COLUMN_PROTECTION]   Zone top: {zone_bounds[3]:.1f}")
    logger.info(f"[COLUMN_PROTECTION]   Roads width: {reference_book.roads_width:.1f}")
    logger.info(f"[COLUMN_PROTECTION]   Strip Y: [{strip_y_min:.1f}, {strip_y_max:.1f}]")
    logger.info(f"[COLUMN_PROTECTION]   Strip width: {strip_width:.1f}mm")
    
    if strip_width >= reference_book.min_free_strip_width:
        solution.free_strips.append({
            'y_min': strip_y_min,
            'y_max': strip_y_max,
            'width': strip_width,
            'index': len(solution.free_strips)
        })
        logger.info(f"[COLUMN_PROTECTION]   ✓ ADDED strip {len(solution.free_strips)-1}")
    else:
        logger.warning(f"[COLUMN_PROTECTION]   ✗ REJECTED: {strip_width:.1f} < {reference_book.min_free_strip_width:.1f}")
    
    logger.info(f"[COLUMN_PROTECTION] ========================================")
    logger.info(f"[COLUMN_PROTECTION] RESULT: {len(solution.free_strips)} free strips")
    if solution.free_strips:
        total_free = sum(s['width'] for s in solution.free_strips)
        logger.info(f"[COLUMN_PROTECTION] Total free: {total_free:.1f}mm of {zone_bounds[3]-zone_bounds[1]:.1f}mm")
    logger.info(f"[COLUMN_PROTECTION] ========================================")


def set_first_free_strip(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Sets the current strip index to 0 (first free strip)."""
    logger.info("[COLUMN_PROTECTION] Setting first free strip")
    
    if not solution.free_strips:
        logger.warning("[COLUMN_PROTECTION] ✗ No free strips available!")
        raise ActionFailure("No free strips available for rack placement")
    
    solution.current_strip_idx = 0
    strip = solution.free_strips[0]
    logger.info(f"[COLUMN_PROTECTION] ✓ Strip 0: Y=[{strip['y_min']:.1f}, {strip['y_max']:.1f}], "
                f"width={strip['width']:.1f}mm")


def check_if_more_strips_available(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Checks if there are more free strips to process."""
    logger.info(f"[COLUMN_PROTECTION] Check strips: current={solution.current_strip_idx}, "
                f"total={len(solution.free_strips)}")
    
    if solution.current_strip_idx >= len(solution.free_strips) - 1:
        logger.info("[COLUMN_PROTECTION] ✓ All strips processed")
        raise ActionFailure("No more free strips to process")
    
    logger.info(f"[COLUMN_PROTECTION] More strips: {len(solution.free_strips) - solution.current_strip_idx - 1}")


def set_next_free_strip(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Moves to the next free strip."""
    if solution.current_strip_idx >= len(solution.free_strips) - 1:
        logger.error("[COLUMN_PROTECTION] ✗ Already at last strip!")
        raise ActionFailure("Already at last free strip")
    
    solution.current_strip_idx += 1
    strip = solution.free_strips[solution.current_strip_idx]
    logger.info(f"[COLUMN_PROTECTION] ✓ Strip {solution.current_strip_idx}: "
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
    """Calculates the required distance between double rack halves for a column."""
    bounds = column.contour.bounds
    column_width = bounds[2] - bounds[0]
    
    distance = column_width + 2 * column.clearance + reference_book.double_rack_distance_eps
    
    max_distance = reference_book.max_protective_rack_internal_distance
    if distance > max_distance:
        logger.warning(f"[COLUMN_PROTECTION] Column too wide: {column_width:.1f}mm, "
                      f"distance {distance:.1f} > max {max_distance:.1f}")
        distance = max_distance
    
    logger.info(f"[COLUMN_PROTECTION]   Rack distance: {distance:.1f}mm "
                f"(column={column_width:.1f}, clearance={column.clearance:.1f}, eps={reference_book.double_rack_distance_eps:.1f})")
    
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
    
    logger.info(f"[COLUMN_PROTECTION]   Column Y: [{column_bounds[1]:.1f}, {column_bounds[3]:.1f}]")
    logger.info(f"[COLUMN_PROTECTION]   Zone Y: [{zone_bounds[1]:.1f}, {zone_bounds[3]:.1f}]")
    logger.info(f"[COLUMN_PROTECTION]   Pallet length: {pallet.length:.1f}mm")
    
    # Calculate dynamic distance
    rack_distance = _calculate_dynamic_rack_distance_for_column(column, reference_book)
    
    # Calculate total rack height
    total_rack_height = 2 * pallet.length + rack_distance
    
    logger.info(f"[COLUMN_PROTECTION]   Total rack height: 2×{pallet.length:.1f} + {rack_distance:.1f} = {total_rack_height:.1f}mm")
    
    # Calculate available space
    zone_height = zone_bounds[3] - zone_bounds[1]
    available_height = zone_height - 2 * reference_book.roads_width
    
    logger.info(f"[COLUMN_PROTECTION]   Zone height: {zone_height:.1f}mm")
    logger.info(f"[COLUMN_PROTECTION]   Available (with roads): {zone_height:.1f} - 2×{reference_book.roads_width:.1f} = {available_height:.1f}mm")
    
    if total_rack_height > available_height:
        logger.error(f"[COLUMN_PROTECTION]   ✗ TOO TALL: {total_rack_height:.1f} > {available_height:.1f}")
        raise ValueError(f"Rack too tall: {total_rack_height:.1f} > {available_height:.1f}")
    
    # Calculate Y position
    column_center_y = (column_bounds[1] + column_bounds[3]) / 2
    ideal_first_rack_y = column_center_y - rack_distance / 2 - pallet.length / 2
    min_first_rack_y = zone_bounds[1] + reference_book.roads_width
    max_first_rack_y = zone_bounds[3] - reference_book.roads_width - total_rack_height
    first_rack_y = max(min_first_rack_y, min(ideal_first_rack_y, max_first_rack_y))
    
    logger.info(f"[COLUMN_PROTECTION]   Column center: {column_center_y:.1f}")
    logger.info(f"[COLUMN_PROTECTION]   Ideal Y: {ideal_first_rack_y:.1f}")
    logger.info(f"[COLUMN_PROTECTION]   Min Y: {min_first_rack_y:.1f}")
    logger.info(f"[COLUMN_PROTECTION]   Max Y: {max_first_rack_y:.1f}")
    logger.info(f"[COLUMN_PROTECTION]   Final Y: {first_rack_y:.1f}")
    logger.info(f"[COLUMN_PROTECTION]   Expected rack Y: [{first_rack_y:.1f}, {first_rack_y + total_rack_height:.1f}]")
    
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
        logger.info(f"[COLUMN_PROTECTION]   Actual rack Y: [{rack_bounds[1]:.1f}, {rack_bounds[3]:.1f}]")
        logger.info(f"[COLUMN_PROTECTION]   Actual height: {rack_bounds[3]-rack_bounds[1]:.1f}mm")
        
        # Verify boundaries
        min_allowed_y = zone_bounds[1] + reference_book.roads_width
        max_allowed_y = zone_bounds[3] - reference_book.roads_width
        
        if rack_bounds[1] < min_allowed_y:
            logger.error(f"[COLUMN_PROTECTION]   ✗ Too low: {rack_bounds[1]:.1f} < {min_allowed_y:.1f}")
            raise ValueError("Rack violates bottom road")
        
        if rack_bounds[3] > max_allowed_y:
            logger.error(f"[COLUMN_PROTECTION]   ✗ Too high: {rack_bounds[3]:.1f} > {max_allowed_y:.1f}")
            raise ValueError("Rack violates top road")
        
        logger.info(f"[COLUMN_PROTECTION]   ✓ Fits vertically")
        
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
    
    logger.info(f"[COLUMN_PROTECTION]   Section: {section_length:.1f}mm")
    logger.info(f"[COLUMN_PROTECTION]   Max length: {max_available_length:.1f}mm")
    logger.info(f"[COLUMN_PROTECTION]   Frames: {frames_count}")
    
    if frames_count > 0:
        protective_rack.add_multiple_frames(frames_count)
    
    # Verify fit
    if not shapely.contains(available_zone.contour, protective_rack.contour):
        logger.warning(f"[COLUMN_PROTECTION]   Trimming...")
        original = len(protective_rack.rack_1)
        while not shapely.contains(available_zone.contour, protective_rack.contour) and len(protective_rack.rack_1) > 0:
            protective_rack.delete_last_frame()
        logger.warning(f"[COLUMN_PROTECTION]   Trimmed: {original} → {len(protective_rack.rack_1)}")


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
            logger.info(f"[COLUMN_PROTECTION] Close racks {i}/{i+1}: gap={gap:.1f}mm")


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
            logger.info(f"[COLUMN_PROTECTION] Rack {idx} near left: {distance_to_left:.1f}mm")
        
        if distance_to_right < reference_book.roads_width * 2:
            logger.info(f"[COLUMN_PROTECTION] Rack {idx} near right: {distance_to_right:.1f}mm")