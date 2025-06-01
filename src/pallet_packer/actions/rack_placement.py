from reference_book import ReferenceBook
from solution import Solution, ActionStatus
import shapely
from src.rack import RackGroup


def check_if_enough_space_for_horizontal_rack_placement(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """
    Checks if there is enough space for horizontal rack placement.

    Args:
        reference_book (ReferenceBook): The reference book containing business
            logic related information.
        solution (Solution): The current solution containing available zones.
    """

    available_zone = solution.available_zones[solution.available_zone_idx]
    smallest_beam_type = solution.beam_types[-1]
    upright_type = solution.upright_type
    pallet = solution.pallets[solution.pallet_idx]

    minimal_rack_height = ((pallet.height + solution.pallet_extra_space
                           + smallest_beam_type.beam_section[0]) * 2
                           + reference_book.frame_height_eps)
    if minimal_rack_height > available_zone.height:
        solution.action_status = ActionStatus.FAILED
        return

    minimal_rack_length = (upright_type.upright_section[0] * 2
                           + smallest_beam_type.length
                           + reference_book.roads_width * 2)
    minimal_rack_width = pallet.length + reference_book.roads_width * 2

    minimal_rack_contour = shapely.geometry.Polygon(
        [
            (0, 0),
            (minimal_rack_length, 0),
            (minimal_rack_length, minimal_rack_width),
            (0, minimal_rack_width),
        ])
    minimal_rack_contour = shapely.affinity.translate(
        minimal_rack_contour,
        xoff=available_zone.contour.bounds[0],
        yoff=available_zone.contour.bounds[1]
    )

    if not available_zone.contains(minimal_rack_contour):
        solution.action_status = ActionStatus.FAILED
        return

    solution.action_status = ActionStatus.SUCCESS


def place_horizontal_rack_group(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    available_zone = solution.available_zones[solution.available_zone_idx]

    rack_group = RackGroup(
        position=available_zone.bounds[:2],
        roads_width=reference_book.roads_width
    )

    solution.current_rack_group = rack_group
    solution.action_status = ActionStatus.SUCCESS
