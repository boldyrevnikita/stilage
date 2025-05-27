from pydantic import BaseModel, Field
from shapely import Polygon


class BeamType(BaseModel):
    beam_type_id: int = Field(
        frozen=True,
        description="Unique identifier for the beam type")
    length: float = Field(
        gt=0, frozen=True,
        description="Length of the beam type in millimeters")
    beam_section: tuple[float, float] = Field(
        frozen=True,
        description="Dimensions of the beam section in millimeters")
    max_shelf_load_capacity_kg: float = Field(
        gt=0, frozen=True,
        description="Maximum load capacity of the shelf in kilograms")
    max_shelf_load_capacity_pallets: int = Field(
        gt=0, frozen=True,
        description="Maximum load capacity of the shelf in pallets")


class UprightType(BaseModel):
    upright_type_id: int = Field(
        frozen=True,
        description="Unique identifier for the upright type")
    upright_section: tuple[float, float, float] = Field(
        frozen=True,
        description="Dimensions of the upright section in millimeters")
    max_shelf_height: float = Field(
        gt=0, frozen=True,
        description="Maximum height between shelves in millimeters")
    max_frame_load_capacity_kg: float = Field(
        gt=0, frozen=True,
        description="Maximum load capacity of the frame in kilograms")


class Rack(BaseModel):
    beam_type: BeamType = Field(
        description="Beam type of the rack")
    upright_type: UprightType = Field(
        description="Upright type of the rack")
    height_0: float = Field(
        default=upright_type.max_shelf_height,
        gt=0, lt=upright_type.max_shelf_height,
        description="Height of the first beam from the ground")
    height_i: float = Field(
        default=upright_type.max_shelf_height,
        gt=0, lt=upright_type.max_shelf_height,
        description="Height between the i-th and (i+1)-th beams"
    )
    height_delta: float = Field(
        gt=0,
        description="Height after the last beam")
    decks_quantity: int = Field(
        gt=0,
        description="Number of decks in the rack")
    frames_quantity: int = Field(
        gt=0,
        description="Number of frames in the rack")

    def __init__(self, beam_type: BeamType, upright_type: UprightType,
                 height_0: float, height_i: float, height_delta: float,
                 decks_quantity: int, frames_quantity: int):
        super().__init__(
            beam_type=beam_type,
            upright_type=upright_type,
            height_0=height_0,
            height_i=height_i,
            height_delta=height_delta,
            decks_quantity=decks_quantity,
            frames_quantity=frames_quantity
        )
        self.contour: Polygon = Field(
            default=self.build_contour(),
            description="Contour of the rack in millimeters")

    def build_contour(self) -> Polygon:
        pass


class RackGroup():
    def __init__(self, racks: list[Rack]):
        self.racks = racks
        self.contour: Polygon = Field(
            default=self.build_contour(),
            description="Contour of the rack group in millimeters")

    def build_contour(self) -> Polygon:
        pass
