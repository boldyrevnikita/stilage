import warnings
from queue import Queue
from typing import List

import ezdxf
import ezdxf.document
import ezdxf.select
import numpy as np
import shapely

from src.zone import AvailableZone, OccupiedZone


def dxf_entity_to_shapely(entity, approx_point_quantity: int = 10
                          ) -> List[shapely.geometry.base.BaseGeometry]:
    skip_entities = [
        ezdxf.entities.Text, ezdxf.entities.MText, ezdxf.entities.Dimension,
        ezdxf.entities.leader.Leader, ezdxf.entities.mleader.MultiLeader]
    q = Queue()
    q.put(entity)
    geometry_list = []

    while not q.empty():
        entity = q.get()
        if type(entity) is ezdxf.entities.Point:
            for v_entity in entity.virtual_entities():
                q.put(v_entity)
        elif type(entity) is ezdxf.entities.Line:
            geometry_list.append(shapely.geometry.LineString(
                [(entity.dxf.start.x, entity.dxf.start.y),
                 (entity.dxf.end.x, entity.dxf.end.y)]))
        elif type(entity) is ezdxf.entities.LWPolyline:
            vertices = [(point[0], point[1])
                        for point in entity.vertices_in_wcs()]
            if entity.is_closed:
                geometry_list.append(shapely.geometry.Polygon(vertices))
            else:
                geometry_list.append(shapely.geometry.LineString(vertices))
        elif type(entity) is ezdxf.entities.Solid:
            vertices = [(point[0], point[1])
                        for point in entity.wcs_vertices()]
            geometry_list.append(shapely.geometry.Polygon(vertices))
        elif type(entity) is ezdxf.entities.Arc:
            center = entity.ocs().to_wcs(entity.dxf.center)
            radius = entity.dxf.radius
            angles = list(entity.angles(10))
            radians = np.deg2rad(angles)
            points = [(center[0] + radius * np.cos(angle),
                       center[1] + radius * np.sin(angle))
                      for angle in radians]
            geometry_list.append(shapely.geometry.LineString(points))
        elif type(entity) is ezdxf.entities.Circle:
            vertices = list(entity.vertices(np.linspace(
                0, 360.0, approx_point_quantity)))
            geometry_list.append(shapely.geometry.Polygon(
                [(point[0], point[1]) for point in vertices]))
        elif type(entity) is ezdxf.entities.Ellipse:
            vertices = list(entity.vertices(np.linspace(0, 2 * np.pi, 10)))
            geometry_list.append(shapely.geometry.Polygon(
                [(point[0], point[1]) for point in vertices]))
        elif type(entity) is ezdxf.entities.Polyline:
            vertices = [(point[0], point[1])
                        for point in entity.points_in_wcs()]
            if entity.is_closed:
                geometry_list.append(shapely.geometry.Polygon(vertices))
            else:
                geometry_list.append(shapely.geometry.LineString(vertices))
        elif type(entity) is ezdxf.entities.Hatch:
            ocs = entity.ocs()
            for path in entity.paths:
                if type(path) is ezdxf.entities.PolylinePath:
                    vertices = [(ocs.to_wcs(point[0]),
                                 ocs.to_wcs(point[1]))
                                for point in path.vertices]
                    if path.is_closed:
                        geometry_list.append(shapely.geometry.Polygon(
                            vertices))
                    else:
                        geometry_list.append(shapely.geometry.LineString(
                            vertices))
                elif type(path) is ezdxf.entities.EdgePath:
                    for edge in path.edges:
                        if (type(edge) is
                                ezdxf.entities.boundary_paths.LineEdge):
                            geometry_list.append(shapely.geometry.LineString(
                                [(ocs.to_wcs(edge.start).x,
                                  ocs.to_wcs(edge.start).y),
                                 (ocs.to_wcs(edge.end).x,
                                  ocs.to_wcs(edge.end).y)]))
                        elif (type(edge) is
                                ezdxf.entities.boundary_paths.ArcEdge):
                            center = ocs.to_wcs(edge.center)
                            radius = edge.radius
                            angles = np.linspace(edge.start_angle,
                                                 edge.end_angle,
                                                 approx_point_quantity)
                            radians = np.deg2rad(angles)
                            points = [(center[0] + radius * np.cos(angle),
                                       center[1] + radius * np.sin(angle))
                                      for angle in radians]
                            geometry_list.append(shapely.geometry.LineString(
                                points))
        elif type(entity) is ezdxf.entities.Insert:
            for v_entity in entity.virtual_entities():
                q.put(v_entity)
        elif type(entity) is ezdxf.entities.Spline:
            bspline = entity.construction_tool()
            points = [p.xy for p in bspline.approximate(approx_point_quantity)]
            geometry_list.append(shapely.geometry.LineString(
                [(point[0], point[1]) for point in points]))
        elif type(entity) in skip_entities:
            pass
        else:
            warnings.warn(f"Unsupported DXF entity type: {type(entity)}")
    return geometry_list


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


def scan_for_occupied_zones(doc: ezdxf.document.Drawing,
                            available_zones: List[AvailableZone],
                            occupied_zone_clearance: float,
                            roads_width: float,
                            ) -> List[OccupiedZone]:
    occupied_zones = []

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
            geometries.extend(dxf_entity_to_shapely(entity))

        polygones = get_polygons_from_primitives(geometries)
        for polygon in polygones:
            occupied_zones.append(OccupiedZone(
                list(polygon.exterior.coords),
                occupied_zone_clearance,
                roads_width
            ))

    return occupied_zones
