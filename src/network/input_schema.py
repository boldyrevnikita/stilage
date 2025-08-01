from pydantic import BaseModel, Field


class AvailableZone(BaseModel):
    boundary: list[tuple[float, float]] = Field(
        description="Boundary coordinates of the rectangular available "
        "zone in the format [(x1, y1), (x2, y2), (x3, y3), (x4, y4)] "
        "in millimeters")
    height: float = Field(
        description="Height of the available zone in millimeters")
    orientation: int = Field(
        description="Preferable rack placement orientation: "
        "0 - any, 1 - horizontal, 2 - vertical")
    id: int = Field(
        description="Unique identifier for the available zone should end on 2")


class RestrictedZone(BaseModel):
    boundary: list[tuple[float, float]] = Field(
        description="Boundary coordinates of the restricted zone in the "
        "format [(x1, y1), (x2, y2), ...] in millimeters. Could be any "
        "polygon")
    clearance: float = Field(
        description="Restricted radius around restricted zone in millimeters")
    id: int = Field(
        description="Unique identifier for the restricted zone should "
        "end on 3")


class RoadZone(BaseModel):
    line: list[tuple[float, float]] = Field(
        description="Line coordinates of the road zone in the format "
        "[(x1, y1), (x2, y2)] in millimeters. Should be a straight line "
        "(two points)")
    width: float = Field(
        description="Width of the road zone in millimeters")
    id: int = Field(
        description="Unique identifier for the road zone should end on 5")


class Cargo(BaseModel):
    weight: int = Field(
        description="Weight of the cargo in kilograms")
    length: int = Field(
        description="Length of the cargo in millimeters")
    width: int = Field(
        description="Width of the cargo in millimeters")
    height: int = Field(
        description="Height of the cargo in millimeters")
    quantity: int = Field(
        description="Quantity of the cargo")
    id: int = Field(
        description="Unique identifier for the cargo should end on 4")


class ModelInput(BaseModel):
    task_id: str = Field(
        description="Unique identifier for the task")
    file_id: str = Field(
        description="Unique identifier for the file")
    available_zones: list[AvailableZone] = Field(
        description="List of available zones for placing racks")
    restricted_zones: list[RestrictedZone] = Field(
        description="List of restricted zones where racks cannot be placed")
    road_zones: list[RoadZone] = Field(
        description="List of road zones where racks cannot be placed")
    cargos: list[Cargo] = Field(
        description="List of cargo items to be placed")
    roads_width: float = Field(
        description="Width of the regular roads in millimeters")
    roads_height: float = Field(
        description="Height of the regular roads in millimeters")
