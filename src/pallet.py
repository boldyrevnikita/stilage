from pydantic import BaseModel, Field


class PalletType(BaseModel):
    pallet_type_id: int = Field(
        frozen=True,
        description="Unique identifier for the pallet type")
    weight: float = Field(
        gt=0, frozen=True,
        description="Weight of the pallet type in kilograms")
    length: float = Field(
        gt=0, frozen=True,
        description="Length of the pallet type in millimeters")
    width: float = Field(
        gt=0, frozen=True,
        description="Width of the pallet type in millimeters")
    height: float = Field(
        gt=0, frozen=True,
        description="Height of the pallet type in millimeters")


class CargoType(BaseModel):
    cargo_type_id: int = Field(
        frozen=True,
        description="Unique identifier for the cargo type")
    weight: float = Field(
        gt=0, frozen=True,
        description="Weight of the cargo type in kilograms")
    length: float = Field(
        gt=0, frozen=True,
        description="Length of the cargo type in millimeters")
    width: float = Field(
        gt=0, frozen=True,
        description="Width of the cargo type in millimeters")
    height: float = Field(
        gt=0, frozen=True,
        description="Height of the cargo type in millimeters")
    quantity: int = Field(
        gt=0, frozen=True,
        description="Quantity of the cargo type")


class Pallet(BaseModel):
    pallet_type: PalletType = Field(
        description="Pallet type of the pallet")
    cargo: CargoType = Field(
        description="Cargo loaded on the pallet")

    @property
    def weight(self) -> float:
        """Weight of the pallet including the cargo"""
        return self.pallet_type.weight + self.cargo.weight

    @property
    def height(self) -> float:
        """Height of the pallet including the cargo"""
        return self.pallet_type.height + self.cargo.height

    @property
    def width(self) -> float:
        """Width of the pallet"""
        return self.pallet_type.width

    @property
    def length(self) -> float:
        """Length of the pallet"""
        return self.pallet_type.length
