from src.forbidden_zone import ForbiddenZone
from src.rack_group import RackGroup
from typing import List


def postprocess(rack_groups: List[RackGroup],
                forbidden_zones: List[ForbiddenZone]) -> List[RackGroup]:
    """Split racks in rack_groups that intersect with forbidden_zones.

    Args:
        rack_groups (List[RackGroup]): rack groups
        forbidden_zones (List[ForbiddenZone]): forbidden zones

    Returns:
        List[RackGroup]: rack groups with splited racks
            that do not intersect with forbidden zones
    """

    for rack_group in rack_groups:
        for forbidden_zone in forbidden_zones:
            if not forbidden_zone.intersects(rack_group.restrictive_bounds):
                continue
            new_racks = forbidden_zone.process_intersection(rack_group)
            rack_group.racks = new_racks

    return rack_groups
