from typing import List, Tuple

import numpy as np

from src.available_zone import AvailableZone
from src.forbidden_zone import ForbiddenZone
from src.rack import RackSection


def preprocess(available_zones: List[AvailableZone],
               forbidden_zones: List[ForbiddenZone],
               rack_infos: List[RackSection],
               roads_width: float) -> Tuple[List[AvailableZone],
                                            List[ForbiddenZone],
                                            List[RackSection]]:
    forbidden_zones, rack_infos = update_clearance(forbidden_zones,
                                                   rack_infos, roads_width)
    rack_infos = update_racks_quantity(available_zones, rack_infos)

    return available_zones, forbidden_zones, rack_infos


def update_racks_quantity(available_zones: List[AvailableZone],
                          rack_infos: List[RackSection]) -> List[RackSection]:
    sum_area = np.sum(zone.available_area_size for zone in available_zones)

    for rack_section in rack_infos:
        if (rack_section.abs_quantity is None
            and rack_section.rel_quantity is None
            and rack_section.max_quantity is None
                and rack_section.min_quantity is None):
            rack_section.update_abs_quantity(int(
                sum_area / (rack_section.unit_length * rack_section.width)))

    return rack_infos


def update_clearance(forbidden_zones: List[ForbiddenZone],
                     rack_infos: List[RackSection],
                     roads_width: float) -> Tuple[List[ForbiddenZone],
                                                  List[RackSection]]:
    for zone in forbidden_zones:
        new_clearance = max(zone.distance_from_zone, roads_width)
        zone.update_clearance(new_clearance)

    for rack_section in rack_infos:
        rack_section.side_distance = max(rack_section.side_distance,
                                         roads_width / 2)
        rack_section.back_distance = max(rack_section.back_distance,
                                         roads_width / 2)
        rack_section.front_distance = max(rack_section.front_distance,
                                          roads_width / 2)

    return forbidden_zones, rack_infos
