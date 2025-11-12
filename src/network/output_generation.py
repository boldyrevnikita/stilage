from src.network.output_schema import ModelOutput, RackOutput
from src.pallet_packer.solution import Solution
from src.rack import DoubleRack
from src.reference_book import ReferenceBook
from collections import defaultdict
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def calculate_jumper_presence(rack, is_rotated: bool = False) -> list[list[int]]:
    """Вычисляет наличие перемычек для стеллажа.
    
    Логика:
    - Каждый элемент [x, y] описывает один фрейм (deck)
    - x: 1 = есть перемычка ДО фрейма (слева/снизу), 0 = пересекает колонну
    - y: 1 = есть перемычка ПОСЛЕ фрейма (справа/сверху), 0 = пересекает колонну
    
    Возвращает один массив для всех фреймов обоих под-стеллажей.
    """
    from shapely.geometry import LineString
    
    # Простые случаи - одинарный стеллаж или без защитной колонны
    if not isinstance(rack, DoubleRack):
        num_decks = len(rack.decks)
        return [[1, 1] for _ in range(num_decks)]
    
    if not rack.is_protective or rack.protected_column is None:
        num_decks_1 = len(rack.rack_1.decks)
        num_decks_2 = len(rack.rack_2.decks)
        return [[1, 1] for _ in range(num_decks_1 + num_decks_2)]
    
    logger.warning(f"[JUMPER_CALC] ════════════════════════════════════════════════════════")
    logger.warning(f"[JUMPER_CALC] Calculating jumper presence for PROTECTIVE rack")
    
    column = rack.protected_column
    column_bounds = column.contour.bounds
    
    rack_1_bounds = rack.rack_1.bounds
    rack_2_bounds = rack.rack_2.bounds
    
    logger.warning(f"[JUMPER_CALC] rack_1 bounds: {rack_1_bounds}")
    logger.warning(f"[JUMPER_CALC] rack_2 bounds: {rack_2_bounds}")
    logger.warning(f"[JUMPER_CALC] column bounds: {column_bounds}")
    
    # Центры под-стеллажей
    rack_1_center_x = (rack_1_bounds[0] + rack_1_bounds[2]) / 2
    rack_2_center_x = (rack_2_bounds[0] + rack_2_bounds[2]) / 2
    rack_1_center_y = (rack_1_bounds[1] + rack_1_bounds[3]) / 2
    rack_2_center_y = (rack_2_bounds[1] + rack_2_bounds[3]) / 2
    
    # Определение ориентации
    x_diff = abs(rack_1_center_x - rack_2_center_x)
    y_diff = abs(rack_1_center_y - rack_2_center_y)
    
    racks_side_by_side_on_x = (x_diff > y_diff)
    
    logger.warning(f"[JUMPER_CALC] rack_1 center: ({rack_1_center_x:.1f}, {rack_1_center_y:.1f})")
    logger.warning(f"[JUMPER_CALC] rack_2 center: ({rack_2_center_x:.1f}, {rack_2_center_y:.1f})")
    logger.warning(f"[JUMPER_CALC] X difference: {x_diff:.1f}, Y difference: {y_diff:.1f}")
    logger.warning(f"[JUMPER_CALC] Racks side-by-side on X: {racks_side_by_side_on_x}")
    logger.warning(f"[JUMPER_CALC] → Jumpers orientation: {'VERTICAL (along Y)' if racks_side_by_side_on_x else 'HORIZONTAL (along X)'}")
    
    # Буфер для колонны
    column_buffer = column.contour.buffer(10)
    
    result = []
    
    # Обрабатываем оба под-стеллажа
    for rack_idx, subrack in enumerate([rack.rack_1, rack.rack_2]):
        num_decks = len(subrack.decks)
        
        logger.warning(f"[JUMPER_CALC] Processing rack_{rack_idx + 1} with {num_decks} decks")
        
        # Итерируемся по каждому фрейму
        for deck_idx, deck in enumerate(subrack.decks):
            deck_bounds = deck.bounds  # (min_x, min_y, max_x, max_y)
            
            # Определяем координаты перемычек ДО и ПОСЛЕ фрейма
            if racks_side_by_side_on_x:
                # Стеллажи ГОРИЗОНТАЛЬНО → Перемычки ВЕРТИКАЛЬНЫЕ (вдоль Y)
                
                # Координаты X для перемычек (границы фрейма)
                jumper_before_x = deck_bounds[0]  # Левая граница фрейма
                jumper_after_x = deck_bounds[2]   # Правая граница фрейма
                
                # Y координаты (от одного стеллажа к другому)
                if rack_1_center_y < rack_2_center_y:
                    jumper_y_start = rack_1_bounds[3]  # Верхний край rack_1
                    jumper_y_end = rack_2_bounds[1]    # Нижний край rack_2
                else:
                    jumper_y_start = rack_2_bounds[3]  # Верхний край rack_2
                    jumper_y_end = rack_1_bounds[1]    # Нижний край rack_1
                
                # Линия перемычки ДО фрейма
                jumper_before_line = LineString([
                    (jumper_before_x, jumper_y_start),
                    (jumper_before_x, jumper_y_end)
                ])
                
                # Линия перемычки ПОСЛЕ фрейма
                jumper_after_line = LineString([
                    (jumper_after_x, jumper_y_start),
                    (jumper_after_x, jumper_y_end)
                ])
                
            else:
                # Стеллажи ВЕРТИКАЛЬНО → Перемычки ГОРИЗОНТАЛЬНЫЕ (вдоль X)
                
                # Координаты Y для перемычек (границы фрейма)
                jumper_before_y = deck_bounds[1]  # Нижняя граница фрейма
                jumper_after_y = deck_bounds[3]   # Верхняя граница фрейма
                
                # X координаты (от одного стеллажа к другому)
                if rack_1_center_x < rack_2_center_x:
                    jumper_x_start = rack_1_bounds[2]  # Правый край rack_1
                    jumper_x_end = rack_2_bounds[0]    # Левый край rack_2
                else:
                    jumper_x_start = rack_2_bounds[2]  # Правый край rack_2
                    jumper_x_end = rack_1_bounds[0]    # Левый край rack_1
                
                # Линия перемычки ДО фрейма
                jumper_before_line = LineString([
                    (jumper_x_start, jumper_before_y),
                    (jumper_x_end, jumper_before_y)
                ])
                
                # Линия перемычки ПОСЛЕ фрейма
                jumper_after_line = LineString([
                    (jumper_x_start, jumper_after_y),
                    (jumper_x_end, jumper_after_y)
                ])
            
            # Проверяем пересечения с колонной
            before_intersects = jumper_before_line.intersects(column_buffer)
            after_intersects = jumper_after_line.intersects(column_buffer)
            
            # Если пересекает - 0, иначе - 1
            left_present = 0 if before_intersects else 1
            right_present = 0 if after_intersects else 1
            
            result.append([left_present, right_present])
            
            logger.warning(
                f"[JUMPER_CALC]   rack_{rack_idx + 1} deck {deck_idx}: "
                f"[{left_present}, {right_present}] "
                f"{'(INTERSECTS)' if (before_intersects or after_intersects) else '(OK)'}"
            )
    
    logger.warning(f"[JUMPER_CALC] Final jumper list (total {len(result)} decks): {result}")
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