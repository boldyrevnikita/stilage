from typing import List, Tuple

import shapely


class AvailableZone:
    def __init__(self, polygon: List[Tuple[float, float]], height: float):
        self.geometry = shapely.geometry.Polygon(polygon)
        self.height = height
        self.available_area_size = shapely.area(self.geometry)
        self.__check_if_geometry_match_bounding_box()

    def __check_if_geometry_match_bounding_box(self):
        """Checks if the Available Zone boundary (geometry) is a rectangle
        with sides parallel to axis

        Raises:
            ValueError: Available Zone boundary is not a rectangle
        """
        if self.geometry.area != self.geometry.envelope.area:
            raise ValueError("Available Zone boundary should be a rectangle "
                             "with sides parallel to axis")

    def __get_split_zones(self, p0: Tuple[float, float],
                          p1: Tuple[float, float],
                          ps: Tuple[float, float], is_left_smallest: bool
                          ) -> Tuple['AvailableZone', 'AvailableZone', float]:
        """Get the two zones after splitting the current zone with a
        point

        Args:
            p0 (Tuple[float, float]): The down-left point of the zone
            p1 (Tuple[float, float]): The up-right point of the zone
            ps (Tuple[float, float]): The point to split the zone
            is_left_smallest (bool): True if the left zone should
                be the smallest

        Returns:
            Tuple[AvailableZone, AvailableZone, float]: The two zones and the
            maximum available area among them
        """
        x0, y0 = p0
        x1, y1 = p1
        xs, ys = ps

        if is_left_smallest:
            zone_1 = AvailableZone([(x0, ys), (xs, ys), (xs, y1), (x0, y1)],
                                   self.height)
            zone_2 = AvailableZone([(xs, y0), (x1, y0), (x1, y1), (xs, y1)],
                                   self.height)
            max_available_area = max(zone_1.available_area_size,
                                     zone_2.available_area_size)
        else:
            zone_1 = AvailableZone([(x0, ys), (x1, ys), (x1, y1), (x0, y1)],
                                   self.height)
            zone_2 = AvailableZone([(xs, y0), (x1, y0), (x1, ys), (xs, ys)],
                                   self.height)
            max_available_area = max(zone_1.available_area_size,
                                     zone_2.available_area_size)

        return zone_1, zone_2, max_available_area

    def split_zone(self, point: Tuple[float, float]) -> Tuple['AvailableZone',
                                                              'AvailableZone']:
        """Split the zone with a point. The point must be inside the zone.
        One of the two zones should be as big as possible.

        Args:
            point (Tuple[float, float]): The point to split the zone

        Raises:
            ValueError: If the point is not inside the zone

        Returns:
            Tuple[AvailableZone, AvailableZone]: The two zones after the split
        """
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
