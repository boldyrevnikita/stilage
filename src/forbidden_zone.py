from typing import List, Tuple
from src.rack_group import RackGroup
from src.rack import Rack
import shapely


class ForbiddenZone:
    def __init__(self, polygon: List[Tuple[float, float]],
                 distance_from_zone: float):
        self.geometry = shapely.geometry.Polygon(polygon)
        self.distance_from_zone = distance_from_zone
        self.geometry_with_clearance = self.geometry.buffer(distance_from_zone,
                                                            join_style=2)

    def intersects(self,
                   object: shapely.geometry.base.BaseGeometry) -> bool:
        """Check if the object intersects with the area of the forbidden zone
        or its clearance

        Args:
            object (shapely.geometry.base.BaseGeometry): The object to check.

        Returns:
            bool: True if the object intersects with the area of the forbidden
            zone or its clearance, False otherwise
        """
        return self.geometry_with_clearance.intersects(object)

    def update_clearance(self, new_distance: float):
        """Update the clearance of the forbidden zone.

        Args:
            new_distance (float): The new clearance distance.
        """
        self.distance_from_zone = new_distance
        self.geometry_with_clearance = self.geometry.buffer(new_distance,
                                                            join_style=2)

    def process_intersection(self, rack_group: RackGroup) -> List[Rack]:
        new_racks = []

        for rack in rack_group.racks:
            if not self.intersects(rack.get_convex_hull()):
                new_racks.append(rack)
                continue
            shelfs = [[] for _ in range(
                rack.get_sections_in_width())]
            pillars = [[] for _ in range(
                rack.get_sections_in_width())]
            unit_quantity = []

            is_intersects = False
            for jdx in range(rack.get_sections_in_length()):
                for row in rack.pillar_rows:
                    if self.intersects(row[jdx]):
                        if len(shelfs) > 0 and len(shelfs[-1]) > 0:
                            for new_row in shelfs:
                                new_row.pop()
                            unit_quantity.pop()
                        if len(shelfs[-1]) > 0:
                            new_racks.append(Rack(
                                shelfs, pillars,
                                rack.rack_section,
                                rack.get_sections_in_height(),
                                unit_quantity))
                            shelfs = [[] for _ in range(
                                rack.get_sections_in_width())]
                            unit_quantity = []
                        if len(pillars[-1]) > 0:
                            pillars = [[] for _ in range(
                                rack.get_sections_in_width())]
                        is_intersects = True
                        break

                if is_intersects:
                    is_intersects = False
                    continue

                for kdx, row in enumerate(rack.pillar_rows):
                    pillars[kdx].append(row[jdx])

                for row in rack.shelf_rows:
                    if self.intersects(row[jdx]):
                        if len(shelfs[-1]) > 0:
                            new_racks.append(Rack(
                                shelfs, pillars,
                                rack.rack_section,
                                rack.get_sections_in_height(),
                                unit_quantity))
                            shelfs = [[] for _ in range(
                                rack.get_sections_in_width())]
                            unit_quantity = []
                        if len(pillars[-1]) > 0:
                            pillars = [[] for _ in range(
                                rack.get_sections_in_width())]
                        is_intersects = True
                        break

                if is_intersects:
                    is_intersects = False
                    continue

                for kdx, row in enumerate(rack.shelf_rows):
                    shelfs[kdx].append(row[jdx])
                unit_quantity.append(
                    rack.shelfs_length_unit_quantity[jdx])

            for row in rack.pillar_rows:
                if self.intersects(row[-1]):
                    if len(shelfs) > 0 and len(shelfs[-1]) > 0:
                        for new_row in shelfs:
                            new_row.pop()
                        unit_quantity.pop()
                    is_intersects = True
                    break

            if not is_intersects:
                for kdx, row in enumerate(rack.pillar_rows):
                    pillars[kdx].append(row[-1])

            if len(shelfs[-1]) > 0:
                new_racks.append(Rack(
                    shelfs, pillars,
                    rack.rack_section,
                    rack.get_sections_in_height(),
                    unit_quantity))

        return new_racks


class RoadZone(ForbiddenZone):
    def __init__(self, polygon: List[Tuple[float, float]],
                 distance_from_zone: float = 0.0):
        super().__init__(polygon, distance_from_zone)
