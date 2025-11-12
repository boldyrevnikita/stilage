from src.reference_book import ReferenceBook
from src.pallet_packer.solution import Solution, ActionFailure
from src.rack import DoubleRack, RackGroup
from src.zone import OccupiedZone
import shapely
from copy import deepcopy
import logging
import math

logger = logging.getLogger(__name__)

def identify_and_protect_all_columns(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Main function that executes Phase 1: identify all columns and protect them."""
    logger.warning("[COLUMN_PROTECTION] ========================================")
    logger.warning("[COLUMN_PROTECTION] Starting Phase 1: Protect all columns")
    logger.warning("[COLUMN_PROTECTION] ========================================")
    
    identify_columns_in_zone(reference_book, solution)
    
    create_protective_double_racks_for_all_columns(reference_book, solution)
    
    optimize_protective_racks(reference_book, solution)
    
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
            
            rack_group.racks.append(protective_rack)
            
            rack_group.is_protective = True
            
            if hasattr(rack_group, '_update_bounds'):
                rack_group._update_bounds()
            
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
    
    solution.protective_racks.sort(key=lambda r: r.bounds[1])
    
    _merge_close_protective_racks(solution, reference_book)
    
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
    
    unique_racks = []
    seen_bounds = set()
    for rack in solution.protective_racks:
        bounds_tuple = (round(rack.bounds[1], 1), round(rack.bounds[3], 1))
        if bounds_tuple not in seen_bounds:
            unique_racks.append(rack)
            seen_bounds.add(bounds_tuple)
    
    logger.warning(f"[COLUMN_PROTECTION] Deduplication: {len(solution.protective_racks)} total → {len(unique_racks)} unique")
    
    sorted_racks = sorted(unique_racks, key=lambda r: r.bounds[1])
    
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
    
    solution.last_intersected_vertical_road = None
    
    strip = solution.free_strips[0]
    logger.warning(f"[COLUMN_PROTECTION] Set first strip: Y=[{strip['y_min']:.1f}, {strip['y_max']:.1f}], "
                f"width={strip['width']:.1f}mm")


def check_if_more_strips_available(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Checks if there are more free strips to process.
    
    This function MUST return FAILURE (raise ActionFailure) 
    when all strips are processed, so the state machine proceeds to 
    rotate_everything_90_counterclockwise and then split_available_zone.
    """
    if solution.current_strip_idx >= len(solution.free_strips) - 1:
        logger.warning("[COLUMN_PROTECTION] All strips processed")
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
    
    solution.last_intersected_vertical_road = None
    
    strip = solution.free_strips[solution.current_strip_idx]
    logger.warning(f"[COLUMN_PROTECTION] Set next strip {solution.current_strip_idx}: "
                f"Y=[{strip['y_min']:.1f}, {strip['y_max']:.1f}], width={strip['width']:.1f}mm")


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
    reference_book: ReferenceBook,
    solution: Solution
) -> float:
    """Calculates dynamic rack_distance based on column size and orientation.
    
    Logic:
    1. Choose column dimension based on orientation
    2. Calculate actual_gap: column + 50mm per side
    3. Convert to rack_distance: add eps
    4. Round rack_distance UP to multiple of 50 (jumper sizes!)
    5. Cap at maximum 1100mm
    
    Args:
        column: The column to calculate distance for
        reference_book: Reference book with configuration
        solution: Current solution (needed for is_rotated flag)
    
    Returns:
        rack_distance in mm (multiple of 50, max 1100)
    """
    import math
    
    column_bounds = column.contour.bounds
    column_width = column_bounds[2] - column_bounds[0]
    column_height = column_bounds[3] - column_bounds[1]
    
    if solution.is_rotated:
        column_size = column_width
        orientation_desc = "vertical (rotated)"
    else:
        column_size = column_height
        orientation_desc = "horizontal"
    
    logger.warning(f"[COLUMN_PROTECTION] Calculating rack_distance:")
    logger.warning(f"[COLUMN_PROTECTION]   Column: {column_width:.1f} x {column_height:.1f} mm")
    logger.warning(f"[COLUMN_PROTECTION]   Orientation: {orientation_desc}")
    logger.warning(f"[COLUMN_PROTECTION]   Selected dimension: {column_size:.1f} mm")
    
    CLEARANCE = 50  
    actual_gap = column_size + 2 * CLEARANCE
    logger.warning(f"[COLUMN_PROTECTION]   Desired actual_gap: {actual_gap:.1f} mm")
    
    eps = reference_book.double_rack_distance_eps
    rack_distance_raw = actual_gap + eps
    logger.warning(f"[COLUMN_PROTECTION]   Raw rack_distance: {actual_gap:.1f} + {eps:.1f} = {rack_distance_raw:.1f} mm")
    
    JUMPER_STEP = 50  
    rack_distance_rounded = math.ceil(rack_distance_raw / JUMPER_STEP) * JUMPER_STEP
    logger.warning(f"[COLUMN_PROTECTION]   Rounded to jumper size: {rack_distance_rounded:.1f} mm")
    
    MAX_RACK_DISTANCE = 1100  
    rack_distance_final = min(rack_distance_rounded, MAX_RACK_DISTANCE)
    
    if rack_distance_rounded > MAX_RACK_DISTANCE:
        logger.warning(f"[COLUMN_PROTECTION]   Exceeds max jumper {MAX_RACK_DISTANCE} mm, capping...")
    
    actual_gap_final = rack_distance_final - eps
    clearance_final = (actual_gap_final - column_size) / 2
    
    logger.warning(f"[COLUMN_PROTECTION]   ════════════════════════════════")
    logger.warning(f"[COLUMN_PROTECTION]    Final rack_distance: {rack_distance_final:.1f} mm")
    logger.warning(f"[COLUMN_PROTECTION]      → actual_gap: {actual_gap_final:.1f} mm")
    logger.warning(f"[COLUMN_PROTECTION]      → clearance: {clearance_final:.1f} mm per side")
    logger.warning(f"[COLUMN_PROTECTION]   ════════════════════════════════")
    
    return rack_distance_final


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
    
    logger.warning(f"[COLUMN_PROTECTION] ========================================")
    logger.warning(f"[COLUMN_PROTECTION] Creating protective rack for column")
    logger.warning(f"[COLUMN_PROTECTION]   Column bounds: {column_bounds}")
    logger.warning(f"[COLUMN_PROTECTION]   Zone bounds: {zone_bounds}")
    
    rack_distance = _calculate_dynamic_rack_distance_for_column(
        column, 
        reference_book,
        solution  
    )
    logger.warning(f"[COLUMN_PROTECTION]   Calculated rack_distance: {rack_distance:.1f}mm")
    
    actual_gap = rack_distance - reference_book.double_rack_distance_eps
    total_rack_height = 2 * pallet.length + actual_gap
    
    logger.warning(f"[COLUMN_PROTECTION]   Pallet length: {pallet.length:.1f}mm")
    logger.warning(f"[COLUMN_PROTECTION]   Actual gap: {actual_gap:.1f}mm")
    logger.warning(f"[COLUMN_PROTECTION]   Total rack height: {total_rack_height:.1f}mm")
    
    zone_height = zone_bounds[3] - zone_bounds[1]
    available_height = zone_height - 2 * reference_book.roads_width
    
    logger.warning(f"[COLUMN_PROTECTION]   Zone height: {zone_height:.1f}mm")
    logger.warning(f"[COLUMN_PROTECTION]   Available height: {available_height:.1f}mm")
    
    if total_rack_height > available_height:
        logger.error(f"[COLUMN_PROTECTION] Rack too tall: {total_rack_height:.1f} > {available_height:.1f}")
        raise ValueError(f"Rack too tall: {total_rack_height:.1f} > {available_height:.1f}")
    
    column_center_y = (column_bounds[1] + column_bounds[3]) / 2
    first_rack_y = column_center_y - (total_rack_height / 2)
    
    min_first_rack_y = zone_bounds[1] + reference_book.roads_width
    max_first_rack_y = zone_bounds[3] - reference_book.roads_width - total_rack_height
    first_rack_y = max(min_first_rack_y, min(first_rack_y, max_first_rack_y))
    
    position = (zone_bounds[0], first_rack_y)
    logger.warning(f"[COLUMN_PROTECTION]   Position: {position}")
    
    try:
        logger.warning(f"[COLUMN_PROTECTION] Creating DoubleRack with:")
        logger.warning(f"[COLUMN_PROTECTION]   is_protective=True")
        logger.warning(f"[COLUMN_PROTECTION]   protected_column={column}")
        
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
        
        logger.warning(f"[COLUMN_PROTECTION] ========================================")
        logger.warning(f"[COLUMN_PROTECTION] DoubleRack created successfully!")
        logger.warning(f"[COLUMN_PROTECTION] Checking attributes:")
        logger.warning(f"[COLUMN_PROTECTION]   protective_rack.is_protective = {protective_rack.is_protective}")
        logger.warning(f"[COLUMN_PROTECTION]   protective_rack.protected_column = {protective_rack.protected_column}")
        logger.warning(f"[COLUMN_PROTECTION]   protective_rack.protected_column is not None: {protective_rack.protected_column is not None}")
        
        logger.warning(f"[COLUMN_PROTECTION] Checking rack_1 attributes:")
        logger.warning(f"[COLUMN_PROTECTION]   rack_1.is_protective = {protective_rack.rack_1.is_protective}")
        logger.warning(f"[COLUMN_PROTECTION]   rack_1.protected_column = {protective_rack.rack_1.protected_column}")
        logger.warning(f"[COLUMN_PROTECTION]   rack_1.protected_column is not None: {protective_rack.rack_1.protected_column is not None}")
        
        logger.warning(f"[COLUMN_PROTECTION] Checking rack_2 attributes:")
        logger.warning(f"[COLUMN_PROTECTION]   rack_2.is_protective = {protective_rack.rack_2.is_protective}")
        logger.warning(f"[COLUMN_PROTECTION]   rack_2.protected_column = {protective_rack.rack_2.protected_column}")
        logger.warning(f"[COLUMN_PROTECTION]   rack_2.protected_column is not None: {protective_rack.rack_2.protected_column is not None}")
        
        rack_bounds = protective_rack.bounds
        logger.warning(f"[COLUMN_PROTECTION] Rack bounds: {rack_bounds}")
        logger.warning(f"[COLUMN_PROTECTION]   rack_1 bounds: {protective_rack.rack_1.bounds}")
        logger.warning(f"[COLUMN_PROTECTION]   rack_2 bounds: {protective_rack.rack_2.bounds}")
        
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
        
        logger.warning(f"[COLUMN_PROTECTION] Checking column position:")
        logger.warning(f"[COLUMN_PROTECTION]   rack_1 ends at Y={rack1_end:.1f}")
        logger.warning(f"[COLUMN_PROTECTION]   Column starts at Y={column_bounds[1]:.1f}")
        logger.warning(f"[COLUMN_PROTECTION]   Column ends at Y={column_bounds[3]:.1f}")
        logger.warning(f"[COLUMN_PROTECTION]   rack_2 starts at Y={rack2_start:.1f}")
        
        if column_bounds[1] < rack1_end or column_bounds[3] > rack2_start:
            logger.error(f"[COLUMN_PROTECTION] ⚠️ Column not in gap!")
            logger.error(f"[COLUMN_PROTECTION]   Column overlaps with rack_1: {column_bounds[1] < rack1_end}")
            logger.error(f"[COLUMN_PROTECTION]   Column overlaps with rack_2: {column_bounds[3] > rack2_start}")
        else:
            logger.warning(f"[COLUMN_PROTECTION] ✅ Column correctly positioned in gap")
        
        logger.warning(f"[COLUMN_PROTECTION] Filling protective rack with frames...")
        _fill_protective_rack_with_frames(
            protective_rack, 
            available_zone,
            solution.current_road_zones  
        )
        
        logger.warning(f"[COLUMN_PROTECTION] After filling:")
        logger.warning(f"[COLUMN_PROTECTION]   rack_1 has {len(protective_rack.rack_1.decks)} decks")
        logger.warning(f"[COLUMN_PROTECTION]   rack_2 has {len(protective_rack.rack_2.decks)} decks")
        
        logger.warning(f"[COLUMN_PROTECTION] Checking deck-column intersections:")
        for idx, deck in enumerate(protective_rack.rack_1.decks):
            deck_bounds = deck.bounds
            intersects = shapely.intersects(deck, column.contour)
            y_overlap = (deck_bounds[1] < column_bounds[3] and deck_bounds[3] > column_bounds[1])
            logger.warning(f"[COLUMN_PROTECTION]   rack_1 deck {idx}: "
                          f"Y=[{deck_bounds[1]:.1f}, {deck_bounds[3]:.1f}], "
                          f"intersects={intersects}, y_overlap={y_overlap}")
        
        for idx, deck in enumerate(protective_rack.rack_2.decks):
            deck_bounds = deck.bounds
            intersects = shapely.intersects(deck, column.contour)
            y_overlap = (deck_bounds[1] < column_bounds[3] and deck_bounds[3] > column_bounds[1])
            logger.warning(f"[COLUMN_PROTECTION]   rack_2 deck {idx}: "
                          f"Y=[{deck_bounds[1]:.1f}, {deck_bounds[3]:.1f}], "
                          f"intersects={intersects}, y_overlap={y_overlap}")
        
        logger.warning(f"[COLUMN_PROTECTION] ========================================")
        
        return protective_rack
        
    except Exception as e:
        logger.error(f"[COLUMN_PROTECTION] Failed to create protective rack: {e}")
        logger.exception(e)
        raise ValueError(f"Cannot create rack: {e}")


