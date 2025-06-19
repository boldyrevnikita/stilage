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
