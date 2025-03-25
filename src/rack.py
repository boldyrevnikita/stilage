import shapely
from typing import List


class RackSection:
    def __init__(self, id: int, length: float, width: float, height_0: float,
                 height_i: float, height_delta: float,
                 abs_quantity: int, min_quantity: int, max_quantity: int,
                 rel_quantity: float,
                 pillar_width: float,
                 back_connection_distance: float,
                 front_distance: float,
                 back_distance: float, side_distance: float):
        self.id = id
        self.length = length
        self.width = width
        self.height_0 = height_0
        self.height_i = height_i
        self.height_delta = height_delta
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

    def update_abs_quantity(self, quantity: int) -> None:
        """Update the absolute quantity.

        Args:
            quantity (int): quantity
        """
        self.abs_quantity = quantity
        self.quantity_left = quantity


class Rack:
    def __init__(self, shelf_rows: List[List[shapely.geometry.Polygon]],
                 pillar_rows: List[List[shapely.geometry.Polygon]],
                 sections_in_height: int):
        self.shelf_rows = shelf_rows
        self.pillar_rows = pillar_rows
        self.sections_in_height = sections_in_height

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
        return len(self.shelf_rows[0])

    def get_sections_in_width(self) -> int:
        """Get the number of sections in width.

        Returns:
            int: number of sections in width
        """
        return len(self.shelf_rows)

    def get_sections_in_height(self) -> int:
        """Get the number of sections in height.

        Returns:
            int: number of sections in height
        """
        return self.sections_in_height