def _fill_protective_rack_with_frames(
    protective_rack: DoubleRack,
    available_zone,
    road_zones: list
) -> None:
    """Fills a protective rack with frames, handling road zone intersections.
    
    Now tracks last intersected road zone to prevent consecutive bridge frames
    """
    section_length = (protective_rack.rack_1.beam_type.length + 
                     protective_rack.rack_1.upright_type.width)
    
    zone_bounds = available_zone.bounds
    max_available_length = zone_bounds[2] - protective_rack.bounds[0]
    
    frames_count = max(0, int(max_available_length // section_length))
    
    logger.warning(f"[COLUMN_PROTECTION] Filling protective rack with up to {frames_count} frames")
    
    last_bridged_road_zone = None
    
    for i in range(frames_count):
        protective_rack.add_frame()
        
        intersects_road = False
        for road_zone in road_zones:
            if protective_rack.last_frame_intersects(road_zone.contour):
                intersects_road = True
                if not road_zone.is_horizontal():
                    if road_zone is not last_bridged_road_zone:
                        frame_idx = len(protective_rack.rack_1) - 1
                        protective_rack.make_frame_bridge(frame_idx)
                        last_bridged_road_zone = road_zone
                        logger.warning(f"[COLUMN_PROTECTION] Set frame {frame_idx} as BRIDGE in protective rack (vertical road intersection)")
                    else:
                        logger.warning(f"[COLUMN_PROTECTION]  Frame {i} intersects same road zone as previous frame - skipping bridge (already bridged)")
                else:
                    logger.warning(f"[COLUMN_PROTECTION] Frame {i} intersects horizontal road - no bridge needed")
                break
        
        if not intersects_road:
            last_bridged_road_zone = None
        
        if not shapely.contains(available_zone.contour, protective_rack.contour):
            protective_rack.delete_last_frame()
            logger.warning(f"[COLUMN_PROTECTION] Removed frame {i} - doesn't fit in zone")
            break
    
    final_frames = len(protective_rack.rack_1)
    logger.warning(f"[COLUMN_PROTECTION] Protective rack filled with {final_frames} frames")


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