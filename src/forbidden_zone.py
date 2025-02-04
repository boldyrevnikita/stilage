from typing import List, Tuple

import shapely


class ForbiddenZone:
    def __init__(self, polygon: List[Tuple[float, float]],
                 distance_from_zone: float):
        self.geometry = shapely.geometry.Polygon(polygon)
        self.geometry_with_clearance = self.geometry.buffer(distance_from_zone,
                                                            join_style=2)

    def is_inside(self,
                  object: shapely.geometry.base.BaseGeometry) -> bool:
        return self.geometry_with_clearance.contains(object)
