from shapely import Polygon
from src.pallet import Pallet

class BeamType:
    def __init__(self, beam_type_id: int, length: float,
                 beam_section: tuple[float, float],
                 max_shelf_load_capacity_kg: float,
                 max_shelf_load_capacity_pallets: int):
        self.beam_type_id = beam_type_id
        self.length = length
        self.beam_section = beam_section
        self.max_shelf_load_capacity_kg = max_shelf_load_capacity_kg
        self.max_shelf_load_capacity_pallets = max_shelf_load_capacity_pallets


class UprightType:
    def __init__(self, upright_type_id: int,
                upright_section: tuple[float, float, float],
                max_shelf_height: float,
                max_frame_load_capacity_kg: float):
        self.upright_type_id = upright_type_id
        self.upright_section = upright_section
        self.max_shelf_height = max_shelf_height
        self.max_frame_load_capacity_kg = max_frame_load_capacity_kg
    
    @property
    def width(self) -> float:
        """Width of the upright"""
        return self.upright_section[0] 


class Rack:
    def __init__(self, beam_type: BeamType, upright_type: UprightType):
        self.beam_type = beam_type
        self.upright_type = upright_type
        self.decks: list[Polygon] = []
        self.uprights: list[Polygon] = []
        self.enabled_rack
        self.contour: Polygon = self.build_contour()
    
    def __init_simple_rack(self) -> None:
        pass
    
    def build_contour(self) -> Polygon:
        pass


class DoubleRack(Rack):

class RackGroup():
    def __init__(self, position: tuple[float, float],
                 roads_width: float,
                 beam_types: list[BeamType],
                 upright_type: UprightType,
                 pallet: Pallet):
        self.position = position
        self.roads_width = roads_width
        self.next_rack_placement = self._get_first_rack_placement()
        self.current_rack: Rack = 

    def _get_first_rack_placement(self) -> tuple[float, float]:
        return (self.position[0] + self.roads_width,
                self.position[1] + self.roads_width)
    
    def _get_first_rack(self) -> Rack:
        smallest_beam_type = solution.beam_types[-1]
        upright_type = solution.upright_type
        pallet = solution.pallets[solution.pallet_idx]
        
        minimal_rack_length = (upright_type.upright_section[0] * 2
                           + smallest_beam_type.length
                           + reference_book.roads_width * 2)
        minimal_rack_width = pallet.length + reference_book.roads_width * 2

        minimal_rack_contour = shapely.geometry.Polygon(
            [
                (0, 0),
                (minimal_rack_length, 0),
                (minimal_rack_length, minimal_rack_width),
                (0, minimal_rack_width),
            ])
        minimal_rack_contour = shapely.affinity.translate(
            minimal_rack_contour,
            xoff=available_zone.contour.bounds[0],
            yoff=available_zone.contour.bounds[1]
    )
