from src.network.output_schema import ModelOutput, RackOutput
from src.pallet_packer.solution import Solution
from src.rack import DoubleRack
from src.reference_book import ReferenceBook
from collections import defaultdict
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# def calculate_jumper_presence(rack, is_rotated: bool = False) -> list[list[int]]:
#     from shapely.geometry import LineString
    
#     if not isinstance(rack, DoubleRack):
#         num_decks = len(rack.decks)
#         return [[1, 1] for _ in range(num_decks)]
    
#     if not rack.is_protective or rack.protected_column is None:
#         num_decks_1 = len(rack.rack_1.decks)
#         num_decks_2 = len(rack.rack_2.decks)
#         return [[1, 1] for _ in range(num_decks_1 + num_decks_2)]
    
#     logger.warning(f"[JUMPER_CALC] ════════════════════════════════════════════════════════")
#     logger.warning(f"[JUMPER_CALC] Calculating jumper presence for PROTECTIVE rack")
    
#     column = rack.protected_column
#     column_bounds = column.contour.bounds
#     rack_1_bounds = rack.rack_1.bounds
#     rack_2_bounds = rack.rack_2.bounds
    
#     logger.warning(f"[JUMPER_CALC] rack_1 bounds: {rack_1_bounds}")
#     logger.warning(f"[JUMPER_CALC] rack_2 bounds: {rack_2_bounds}")
#     logger.warning(f"[JUMPER_CALC] column bounds: {column_bounds}")
    
#     rack_1_center_x = (rack_1_bounds[0] + rack_1_bounds[2]) / 2
#     rack_2_center_x = (rack_2_bounds[0] + rack_2_bounds[2]) / 2
#     rack_1_center_y = (rack_1_bounds[1] + rack_1_bounds[3]) / 2
#     rack_2_center_y = (rack_2_bounds[1] + rack_2_bounds[3]) / 2
    
#     x_diff = abs(rack_1_center_x - rack_2_center_x)
#     y_diff = abs(rack_1_center_y - rack_2_center_y)
#     racks_side_by_side_on_x = (x_diff > y_diff)
    
#     logger.warning(f"[JUMPER_CALC] rack_1 center: ({rack_1_center_x:.1f}, {rack_1_center_y:.1f})")
#     logger.warning(f"[JUMPER_CALC] rack_2 center: ({rack_2_center_x:.1f}, {rack_2_center_y:.1f})")
#     logger.warning(f"[JUMPER_CALC] X difference: {x_diff:.1f}, Y difference: {y_diff:.1f}")
#     logger.warning(f"[JUMPER_CALC] Racks side-by-side on X: {racks_side_by_side_on_x}")
#     logger.warning(f"[JUMPER_CALC] → Jumpers orientation: {'HORIZONTAL (along X)' if racks_side_by_side_on_x else 'VERTICAL (along Y)'}")
    
#     column_buffer = column.contour.buffer(10)
#     result = []
    
#     for rack_idx, subrack in enumerate([rack.rack_1, rack.rack_2]):
#         num_decks = len(subrack.decks)
#         logger.warning(f"[JUMPER_CALC] Processing rack_{rack_idx + 1} with {num_decks} decks")
        
#         for deck_idx, deck in enumerate(subrack.decks):
#             deck_bounds = deck.bounds
            
#             if racks_side_by_side_on_x:
#                 jumper_before_y = deck_bounds[1]
#                 jumper_after_y = deck_bounds[3]
                
#                 if rack_1_center_x < rack_2_center_x:
#                     jumper_x_start = rack_1_bounds[2]
#                     jumper_x_end = rack_2_bounds[0]
#                 else:
#                     jumper_x_start = rack_2_bounds[2]
#                     jumper_x_end = rack_1_bounds[0]
                
#                 jumper_before_line = LineString([
#                     (jumper_x_start, jumper_before_y),
#                     (jumper_x_end, jumper_before_y)
#                 ])
                
#                 jumper_after_line = LineString([
#                     (jumper_x_start, jumper_after_y),
#                     (jumper_x_end, jumper_after_y)
#                 ])
                
#             else:
#                 jumper_before_x = rack_1_bounds[0]  
#                 jumper_after_x = rack_1_bounds[2]
                
#                 if rack_1_center_y < rack_2_center_y:
#                     jumper_y_start = rack_1_bounds[3]
#                     jumper_y_end = rack_2_bounds[1]
#                 else:
#                     jumper_y_start = rack_2_bounds[3]
#                     jumper_y_end = rack_1_bounds[1]
                
#                 jumper_before_line = LineString([
#                     (jumper_before_x, jumper_y_start),
#                     (jumper_before_x, jumper_y_end)
#                 ])
                
#                 jumper_after_line = LineString([
#                     (jumper_after_x, jumper_y_start),
#                     (jumper_after_x, jumper_y_end)
#                 ])
            
