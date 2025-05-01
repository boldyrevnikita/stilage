import shapely
from typing import List, Literal, Tuple
import numpy as np


class RackSection:
    def __init__(self, id: int, unit_length: float, width: float,
                 height_0: float, height_i: float, height_delta: float,
                 min_unit_shelf_quantity: int,
                 max_unit_shelf_quantity: int,
                 abs_quantity: int, min_quantity: int, max_quantity: int,
                 rel_quantity: float,
                 pillar_width: float,
                 back_connection_distance: float,
                 front_distance: float,
                 back_distance: float, side_distance: float,
                 cargo_weight: float = 0.0) -> None:
        self.id = id
        self.unit_length = unit_length
        self.width = width
        self.height_0 = height_0
        self.height_i = height_i
        self.height_delta = height_delta
        self.min_unit_shelf_quantity = 2
        self.max_unit_shelf_quantity = 4
        self.abs_quantity = abs_quantity
        self.min_quantity = min_quantity
        self.max_quantity = max_quantity
        self.rel_quantity = rel_quantity
        self.quantity_left = abs_quantity
        self.pillar_width = pillar_width
        self.back_connection_distance = back_connection_distance
        self.front_distance = front_distance
        self.back_distance = back_distance
        self.side_distance = side_distance
        self.cargo_weight = cargo_weight
        self.max_available_weight_on_shelf = [
            5000.0, 3800.0, 2100
        ]

        available_height_i = [750.0, 1000.0, 1250.0, 1500.0, 1750.0, 2000.0]
        available_max_weight_load = [21000.0, 20800.0, 20500.0,
                                     19600.0, 18900.0, 18000.0]
        self.max_load_weight = available_max_weight_load[-1]
        height_i = available_height_i[-1]

        for i in range(len(available_height_i)):
            if self.height_i <= available_height_i[i]:
                self.max_load_weight = available_max_weight_load[i]
                height_i = available_height_i[i]
                break
        self.height_i = height_i

    def update_abs_quantity(self, quantity: int) -> None:
        """Update the absolute quantity.

        Args:
            quantity (int): quantity
        """
        self.abs_quantity = quantity
        self.quantity_left = quantity


