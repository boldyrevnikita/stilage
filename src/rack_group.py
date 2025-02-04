import shapely

from src.rack_info import RackInfo


class RackGroup:
    def __init__(self, rack_info: RackInfo, group_length: int,
                 group_width: int, init_racks=True):
        self.rack_info = rack_info
        self.group_length = group_length
        self.group_width = group_width
        self.racks = []
        self.physical_bounds = None
        self.restrictive_bounds = None

        self.__init_bounds()
        if init_racks:
            self.__init_racks()

    def __init_bounds(self) -> None:
        x_0, y_0 = 0.0, 0.0
        x_1 = (x_0 + self.rack_info.length * self.group_length
               + self.rack_info.side_connection_distance
               * (self.group_length - 1)
               + 2 * self.rack_info.side_distance)

        y_1 = (y_0 + self.rack_info.width * self.group_width
               + self.rack_info.back_connection_distance
               * ((self.group_width - 1) // 2)
               + self.rack_info.front_distance * (self.group_width // 2))
        if self.group_width % 2 == 0:
            y_1 += self.rack_info.back_distance * 2
        else:
            y_1 += self.rack_info.back_distance + self.rack_info.front_distance

        self.restrictive_bounds = shapely.geometry.Polygon(
            [(x_0, y_0), (x_1, y_0), (x_1, y_1), (x_0, y_1)])

        x_0_p = x_0 + self.rack_info.side_distance
        y_0_p = y_0 + self.rack_info.back_distance
        x_1_p = x_1 - self.rack_info.side_distance

        if self.group_width % 2 == 0:
            y_1_p = y_1 - self.rack_info.back_distance
        else:
            y_1_p = y_1 - self.rack_info.front_distance

        self.physical_bounds = shapely.geometry.Polygon(
            [(x_0_p, y_0_p), (x_1_p, y_0_p), (x_1_p, y_1_p), (x_0_p, y_1_p)])

    def __init_racks(self) -> None:
        self.racks = []

        x = self.rack_info.side_distance
        y = self.rack_info.back_distance
        self.__init_rack_row(x, y)

        for _ in range((self.group_width - 1) // 2):
            y += self.rack_info.width + self.rack_info.front_distance
            self.__init_rack_row(x, y)
            y += self.rack_info.width + self.rack_info.back_connection_distance
            self.__init_rack_row(x, y)

        if self.group_width % 2 == 0:
            y += self.rack_info.width + self.rack_info.front_distance
            self.__init_rack_row(x, y)

    def __init_rack_row(self, x: float, y: float) -> None:
        for _ in range(self.group_length):
            rack = shapely.geometry.Polygon([(x, y),
                                             (x + self.rack_info.length, y),
                                             (x + self.rack_info.length,
                                              y + self.rack_info.width),
                                             (x, y + self.rack_info.width)])
            self.racks.append(rack)
            x += self.rack_info.length \
                + self.rack_info.side_connection_distance

    def translate(self, x_diff: float, y_diff: float) -> None:
        """Shift geometry by specified offset values.

        Args:
            x_diff (float): x-axis offset value
            y_diff (float): y-axis offset value
        """

        for i, rack in enumerate(self.racks):
            self.racks[i] = shapely.affinity.translate(rack, x_diff, y_diff)
        self.physical_bounds = shapely.affinity.translate(
            self.physical_bounds, x_diff, y_diff)
        self.restrictive_bounds = shapely.affinity.translate(
            self.restrictive_bounds, x_diff, y_diff)

    def rotate90(self) -> None:
        """Rotate geometry counterclockwise by 90 degrees around
        (x_min, y_min) bounding box point, then shift it to the right
        to preserve (x_min, y_min) point position.
        """
        bounds = self.restrictive_bounds.bounds
        rot_point = (bounds[0], bounds[1])
        x_shift = bounds[3] - bounds[1]

        for i, rack in enumerate(self.racks):
            self.racks[i] = shapely.affinity.rotate(rack, 90, origin=rot_point)
        self.physical_bounds = shapely.affinity.rotate(
            self.physical_bounds, 90, origin=rot_point)
        self.restrictive_bounds = shapely.affinity.rotate(
            self.restrictive_bounds, 90, origin=rot_point)

        self.translate(x_shift, 0)