#             before_intersects = jumper_before_line.intersects(column_buffer)
#             after_intersects = jumper_after_line.intersects(column_buffer)
            
#             left_present = 0 if before_intersects else 1
#             right_present = 0 if after_intersects else 1
            
#             result.append([left_present, right_present])
            
#             logger.warning(
#                 f"[JUMPER_CALC]   rack_{rack_idx + 1} deck {deck_idx}: "
#                 f"[{left_present}, {right_present}] "
#                 f"{'(INTERSECTS)' if (before_intersects or after_intersects) else '(OK)'}"
#             )
    
#     logger.warning(f"[JUMPER_CALC] Final jumper list (total {len(result)} decks): {result}")
#     logger.warning(f"[JUMPER_CALC] ════════════════════════════════════════════════════════")
    
#     return result

def calculate_jumper_presence(rack, is_rotated: bool = False) -> list[list[int]]:
    from shapely.geometry import LineString
    
    if not isinstance(rack, DoubleRack):
        num_decks = len(rack.decks)
        return [[1, 1] for _ in range(num_decks)]
    
    if not rack.is_protective or rack.protected_column is None:
        num_decks_1 = len(rack.rack_1.decks)
        return [[1, 1] for _ in range(num_decks_1)]
    
    logger.warning(f"[JUMPER_CALC] ════════════════════════════════════════════════════════")
    logger.warning(f"[JUMPER_CALC] Calculating jumper presence for PROTECTIVE rack")
    
    column = rack.protected_column
    column_bounds = column.contour.bounds
    rack_1_bounds = rack.rack_1.bounds
    rack_2_bounds = rack.rack_2.bounds
    
    logger.warning(f"[JUMPER_CALC] rack_1 bounds: {rack_1_bounds}")
    logger.warning(f"[JUMPER_CALC] rack_2 bounds: {rack_2_bounds}")
    logger.warning(f"[JUMPER_CALC] column bounds: {column_bounds}")
    
    rack_1_center_x = (rack_1_bounds[0] + rack_1_bounds[2]) / 2
    rack_2_center_x = (rack_2_bounds[0] + rack_2_bounds[2]) / 2
    rack_1_center_y = (rack_1_bounds[1] + rack_1_bounds[3]) / 2
    rack_2_center_y = (rack_2_bounds[1] + rack_2_bounds[3]) / 2
    
    x_diff = abs(rack_1_center_x - rack_2_center_x)
    y_diff = abs(rack_1_center_y - rack_2_center_y)
    racks_side_by_side_on_x = (x_diff > y_diff)
    
    logger.warning(f"[JUMPER_CALC] rack_1 center: ({rack_1_center_x:.1f}, {rack_1_center_y:.1f})")
    logger.warning(f"[JUMPER_CALC] rack_2 center: ({rack_2_center_x:.1f}, {rack_2_center_y:.1f})")
    logger.warning(f"[JUMPER_CALC] X difference: {x_diff:.1f}, Y difference: {y_diff:.1f}")
    logger.warning(f"[JUMPER_CALC] Racks side-by-side on X: {racks_side_by_side_on_x}")
    logger.warning(f"[JUMPER_CALC] → Jumpers orientation: {'HORIZONTAL (along X)' if racks_side_by_side_on_x else 'VERTICAL (along Y)'}")
    
    column_buffer = column.contour.buffer(10)
    
    rack1_results = []
    rack2_results = []
    
    for rack_idx, subrack in enumerate([rack.rack_1, rack.rack_2]):
        num_decks = len(subrack.decks)
        logger.warning(f"[JUMPER_CALC] Processing rack_{rack_idx + 1} with {num_decks} decks")
        
        current_results = rack1_results if rack_idx == 0 else rack2_results
        
        for deck_idx, deck in enumerate(subrack.decks):
            deck_bounds = deck.bounds
            
            if racks_side_by_side_on_x:
                jumper_before_y = deck_bounds[1]
                jumper_after_y = deck_bounds[3]
                
                if rack_1_center_x < rack_2_center_x:
                    jumper_x_start = rack_1_bounds[2]
                    jumper_x_end = rack_2_bounds[0]
                else:
                    jumper_x_start = rack_2_bounds[2]
                    jumper_x_end = rack_1_bounds[0]
                
                jumper_before_line = LineString([
                    (jumper_x_start, jumper_before_y),
                    (jumper_x_end, jumper_before_y)
                ])
                
                jumper_after_line = LineString([
                    (jumper_x_start, jumper_after_y),
                    (jumper_x_end, jumper_after_y)
                ])
                
            else:
                jumper_before_x = rack_1_bounds[0]  
                jumper_after_x = rack_1_bounds[2]
                
                if rack_1_center_y < rack_2_center_y:
                    jumper_y_start = rack_1_bounds[3]
                    jumper_y_end = rack_2_bounds[1]
                else:
                    jumper_y_start = rack_2_bounds[3]
                    jumper_y_end = rack_1_bounds[1]
                
                jumper_before_line = LineString([
                    (jumper_before_x, jumper_y_start),
                    (jumper_before_x, jumper_y_end)
                ])
                
                jumper_after_line = LineString([
                    (jumper_after_x, jumper_y_start),
                    (jumper_after_x, jumper_y_end)
                ])
            
            before_intersects = jumper_before_line.intersects(column_buffer)
            after_intersects = jumper_after_line.intersects(column_buffer)
            
            left_present = 0 if before_intersects else 1
            right_present = 0 if after_intersects else 1
            
            current_results.append([left_present, right_present])
            
            logger.warning(
                f"[JUMPER_CALC]   rack_{rack_idx + 1} deck {deck_idx}: "
                f"[{left_present}, {right_present}] "
                f"{'(INTERSECTS)' if (before_intersects or after_intersects) else '(OK)'}"
            )
    
    num_frames = len(rack1_results)
    result = []
    
    for i in range(num_frames):
        left_combined = min(rack1_results[i][0], rack2_results[i][0])
        right_combined = min(rack1_results[i][1], rack2_results[i][1])
        result.append([left_combined, right_combined])
        
        logger.warning(
            f"[JUMPER_CALC] Frame {i}: rack_1=[{rack1_results[i][0]},{rack1_results[i][1]}] "
            f"rack_2=[{rack2_results[i][0]},{rack2_results[i][1]}] → "
            f"combined=[{left_combined},{right_combined}]"
        )
    
    logger.warning(f"[JUMPER_CALC] Final jumper list (total {len(result)} frames): {result}")
    logger.warning(f"[JUMPER_CALC] ════════════════════════════════════════════════════════")
    
    return result

