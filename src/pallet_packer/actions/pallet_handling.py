from src.reference_book import ReferenceBook
from src.pallet_packer.solution import Solution, ActionFailure


def set_next_pallet(
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

    if solution.pallet_idx < len(solution.pallets) - 1:
        solution.pallet_idx += 1
    else:
        raise ActionFailure("No more pallets to process.")


def sort_pallets_by_weight_height_width(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Sorts the pallets in the solution by weight, height, and width.
    Args:
        reference_book (ReferenceBook): The reference book containing business
            logic related information.
        solution (Solution): The current solution containing pallets.
    """
    solution.pallets.sort(key=lambda x: (x.weight, x.height, x.width))


def increase_pallet_counter(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Increases the pallet count for the current pallet in the solution.

    Args:
        reference_book (ReferenceBook): The reference book containing business
            logic related information.
        solution (Solution): The current solution containing pallets.
    """
    cargo_id = solution.pallets[solution.pallet_idx].cargo.cargo_type_id
    current_rack = solution.current_rack_group.get_current_rack()
    solution.pallet_count[cargo_id] += (
        current_rack.calculate_pallet_capacity_in_ith_frame(
            len(current_rack) - 1))


def assert_current_pallets_are_enough(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Asserts that the current pallets in the solution are enough to fill
        new frames.

    Args:
        reference_book (ReferenceBook): The reference book containing business
            logic related information.
        solution (Solution): The current solution containing pallets.
    """
    current_cargo_max_quantity = (
        solution.pallets[solution.pallet_idx].cargo.quantity)
    cargo_id = solution.pallets[solution.pallet_idx].cargo.cargo_type_id

    if current_cargo_max_quantity - solution.pallet_count[cargo_id] <= 0:
        raise ActionFailure(
            f"Not enough pallets of cargo type {cargo_id} to fill new frames."
        )
