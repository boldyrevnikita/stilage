from src.pallet import Pallet
from src.pallet_packer.solution import Solution, ActionFailure
from src.rack import BeamType, UprightType
from src.reference_book import ReferenceBook
from src.zone import AvailableZone


def find_suitable_beams_and_upright(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Finds suitable beams and upright types for the current pallet
    based on the available zone and pallet type in the solution.
    Args:
        reference_book (ReferenceBook): The reference book containing
            business logic related information.
        solution (Solution): The current solution containing available zones
            and pallets.
    """
    available_zone = solution.available_zones[
        solution.available_zone_idx
    ]
    pallet = solution.pallets[solution.pallet_idx]
    
    print("=" * 80)
    print("🔍 НАЧАЛО ВЫБОРА БАЛКИ И СТОЙКИ")
    print(f"📦 Паллета: тип={pallet.pallet_type.pallet_type_id}, "
          f"вес={pallet.weight} кг, высота={pallet.height} мм")
    print(f"📏 Зона: высота={available_zone.height} мм")
    print("=" * 80)
    
    (beam_types, upright_type, max_shelfs,
        max_shelfs_bridge, pallet_extra_space) = (
        _find_suitable_beams_and_upright(
            reference_book=reference_book,
            available_zone=available_zone,
            pallet=pallet)
        )
    beam_types.sort(key=lambda x: -x.length)

    solution.beam_types = beam_types
    solution.upright_type = upright_type
    solution.pallet_extra_space = pallet_extra_space
    solution.max_shelfs = max_shelfs
    solution.max_shelfs_bridge = max_shelfs_bridge
    
    print("=" * 80)
    print("✅ ИТОГОВЫЙ РЕЗУЛЬТАТ:")
    print(f"   Выбранная стойка: {upright_type}")
    print(f"   Количество полок: {max_shelfs}")
    print(f"   Полок на мосту: {max_shelfs_bridge}")
    print("=" * 80)


def _find_suitable_beams_and_upright(
    reference_book: ReferenceBook,
    available_zone: AvailableZone,
    pallet: Pallet
) -> tuple[list[BeamType], UprightType, float, float, float]:
    """Finds suitable beams and upright types for the given pallet
    based on the available zone and pallet type.
    Args:
        reference_book (ReferenceBook): The reference book containing
            business logic related information.
        available_zone (AvailableZone): The available zone to place racks.
        pallet (Pallet): The pallet to find suitable beams and upright
            types for.
    Returns:
        tuple: A tuple containing:
            - list[BeamType]: All suitable beam types for the pallet.
            - UprightType: The chosen upright type for the pallet.
            - float: The maximum number of shelves that can be placed.
            - float: The maximum number of shelves that can be
                placed in a bridge.
            - float: The extra space required for the pallet.
    """
    choosed_beam_type = _find_suitable_beam_type(
        reference_book=reference_book,
        pallet=pallet
    )
    choosed_upright_type, pallet_extra_space, max_shelfs, max_shelfs_bridge = (
        _find_suitable_upright_type(
            reference_book=reference_book,
            available_zone=available_zone,
            pallet=pallet,
            beam_type=choosed_beam_type
        )
    )
    all_suitable_beam_types = _find_all_suitable_beam_types(
        reference_book=reference_book,
        pallet=pallet,
        beam_type=choosed_beam_type
    )

    return (all_suitable_beam_types, choosed_upright_type,
            max_shelfs, max_shelfs_bridge, pallet_extra_space)


def _find_suitable_beam_type(
    reference_book: ReferenceBook,
    pallet: Pallet
) -> BeamType:
    """
    Finds a suitable beam type for the given pallet.

    Args:
        reference_book (ReferenceBook): The reference book containing
            business logic related information.
        pallet (Pallet): The pallet to find a suitable beam type for.
    Returns:
        BeamType: The suitable beam type for the given pallet.
    """
    available_beam_types = reference_book.beam_types[
        pallet.pallet_type.pallet_type_id
    ]
    
    print("\n🔧 ВЫБОР БАЛКИ:")
    print(f"   Доступно балок: {len(available_beam_types)}")
    print("   Первые 5 балок в списке:")
    for i, bt in enumerate(available_beam_types[:5]):
        print(f"      {i+1}. Длина={bt.length} мм, "
              f"сечение={bt.beam_section}, "
              f"макс_паллет={bt.max_shelf_load_capacity_pallets}, "
              f"макс_вес={bt.max_shelf_load_capacity_kg} кг")

    shelf_load_kg = 0
    for idx, beam_type in enumerate(available_beam_types):
        shelf_load_kg = (pallet.weight
                         * beam_type.max_shelf_load_capacity_pallets)
        print(f"\n   Проверка балки #{idx+1}:")
        print(f"      Длина: {beam_type.length} мм")
        print(f"      Сечение: {beam_type.beam_section}")
        print(f"      Паллет на полке: {beam_type.max_shelf_load_capacity_pallets}")
        print(f"      Нагрузка: {pallet.weight} кг × {beam_type.max_shelf_load_capacity_pallets} = {shelf_load_kg} кг")
        print(f"      Макс грузоподъемность: {beam_type.max_shelf_load_capacity_kg} кг")
        
        if shelf_load_kg <= beam_type.max_shelf_load_capacity_kg:
            print(f"   ✅ ВЫБРАНА: Длина={beam_type.length} мм, "
                  f"Сечение={beam_type.beam_section}, "
                  f"Высота балки={beam_type.beam_section[0]} мм")
            return beam_type
        else:
            print(f"   ❌ Не подходит: {shelf_load_kg} > {beam_type.max_shelf_load_capacity_kg}")

    raise ActionFailure(
        "No suitable beam type found for the given pallet."
    )


def _find_suitable_upright_type(
    reference_book: ReferenceBook,
    available_zone: AvailableZone,
    pallet: Pallet,
    beam_type: BeamType
) -> tuple[UprightType, float, float, float]:
    """
    Finds a suitable upright type for the given pallet and available zone.
    Args:
        reference_book (ReferenceBook): The reference book containing
            business logic related information.
        available_zone (AvailableZone): The available zone to place racks.
        pallet (Pallet): The pallet to find a suitable upright type for.
        beam_type (BeamType): The beam type to use.
    Returns:
        tuple: A tuple containing:
            - UprightType: The chosen upright type for the pallet.
            - float: The extra space required for the pallet.
            - float: The maximum number of shelves that can be placed.
            - float: The maximum number of shelves that can be
                placed in a bridge.
    """
    print("\n🏗️  ВЫБОР СТОЙКИ:")
    print(f"   Входные данные:")
    print(f"      Высота зоны: {available_zone.height} мм")
    print(f"      frame_height_eps: {reference_book.frame_height_eps} мм")
    print(f"      available_zone.height % 500 = {available_zone.height % 500}")
    
    available_height = available_zone.height - max(reference_book.frame_height_eps, available_zone.height % 500)
    print(f"   📏 Доступная высота: {available_height} мм")

    pallet_extra_space = reference_book.frame_height2pallet_extra_space[-1][1]
    print(f"\n   Определение extra_space:")
    for frame_height, extra_space in \
            reference_book.frame_height2pallet_extra_space:
        print(f"      Если высота <= {frame_height}: extra_space = {extra_space}")
        if available_height <= frame_height:
            pallet_extra_space = extra_space
            print(f"   ✅ Выбрано: pallet_extra_space = {pallet_extra_space} мм")
            break

    print(f"\n   📊 Расчет высоты полки:")
    print(f"      pallet.height = {pallet.height} мм")
    print(f"      pallet_extra_space = {pallet_extra_space} мм")
    print(f"      beam_type.height = {beam_type.beam_section[0]} мм")
    
    shelf_height = pallet.height + pallet_extra_space + beam_type.beam_section[0]
    print(f"   📦 shelf_height = {pallet.height} + {pallet_extra_space} + {beam_type.beam_section[0]} = {shelf_height} мм")
    
    max_shelfs = available_height // shelf_height
    print(f"   🔢 max_shelfs = {available_height} // {shelf_height} = {max_shelfs}")

    if max_shelfs == 0:
        raise ActionFailure(
            "Building ceiling is too low."
        )

    max_shelfs_bridge = ((available_height - reference_book.roads_height)
                         // shelf_height)
    max_shelfs_bridge = max(0, max_shelfs_bridge)
    print(f"   🌉 max_shelfs_bridge = {max_shelfs_bridge}")

    shelf_load_kg = pallet.weight * beam_type.max_shelf_load_capacity_pallets
    max_frame_load_kg = shelf_load_kg * max_shelfs
    
    print(f"\n   💪 Расчет нагрузки:")
    print(f"      shelf_load_kg = {pallet.weight} × {beam_type.max_shelf_load_capacity_pallets} = {shelf_load_kg} кг")
    print(f"      max_frame_load_kg = {shelf_load_kg} × {max_shelfs} = {max_frame_load_kg} кг")
    
    # Initialize upright_type to avoid 'referenced before assignment' error
    upright_type: UprightType | None = None
    
    print(f"\n   🔍 ПОИСК ПОДХОДЯЩЕЙ СТОЙКИ:")
    print(f"      Требования: max_shelf_height >= {shelf_height}, max_frame_load >= {max_frame_load_kg}")
    
    iteration = 0
    while max_shelfs >= 0 and upright_type is None:
        iteration += 1
        print(f"\n      --- Итерация #{iteration} ---")
        print(f"      Текущие параметры: max_shelfs={max_shelfs}, max_frame_load_kg={max_frame_load_kg}")
        
        # Search for suitable upright by shelf height and frame load capacity
        for ut_idx, ut in enumerate(reference_book.upright_types):
            if ut_idx < 3 or (ut.max_shelf_height >= shelf_height and
                ut.max_frame_load_capacity_kg >= max_frame_load_kg):
                # Печатаем первые 3 стойки всегда, остальные только если подходят
                match = (ut.max_shelf_height >= shelf_height and
                        ut.max_frame_load_capacity_kg >= max_frame_load_kg)
                symbol = "✅" if match else "❌"
                if ut_idx < 3 or match:
                    print(f"         {symbol} Стойка #{ut_idx}: "
                          f"section={ut.upright_section}, "
                          f"max_shelf_h={ut.max_shelf_height}, "
                          f"max_load={ut.max_frame_load_capacity_kg}, "
                          f"min_h={ut.min_rack_height}, max_h={ut.max_rack_height}")
                
            if (ut.max_shelf_height >= shelf_height and
                ut.max_frame_load_capacity_kg >= max_frame_load_kg):
                upright_type = ut
                print(f"      ✅ НАЙДЕНА подходящая стойка!")
                break
        
        if upright_type is None:
            # Reduce number of shelves and recalculate load
            print(f"      ⚠️  Стойка не найдена, уменьшаем количество полок")
            max_shelfs -= 1
            max_shelfs_bridge = min(max_shelfs_bridge, max_shelfs)
            max_frame_load_kg -= shelf_load_kg
            print(f"      Новые параметры: max_shelfs={max_shelfs}, max_frame_load_kg={max_frame_load_kg}")

    if upright_type is None:
        raise ActionFailure(
            "No suitable upright type found for the given pallet."
        )

    print(f"\n   ✅ ВЫБРАНА СТОЙКА:")
    print(f"      ID: {upright_type.upright_type_id}")
    print(f"      Сечение: {upright_type.upright_section}")
    print(f"      Max высота полки: {upright_type.max_shelf_height} мм")
    print(f"      Max нагрузка: {upright_type.max_frame_load_capacity_kg} кг")
    print(f"      Min высота рамы: {upright_type.min_rack_height} мм")
    print(f"      Max высота рамы: {upright_type.max_rack_height} мм")

    frame_height = shelf_height * max_shelfs + reference_book.frame_height_eps
    print(f"\n   📐 Проверка высоты рамы:")
    print(f"      frame_height = {shelf_height} × {max_shelfs} + {reference_book.frame_height_eps} = {frame_height} мм")
    
    if frame_height < upright_type.min_rack_height:
        print(f"   ❌ ОШИБКА: {frame_height} < {upright_type.min_rack_height} (min_rack_height)")
        raise ActionFailure(
            "No suitable upright type found for the given pallet, "
            "since frame height is less than minimum available rack height"
        )

    adjustment_count = 0
    while frame_height > upright_type.max_rack_height:
        adjustment_count += 1
        print(f"   ⚠️  Корректировка #{adjustment_count}: {frame_height} > {upright_type.max_rack_height}, уменьшаем полки")
        max_shelfs -= 1
        max_shelfs_bridge = max(0, min(max_shelfs_bridge, max_shelfs))
        frame_height = (shelf_height * max_shelfs
                        + reference_book.frame_height_eps)
        print(f"      Новые: max_shelfs={max_shelfs}, frame_height={frame_height}")

    print(f"   ✅ Финальная высота рамы: {frame_height} мм")
    
    # Final checks
    if upright_type.max_shelf_height < shelf_height:
        print(f"   ❌ ОШИБКА: max_shelf_height ({upright_type.max_shelf_height}) < shelf_height ({shelf_height})")
        raise ActionFailure(
            "No suitable upright type found for the given pallet, "
            "since the pallet+cargo height exceeds maximum shelf height"
        )
    if upright_type.max_frame_load_capacity_kg < shelf_load_kg:
        print(f"   ❌ ОШИБКА: max_frame_load ({upright_type.max_frame_load_capacity_kg}) < shelf_load ({shelf_load_kg})")
        raise ActionFailure(
            "No suitable upright type found for the given pallet, "
            "since the pallet weight exceeds maximum frame load capacity"
        )

    print(f"\n   🎯 Финальные параметры:")
    print(f"      Количество полок: {max_shelfs}")
    print(f"      Полок на мосту: {max_shelfs_bridge}")
    print(f"      Extra space: {pallet_extra_space} мм")

    return upright_type, pallet_extra_space, max_shelfs, max_shelfs_bridge


def _find_all_suitable_beam_types(
    reference_book: ReferenceBook,
    pallet: Pallet,
    beam_type: BeamType
) -> list[BeamType]:
    """ Finds all suitable beam types for the given pallet
    based on the beam type properties.
    Args:
        reference_book (ReferenceBook): The reference book containing
            business logic related information.
        pallet (Pallet): The pallet to find suitable beam types for.
        beam_type (BeamType): The beam type to use.
    Returns:
        list[BeamType]: All suitable beam types for the given pallet.
    """
    available_beam_types = reference_book.beam_types[
        pallet.pallet_type.pallet_type_id
    ]

    suitable_beams = []
    for beam in available_beam_types:
        if (beam_type.beam_section == beam.beam_section
                and beam_type.length >= beam.length):
            suitable_beams.append(beam)
    
    print(f"\n📋 Найдено подходящих балок: {len(suitable_beams)}")
    for i, beam in enumerate(suitable_beams[:3]):
        print(f"   {i+1}. Длина={beam.length} мм, сечение={beam.beam_section}")

    return suitable_beams