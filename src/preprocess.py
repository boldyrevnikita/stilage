from src.forbidden_zone import ForbiddenZone
from src.rack import RackSection
from typing import List, Tuple


def preprocess(forbidden_zones: List[ForbiddenZone],
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
