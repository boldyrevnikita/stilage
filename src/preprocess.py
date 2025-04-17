from typing import List, Tuple

import ezdxf.document
import ezdxf.select
import numpy as np

from src.available_zone import AvailableZone
from src.forbidden_zone import ForbiddenZone
from src.rack import RackSection
import ezdxf
import shapely
import warnings


def preprocess(doc: ezdxf.document.Drawing,
               available_zones: List[AvailableZone],
               forbidden_zones: List[ForbiddenZone],
               rack_infos: List[RackSection],
               roads_width: float,
               forbiden_zone_clearance) -> Tuple[List[AvailableZone],
                                                 List[ForbiddenZone],
                                                 List[RackSection]]:
    forbidden_zones += scan_for_forbidden_zones(doc, available_zones,
                                                forbiden_zone_clearance)
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


def dxf_entity_to_shapely(entity, approx_point_quantity: int = 10
                          ) -> shapely.geometry.base.BaseGeometry:
    if entity.dxftype() == 'LINE':
        return shapely.geometry.LineString(
            [(entity.dxf.start.x, entity.dxf.start.y),
             (entity.dxf.end.x, entity.dxf.end.y)])
    elif entity.dxftype() == 'LWPOLYLINE':
        if entity.is_closed:
            return shapely.geometry.Polygon(
                [(point[0], point[1]) for point in entity.get_points()])
        else:
            return shapely.geometry.LineString(
                [(point[0], point[1]) for point in entity.get_points()])
    elif entity.dxftype() == 'ARC':
        center = entity.dxf.center
        radius = entity.dxf.radius
        angles = list(entity.angles(approx_point_quantity))
        radians = np.deg2rad(angles)
        points = [(center[0] + radius * np.cos(angle),
                   center[1] + radius * np.sin(angle)) for angle in radians]
        return shapely.geometry.LineString(points)
    elif entity.dxftype() == 'CIRCLE':
        vertices = list(entity.vertices(np.linspace(0, 360.0,
                                                    approx_point_quantity)))
        return shapely.geometry.Polygon(
            [(point[0], point[1]) for point in vertices])
    elif entity.dxftype() == 'MTEXT':
        return None
    elif entity.dxftype() == 'TEXT':
        return None
    else:
        warnings.warn(f"Unsupported DXF entity type: {entity.dxftype()}")
        return None


def get_polygons_from_primitives(
    primitives: List[shapely.geometry.base.BaseGeometry],
        eps: float = 1e-9) -> List[shapely.Polygon]:

    polygons = []
    primitives_processed = []
    for prim in primitives:
        primitives_processed.append(prim.buffer(
            eps, join_style=2, cap_style=2))

    gm = shapely.union_all(primitives_processed)

    if type(gm) is shapely.geometry.Polygon:
        convex_hull = gm.convex_hull
        convex_hull = convex_hull.buffer(-eps, join_style=2, cap_style=2)
        polygons.append(convex_hull)
    elif type(gm) is shapely.geometry.MultiPolygon:
        for polygon in gm.geoms:
            convex_hull = polygon.convex_hull
            convex_hull = convex_hull.buffer(-eps, join_style=2, cap_style=2)
            polygons.append(convex_hull)

    return polygons


def scan_for_forbidden_zones(doc: ezdxf.document.Drawing,
                             available_zones: List[AvailableZone],
                             forbiden_zone_clearance: float
                             ) -> List[ForbiddenZone]:
    forbidden_zones = []

    msp = doc.modelspace()

    for zone in available_zones:
        geometries = []
        zone_bbox = zone.geometry.bounds
        window = ezdxf.select.Window(
            (zone_bbox[0], zone_bbox[1]),
            (zone_bbox[2], zone_bbox[3]),
        )

        entities = ezdxf.select.bbox_inside(
            window, msp
        )

        for entity in entities:
            geometry = dxf_entity_to_shapely(entity)
            if geometry is not None:
                geometries.append(geometry)

        polygones = get_polygons_from_primitives(geometries)
        for polygon in polygones:
            forbidden_zones.append(ForbiddenZone(
                list(polygon.exterior.coords),
                forbiden_zone_clearance)
            )

    return forbidden_zones
