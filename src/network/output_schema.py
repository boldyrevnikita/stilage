from pydantic import BaseModel, Field
from typing import Optional


class RackOutput(BaseModel):
    boundary: list[tuple[int, int]] = Field(
        description="""Boundary coordinates of the rack in
        the format [(x1, y1), (x2, y2), ...]"""
    )
    sections_in_length: int = Field(
        description="""Number of sections in the length of the rack"""
    )
    sections_in_width: int = Field(
        description="""Number of sections in the width of the rack"""
    )
    sections_in_height: int = Field(
        description="""Number of sections in the height of the rack"""
    )
    sections_in_height_special: int = Field(
        description="""Number of sections in the height of
        the rack that are special"""
    )
    orientation: int = Field(
        description="Orientation of the rack"
    )
    upright_section: tuple[int, int, float] = Field(
        description="""Tuple representing the upright section of the rack:
        (width, length, wall thickness)"""
    )
    beam_section: tuple[int, float] = Field(
        description="""Tuple representing the beam section of the rack:
        (width, wall thickness)"""
    )
    pallet_size: tuple[int, int] = Field(
        description="""Tuple representing the pallet size:
        (width, length)"""
    )
    units: list[list[int]] = Field(
        description="""List of lists representing the number of pallets:
        each inner list corresponds to a rack,
        and each integer represents the number of pallets in that unit"""
    )
    special_units: list[list[int]] = Field(
        description="""List of lists representing special units in the rack,
        where each inner list corresponds to a rack and
        each integer is a special unit identifier (e.g. 0 for no special unit,
        1 for a special unit)"""
    )
    beam_lengths: list[list[int]] = Field(
        description="""List of lists representing the beam lengths:
        each inner list corresponds to a rack,
        and each integer represents the length of the beam in that unit"""
    )
    rack_distance: Optional[float] = Field(
        default=None,
        description="""Distance between racks, if applicable"""
    )


class ModelOutput(BaseModel):
    task_id: str = Field(description="Unique identifier for the task")
    racks: dict[str, RackOutput] = Field(
        description="""Dictionary mapping cargo IDs
        to their respective rack outputs""",
    )
    warnings_and_errors: Optional[str] = Field(
        default=None,
        description="""Warnings and errors encountered during processing,
        if any"""
    )
    success_predict: bool = Field(
        default=True,
        description="""Indicates whether the prediction was successful"""
    )
