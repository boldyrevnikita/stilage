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

    shelf_load_kg = 0
    for beam_type in available_beam_types:
        shelf_load_kg = (pallet.weight
                         * beam_type.max_shelf_load_capacity_pallets)
        if shelf_load_kg <= beam_type.max_shelf_load_capacity_kg:
            return beam_type

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
    available_height = available_zone.height - reference_book.frame_height_eps

    pallet_extra_space = reference_book.frame_height2pallet_extra_space[-1][1]
    for frame_height, extra_space in \
            reference_book.frame_height2pallet_extra_space:
        if available_height <= frame_height:
            pallet_extra_space = extra_space
            break

    shelf_height = pallet.height + pallet_extra_space + beam_type.height
    max_shelfs = available_zone.height // shelf_height

    if max_shelfs == 0:
        raise ActionFailure(
            "Building ceiling is too low."
        )

    max_shelfs_bridge = ((available_zone.height - reference_book.roads_height)
                         // shelf_height)
    max_shelfs_bridge = max(0, max_shelfs_bridge)

    shelf_load_kg = pallet.weight * beam_type.max_shelf_load_capacity_pallets
    max_frame_load_kg = shelf_load_kg * max_shelfs

    while max_shelfs >= 0:
        for upright_type in reference_book.upright_types:
            if (upright_type.max_shelf_height >= shelf_height and
                upright_type.max_frame_load_capacity_kg
                    >= max_frame_load_kg):
                return (upright_type, pallet_extra_space,
                        max_shelfs, max_shelfs_bridge)

        max_shelfs -= 1
        max_shelfs_bridge = min(max_shelfs_bridge, max_shelfs)
        max_frame_load_kg -= shelf_load_kg

    frame_height = shelf_height * max_shelfs + reference_book.frame_height_eps
    if frame_height < upright_type.min_rack_height:
        raise ActionFailure(
            "No suitable upright type found for the given pallet, "
            "since frame height less then minumum available rack height"
        )

    while frame_height > upright_type.max_rack_height:
        max_shelfs -= 1
        max_shelfs_bridge -= 1
        frame_height = (shelf_height * max_shelfs
                        + reference_book.frame_height_eps)

    if upright_type.max_shelf_height < shelf_height:
        raise ActionFailure(
            "No suitable upright type found for the given pallet, "
            "since the pallet+cargo height exceeds maximum shelf height"
        )
    if upright_type.max_frame_load_capacity_kg < shelf_load_kg:
        raise ActionFailure(
            "No suitable upright type found for the given pallet, "
            "since the pallet weight exceeds maximum frame load capacity"
        )

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

    return suitable_beams
