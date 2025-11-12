from pydantic import BaseModel, Field
from typing import Optional


class RackOutput(BaseModel):
    boundary: list[tuple[int, int]] = Field(
        description="""Boundary coordinates of the rack in
        the format [(x1, y1), (x2, y2), (x3, y3), (x4, y4)]"""
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
    pallet_with_cargo_height: int = Field(
        description="""Height of the pallet with cargo in the rack"""
    )
    pallet_with_cargo_extra_height: int = Field(
        description="""Extra height of the pallet with cargo in the rack"""
    )
    beam_height: int = Field(
        description="""Height of the beam in the rack"""
    )
    frame_height_eps: int = Field(
        description="""Epsilon value for the frame height"""
    )
    metric_frame_height: int = Field(
        description="""Height of the frame in the rack in metric units"""
    )
    metric_special_frame_height: int = Field(
        description="""Height of the special frame in the rack in
        metric units"""
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
        each integer is a special unit identifier (1 for no special unit,
        2 for a turned off unit, 3 for special unit)"""
    )
    beam_lengths: list[list[int]] = Field(
        description="""List of lists representing the beam lengths:
        each inner list corresponds to a rack,
        and each integer represents the length of the beam in that unit"""
    )
    rack_distance: Optional[int] = Field(
        default=None,
        description="""Distance between racks, if applicable"""
    )
    jumper_presence: Optional[list[list[int]]] = Field(
        default=None,
        description="""Presence of jumpers around rack frames/decks.
        Format: [[left, right], [left, right], ...] where:
        - Each pair [left, right] describes one frame/deck
        - left: 1 = jumper present BEFORE frame (left/bottom), 0 = blocked by column
        - right: 1 = jumper present AFTER frame (right/top), 0 = blocked by column
        - Single flat list containing all frames from both sub-racks (rack_1 + rack_2)
        Example for 5 frames with column intersection between frames 2-3 and after frame 5:
        [[1,1], [1,0], [0,1], [1,1], [1,0]]"""
    )


class ModelOutput(BaseModel):
    task_id: str = Field(description="Unique identifier for the task")
    racks: dict[str, list[RackOutput]] = Field(
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
