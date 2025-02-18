from typing import List, Tuple

import shapely


class Building:
    def __init__(self, walls: List[Tuple[float, float]],
                 distance_from_walls: float):
        self.walls = shapely.geometry.Polygon(walls)
        self.distance_from_walls = distance_from_walls
        self.available_space = self.walls.buffer(-distance_from_walls,
                                                 join_style=2)

    def contains(self, object: shapely.geometry.base.BaseGeometry) -> bool:
        """Check if the object is contained in the available space of
        the building

        Args:
            object (shapely.geometry.base.BaseGeometry): The object to check.

        Returns:
            bool: True if the object is contained in the available space of
            the building, False otherwise
        """
        return self.available_space.contains(object)

    def intersects(self, object: shapely.geometry.base.BaseGeometry) -> bool:
        """Check if the object intersects with the area of the building
        bounded by the walls

        Args:
            object (shapely.geometry.base.BaseGeometry): The object to check.

        Returns:
            bool: True if the object intersects with the area of the building
            bounded by the walls, False otherwise
        """
        return self.walls.intersects(object)
