import warnings
from typing import List

from src.rack_group import RackGroup
from src.rack_info import RackInfo
from src.zone import Zone


class Packer:
    def __init__(self, zones: List[Zone], rack_infos: List[RackInfo]):
        self.zones = zones.copy()
        self.rack_infos = rack_infos.copy()
        self.rack_groups = []

    def pack(self) -> None:
        # Sort zones by available_area and height (highest first)
        self.zones.sort(key=lambda zone: zone.available_area_size,
                        reverse=True)
        self.zones.sort(key=lambda zone: zone.height,
                        reverse=True)
        # Sort rack_infos by height and area (highest first)
        self.rack_infos.sort(
            key=lambda rack_info: rack_info.width * rack_info.length,
            reverse=True)
        self.rack_infos.sort(key=lambda rack_info: rack_info.height,
                             reverse=True)
        while len(self.rack_infos) > 0:
            is_successful_rack_placement = False

            for zone in self.zones:
                if zone.height < self.rack_infos[0].height:
                    continue

                bounds = zone.bounds
                zone_x0, zone_y0 = bounds[:2]

                group_length = 1
                group_width = 1
                rack_group = RackGroup(self.rack_infos[0], group_length,
                                       group_width, False)
                rack_group.translate(zone_x0, zone_y0)

                while (zone.geometry.covers(rack_group.restrictive_bounds)
                       and self.rack_infos[0].quantity_left -
                       group_length * group_width >= 0):
                    group_length += 1
                    rack_group = RackGroup(self.rack_infos[0], group_length,
                                           group_width, False)
                    rack_group.translate(zone_x0, zone_y0)
                group_length -= 1

                if group_length == 0:
                    continue

                rack_group = RackGroup(self.rack_infos[0], group_length,
                                       group_width, False)
                rack_group.translate(zone_x0, zone_y0)

                while (zone.geometry.covers(rack_group.restrictive_bounds)
                       and self.rack_infos[0].quantity_left -
                       group_length * group_width >= 0):
                    group_width += 1
                    rack_group = RackGroup(self.rack_infos[0], group_length,
                                           group_width, False)
                    rack_group.translate(zone_x0, zone_y0)
                group_width -= 1

                if group_width == 0:
                    continue

                rack_group = RackGroup(self.rack_infos[0], group_length,
                                       group_width)
                rack_group.translate(zone_x0, zone_y0)

                self.rack_groups.append(rack_group)
                self.rack_infos[0].quantity_left -= group_length * group_width
                split_point = rack_group.restrictive_bounds.bounds[2:]
                zone_1, zone_2 = zone.split_zone(split_point)
                self.zones.remove(zone)
                self.zones.append(zone_1)
                self.zones.append(zone_2)

                if self.rack_infos[0].quantity_left == 0:
                    self.rack_infos.pop(0)

                self.zones.sort(key=lambda zone: zone.available_area_size,
                                reverse=True)
                self.zones.sort(key=lambda zone: zone.height,
                                reverse=True)

                is_successful_rack_placement = True
                break

            if not is_successful_rack_placement:
                warnings.warn("No space left for "
                              f"{self.rack_infos[0].quantity_left}"
                              f"racks with id {self.rack_infos[0].id}")
                self.rack_infos.pop(0)
