from src.reference_book import ReferenceBook
from src.solution import Solution, ActionStatus


def rotate_available_zone_90_clockwise(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Rotates the available zone's contour 90 degrees clockwise.

    Args:
        reference_book (ReferenceBook): The reference book containin business
            logic related information.
        solution (Solution): The current solution containing available zones.
    """
    available_zone = solution.available_zones[solution.available_zone_idx]
    available_zone.rotate_az_90_clockwise()
    solution.action_status = ActionStatus.SUCCESS


def rotate_available_zone_90_counterclockwise(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Rotates the available zone's contour 90 degrees counterclockwise.

    Args:
        reference_book (ReferenceBook): The reference book containing business
            logic related information.
        solution (Solution): The current solution containing available zones.
    """
    available_zone = solution.available_zones[solution.available_zone_idx]
    available_zone.rotate_az_90_counterclockwise()
    solution.action_status = ActionStatus.SUCCESS


def set_next_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Sets the next available zone as the current one.
    Args:
        reference_book (ReferenceBook): The reference book containing business
            logic related information.
        solution (Solution): The current solution containing available zones.
    """
    if solution.available_zone_idx < len(solution.available_zones) - 1:
        solution.available_zone_idx += 1
        solution.action_status = ActionStatus.SUCCESS
    else:
        solution.action_status = ActionStatus.FAILED


def set_zone_to_zero_and_set_next_pallet(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Sets the current available zone index to zero and moves to the next pallet.

    Args:
        reference_book (ReferenceBook): The reference book containing business
            logic related information.
        solution (Solution): The current solution containing available zones.
    """
    solution.available_zone_idx = 0
    if solution.pallet_idx < len(solution.pallets) - 1:
        solution.pallet_idx += 1
        solution.action_status = ActionStatus.SUCCESS
    else:
        solution.action_status = ActionStatus.FAILED
