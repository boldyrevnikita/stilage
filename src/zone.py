from shapely import Polygon
from copy import deepcopy
import shapely


class Zone:
    def __init__(self, contour: list[tuple[float, float]]):
        """
        Initializes a Zone with a given contour.

        Args:
            contour (list[tuple[float, float]]): A list of tuples representing
                the vertices of the zone's contour.
        """

        self.contour: Polygon = Polygon(contour)
        if not self.contour.is_valid:
            raise ValueError("Invalid contour for the zone")

    @property
    def area(self) -> float:
        """
        Returns the area of the zone's contour.

        Returns:
            float: The area of the zone.
        """
        return self.contour.area

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """
        Returns the bounding box of the zone's contour.

        Returns:
            tuple[float, float, float, float]: The bounding box of the zone
                in the format (min_x, min_y, max_x, max_y).
        """
        return self.contour.bounds

    def rotate(self, rot_point: tuple[float, float], angle: float) -> None:
        self.contour = shapely.affinity.rotate(
            self.contour, angle=angle, origin=rot_point)


class OccupiedZone(Zone):
    def __init__(self, contour: list[tuple[float, float]], clearance: float,
                 roads_width: float, should_be_available: bool = False):
        """
        Initializes an OccupiedZone with a given contour, clearance,
            and availability status.

        Args:
            contour (list[tuple[float, float]]): A list of tuples representing
                the vertices of the zone's contour.
            clearance (float): The clearance distance from the occupied zone.
            should_be_available (bool, optional): Indicates if the zone should
                be available. Defaults to False.
        """
        super().__init__(contour)
        self.clearance = clearance
        self.roads_width = roads_width
        if self.clearance < 0:
            raise ValueError("Clearance must be non-negative")
        self.should_be_available = should_be_available
        if not isinstance(self.should_be_available, bool):
            raise ValueError("should_be_available must be a boolean")

        self.contour_with_clearance: Polygon = self.contour.buffer(
            self.clearance,  join_style=2)
        self.contour_with_roads_width: Polygon = self.contour.buffer(
            self.roads_width, join_style=2)

    def rotate(self, rot_point: tuple[float, float], angle: float):
        super().rotate(rot_point, angle)
        self.contour_with_clearance = shapely.affinity.rotate(
            self.contour_with_clearance, angle=angle, origin=rot_point)
        self.contour_with_roads_width = shapely.affinity.rotate(
            self.contour_with_roads_width, angle=angle, origin=rot_point)


class SpecialRoadZone(Zone):
    def __init__(self, line: list[tuple[float, float]], width: float):
        """
        Initializes a SpecialRoadZone with a given line and width.

        Args:
            line (list[tuple[float, float]]): A list of tuples representing
                the vertices of the road's line.
            width (float): The width of the road zone.
        """
        self.line = line
        self.width = width

        if self.width <= 0:
            raise ValueError("Width must be greater than zero")
        if len(line) < 2:
            raise ValueError("Line must have at least two points")
        if len(line) > 2:
            raise ValueError("Line must have exactly two points "
                             "for a road zone")
        super().__init__(self.__build_contour())

    def __build_contour(self) -> list[tuple[float, float]]:
        """
        Builds the contour of the road zone based on the line and width.

        Returns:
            list[tuple[float, float]]: A list of tuples representing the
                vertices of the road zone's contour.
        """
        min_x_idx = 0
        if self.line[0][0] > self.line[1][0]:
            min_x_idx = 1
        min_y_idx = 0
        if self.line[0][1] > self.line[1][1]:
            min_y_idx = 1

        orientation = (0 if abs(self.line[0][0] - self.line[1][0])
                       > abs(self.line[0][1] - self.line[1][1]) else 1)

        if orientation == 0:
            x_0, y_0 = self.line[min_x_idx]
            x_1, y_1 = self.line[abs(min_x_idx - 1)]
            if min_x_idx == min_y_idx:
                y_0 = y_0 - self.width / 2
                y_1 = y_1 + self.width / 2
            else:
                y_0 = y_0 + self.width / 2
                y_1 = y_1 - self.width / 2
        else:
            x_0, y_0 = self.line[min_y_idx]
            x_1, y_1 = self.line[abs(min_y_idx - 1)]
            if min_x_idx == min_y_idx:
                x_0 = x_0 - self.width / 2
                x_1 = x_1 + self.width / 2
            else:
                x_0 = x_0 + self.width / 2
                x_1 = x_1 - self.width / 2

        polygon = [(x_0, y_0), (x_1, y_0), (x_1, y_1), (x_0, y_1)]

        return polygon

    def is_horizontal(self) -> int:
        """
        Returns the orientation of the road zone.

        Returns:
            int: True if the road is horizontal, False if vertical.
        """
        bounds = self.contour.bounds
        orientation = (True if abs(bounds[0] - bounds[2])
                       > abs(bounds[1] - bounds[3]) else False)
        return orientation


