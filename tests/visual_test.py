import os
import sys

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))

from src.pallet import CargoType  # noqa: E402
from src.zone import AvailableZone, OccupiedZone, SpecialRoadZone  # noqa: E402
from src.cargo_packer import CargoPacker  # noqa: E402
from src.pallet_packer.pallet_packer import PalletPacker  # noqa: E402
from src.visualize import visualize_solution  # noqa: E402


cargos = [
    CargoType(cargo_type_id=1,
              weight=500.0,
              length=700.0,
              width=500.0,
              height=300.0,
              quantity=1000),
]

available_zones = [
    AvailableZone(
        contour=[(0, 0), (20000, 0), (20000, 20000), (0, 20000)],
        height=5000.0,
    )
]

occupied_zones = [
    OccupiedZone(
        contour=[(2000, 2000), (2100, 2000), (2100, 2100), (2000, 2100)],
        clearance=250.0,
        roads_width=3000.0),
    OccupiedZone(
        contour=[(8000, 8000), (8200, 8000), (8200, 8200), (8000, 8200)],
        clearance=250.0,
        roads_width=3000.0),
]

special_road_zones = [
    SpecialRoadZone(
        line=[(0, 9000), (20000, 9000)],
        width=3000.0,
    )
]

pallets = CargoPacker.pack_cargos(
    cargos=cargos
)

print(len(pallets))

solution = PalletPacker.pack_pallets(
    pallets=pallets,
    available_zones=available_zones,
    occupied_zones=occupied_zones,
    special_road_zones=special_road_zones
)

if solution:
    solution.available_zones = available_zones
    visualize_solution(solution)
    print("Packing successful!")
