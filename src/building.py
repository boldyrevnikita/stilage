from typing import List, Tuple

import shapely


class Building:
    def __init__(self, walls: List[Tuple[float, float]],
                 distance_from_walls: float):
        self.walls = shapely.geometry.Polygon(walls)
        self.available_space = self.walls.buffer(-distance_from_walls,
                                                 join_style=2)

    def contains(self, object: shapely.geometry.base.BaseGeometry) -> bool:
        return self.available_space.contains(object)

    def intersects(self, object: shapely.geometry.base.BaseGeometry) -> bool:
        return self.walls.intersects(object)