class AvailableZone(Zone):
    def __init__(self, contour: list[tuple[float, float]], height: float,
                 orientation: int = 0):
        """
        Initializes an AvailableZone with a given contour and height.

        Args:
            contour (list[tuple[float, float]]): A list of tuples representing
                the vertices of the zone's contour.
            height (float): The height of the available zone
            orientation (int): Preferable rack placement orientation in
                the available zone 0 any, 1 horizontal, 2 vertical.
        """

        super().__init__(contour)
        self.height = height
        self.orientation = orientation
        if self.height <= 0:
            raise ValueError("Height must be greater than zero")

    def get_intersecting_occupied_zones(self,
                                        occupied_zones: list[OccupiedZone]
                                        ) -> list[OccupiedZone]:
        intersecting_occupied_zones = []
        for zone in occupied_zones:
            if (shapely.intersects(self.contour, zone.contour_with_clearance)
                    or shapely.intersects(self.contour,
                                          zone.contour_with_roads_width)):
                intersecting_occupied_zones.append(deepcopy(zone))
        return intersecting_occupied_zones

    def get_intersecting_road_zones(self,
                                    special_road_zones: list[SpecialRoadZone]
                                    ) -> list[SpecialRoadZone]:
        intersecting_special_road_zones = []
        for zone in special_road_zones:
            if zone.intersects(self.contour):
                intersecting_special_road_zones.append(deepcopy(zone))
        return intersecting_special_road_zones

    def contains_point(self, point: tuple[float, float]) -> bool:
        """Check if the point is inside the zone.

        Args:
            point (Tuple[float, float]): The point to check

        Returns:
            bool: True if the point is inside the zone, False otherwise
        """
        return shapely.contains(self.contour, shapely.geometry.Point(point))

    def split_zone(self, point: tuple[float, float]) -> tuple['AvailableZone',
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
        x0, y0, x1, y1 = self.bounds

        if not self.contains_point(point):
            raise ValueError("Point is not inside the zone")

        zone_1_l, zone_2_l, max_area_l = self.__get_split_zones(
            (x0, y0), (x1, y1), point, True)
        zone_1_r, zone_2_r, max_area_r = self.__get_split_zones(
            (x0, y0), (x1, y1), point, False)

        if max_area_l > max_area_r:
            return zone_1_l, zone_2_l
        else:
            return zone_1_r, zone_2_r

    def __get_split_zones(self, p0: tuple[float, float],
                          p1: tuple[float, float],
                          ps: tuple[float, float], is_left_smallest: bool
                          ) -> tuple['AvailableZone', 'AvailableZone', float]:
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
            max_available_area = max(zone_1.area,
                                     zone_2.area)
        else:
            zone_1 = AvailableZone([(x0, ys), (x1, ys), (x1, y1), (x0, y1)],
                                   self.height)
            zone_2 = AvailableZone([(xs, y0), (x1, y0), (x1, ys), (xs, ys)],
                                   self.height)
            max_available_area = max(zone_1.area,
                                     zone_2.area)

        return zone_1, zone_2, max_available_area
