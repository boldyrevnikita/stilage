import warnings
from typing import List

from src.rack_group import RackGroup
from src.rack import RackSection
from src.available_zone import AvailableZone


class Packer:
    def __init__(self, zones: List[AvailableZone],
                 rack_sections: List[RackSection]):
        self.zones = zones.copy()
        self.rack_sections = rack_sections.copy()
        self.rack_groups = []

    def pack(self) -> List[RackGroup]:
        """Pack racks into available zones.
        """
        # Sort zones by available_area and height (highest first)
        self.zones.sort(key=lambda zone: zone.available_area_size,
                        reverse=True)
        self.zones.sort(key=lambda zone: zone.height,
                        reverse=True)
        # Sort rack_sections by height and area (highest first)
        self.rack_sections.sort(
            key=lambda rack_section: rack_section.width * rack_section.length,
            reverse=True)
        self.rack_sections.sort(key=lambda rack_section: rack_section.height_0,
                                reverse=True)
        while len(self.rack_sections) > 0:
            is_successful_rack_placement = False

            for zone in self.zones:
                if zone.height < self.rack_sections[0].height_0:
                    continue
                height_diff = (zone.height - self.rack_sections[0].height_0
                               - self.rack_sections[0].height_delta)
                sections_in_height = (
                    height_diff // self.rack_sections[0].height_i + 1)

                bounds = zone.bounds
                zone_x0, zone_y0 = bounds[:2]

                group_length = 1
                group_width = 1
                rack_group = RackGroup(self.rack_sections[0], group_length,
                                       group_width, sections_in_height, False)
                rack_group.translate(zone_x0, zone_y0)

                while (zone.geometry.covers(rack_group.restrictive_bounds)
                       and self.rack_sections[0].quantity_left -
                       group_length * group_width >= 0):
                    group_length += 1
                    rack_group = RackGroup(self.rack_sections[0], group_length,
                                           group_width, sections_in_height,
                                           False)
                    rack_group.translate(zone_x0, zone_y0)
                group_length -= 1

                if group_length == 0:
                    continue

                rack_group = RackGroup(self.rack_sections[0], group_length,
                                       group_width, sections_in_height, False)
                rack_group.translate(zone_x0, zone_y0)

                while (zone.geometry.covers(rack_group.restrictive_bounds)
                       and self.rack_sections[0].quantity_left -
                       group_length * group_width >= 0):
                    group_width += 1
                    rack_group = RackGroup(self.rack_sections[0], group_length,
                                           group_width, sections_in_height,
                                           False)
                    rack_group.translate(zone_x0, zone_y0)
                group_width -= 1

                if group_width == 0:
                    continue

                rack_group = RackGroup(self.rack_sections[0], group_length,
                                       group_width, sections_in_height)
                rack_group.translate(zone_x0, zone_y0)

                self.rack_groups.append(rack_group)
                self.rack_sections[0].quantity_left -= (group_length
                                                        * group_width)
                split_point = rack_group.restrictive_bounds.bounds[2:]
                zone_1, zone_2 = zone.split_zone(split_point)
                self.zones.remove(zone)
                self.zones.append(zone_1)
                self.zones.append(zone_2)

                if self.rack_sections[0].quantity_left == 0:
                    self.rack_sections.pop(0)

                self.zones.sort(key=lambda zone: zone.available_area_size,
                                reverse=True)
                self.zones.sort(key=lambda zone: zone.height,
                                reverse=True)

                is_successful_rack_placement = True
                break

            if not is_successful_rack_placement:
                warnings.warn(
                    "No space left for "
                    f"{int(self.rack_sections[0].quantity_left)} "
                    f"rack sections with id {self.rack_sections[0].id}")
                self.rack_sections.pop(0)

        return self.rack_groups.copy()