def generate_output(solution: Solution,
                    reference_book: ReferenceBook,
                    task_id: str,
                    warnings_and_errors: str,
                    success_predict: bool) -> ModelOutput:
    """Generates the output for the pallet packing solution."""
    if solution is None or getattr(solution, "saved_rack_groups", None) in (None, []):
        return ModelOutput(
            task_id=task_id,
            racks={},
            warnings_and_errors=(warnings_and_errors or "No valid solution produced by solver"),
            success_predict=False
        )
    
    racks = defaultdict(list)
    for rack_group in solution.saved_rack_groups:
        for rack in rack_group.racks:
            cargo_id = str(rack.pallet.cargo.cargo_type_id)
            boundary = [(int(x), int(y))
                        for x, y in zip(*rack.contour.exterior.xy)]
            sections_in_length = len(rack)
            sections_in_width = 1 if not isinstance(rack, DoubleRack) else 2
            sections_in_height = rack.max_shelfs
            sections_in_height_special = rack.max_shelfs_bridge
            orientation = rack.orientation

            upright_section = rack.upright_type.upright_section
            upright_section = (upright_section[0]
                               - reference_book.upright_width_eps,
                               upright_section[1], upright_section[2])

            beam_section = rack.beam_type.beam_section
            pallet_size = (rack.pallet.pallet_type.width,
                           rack.pallet.pallet_type.length)

            if isinstance(rack, DoubleRack):
                subracks2handle = [rack.rack_1, rack.rack_2]
            else:
                subracks2handle = [rack]

            units = []
            special_units = []
            beam_lengths = []

            for subrack in subracks2handle:
                units.append([beam.max_shelf_load_capacity_pallets
                              for beam in subrack.beams])
                special_units.append([status.value
                                      for status in subrack.deck_status])
                beam_lengths.append([beam.length for beam in subrack.beams])

            rack_distance = (rack.rack_distance if isinstance(rack, DoubleRack)
                             else None)

            is_rotated = getattr(solution, 'is_rotated', False)
            jumper_presence = calculate_jumper_presence(rack, is_rotated)

            racks[cargo_id].append(
                RackOutput(
                    boundary=boundary,
                    sections_in_length=sections_in_length,
                    sections_in_width=sections_in_width,
                    sections_in_height=sections_in_height,
                    sections_in_height_special=sections_in_height_special,
                    pallet_with_cargo_height=rack.pallet.height,
                    beam_height=rack.beam_type.height,
                    pallet_with_cargo_extra_height=(
                        rack_group.pallet_extra_space),
                    frame_height_eps=rack_group.frame_height_eps,
                    metric_frame_height=(
                        rack_group.calculate_max_frame_height()),
                    metric_special_frame_height=(
                        rack_group.calculate_max_frame_height()),
                    orientation=orientation,
                    upright_section=upright_section,
                    beam_section=beam_section,
                    pallet_size=pallet_size,
                    units=units,
                    special_units=special_units,
                    beam_lengths=beam_lengths,
                    rack_distance=rack_distance,
                    jumper_presence=jumper_presence
                )
            )

    return ModelOutput(
        task_id=task_id,
        racks=dict(racks),
        warnings_and_errors=warnings_and_errors,
        success_predict=success_predict
    )