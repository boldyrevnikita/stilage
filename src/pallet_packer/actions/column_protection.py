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
    logger.info("[COLUMN_PROTECTION] ========================================")
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
                       f"bounds={bounds}, width={width:.1f}, height={height:.1f}")
        else:
            remaining_occupied_zones.append(occupied_zone)
            logger.debug(f"[COLUMN_PROTECTION] ✗ Not a column {idx}: "
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
        logger.warning("[COLUMN_PROTECTION] No columns found to protect - skipping")
        return
    
    logger.info(f"[COLUMN_PROTECTION] Creating protective racks for {len(solution.columns_in_zone)} columns")
    
    available_zone = solution.available_zones[solution.available_zone_idx]
    zone_bounds = available_zone.bounds
    logger.info(f"[COLUMN_PROTECTION] Zone bounds: x=[{zone_bounds[0]:.1f}, {zone_bounds[2]:.1f}], "
                f"y=[{zone_bounds[1]:.1f}, {zone_bounds[3]:.1f}]")
    logger.info(f"[COLUMN_PROTECTION] Zone size: width={zone_bounds[2]-zone_bounds[0]:.1f}, "
                f"height={zone_bounds[3]-zone_bounds[1]:.1f}")
    
    solution.protective_racks = []
    
    for idx, column in enumerate(solution.columns_in_zone):
        logger.info(f"[COLUMN_PROTECTION] --- Creating rack {idx+1}/{len(solution.columns_in_zone)} ---")
        try:
            protective_rack = _create_protective_rack_for_column(
                column=column,
                available_zone=available_zone,
                reference_book=reference_book,
                solution=solution
            )
            
            solution.protective_racks.append(protective_rack)
            rack_bounds = protective_rack.bounds
            logger.info(f"[COLUMN_PROTECTION] ✓ Rack {idx+1} created: "
                       f"y=[{rack_bounds[1]:.1f}, {rack_bounds[3]:.1f}], "
                       f"height={rack_bounds[3]-rack_bounds[1]:.1f}, "
                       f"frames={len(protective_rack.rack_1)}")
            
        except Exception as e:
            logger.error(f"[COLUMN_PROTECTION] ✗ Failed to create protective rack for column {idx}: {e}")
            continue
    
    if not solution.protective_racks:
        raise ActionFailure("Failed to create any protective racks for columns")
    
    logger.info(f"[COLUMN_PROTECTION] ========================================")
    logger.info(f"[COLUMN_PROTECTION] Successfully created {len(solution.protective_racks)} protective racks")
    logger.info(f"[COLUMN_PROTECTION] ========================================")


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
    logger.info("[COLUMN_PROTECTION] ========================================")
    logger.info("[COLUMN_PROTECTION] ANALYZING FREE STRIPS")
    logger.info("[COLUMN_PROTECTION] ========================================")
    
    available_zone = solution.available_zones[solution.available_zone_idx]
    zone_bounds = available_zone.bounds
    solution.free_strips = []
    
    logger.info(f"[COLUMN_PROTECTION] Zone: x=[{zone_bounds[0]:.1f}, {zone_bounds[2]:.1f}], "
                f"y=[{zone_bounds[1]:.1f}, {zone_bounds[3]:.1f}]")
    logger.info(f"[COLUMN_PROTECTION] Zone height: {zone_bounds[3]-zone_bounds[1]:.1f}mm")
    logger.info(f"[COLUMN_PROTECTION] Min strip width required: {reference_book.min_free_strip_width:.1f}mm")
    logger.info(f"[COLUMN_PROTECTION] Roads width: {reference_book.roads_width:.1f}mm")
    
    if not solution.protective_racks:
        # No protective racks - entire zone is one free strip
        strip_width = zone_bounds[3] - zone_bounds[1]
        solution.free_strips.append({
            'y_min': zone_bounds[1],
            'y_max': zone_bounds[3],
            'width': strip_width,
            'index': 0
        })
        logger.info(f"[COLUMN_PROTECTION] No protective racks - entire zone is free")
        logger.info(f"[COLUMN_PROTECTION] Single strip: width={strip_width:.1f}mm")
        logger.info(f"[COLUMN_PROTECTION] ========================================")
        return
    
    logger.info(f"[COLUMN_PROTECTION] Found {len(solution.protective_racks)} protective racks")
    
    # Sort protective racks by Y coordinate
    sorted_racks = sorted(solution.protective_racks, key=lambda r: r.bounds[1])
    
    # Log all protective racks
    for idx, rack in enumerate(sorted_racks):
        rack_height = rack.bounds[3] - rack.bounds[1]
        logger.info(f"[COLUMN_PROTECTION]   Rack {idx}: y=[{rack.bounds[1]:.1f}, {rack.bounds[3]:.1f}], "
                   f"height={rack_height:.1f}mm")
    
    logger.info(f"[COLUMN_PROTECTION] --- Checking strips ---")
    
    # Strip below first protective rack
    first_rack = sorted_racks[0]
    strip_y_min = zone_bounds[1]
    strip_y_max = first_rack.bounds[1] - reference_book.roads_width
    strip_width = strip_y_max - strip_y_min
    
    logger.info(f"[COLUMN_PROTECTION] Strip BELOW first rack:")
    logger.info(f"[COLUMN_PROTECTION]   y_min = zone_bounds[1] = {zone_bounds[1]:.1f}")
    logger.info(f"[COLUMN_PROTECTION]   y_max = first_rack.y_min - roads_width = {first_rack.bounds[1]:.1f} - {reference_book.roads_width:.1f} = {strip_y_max:.1f}")
    logger.info(f"[COLUMN_PROTECTION]   width = {strip_width:.1f}mm")
    
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
    
    # Strips between consecutive protective racks
    for i in range(len(sorted_racks) - 1):
        rack_1 = sorted_racks[i]
        rack_2 = sorted_racks[i + 1]
        
        strip_y_min = rack_1.bounds[3] + reference_book.roads_width
        strip_y_max = rack_2.bounds[1] - reference_book.roads_width
        strip_width = strip_y_max - strip_y_min
        
        logger.info(f"[COLUMN_PROTECTION] Strip BETWEEN rack {i} and rack {i+1}:")
        logger.info(f"[COLUMN_PROTECTION]   y_min = rack_{i}.y_max + roads_width = {rack_1.bounds[3]:.1f} + {reference_book.roads_width:.1f} = {strip_y_min:.1f}")
        logger.info(f"[COLUMN_PROTECTION]   y_max = rack_{i+1}.y_min - roads_width = {rack_2.bounds[1]:.1f} - {reference_book.roads_width:.1f} = {strip_y_max:.1f}")
        logger.info(f"[COLUMN_PROTECTION]   width = {strip_width:.1f}mm")
        
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
    
    # Strip above last protective rack
    last_rack = sorted_racks[-1]
    strip_y_min = last_rack.bounds[3] + reference_book.roads_width
    strip_y_max = zone_bounds[3]
    strip_width = strip_y_max - strip_y_min
    
    logger.info(f"[COLUMN_PROTECTION] Strip ABOVE last rack:")
    logger.info(f"[COLUMN_PROTECTION]   y_min = last_rack.y_max + roads_width = {last_rack.bounds[3]:.1f} + {reference_book.roads_width:.1f} = {strip_y_min:.1f}")
    logger.info(f"[COLUMN_PROTECTION]   y_max = zone_bounds[3] = {zone_bounds[3]:.1f}")
    logger.info(f"[COLUMN_PROTECTION]   width = {strip_width:.1f}mm")
    
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
    logger.info(f"[COLUMN_PROTECTION] RESULT: {len(solution.free_strips)} free strips available")
    if solution.free_strips:
        total_free_height = sum(s['width'] for s in solution.free_strips)
        logger.info(f"[COLUMN_PROTECTION] Total free height: {total_free_height:.1f}mm")
        logger.info(f"[COLUMN_PROTECTION] Percentage of zone: {100*total_free_height/(zone_bounds[3]-zone_bounds[1]):.1f}%")
    logger.info(f"[COLUMN_PROTECTION] ========================================")


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
    logger.info("[COLUMN_PROTECTION] Setting first free strip")
    
    if not solution.free_strips:
        logger.warning("[COLUMN_PROTECTION] ✗ No free strips available!")
        logger.warning("[COLUMN_PROTECTION] Will proceed with standard placement logic")
        raise ActionFailure("No free strips available for rack placement")
    
    solution.current_strip_idx = 0
    strip = solution.free_strips[0]
    logger.info(f"[COLUMN_PROTECTION] ✓ Starting with strip 0: "
                f"y=[{strip['y_min']:.1f}, {strip['y_max']:.1f}], "
                f"width={strip['width']:.1f}mm")


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
    logger.info(f"[COLUMN_PROTECTION] Checking for more strips (current: {solution.current_strip_idx}, "
                f"total: {len(solution.free_strips)})")
    
    if solution.current_strip_idx >= len(solution.free_strips) - 1:
        logger.info("[COLUMN_PROTECTION] ✓ All free strips processed")
        raise ActionFailure("No more free strips to process")
    
    logger.info(f"[COLUMN_PROTECTION] More strips available: {len(solution.free_strips) - solution.current_strip_idx - 1}")


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
        logger.error("[COLUMN_PROTECTION] ✗ Already at last free strip!")
        raise ActionFailure("Already at last free strip")
    
    solution.current_strip_idx += 1
    strip = solution.free_strips[solution.current_strip_idx]
    logger.info(f"[COLUMN_PROTECTION] ✓ Moving to strip {solution.current_strip_idx}: "
                f"y=[{strip['y_min']:.1f}, {strip['y_max']:.1f}], "
                f"width={strip['width']:.1f}mm")


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
    
    logger.debug(f"[COLUMN_PROTECTION] Rack distance: {distance:.1f}mm (column: {column_width:.1f}mm, "
                f"clearance: {column.clearance:.1f}mm, eps: {reference_book.double_rack_distance_eps:.1f}mm)")
    
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
    - Respects zone boundaries and leaves space for roads
    
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
    column_bounds = column.contour.bounds
    zone_bounds = available_zone.bounds
    pallet = solution.pallets[solution.pallet_idx]
    
    logger.debug(f"[COLUMN_PROTECTION]   Column bounds: y=[{column_bounds[1]:.1f}, {column_bounds[3]:.1f}]")
    logger.debug(f"[COLUMN_PROTECTION]   Zone bounds: y=[{zone_bounds[1]:.1f}, {zone_bounds[3]:.1f}]")
    
    # Calculate dynamic distance
    rack_distance = _calculate_dynamic_rack_distance_for_column(column, reference_book)
    
    # Calculate total rack height (both racks + distance between them)
    total_rack_height = 2 * pallet.length + rack_distance
    
    logger.debug(f"[COLUMN_PROTECTION]   Pallet length: {pallet.length:.1f}mm")
    logger.debug(f"[COLUMN_PROTECTION]   Rack distance: {rack_distance:.1f}mm")
    logger.debug(f"[COLUMN_PROTECTION]   Total rack height: {total_rack_height:.1f}mm")
    
    # Calculate available space (zone height minus roads on both sides)
    zone_height = zone_bounds[3] - zone_bounds[1]
    available_height = zone_height - 2 * reference_book.roads_width
    
    logger.debug(f"[COLUMN_PROTECTION]   Zone height: {zone_height:.1f}mm")
    logger.debug(f"[COLUMN_PROTECTION]   Available height (with roads): {available_height:.1f}mm")
    
    if total_rack_height > available_height:
        logger.error(f"[COLUMN_PROTECTION]   ✗ Rack too tall! {total_rack_height:.1f} > {available_height:.1f}")
        raise ValueError(f"Protective rack doesn't fit in zone: {total_rack_height:.1f}mm > {available_height:.1f}mm")
    
    # Calculate Y position - try to center on column, but respect zone boundaries
    column_center_y = (column_bounds[1] + column_bounds[3]) / 2
    
    # Ideal position: center rack on column
    ideal_first_rack_y = column_center_y - rack_distance / 2 - pallet.length / 2
    
    # Minimum position: must leave space for road at bottom
    min_first_rack_y = zone_bounds[1] + reference_book.roads_width
    
    # Maximum position: must fit both racks + road at top
    max_first_rack_y = zone_bounds[3] - reference_book.roads_width - total_rack_height
    
    # Choose position that respects boundaries
    first_rack_y = max(min_first_rack_y, min(ideal_first_rack_y, max_first_rack_y))
    
    logger.debug(f"[COLUMN_PROTECTION]   Column center Y: {column_center_y:.1f}")
    logger.debug(f"[COLUMN_PROTECTION]   Ideal Y: {ideal_first_rack_y:.1f}")
    logger.debug(f"[COLUMN_PROTECTION]   Min Y: {min_first_rack_y:.1f}")
    logger.debug(f"[COLUMN_PROTECTION]   Max Y: {max_first_rack_y:.1f}")
    logger.debug(f"[COLUMN_PROTECTION]   Final Y: {first_rack_y:.1f}")
    
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
        
        # Verify rack fits vertically with roads
        rack_bounds = protective_rack.bounds
        
        expected_rack_top = first_rack_y + total_rack_height
        logger.debug(f"[COLUMN_PROTECTION]   Expected rack bounds: y=[{first_rack_y:.1f}, {expected_rack_top:.1f}]")
        logger.debug(f"[COLUMN_PROTECTION]   Actual rack bounds: y=[{rack_bounds[1]:.1f}, {rack_bounds[3]:.1f}]")
        
        # Check bottom boundary
        min_allowed_y = zone_bounds[1] + reference_book.roads_width
        if rack_bounds[1] < min_allowed_y:
            logger.error(f"[COLUMN_PROTECTION]   ✗ Rack starts too low: {rack_bounds[1]:.1f} < {min_allowed_y:.1f}")
            raise ValueError("Rack violates bottom road space")
        
        # Check top boundary
        max_allowed_y = zone_bounds[3] - reference_book.roads_width
        if rack_bounds[3] > max_allowed_y:
            logger.error(f"[COLUMN_PROTECTION]   ✗ Rack extends too high: {rack_bounds[3]:.1f} > {max_allowed_y:.1f}")
            raise ValueError("Rack violates top road space")
        
        logger.debug(f"[COLUMN_PROTECTION]   ✓ Rack fits vertically")
        
        # Fill with frames
        _fill_protective_rack_with_frames(protective_rack, available_zone)
        
        logger.debug(f"[COLUMN_PROTECTION]   ✓ Rack created successfully")
        
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
    section_length = (protective_rack.rack_1.beam_type.length + 
                     protective_rack.rack_1.upright_type.width)
    
    zone_bounds = available_zone.bounds
    max_available_length = zone_bounds[2] - protective_rack.bounds[0]
    
    frames_count = max(0, int(max_available_length // section_length))
    
    logger.debug(f"[COLUMN_PROTECTION]   Section length: {section_length:.1f}mm")
    logger.debug(f"[COLUMN_PROTECTION]   Max available length: {max_available_length:.1f}mm")
    logger.debug(f"[COLUMN_PROTECTION]   Calculated frames: {frames_count}")
    
    if frames_count > 0:
        protective_rack.add_multiple_frames(frames_count)
        logger.debug(f"[COLUMN_PROTECTION]   Added {frames_count} frames")
    
    # Verify the rack fits in the zone horizontally
    if not shapely.contains(available_zone.contour, protective_rack.contour):
        logger.warning(f"[COLUMN_PROTECTION]   Rack doesn't fit horizontally! Trimming...")
        original_frames = len(protective_rack.rack_1)
        while not shapely.contains(available_zone.contour, protective_rack.contour) and len(protective_rack.rack_1) > 0:
            protective_rack.delete_last_frame()
        final_frames = len(protective_rack.rack_1)
        logger.warning(f"[COLUMN_PROTECTION]   Had to trim from {original_frames} to {final_frames} frames")


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
    
    for i in range(len(solution.protective_racks) - 1):
        current_rack = solution.protective_racks[i]
        next_rack = solution.protective_racks[i + 1]
        
        current_column = current_rack.protected_column
        next_column = next_rack.protected_column
        
        gap = next_column.bounds[1] - current_column.bounds[3]
        
        if gap < reference_book.roads_width:
            logger.info(f"[COLUMN_PROTECTION] Close racks {i} and {i+1}: gap={gap:.1f}mm < {reference_book.roads_width:.1f}mm")
            # For now, just log - merging is complex


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
    
    for idx, protective_rack in enumerate(solution.protective_racks):
        column = protective_rack.protected_column
        column_bounds = column.bounds
        
        distance_to_left = column_bounds[0] - zone_bounds[0]
        distance_to_right = zone_bounds[2] - column_bounds[2]
        
        if distance_to_left < reference_book.roads_width * 2:
            logger.debug(f"[COLUMN_PROTECTION] Rack {idx} near left edge: {distance_to_left:.1f}mm")
        
        if distance_to_right < reference_book.roads_width * 2:
            logger.debug(f"[COLUMN_PROTECTION] Rack {idx} near right edge: {distance_to_right:.1f}mm")