import shapely

from src.rack import RackSection, Rack


class RackGroup:
    def __init__(self, rack_section_info: RackSection, group_length: int,
                 group_width: int, sections_in_height: int,
                 last_shelf_unit_length: int, max_unit_shelf_quantity,
                 init_racks=True):
        self.rack_section_info = rack_section_info
        self.group_length = group_length
        self.group_width = group_width
        self.sections_in_height = sections_in_height
        self.max_unit_shelf_quantity = max_unit_shelf_quantity
        self.last_shelf_unit_length = last_shelf_unit_length
        self.racks = []
        self.physical_bounds = None
        self.restrictive_bounds = None

        self.available_lengths = [1850.0, 2700, 3600.0]

        self.__init_bounds()
        if init_racks:
            self.__init_racks()

    def __init_bounds(self) -> None:
        """Initialize physical and restrictive bounds for rack group.
        """
        x_0, y_0 = 0.0, 0.0
        x_1 = (x_0 + self.available_lengths[
            self.max_unit_shelf_quantity-2]
               * (self.group_length - 1)
               + self.available_lengths[self.last_shelf_unit_length-2]
               + self.rack_section_info.pillar_width
               * (self.group_length + 1)
               + 2 * self.rack_section_info.side_distance)

        y_1 = (y_0 + self.rack_section_info.width * self.group_width
               + self.rack_section_info.back_connection_distance
               * ((self.group_width - 1) // 2)
               + self.rack_section_info.front_distance
               * (self.group_width // 2))
        if self.group_width % 2 == 0:
            y_1 += self.rack_section_info.back_distance * 2
        else:
            y_1 += (self.rack_section_info.back_distance
                    + self.rack_section_info.front_distance)

        self.restrictive_bounds = shapely.geometry.Polygon(
            [(x_0, y_0), (x_1, y_0), (x_1, y_1), (x_0, y_1)])

        x_0_p = x_0 + self.rack_section_info.side_distance
        y_0_p = y_0 + self.rack_section_info.back_distance
        x_1_p = x_1 - self.rack_section_info.side_distance

        if self.group_width % 2 == 0:
            y_1_p = y_1 - self.rack_section_info.back_distance
        else:
            y_1_p = y_1 - self.rack_section_info.front_distance

        self.physical_bounds = shapely.geometry.Polygon(
            [(x_0_p, y_0_p), (x_1_p, y_0_p), (x_1_p, y_1_p), (x_0_p, y_1_p)])

    def __init_racks(self) -> None:
        """Initialize racks in the group.
        """
        self.racks = []

        shelfs_length_unit_quantity = (
            [self.max_unit_shelf_quantity]
            * (self.group_length - 1)
            + [self.last_shelf_unit_length]
        )

        x = self.rack_section_info.side_distance
        y = self.rack_section_info.back_distance
        self.racks.append(Rack(
            x, y, self.rack_section_info,
            self.group_length, 1,
            self.sections_in_height, shelfs_length_unit_quantity
        ))

        for _ in range((self.group_width - 1) // 2):
            y += (self.rack_section_info.width
                  + self.rack_section_info.front_distance)

            self.racks.append(Rack(
                x, y, self.rack_section_info,
                self.group_length, 2,
                self.sections_in_height, shelfs_length_unit_quantity
            ))

            y += (self.rack_section_info.width
                  + self.rack_section_info.back_connection_distance)

        if self.group_width % 2 == 0:
            y += (self.rack_section_info.width
                  + self.rack_section_info.front_distance)
            self.racks.append(Rack(
                x, y, self.rack_section_info,
                self.group_length, 1,
                self.sections_in_height, shelfs_length_unit_quantity
            ))

    def translate(self, x_diff: float, y_diff: float) -> None:
        """Shift rack group by specified offset values.

        Args:
            x_diff (float): x-axis offset value
            y_diff (float): y-axis offset value
        """

        for rack in self.racks:
            rack.translate(x_diff, y_diff)
        self.physical_bounds = shapely.affinity.translate(
            self.physical_bounds, x_diff, y_diff)
        self.restrictive_bounds = shapely.affinity.translate(
            self.restrictive_bounds, x_diff, y_diff)

    def rotate90(self) -> None:
        """Rotate rack group counterclockwise by 90 degrees around
        (x_min, y_min) bounding box point, then shift it to the right
        to preserve (x_min, y_min) bounding box point position.
        """
        bounds = self.restrictive_bounds.bounds
        rot_point = (bounds[0], bounds[1])
        x_shift = bounds[3] - bounds[1]

        for rack in self.racks:
            rack.rotate(90, origin=rot_point)
        self.physical_bounds = shapely.affinity.rotate(
            self.physical_bounds, 90, origin=rot_point)
        self.restrictive_bounds = shapely.affinity.rotate(
            self.restrictive_bounds, 90, origin=rot_point)

        self.translate(x_shift, 0)
