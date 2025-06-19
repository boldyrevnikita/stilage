from src.pallet_packer.solution import Solution
from src.reference_book import ReferenceBook


def default_action(_: ReferenceBook, solution: Solution) -> None:
    """Executes the default "empty" action for a solution.

    Args:
        _: ReferenceBook: The reference book (not used in this action).
        solution (Solution): The solution to be updated.
    """
    return
