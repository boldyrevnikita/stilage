from typing import List, Tuple

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
