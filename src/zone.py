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

    def intersects(self, geometry: Polygon) -> bool:
        """
        Checks if the zone intersects with a given geometry.

        Args:
            geometry (Polygon): The geometry to check for intersection.

        Returns:
            bool: True if the zone intersects with the geometry,
                False otherwise.
        """
        return self.contour.intersects(geometry)

    def contains(self, geometry: Polygon) -> bool:
        """
        Checks if the zone contains a given geometry.

        Args:
            geometry (Polygon): The geometry to check for containment.

        Returns:
            bool: True if the zone contains the geometry,
                False otherwise.
        """
        return self.contour.contains(geometry)

    def bounds(self) -> tuple[float, float, float, float]:
        """
        Returns the bounding box of the zone's contour.

        Returns:
            tuple[float, float, float, float]: The bounding box of the zone
                in the format (min_x, min_y, max_x, max_y).
        """
        return self.contour.bounds


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

    def intersects_with_clearance(self, geometry: Polygon) -> bool:
        """
        Checks if the occupied zone intersects with a given geometry
            considering the clearance.

        Args:
            geometry (Polygon): The geometry to check for intersection.

        Returns:
            bool: True if the occupied zone intersects with the geometry
                considering the clearance, False otherwise.
        """
        return self.contour_with_clearance.intersects(geometry)

    def intersects_with_roads_width(self, geometry: Polygon) -> bool:
        """
        Checks if the occupied zone intersects with a given geometry
            considering the roads width.

        Args:
            geometry (Polygon): The geometry to check for intersection.

        Returns:
            bool: True if the occupied zone intersects with the geometry
                considering the roads width, False otherwise.
        """
        return self.contour_with_roads_width.intersects(geometry)


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
        pass


class AvailableZone(Zone):
    def __init__(self, contour: list[tuple[float, float]], height: float):
        """
        Initializes an AvailableZone with a given contour and height.

        Args:
            contour (list[tuple[float, float]]): A list of tuples representing
                the vertices of the zone's contour.
            height (float): The height of the available zone.
        """

        super().__init__(contour)
        self.height = height
        if self.height <= 0:
            raise ValueError("Height must be greater than zero")

        self.occupied_zones: list[OccupiedZone] = []
        self.special_road_zones: list[SpecialRoadZone] = []

    def add_occupied_zones(self, occupied_zones: list[OccupiedZone]) -> None:
        for zone in occupied_zones:
            if (zone.intersects_with_clearance(self.contour)
                    or zone.intersects_with_roads_width(self.contour)):
                self.occupied_zones.append(deepcopy(zone))

    def add_special_road_zones(self,
                               special_road_zones: list[SpecialRoadZone]
                               ) -> None:
        for zone in special_road_zones:
            if zone.intersects(self.contour):
                self.special_road_zones.append(deepcopy(zone))

    def rotate_az_90_clockwise(self) -> None:
        """
        Rotates the available zone's contour 90 degrees clockwise.
        """
        bounds = self.contour.bounds
        rot_point = bounds[0], bounds[1]
        y_shift = bounds[2] - bounds[0]

        self.rotate(angle=90, rot_point=rot_point)
        self.translate(0, y_shift)

    def rotate_az_90_counterclockwise(self) -> None:
        """
        Rotates the available zone's contour 90 degrees counterclockwise.
        """
        bounds = self.contour.bounds
        rot_point = bounds[0], bounds[1]
        x_shift = bounds[3] - bounds[1]

        self.rotate(angle=-90, rot_point=rot_point)
        self.translate(x_shift, 0)

    def rotate(self, angle, rot_point) -> None:
        for zone in self.occupied_zones:
            zone.contour = shapely.affinity.rotate(
                zone.contour, angle=angle, origin=rot_point)
            zone.contour_with_clearance = shapely.affinity.rotate(
                zone.contour_with_clearance, angle=angle, origin=rot_point)
            zone.contour_with_roads_width = shapely.affinity.rotate(
                zone.contour_with_roads_width, angle=angle, origin=rot_point)

        for zone in self.special_road_zones:
            zone.contour = shapely.affinity.rotate(
                zone.contour, angle=angle, origin=rot_point)

        self.contour = shapely.affinity.rotate(
            self.contour, angle=angle, origin=rot_point)

    def translate(self, dx: float, dy: float) -> None:
        """
        Translates the available zone's contour by dx and dy.

        Args:
            dx (float): The translation distance in the x direction.
            dy (float): The translation distance in the y direction.
        """

        self.contour = shapely.affinity.translate(self.contour, dx, dy)
        for zone in self.occupied_zones:
            zone.contour = shapely.affinity.translate(zone.contour, dx, dy)
            zone.contour_with_clearance = shapely.affinity.translate(
                zone.contour_with_clearance, dx, dy)
            zone.contour_with_roads_width = shapely.affinity.translate(
                zone.contour_with_roads_width, dx, dy)

        for zone in self.special_road_zones:
            zone.contour = shapely.affinity.translate(zone.contour, dx, dy)
