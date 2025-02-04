from typing import List, Tuple

import shapely


class Zone:
    def __init__(self, polygon: List[Tuple[float, float]], height: float):
        self.geometry = shapely.geometry.Polygon(polygon)
        self.height = height
        self.available_area_size = shapely.area(self.geometry)

    def __get_split_zones(self, p0: Tuple[float, float],
                          p1: Tuple[float, float],
                          ps: Tuple[float, float], is_left_smallest: bool
                          ) -> Tuple['Zone', 'Zone', float]:
        x0, y0 = p0
        x1, y1 = p1
        xs, ys = ps

        if is_left_smallest:
            zone_1 = Zone([(x0, ys), (xs, ys), (xs, y1), (x0, y1)],
                          self.height)
            zone_2 = Zone([(xs, y0), (x1, y0), (x1, y1), (xs, y1)],
                          self.height)
            max_available_area = max(zone_1.available_area_size,
                                     zone_2.available_area_size)
        else:
            zone_1 = Zone([(x0, ys), (x1, ys), (x1, y1), (x0, y1)],
                          self.height)
            zone_2 = Zone([(xs, y0), (x1, y0), (x1, ys), (xs, ys)],
                          self.height)
            max_available_area = max(zone_1.available_area_size,
                                     zone_2.available_area_size)

        return zone_1, zone_2, max_available_area

    def split_zone(self, point: Tuple[float, float]) -> Tuple['Zone', 'Zone']:
        x0, y0, x1, y1 = self.geometry.bounds

        if not self.geometry.covers(shapely.geometry.Point(point)):
            raise ValueError("Point is not inside the zone")

        zone_1_l, zone_2_l, max_area_l = self.__get_split_zones(
            (x0, y0), (x1, y1), point, True)
        zone_1_r, zone_2_r, max_area_r = self.__get_split_zones(
            (x0, y0), (x1, y1), point, False)

        if max_area_l > max_area_r:
            return zone_1_l, zone_2_l
        else:
            return zone_1_r, zone_2_r

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        return self.geometry.bounds
