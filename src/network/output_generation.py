from src.network.output_schema import ModelOutput, RackOutput
from src.pallet_packer.solution import Solution
from src.rack import DoubleRack
from src.reference_book import ReferenceBook
from collections import defaultdict
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def calculate_jumper_presence(rack, is_rotated: bool = False) -> list[list[list[int]]]:
    """Вычисляет наличие перемычек для стеллажа.
    
    Для защитных стеллажей (protective DoubleRack) проверяет пересечения перемычек с колонной.
    Для обычных стеллажей все перемычки присутствуют.
    """
    import shapely
    from shapely.geometry import LineString
    
    if not isinstance(rack, DoubleRack):
        num_sections = len(rack)
        return [[[1, 1] for _ in range(num_sections)]]
    
    if not rack.is_protective or rack.protected_column is None:
        num_sections_1 = len(rack.rack_1)
        num_sections_2 = len(rack.rack_2)
        return [
            [[1, 1] for _ in range(num_sections_1)],
            [[1, 1] for _ in range(num_sections_2)]
        ]
    
    logger.warning(f"[JUMPER_CALC] ════════════════════════════════════════════════════════")
    logger.warning(f"[JUMPER_CALC] Calculating jumper presence for PROTECTIVE rack")
    logger.warning(f"[JUMPER_CALC] is_rotated: {is_rotated}")
    
    column = rack.protected_column
    column_bounds = column.contour.bounds
    
    rack_1_bounds = rack.rack_1.bounds
    rack_2_bounds = rack.rack_2.bounds
    
    logger.warning(f"[JUMPER_CALC] rack_1 bounds: {rack_1_bounds}")
    logger.warning(f"[JUMPER_CALC] rack_2 bounds: {rack_2_bounds}")
    logger.warning(f"[JUMPER_CALC] column bounds: {column_bounds}")
    
    column_buffer = column.contour.buffer(10)  
    
    result = []
    
    for rack_idx, subrack in enumerate([rack.rack_1, rack.rack_2]):
        subrack_jumpers = []
        
        logger.warning(f"[JUMPER_CALC] Processing rack_{rack_idx + 1} with {len(subrack.decks)} decks")
        
        for deck_idx, deck in enumerate(subrack.decks):
            deck_bounds = deck.bounds
            
            if is_rotated:
                jumper_y = (deck_bounds[1] + deck_bounds[3]) / 2
                
                jumper_x_start = rack_1_bounds[2]  
                jumper_x_end = rack_2_bounds[0]    
                
                jumper_x_mid = (jumper_x_start + jumper_x_end) / 2
                left_jumper_line = LineString([
                    (jumper_x_start, jumper_y),
                    (jumper_x_mid, jumper_y)
                ])
                
                right_jumper_line = LineString([
                    (jumper_x_mid, jumper_y),
                    (jumper_x_end, jumper_y)
                ])
                
            else:
                jumper_x = (deck_bounds[0] + deck_bounds[2]) / 2
                
                jumper_y_start = rack_1_bounds[3]  
                jumper_y_end = rack_2_bounds[1]    
                
                jumper_y_mid = (jumper_y_start + jumper_y_end) / 2
                left_jumper_line = LineString([
                    (jumper_x, jumper_y_start),
                    (jumper_x, jumper_y_mid)
                ])
                
                right_jumper_line = LineString([
                    (jumper_x, jumper_y_mid),
                    (jumper_x, jumper_y_end)
                ])
            
            left_intersects = left_jumper_line.intersects(column_buffer)
            right_intersects = right_jumper_line.intersects(column_buffer)
            
            left_present = 0 if left_intersects else 1
            right_present = 0 if right_intersects else 1
            
            subrack_jumpers.append([left_present, right_present])
            
            if left_intersects or right_intersects:
                logger.warning(
                    f"[JUMPER_CALC]   rack_{rack_idx + 1} deck {deck_idx}: "
                    f"left={left_present}, right={right_present} "
                    f"(column intersection detected)"
                )
        
        result.append(subrack_jumpers)
    
    logger.warning(f"[JUMPER_CALC] Final jumper matrix: {result}")
    logger.warning(f"[JUMPER_CALC] ════════════════════════════════════════════════════════")
    
    return result

def generate_output(solution: Solution,
                    reference_book: ReferenceBook,
                    task_id: str,
                    warnings_and_errors: str,
                    success_predict: bool) -> ModelOutput:
    """Generates the output for the pallet packing solution.
    Args:
        solution (Solution): The solution containing the pallet packing state.
        reference_book (ReferenceBook): The reference book containing
            business logic related information.
        task_id (str): The task ID for the output.
        warnings_and_errors (str): Warnings and errors encountered during
            the solution generation.
        success_predict (bool): Whether the prediction was successful.
    Returns:
        ModelOutput: Output of the pallet packing model.
    """
    if solution is None or getattr(solution, "saved_rack_groups", None) in (None, []):
        return ModelOutput(task_id=task_id,racks={},warnings_and_errors=(warnings_and_errors or "No valid solution produced by solver"),success_predict=False)
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

            # substract upright_width_eps from upright_width
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