class Rack:
    def __init__(self, *args, **kwargs):
        self.available_lengths = [1850.0, 2700.0, 3600.0]
        if isinstance(args[0], float):
            self.init_xy(*args, **kwargs)
        else:
            self.init_shelfs_pillars(*args, **kwargs)

    def init_xy(self, x: float, y: float,
                rack_section: RackSection, sections_in_length: int,
                sections_in_width: Literal[1, 2], sections_in_height: int,
                shelfs_length_unit_quantity: List[int]):
        self.rack_section = rack_section
        self.sections_in_length = sections_in_length
        self.sections_in_width = sections_in_width
        self.sections_in_height = sections_in_height
        self.shelfs_length_unit_quantity = shelfs_length_unit_quantity
        self.shelfs_special = np.zeros_like(
            self.get_shelfs_length_unit_quantity()).tolist()

        self.shelf_rows, self.pillar_rows = self.__init_rack(x, y)

    def init_shelfs_pillars(self,
                            shelf_rows: List[List[shapely.geometry.Polygon]],
                            pillar_rows: List[List[shapely.geometry.Polygon]],
                            rack_section: RackSection,
                            sections_in_height: int,
                            shelfs_length_unit_quantity: List[int],
                            shelfs_special: List[int]):
        self.rack_section = rack_section
        self.sections_in_length = len(shelf_rows[0])
        self.sections_in_width = len(shelf_rows)
        self.sections_in_height = sections_in_height
        self.shelfs_length_unit_quantity = shelfs_length_unit_quantity
        self.shelfs_special = shelfs_special

        self.shelf_rows, self.pillar_rows = shelf_rows, pillar_rows

    def __init_rack(self, x: float, y: float
                    ) -> Tuple[List[List[shapely.geometry.Polygon]],
                               List[List[shapely.geometry.Polygon]]]:
        if self.sections_in_width == 1:
            shelf_row_1, pillar_row_1 = self.__init_rack_row(x, y)
            return [shelf_row_1], [pillar_row_1]
        elif self.sections_in_width == 2:
            shelf_row_1, pillar_row_1 = self.__init_rack_row(x, y)
            y += (self.rack_section.width
                  + self.rack_section.back_connection_distance)
            shelf_row_2, pillar_row_2 = self.__init_rack_row(x, y)
            return [shelf_row_1, shelf_row_2], [pillar_row_1, pillar_row_2]
        else:
            raise ValueError("Rack width must be 1 or 2.")

    def __init_rack_row(self, x: float, y: float
                        ) -> Tuple[List[shapely.geometry.Polygon],
                                   List[shapely.geometry.Polygon]]:
        """Initialize the rack.
        """
        shelf_row = []
        pillar_row = []

        for col_idx in range(self.sections_in_length):
            shelf_length = (
                self.available_lengths[
                    self.shelfs_length_unit_quantity[col_idx] - 2])

            pillar = shapely.geometry.Polygon([
                (x, y),
                (x + self.rack_section.pillar_width, y),
                (x + self.rack_section.pillar_width,
                 y + self.rack_section.width),
                (x, y + self.rack_section.width)])

            x += self.rack_section.pillar_width

            shelf = shapely.geometry.Polygon([
                (x, y),
                (x + shelf_length, y),
                (x + shelf_length,
                 y + self.rack_section.width),
                (x, y + self.rack_section.width)])

            x += shelf_length

            shelf_row.append(shelf)
            pillar_row.append(pillar)

        pillar_row.append(
            shapely.geometry.Polygon([
                (x, y),
                (x + self.rack_section.pillar_width, y),
                (x + self.rack_section.pillar_width,
                 y + self.rack_section.width),
                (x, y + self.rack_section.width)]))

        return shelf_row, pillar_row

    def translate(self, x_diff: float, y_diff: float) -> None:
        """Translate the rack.

        Args:
            x_diff (float): x translation
            y_diff (float): y translation
        """
        for i, row in enumerate(self.shelf_rows):
            for j, shelf in enumerate(row):
                self.shelf_rows[i][j] = shapely.affinity.translate(
                    shelf, x_diff, y_diff)
        for i, row in enumerate(self.pillar_rows):
            for j, pillar in enumerate(row):
                self.pillar_rows[i][j] = shapely.affinity.translate(
                    pillar, x_diff, y_diff)

    def rotate(self, angle: float, origin: shapely.geometry.Point) -> None:
        """Rotate the rack.

        Args:
            angle (float): angle of rotation
            origin (shapely.geometry.Point): origin of rotation
        """
        for i, row in enumerate(self.shelf_rows):
            for j, shelf in enumerate(row):
                self.shelf_rows[i][j] = shapely.affinity.rotate(
                    shelf, angle, origin)
        for i, row in enumerate(self.pillar_rows):
            for j, pillar in enumerate(row):
                self.pillar_rows[i][j] = shapely.affinity.rotate(
                    pillar, angle, origin)

    def get_rack_components(self) -> List[shapely.geometry.Polygon]:
        """Get the rack components.

        Returns:
            List: rack components
        """
        rack_components = []
        [rack_components.extend(row) for row in self.shelf_rows]
        [rack_components.extend(row) for row in self.pillar_rows]
        return rack_components

    def get_convex_hull(self) -> shapely.geometry.Polygon:
        """Get the convex hull of the rack.

        Returns:
            shapely.geometry.Polygon: convex hull of the rack
        """
        rack_components = self.get_rack_components()
        return shapely.MultiPolygon(rack_components).convex_hull

    def get_exterior(self) -> shapely.geometry.polygon.LinearRing:
        """Get the exterior of the rack.

        Returns:
            shapely.geometry.Polygon: exterior of the rack
        """
        return self.get_convex_hull().exterior

    def get_shelfs_exteriors(self
                             ) -> List[shapely.geometry.polygon.LinearRing]:
        """Get the exterior of the shelfs.

        Returns:
            List: exterior of the shelfs
        """
        exteriors = []
        for row in self.shelf_rows:
            for shelf in row:
                exteriors.append(shelf.exterior)
        return exteriors

    def get_pillars_exteriors(self
                              ) -> List[shapely.geometry.polygon.LinearRing]:
        """Get the exterior of the pillars.

        Returns:
            List: exterior of the pillars
        """
        exteriors = []
        for row in self.pillar_rows:
            for pillar in row:
                exteriors.append(pillar.exterior)
        return exteriors

    def get_sections_in_length(self) -> int:
        """Get the number of sections in length.

        Returns:
            int: number of sections in length
        """
        return self.sections_in_length

    def get_sections_in_width(self) -> int:
        """Get the number of sections in width.

        Returns:
            int: number of sections in width
        """
        return self.sections_in_width

    def get_sections_in_height(self) -> int:
        """Get the number of sections in height.

        Returns:
            int: number of sections in height
        """
        return self.sections_in_height

    def get_shelfs_length_unit_quantity(self) -> List[int]:
        """Get the shelfs length unit quantity.

        Returns:
            List: shelfs length unit quantity
        """
        shelfs_length_unit_quantity = [
            self.shelfs_length_unit_quantity
            for _ in range(self.sections_in_width)
        ]

        return shelfs_length_unit_quantity

    def get_shelfs_special(self) -> List[int]:
        """Get the special shelfs.
        Returns:
            List: special shelfs
        """

        return self.shelfs_special
