"""
Zone module for representing different types of zones in the warehouse.

This module contains classes for:
- Zone: Base class for all zone types
- OccupiedZone: Zones that are occupied by obstacles (columns, equipment, etc.)
- SpecialRoadZone: Zones reserved for special roads/passages
- AvailableZone: Zones available for rack placement
"""

from shapely import Polygon
from copy import deepcopy
import shapely


class Zone:
    """Base class for all zone types in the warehouse."""
    
    def __init__(self, contour: list[tuple[float, float]]):
        """Initializes a Zone with a given contour.

        Args:
            contour (list[tuple[float, float]]): A list of tuples representing
                the vertices of the zone's contour.
        
        Raises:
            ValueError: If the contour is invalid.
        """
        self.contour: Polygon = Polygon(contour)
        if not self.contour.is_valid:
            raise ValueError("Invalid contour for the zone")

    @property
    def area(self) -> float:
        """Returns the area of the zone's contour.

        Returns:
            float: The area of the zone in square millimeters.
        """
        return self.contour.area

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Returns the bounding box of the zone's contour.

        Returns:
            tuple[float, float, float, float]: The bounding box of the zone
                in the format (min_x, min_y, max_x, max_y).
        """
        return self.contour.bounds

    def rotate(self, rot_point: tuple[float, float], angle: float) -> None:
        """Rotates the zone around a given point.
        
        Args:
            rot_point (tuple[float, float]): The point around which to rotate.
            angle (float): The angle (in degrees) to rotate the zone.
        """
        self.contour = shapely.affinity.rotate(
            self.contour, angle=angle, origin=rot_point)
    
    def translate(self, xoff: float, yoff: float) -> None:
        """Translates the zone by given offsets.
        
        Args:
            xoff (float): X-axis offset in millimeters.
            yoff (float): Y-axis offset in millimeters.
        """
        self.contour = shapely.affinity.translate(self.contour, xoff, yoff)
    
    def intersects(self, other) -> bool:
        """Checks if this zone intersects with another geometry.
        
        Args:
            other: A Shapely geometry object or Zone.
        
        Returns:
            bool: True if zones intersect, False otherwise.
        """
        if isinstance(other, Zone):
            return shapely.intersects(self.contour, other.contour)
        else:
            return shapely.intersects(self.contour, other)
    
    def contains(self, other) -> bool:
        """Checks if this zone contains another geometry.
        
        Args:
            other: A Shapely geometry object or Zone.
        
        Returns:
            bool: True if this zone contains the other, False otherwise.
        """
        if isinstance(other, Zone):
            return shapely.contains(self.contour, other.contour)
        else:
            return shapely.contains(self.contour, other)
    
    def __repr__(self) -> str:
        """Returns a string representation of the Zone.
        
        Returns:
            str: String representation with bounds and area.
        """
        return f"{self.__class__.__name__}(bounds={self.bounds}, area={self.area:.1f})"


class OccupiedZone(Zone):
    """Represents a zone that is occupied by an obstacle.
    
    Occupied zones can be:
    - Columns (compact obstacles that can be protected by double racks)
    - Walls, equipment, or other large obstacles
    - Temporary obstacles that should remain accessible
    """
    
    def __init__(self, contour: list[tuple[float, float]], clearance: float,
                 roads_width: float, should_be_available: bool = False,
                 is_column: bool = False):
        """Initializes an OccupiedZone with a given contour, clearance,
        and availability status.

        Args:
            contour (list[tuple[float, float]]): A list of tuples representing
                the vertices of the zone's contour.
            clearance (float): The clearance distance from the occupied zone
                (safety buffer around the obstacle).
            roads_width (float): The width of the roads around the occupied
                zone (space needed for forklift passage).
            should_be_available (bool, optional): Indicates if the zone should
                be available for passage. Defaults to False.
            is_column (bool, optional): Whether this zone is identified as a column.
                Columns are typically protected by double racks. Defaults to False.
        
        Raises:
            ValueError: If clearance is negative or should_be_available is not boolean.
        """
        super().__init__(contour)
        
        self.clearance = clearance
        self.roads_width = roads_width
        
        if self.clearance < 0:
            raise ValueError("Clearance must be non-negative")
        
        self.should_be_available = should_be_available
        if not isinstance(self.should_be_available, bool):
            raise ValueError("should_be_available must be a boolean")
        
        # NEW: Mark if this is a column
        self.is_column = is_column

        # Create buffered contours for clearance and road width
        self.contour_with_clearance: Polygon = self.contour.buffer(
            self.clearance, join_style=2)
        self.contour_with_roads_width: Polygon = self.contour.buffer(
            self.roads_width, join_style=2)

    def rotate(self, rot_point: tuple[float, float], angle: float) -> None:
        """Rotates the occupied zone and its buffers.

        Args:
            rot_point (tuple[float, float]): The point around which to rotate.
            angle (float): The angle (in degrees) to rotate the zone.
        """
        super().rotate(rot_point, angle)
        self.contour_with_clearance = shapely.affinity.rotate(
            self.contour_with_clearance, angle=angle, origin=rot_point)
        self.contour_with_roads_width = shapely.affinity.rotate(
            self.contour_with_roads_width, angle=angle, origin=rot_point)
    
    def translate(self, xoff: float, yoff: float) -> None:
        """Translates the occupied zone and its buffers.
        
        Args:
            xoff (float): X-axis offset in millimeters.
            yoff (float): Y-axis offset in millimeters.
        """
        super().translate(xoff, yoff)
        self.contour_with_clearance = shapely.affinity.translate(
            self.contour_with_clearance, xoff, yoff)
        self.contour_with_roads_width = shapely.affinity.translate(
            self.contour_with_roads_width, xoff, yoff)
    
    def is_compact(self, max_aspect_ratio: float = 3.0) -> bool:
        """Checks if the occupied zone is compact (close to square shape).
        
        Compact zones are typically columns or pillars. Non-compact zones
        are usually walls, barriers, or elongated obstacles.
        
        Args:
            max_aspect_ratio (float): Maximum allowed aspect ratio 
                (max_dimension / min_dimension) for a zone to be considered compact.
                Default is 3.0.
        
        Returns:
            bool: True if the zone is compact, False otherwise.
        """
        bounds = self.contour.bounds
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        
        if min(width, height) == 0:
            return False
        
        aspect_ratio = max(width, height) / min(width, height)
        return aspect_ratio <= max_aspect_ratio
    
    def get_dimensions(self) -> tuple[float, float]:
        """Returns the width and height of the occupied zone.
        
        Returns:
            tuple[float, float]: (width, height) in millimeters.
        """
        bounds = self.contour.bounds
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        return width, height
    
    def get_max_dimension(self) -> float:
        """Returns the maximum dimension (width or height) of the zone.
        
        Returns:
            float: Maximum dimension in millimeters.
        """
        width, height = self.get_dimensions()
        return max(width, height)
    
    def get_aspect_ratio(self) -> float:
        """Returns the aspect ratio (max_dimension / min_dimension) of the zone.
        
        Returns:
            float: Aspect ratio. Returns infinity if one dimension is zero.
        """
        width, height = self.get_dimensions()
        if min(width, height) == 0:
            return float('inf')
        return max(width, height) / min(width, height)
    
    def __repr__(self) -> str:
        """Returns a string representation of the OccupiedZone.
        
        Returns:
            str: String representation with key properties.
        """
        width, height = self.get_dimensions()
        return (f"OccupiedZone(bounds={self.bounds}, area={self.area:.1f}, "
                f"w={width:.1f}, h={height:.1f}, clearance={self.clearance:.1f}, "
                f"is_column={self.is_column})")


class SpecialRoadZone(Zone):
    """Represents a special road zone that must remain clear for traffic.
    
    Special road zones are typically main passages or fire lanes that
    cannot be obstructed by racks. Racks may cross these zones using bridges.
    """
    
    def __init__(self, line: list[tuple[float, float]], width: float):
        """Initializes a SpecialRoadZone with a given line and width.

        Args:
            line (list[tuple[float, float]]): A list of tuples representing
                the vertices of the road's centerline (must be exactly 2 points).
            width (float): The width of the road zone in millimeters.
        
        Raises:
            ValueError: If width is non-positive or line doesn't have exactly 2 points.
        """
        if width <= 0:
            raise ValueError("Width must be greater than zero")
        if len(line) < 2:
            raise ValueError("Line must have at least two points")
        if len(line) > 2:
            raise ValueError("Line must have exactly two points for a road zone")
        
        self.line = line
        self.width = width
        
        super().__init__(self.__build_contour())

    def __build_contour(self) -> list[tuple[float, float]]:
        """Builds the contour of the road zone based on the line and width.
        
        The road zone is represented as a rectangle centered on the line,
        with the specified width perpendicular to the line direction.

        Returns:
            list[tuple[float, float]]: A list of tuples representing the
                vertices of the road zone's contour (rectangle).
        """
        min_x_idx = 0
        if self.line[0][0] > self.line[1][0]:
            min_x_idx = 1
        min_y_idx = 0
        if self.line[0][1] > self.line[1][1]:
            min_y_idx = 1

        # Determine orientation: 0 = horizontal, 1 = vertical
        orientation = (0 if abs(self.line[0][0] - self.line[1][0])
                       > abs(self.line[0][1] - self.line[1][1]) else 1)

        if orientation == 0:
            # Horizontal road
            x_0, y_0 = self.line[min_x_idx]
            x_1, y_1 = self.line[abs(min_x_idx - 1)]
            if min_x_idx == min_y_idx:
                y_0 = y_0 - self.width / 2
                y_1 = y_1 + self.width / 2
            else:
                y_0 = y_0 + self.width / 2
                y_1 = y_1 - self.width / 2
        else:
            # Vertical road
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

    def is_horizontal(self) -> bool:
        """Returns the orientation of the road zone.

        Returns:
            bool: True if the road is horizontal (width > height), 
                  False if vertical (height > width).
        """
        bounds = self.contour.bounds
        orientation = (True if abs(bounds[0] - bounds[2])
                       > abs(bounds[1] - bounds[3]) else False)
        return orientation
    
    def get_orientation(self) -> str:
        """Returns the orientation of the road as a string.
        
        Returns:
            str: "horizontal" or "vertical"
        """
        return "horizontal" if self.is_horizontal() else "vertical"
    
    def __repr__(self) -> str:
        """Returns a string representation of the SpecialRoadZone.
        
        Returns:
            str: String representation with key properties.
        """
        return (f"SpecialRoadZone(bounds={self.bounds}, width={self.width:.1f}, "
                f"orientation={self.get_orientation()})")


class AvailableZone(Zone):
    """Represents a zone available for rack placement.
    
    Available zones define areas where racks can be placed. They have:
    - A maximum height constraint (ceiling height)
    - Optional orientation preference for rack placement
    """
    
    def __init__(self, contour: list[tuple[float, float]], height: float,
                 orientation: int = 0):
        """Initializes an AvailableZone with a given contour and height.

        Args:
            contour (list[tuple[float, float]]): A list of tuples representing
                the vertices of the zone's contour.
            height (float): The height (ceiling clearance) of the available zone
                in millimeters.
            orientation (int): Preferable rack placement orientation in
                the available zone:
                - 0: any orientation allowed (default)
                - 1: only horizontal racks allowed
                - 2: only vertical racks allowed
        
        Raises:
            ValueError: If height is non-positive.
        """
        super().__init__(contour)
        
        self.height = height
        self.orientation = orientation
        
        if self.height <= 0:
            raise ValueError("Height must be greater than zero")

    def get_intersecting_occupied_zones(self,
                                        occupied_zones: list[OccupiedZone]
                                        ) -> list[OccupiedZone]:
        """Gets the occupied zones that intersect with the current available zone.

        Args:
            occupied_zones (list[OccupiedZone]): A list of occupied zones to
                check for intersection.
        
        Returns:
            list[OccupiedZone]: A list of occupied zones that intersect with
                the current available zone.
        """
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
        """Gets the special road zones that intersect with the current available zone.
        
        Args:
            special_road_zones (list[SpecialRoadZone]): A list of special road zones
                to check for intersection.
        
        Returns:
            list[SpecialRoadZone]: A list of special road zones that intersect
                with the current available zone.
        """
        intersecting_special_road_zones = []
        for zone in special_road_zones:
            if zone.intersects(self.contour):
                intersecting_special_road_zones.append(deepcopy(zone))
        return intersecting_special_road_zones

    def contains_point(self, point: tuple[float, float]) -> bool:
        """Checks if a point is inside the zone.

        Args:
            point (tuple[float, float]): The point to check (x, y coordinates).

        Returns:
            bool: True if the point is inside the zone, False otherwise.
        """
        return shapely.contains(self.contour, shapely.geometry.Point(point))

    def split_zone(self, point: tuple[float, float]) -> tuple['AvailableZone',
                                                              'AvailableZone']:
        """Splits the zone at a given point into two zones.
        
        The point must be inside the zone. The split creates two rectangular zones,
        maximizing the area of the larger zone.

        Args:
            point (tuple[float, float]): The point to split the zone at.

        Raises:
            ValueError: If the point is not inside the zone.

        Returns:
            tuple[AvailableZone, AvailableZone]: The two zones after the split.
        """
        x0, y0, x1, y1 = self.bounds

        if not self.contains_point(point):
            raise ValueError("Point is not inside the zone")

        # Try both split orientations and choose the one with larger max area
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
        """Gets the two zones after splitting the current zone with a point.

        Args:
            p0 (tuple[float, float]): The bottom-left point of the zone.
            p1 (tuple[float, float]): The top-right point of the zone.
            ps (tuple[float, float]): The point to split the zone at.
            is_left_smallest (bool): True if the left zone should be the smallest.

        Returns:
            tuple[AvailableZone, AvailableZone, float]: The two zones and the
            maximum available area among them.
        """
        x0, y0 = p0
        x1, y1 = p1
        xs, ys = ps

        if is_left_smallest:
            zone_1 = AvailableZone([(x0, ys), (xs, ys), (xs, y1), (x0, y1)],
                                   self.height, self.orientation)
            zone_2 = AvailableZone([(xs, y0), (x1, y0), (x1, y1), (xs, y1)],
                                   self.height, self.orientation)
            max_available_area = max(zone_1.area, zone_2.area)
        else:
            zone_1 = AvailableZone([(x0, ys), (x1, ys), (x1, y1), (x0, y1)],
                                   self.height, self.orientation)
            zone_2 = AvailableZone([(xs, y0), (x1, y0), (x1, ys), (xs, ys)],
                                   self.height, self.orientation)
            max_available_area = max(zone_1.area, zone_2.area)

        return zone_1, zone_2, max_available_area
    
    def get_orientation_name(self) -> str:
        """Returns the orientation preference as a string.
        
        Returns:
            str: "any", "horizontal", or "vertical"
        """
        if self.orientation == 0:
            return "any"
        elif self.orientation == 1:
            return "horizontal"
        elif self.orientation == 2:
            return "vertical"
        else:
            return "unknown"
    
    def __repr__(self) -> str:
        """Returns a string representation of the AvailableZone.
        
        Returns:
            str: String representation with key properties.
        """
        return (f"AvailableZone(bounds={self.bounds}, area={self.area:.1f}, "
                f"height={self.height:.1f}, orientation={self.get_orientation_name()})")