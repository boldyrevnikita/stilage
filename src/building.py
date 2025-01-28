import shapely
from typing import List, Tuple


class Building:
    def __init__(self, walls: List[Tuple[float]], distance_from_walls: float):
        self.walls = shapely.geometry.Polygon(walls)
        self.available_space = self.walls.buffer(-distance_from_walls,
                                                 join_style=2)

    def is_inside_available_space(self,
                                  object: shapely.geometry.base.BaseGeometry):
        return self.available_space.contains(object)
