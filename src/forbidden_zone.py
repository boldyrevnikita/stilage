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
            shelfs_special = [[] for _ in range(
                rack.get_sections_in_width())]

            is_intersects = False
            for jdx in range(rack.get_sections_in_length()):
                for row in rack.pillar_rows:
                    if self.intersects(row[jdx]):
                        if len(shelfs) > 0 and len(shelfs[-1]) > 0:
                            for new_row, special_row in zip(shelfs,
                                                            shelfs_special):
                                new_row.pop()
                                special_row.pop()
                            unit_quantity.pop()
                        if len(shelfs[-1]) > 0:
                            new_racks.append(Rack(
                                shelfs, pillars,
                                rack.rack_section,
                                rack.get_sections_in_height(),
                                unit_quantity,
                                shelfs_special))
                            shelfs = [[] for _ in range(
                                rack.get_sections_in_width())]
                            unit_quantity = []
                            shelfs_special = [[] for _ in range(
                                rack.get_sections_in_width())]
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
                                unit_quantity,
                                shelfs_special))
                            shelfs = [[] for _ in range(
                                rack.get_sections_in_width())]
                            shelfs_special = [[] for _ in range(
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
                    shelfs_special[kdx].append(rack.shelfs_special[kdx][jdx])
                unit_quantity.append(
                    rack.shelfs_length_unit_quantity[jdx])

            for row in rack.pillar_rows:
                if self.intersects(row[-1]):
                    if len(shelfs) > 0 and len(shelfs[-1]) > 0:
                        for new_row, special_row in zip(shelfs,
                                                        shelfs_special):
                            new_row.pop()
                            special_row.pop()
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
                    unit_quantity,
                    shelfs_special))

        return new_racks


class RoadZone(ForbiddenZone):
    def __init__(self, line: List[Tuple[float, float]],
                 width: float):
        min_x_idx = 0
        min_y_idx = 0

        if line[0][0] > line[1][0]:
            min_x_idx = 1
        if line[0][1] > line[1][1]:
            min_y_idx = 1

        self.orientation = (0 if abs(line[0][0] - line[1][0])
                            > abs(line[0][1] - line[1][1]) else 1)

        if self.orientation == 0:
            x_0 = line[min_x_idx][0]
            y_0 = line[min_y_idx][1] - width / 2
            x_1 = line[abs(min_x_idx - 1)][0]
            y_1 = line[abs(min_y_idx - 1)][1] + width / 2
        else:
            x_0 = line[min_x_idx][0] - width / 2
            y_0 = line[min_y_idx][1]
            x_1 = line[abs(min_x_idx - 1)][0] + width / 2
            y_1 = line[abs(min_y_idx - 1)][1]

        polygon = [(x_0, y_0), (x_1, y_0), (x_1, y_1), (x_0, y_1)]

        super().__init__(polygon, 0.0)
        self.road_width = width

    def process_intersection(self, rack_group: RackGroup) -> List[Rack]:
        max_shelf_length = (
            rack_group.rack_section_info.max_unit_shelf_quantity
            * rack_group.rack_section_info.unit_length
        )

        if max_shelf_length < self.road_width or self.orientation == 0:
            return super().process_intersection(rack_group)
        else:
            for rack in rack_group.racks:
                closest_shelf_idx = None
                closest_distance = float("inf")

                for idx, shelf in enumerate(rack.shelf_rows[0]):
                    distance = shelf.distance(self.geometry_with_clearance)

                    if distance < closest_distance:
                        closest_distance = distance
                        closest_shelf_idx = idx

                if closest_shelf_idx is not None:
                    for row_idx in range(len(rack.shelfs_special)):
                        rack.shelfs_special[row_idx][closest_shelf_idx] = 1

        return rack_group.racks
