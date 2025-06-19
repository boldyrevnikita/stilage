from src.reference_book import ReferenceBook
from src.zone import AvailableZone
from src.pallet import Pallet
from src.rack import BeamType, UprightType
from src.pallet_packer.solution import Solution, ActionStatus


def find_suitable_beams_and_upright(
    reference_book: ReferenceBook,
    solution: Solution
) -> int:
    available_zone = solution.available_zones[
        solution.available_zone_idx
    ]
    pallet = solution.pallets[solution.pallet_idx]
    beam_types, upright_type, pallet_extra_space = (
        _find_suitable_beams_and_upright(
            reference_book=reference_book,
            available_zone=available_zone,
            pallet=pallet)
        )
    beam_types.sort(key=lambda x: -x.length)

    solution.beam_types = beam_types
    solution.upright_type = upright_type
    solution.pallet_extra_space = pallet_extra_space

    solution.action_status = ActionStatus.SUCCESS


def _find_suitable_beams_and_upright(
    reference_book: ReferenceBook,
    available_zone: AvailableZone,
    pallet: Pallet
) -> tuple[list[BeamType], UprightType, float]:
    choosed_beam_type = _find_suitable_beam_type(
        reference_book=reference_book,
        pallet=pallet
    )
    choosed_upright_type, pallet_extra_space = _find_suitable_upright_type(
        reference_book=reference_book,
        available_zone=available_zone,
        pallet=pallet,
        beam_type=choosed_beam_type
    )
    all_suitable_beam_types = _find_all_suitable_beam_types(
        reference_book=reference_book,
        pallet=pallet,
        beam_type=choosed_beam_type
    )

    return all_suitable_beam_types, choosed_upright_type, pallet_extra_space


def _find_suitable_beam_type(
    reference_book: ReferenceBook,
    pallet: Pallet
) -> BeamType:
    available_beam_types = reference_book.beam_types[
        pallet.pallet_type.pallet_type_id
    ]

    shelf_load_kg = 0
    for beam_type in available_beam_types:
        shelf_load_kg = (pallet.weight
                         * beam_type.max_shelf_load_capacity_pallets)
        if shelf_load_kg <= beam_type.max_shelf_load_capacity_kg:
            return beam_type

    raise ValueError(
        "No suitable beam type found for the given pallet."
    )


def _find_suitable_upright_type(
    reference_book: ReferenceBook,
    available_zone: AvailableZone,
    pallet: Pallet,
    beam_type: BeamType
) -> tuple[UprightType, float]:
    available_height = available_zone.height - reference_book.frame_height_eps

    pallet_extra_space = reference_book.frame_height2pallet_extra_space[-1][1]
    for frame_height, extra_space in \
            reference_book.frame_height2pallet_extra_space:
        if available_height <= frame_height:
            pallet_extra_space = extra_space
            break

    shelf_height = pallet.height + pallet_extra_space
    max_shelfs = available_zone.height // shelf_height
    shelf_load_kg = pallet.weight * beam_type.max_shelf_load_capacity_pallets
    max_frame_load_kg = shelf_load_kg * max_shelfs

    for upright_type in reference_book.upright_types:
        if (upright_type.max_shelf_height >= shelf_height and
                upright_type.max_frame_load_capacity_kg >= max_frame_load_kg):
            return upright_type, pallet_extra_space

    if upright_type.max_shelf_height < shelf_height:
        raise ValueError(
            "No suitable upright type found for the given pallet, "
            "since the pallet+cargo height exceeds maximum shelf height"
        )
    if upright_type.max_frame_load_capacity_kg < shelf_load_kg:
        raise ValueError(
            "No suitable upright type found for the given pallet, "
            "since the pallet weight exceeds maximum frame load capacity"
        )

    return upright_type, pallet_extra_space


def _find_all_suitable_beam_types(
    reference_book: ReferenceBook,
    pallet: Pallet,
    beam_type: BeamType
) -> list[BeamType]:
    available_beam_types = reference_book.beam_types[
        pallet.pallet_type.pallet_type_id
    ]

    suitable_beams = []
    for beam in available_beam_types:
        if (beam_type.beam_section == beam.beam_section
                and beam_type.length >= beam.length):
            suitable_beams.append(beam)

    return suitable_beams
