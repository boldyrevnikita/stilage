from src.forbidden_zone import ForbiddenZone
from src.rack_group import RackGroup
from src.rack import Rack
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
            new_racks = []

            for i, rack in enumerate(rack_group.racks):
                if not forbidden_zone.intersects(rack.get_convex_hull()):
                    new_racks.append(rack)
                    continue
                shelfs = [[] for _ in range(
                    rack.get_sections_in_width())]
                pillars = [[] for _ in range(
                    rack.get_sections_in_width())]

                is_intersects = False
                for jdx in range(rack.get_sections_in_length()):
                    for row in rack.pillar_rows:
                        if forbidden_zone.intersects(row[jdx]):
                            if len(shelfs) > 0 and len(shelfs[-1]) > 0:
                                for new_row in shelfs:
                                    new_row.pop()
                            if len(shelfs[-1]) > 0:
                                new_racks.append(Rack(shelfs, pillars))
                                shelfs = [[] for _ in range(
                                    rack.get_sections_in_width())]
                            if len(pillars[-1]) > 0:
                                pillars = [[] for _ in range(
                                    rack.get_sections_in_width())]
                            is_intersects = True
                            break

                    if is_intersects:
                        is_intersects = False
                        continue

                    for kdx, row in enumerate(rack.pillar_rows):
                        pillars[kdx].append(row[jdx])

                    for row in rack.shelf_rows:
                        if forbidden_zone.intersects(row[jdx]):
                            if len(shelfs[-1]) > 0:
                                new_racks.append(Rack(shelfs, pillars))
                                shelfs = [[] for _ in range(
                                    rack.get_sections_in_width())]
                            if len(pillars[-1]) > 0:
                                pillars = [[] for _ in range(
                                    rack.get_sections_in_width())]
                            is_intersects = True
                            break

                    if is_intersects:
                        is_intersects = False
                        continue

                    for kdx, row in enumerate(rack.shelf_rows):
                        shelfs[kdx].append(row[jdx])

                for row in rack.pillar_rows:
                    if forbidden_zone.intersects(row[-1]):
                        if len(shelfs) > 0 and len(shelfs[-1]) > 0:
                            for new_row in shelfs:
                                new_row.pop()
                        is_intersects = True
                        break

                if not is_intersects:
                    for kdx, row in enumerate(rack.pillar_rows):
                        pillars[kdx].append(row[-1])

                if len(shelfs[-1]) > 0:
                    new_racks.append(Rack(shelfs, pillars))
            rack_group.racks = new_racks

    return rack_groups
