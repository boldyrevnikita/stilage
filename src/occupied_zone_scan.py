import warnings
from queue import Queue
from collections import deque
from typing import List

import ezdxf
import ezdxf.document
import ezdxf.select
import numpy as np
import shapely
import logging

from src.zone import AvailableZone, OccupiedZone

logger = logging.getLogger(__name__)

def _safe_polygon(vertices, min_unique=3):
    """
    Возвращает shapely.Polygon или None, если контур вырожден.
    Требуется минимум 3 уникальные точки (=> 4 с замыканием).
    """
    cleaned = []
    for x, y in vertices:
        if not cleaned or (cleaned[-1][0] != x or cleaned[-1][1] != y):
            cleaned.append((float(x), float(y)))
    if cleaned and cleaned[0] != cleaned[-1]:
        cleaned.append(cleaned[0])
    uniq = set(cleaned[:-1]) if cleaned else set()
    if len(uniq) < min_unique:
        return None
    try:
        return shapely.geometry.Polygon(cleaned)
    except Exception as e:
        logger.debug(f"_safe_polygon: failed with {e}; vertices={len(cleaned)}")
        return None

def dxf_entity_to_shapely(entity, approx_point_quantity: int = 10
                          ) -> List[shapely.geometry.base.BaseGeometry]:
    """Converts a DXF entity to a Shapely geometry object.
    Args:
        entity (ezdxf.entities.Entity): The DXF entity to convert.
        approx_point_quantity (int): The number of points to
            approximate curves.
    Returns:
        List[shapely.geometry.base.BaseGeometry]: A list of Shapely geometry
            objects representing the DXF entity.
    """
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
            pts = [(entity.dxf.start.x, entity.dxf.start.y),
           (entity.dxf.end.x, entity.dxf.end.y)]
            if len(pts) >= 2:
                geometry_list.append(shapely.geometry.LineString(pts))
        elif type(entity) is ezdxf.entities.LWPolyline:
            vertices = [(p[0], p[1]) for p in entity.vertices_in_wcs()]
            if entity.is_closed:
                poly = _safe_polygon(vertices)
                if poly is not None:
                    geometry_list.append(poly)
                elif len(vertices) >= 2:
                    geometry_list.append(shapely.geometry.LineString(vertices))
            else:
                if len(vertices) >= 2:
                    geometry_list.append(shapely.geometry.LineString(vertices))
        elif type(entity) is ezdxf.entities.Solid:
            vertices = [(point[0], point[1])
                        for point in entity.wcs_vertices()]
            poly = _safe_polygon(vertices)
            if poly is not None:
                geometry_list.append(poly)
        elif type(entity) is ezdxf.entities.Arc:
            center = entity.ocs().to_wcs(entity.dxf.center)
            radius = entity.dxf.radius
            angles = list(entity.angles(max(2, approx_point_quantity)))
            radians = np.deg2rad(angles)
            points = [(center[0] + radius * np.cos(a),
                    center[1] + radius * np.sin(a)) for a in radians]
            if len(points) >= 2:
                geometry_list.append(shapely.geometry.LineString(points))
        elif type(entity) is ezdxf.entities.Circle:
            vertices = list(entity.vertices(np.linspace(0, 360.0, max(4, approx_point_quantity))))
            poly = _safe_polygon([(p[0], p[1]) for p in vertices])
            if poly is not None:
                geometry_list.append(poly)
        elif type(entity) is ezdxf.entities.Ellipse:
            vertices = list(entity.vertices(np.linspace(0, 2 * np.pi, max(4, approx_point_quantity))))
            poly = _safe_polygon([(p[0], p[1]) for p in vertices])
            if poly is not None:
                geometry_list.append(poly)
        elif type(entity) is ezdxf.entities.Polyline:
            vertices = [(p[0], p[1]) for p in entity.points_in_wcs()]
            if entity.is_closed:
                poly = _safe_polygon(vertices)
                if poly is not None:
                    geometry_list.append(poly)
            else:
                if len(vertices) >= 2:
                    geometry_list.append(shapely.geometry.LineString(vertices))
        elif type(entity) is ezdxf.entities.Hatch:
            ocs = entity.ocs()
            for path in entity.paths:
                if type(path) is ezdxf.entities.PolylinePath:
                    vertices = [(ocs.to_wcs(p).x, ocs.to_wcs(p).y) for p in path.vertices]
                    if path.is_closed:
                        poly = _safe_polygon(vertices)
                        if poly is not None:
                            geometry_list.append(poly)
                        elif len(vertices) >= 2:
                            geometry_list.append(shapely.geometry.LineString(vertices))
                    else:
                        if len(vertices) >= 2:
                            geometry_list.append(shapely.geometry.LineString(vertices))
                elif type(path) is ezdxf.entities.EdgePath:
                    for edge in path.edges:
                        if type(edge) is ezdxf.entities.boundary_paths.LineEdge:
                            pts = [(ocs.to_wcs(edge.start).x, ocs.to_wcs(edge.start).y),
                                (ocs.to_wcs(edge.end).x,   ocs.to_wcs(edge.end).y)]
                            if len(pts) >= 2:
                                geometry_list.append(shapely.geometry.LineString(pts))
                        elif type(edge) is ezdxf.entities.boundary_paths.ArcEdge:
                            center = ocs.to_wcs(edge.center)
                            radius = edge.radius
                            angles = np.linspace(edge.start_angle, edge.end_angle,
                                                max(2, approx_point_quantity))
                            radians = np.deg2rad(angles)
                            pts = [(center[0] + radius * np.cos(a),
                                    center[1] + radius * np.sin(a)) for a in radians]
                            if len(pts) >= 2:
                                geometry_list.append(shapely.geometry.LineString(pts))

        elif type(entity) is ezdxf.entities.Insert:
            for v_entity in entity.virtual_entities():
                q.put(v_entity)
        elif type(entity) is ezdxf.entities.Spline:
            bspline = entity.construction_tool()
            points = [p.xy for p in bspline.approximate(approx_point_quantity)]
            if len(points) >= 2:
                geometry_list.append(shapely.geometry.LineString([(p[0], p[1]) for p in points]))
        elif type(entity) in skip_entities:
            pass
        else:
            warnings.warn(f"Unsupported DXF entity type: {type(entity)}")
    return geometry_list


def filter_primitives(
    primitives: List[shapely.geometry.base.BaseGeometry],
    available_zones: List[AvailableZone],
) -> List[shapely.geometry.base.BaseGeometry]:
    """Filters the primitives to only include those that are within the
    available zones.

    Args:
        primitives (List[shapely.geometry.base.BaseGeometry]): The list of
            primitives to filter.
        available_zones (List[AvailableZone]): The list of available zones.
    Returns:
        List[shapely.geometry.base.BaseGeometry]: The filtered list of
            primitives that are within the available zones.
    """
    filtered_primitives = []
    for prim in primitives:
        for zone in available_zones:
            if zone.contour.contains(prim):
                filtered_primitives.append(prim)
                break
    return filtered_primitives


def get_polygons_from_primitives(
    primitives: List[shapely.geometry.base.BaseGeometry],
        eps: float = 1e-9) -> List[shapely.Polygon]:
    """Converts a list of Shapely primitives to polygons.
    Args:
        primitives (List[shapely.geometry.base.BaseGeometry]): The list of
            Shapely primitives to convert.
        eps (float): The epsilon value for buffering.
    Returns:
        List[shapely.Polygon]: The list of converted Shapely polygons.
    """

    def process_polygon(polygon: shapely.Polygon,
                        centroid_threshold: float = 300
                        ) -> shapely.Polygon:
        """Processes a polygon to ensure it is valid and returns a
        processed polygon.
        Args:
            polygon (shapely.Polygon): The polygon to process.
            centroid_threshold (float): The threshold for centroid distance.
        Returns:
            shapely.Polygon: The processed polygon.
        """
        convex_hull = polygon.convex_hull
        centroid_distance = (
            abs(polygon.centroid.x - convex_hull.centroid.x)
            + abs(polygon.centroid.y - convex_hull.centroid.y))

        if centroid_distance < centroid_threshold:
            result = convex_hull.buffer(-eps, join_style=2, cap_style=2)
        else:
            result = polygon.buffer(-eps, join_style=2, cap_style=2)
        return result

    polygons = []
    primitives_processed = []
    for prim in primitives:
        primitives_processed.append(prim.buffer(
            eps, join_style=2, cap_style=2))

    gm = shapely.disjoint_subset_union_all(primitives_processed)

    q = deque()
    q.append(gm)
    while q:
        gm = q.popleft()
        if type(gm) is shapely.Polygon:
            entity = process_polygon(gm)
            if isinstance(entity, shapely.MultiPolygon):
                q.append(entity)
            else:
                polygons.append(entity)
        elif type(gm) is shapely.MultiPolygon:
            for entity in gm.geoms:
                q.append(entity)

    return polygons


def filter_empty_polygons(
    polygons: list[shapely.Polygon]
) -> list[shapely.Polygon]:
    """Filters out empty polygons from the list of polygons.
    Args:
        polygons (list[shapely.Polygon]): The list of polygons to filter.
    Returns:
        list[shapely.Polygon]: The filtered list of polygons without
            empty ones.
    """
    filtered_polygons = []
    for polygon in polygons:
        if not polygon.is_empty:
            filtered_polygons.append(polygon)

    return filtered_polygons


def filter_small_polygons(
    polygons: list[shapely.Polygon],
    area_threshold: float = 100
) -> list[shapely.Polygon]:
    """Filters out polygons that are smaller than a given area threshold.
    Args:
        polygons (list[shapely.Polygon]): The list of polygons to filter.
        area_threshold (float): The area threshold below which polygons are
            filtered out.
    Returns:
        list[shapely.Polygon]: The filtered list of polygons that are larger
            than the area threshold.
    """
    filtered_polygons = []
    for polygon in polygons:
        if polygon.area > area_threshold:
            filtered_polygons.append(polygon)

    return filtered_polygons


def filter_thin_polygons(
    polygons: list[shapely.Polygon],
    min_dimension_threshold: float = 50.0
) -> list[shapely.Polygon]:
    """✅ НОВАЯ ФУНКЦИЯ: Фильтрует очень тонкие полигоны - артефакты DXF.
    
    Эта функция удаляет полигоны, где ширина или высота ниже минимального порога.
    Такие полигоны обычно являются:
    - Тонкими линиями из DXF аннотаций
    - Границами текстовых блоков
    - Размерными линиями
    - Другими нефизическими артефактами DXF
    
    Args:
        polygons (list[shapely.Polygon]): Список полигонов для фильтрации
        min_dimension_threshold (float): Минимальная ширина или высота для валидного
            полигона. По умолчанию 50мм (разумно для складских препятствий)
    
    Returns:
        list[shapely.Polygon]: Отфильтрованный список без тонких артефактов
    """
    filtered_polygons = []
    filtered_count = 0
    
    for polygon in polygons:
        bounds = polygon.bounds
        width = bounds[2] - bounds[0]   # max_x - min_x
        height = bounds[3] - bounds[1]  # max_y - min_y
        
        # Пропускаем очень тонкие полигоны (скорее всего артефакты DXF)
        if width < min_dimension_threshold or height < min_dimension_threshold:
            logger.debug(f"[ZONE_FILTER] Отфильтрован тонкий полигон: "
                        f"bounds={bounds}, width={width:.1f}мм, height={height:.1f}мм")
            filtered_count += 1
            continue
            
        filtered_polygons.append(polygon)
    
    if filtered_count > 0:
        logger.warning(f"[ZONE_FILTER] ✅ Отфильтровано {filtered_count} тонких полигонов "
                      f"(порог: {min_dimension_threshold:.1f}мм)")
    
    return filtered_polygons


def filter_intersecting_polygons(
    polygons: List[shapely.Polygon],
        intersection_percentage: float = 0.99) -> List[shapely.Polygon]:
    """Filters out polygons that intersect with others based on a given
    intersection percentage.
    Args:
        polygons (List[shapely.Polygon]): The list of polygons to filter.
        intersection_percentage (float): The percentage of intersection
            required to consider polygons as intersecting.
    Returns:
        List[shapely.Polygon]: The filtered list of polygons that do not
            intersect with others based on the intersection percentage.
    """
    is_intersecting = np.zeros(len(polygons), dtype=bool)
    filtered_polygons = []

    for i in range(len(polygons)):
        if is_intersecting[i]:
            continue
        for j in range(i + 1, len(polygons)):
            if is_intersecting[j]:
                continue
            intersection = polygons[i].intersection(polygons[j])
            if intersection.is_empty:
                continue
            intersection_area = intersection.area
            if (intersection_area / polygons[i].area > intersection_percentage
                and intersection_area / polygons[j].area
                    > intersection_percentage):
                is_intersecting[j] = True
        filtered_polygons.append(polygons[i])

    return filtered_polygons


def scan_for_occupied_zones(doc: ezdxf.document.Drawing,
                            available_zones: List[AvailableZone],
                            occupied_zone_clearance: float,
                            roads_width: float,
                            min_zone_dimension: float = 50.0
                            ) -> List[OccupiedZone]:
    """✅ УЛУЧШЕННАЯ ФУНКЦИЯ: Сканирует DXF документ на occupied zones с фильтрацией артефактов.
    
    Теперь включает фильтрацию тонких полигонов для предотвращения создания
    ложных препятствий из DXF артефактов.
    
    Args:
        doc (ezdxf.document.Drawing): DXF документ для сканирования
        available_zones (List[AvailableZone]): Список доступных зон
        occupied_zone_clearance (float): Зазор для occupied zones
        roads_width (float): Ширина дорог вокруг occupied zones
        min_zone_dimension (float): Минимальная ширина или высота для валидной
            occupied zone. По умолчанию 50мм.
    Returns:
        List[OccupiedZone]: Список найденных occupied zones без артефактов
    """
    logger.info(f"[ZONE_SCAN] 🔍 Начало сканирования occupied zones (мин. размер={min_zone_dimension:.1f}мм)")
    
    occupied_zones = []
    geometries = []

    # Извлекаем все геометрии из DXF
    msp = doc.modelspace()
    entity_count = 0
    for entity in msp:
        geometries.extend(dxf_entity_to_shapely(entity))
        entity_count += 1
    
    logger.info(f"[ZONE_SCAN] Обработано {entity_count} DXF объектов → {len(geometries)} геометрий")

    # Применяем все фильтры последовательно
    geometries = filter_primitives(geometries, available_zones)
    logger.info(f"[ZONE_SCAN] После фильтрации по зонам: {len(geometries)} геометрий")
    
    polygons = get_polygons_from_primitives(geometries)
    logger.info(f"[ZONE_SCAN] После конвертации в полигоны: {len(polygons)} полигонов")
    
    polygons = filter_empty_polygons(polygons)
    logger.info(f"[ZONE_SCAN] После удаления пустых: {len(polygons)} полигонов")
    
    polygons = filter_small_polygons(polygons)
    logger.info(f"[ZONE_SCAN] После фильтрации малых по площади: {len(polygons)} полигонов")
    
    # ✅ НОВОЕ: Фильтруем тонкие полигоны (артефакты DXF)
    polygons = filter_thin_polygons(polygons, min_zone_dimension)
    logger.info(f"[ZONE_SCAN] После фильтрации тонких полигонов: {len(polygons)} полигонов")
    
    polygons = filter_intersecting_polygons(polygons)
    logger.info(f"[ZONE_SCAN] После фильтрации пересекающихся: {len(polygons)} полигонов")

    # Конвертируем в объекты OccupiedZone
    for i, polygon in enumerate(polygons):
        try:
            bounds = polygon.bounds
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]
            
            occupied_zone = OccupiedZone(
                list(polygon.exterior.coords),
                occupied_zone_clearance,
                roads_width
            )
            occupied_zones.append(occupied_zone)
            
            logger.debug(f"[ZONE_SCAN] Создана OccupiedZone {i+1}: "
                        f"bounds={bounds}, размер={width:.1f}x{height:.1f}мм")
                        
        except Exception as e:
            logger.warning(f"[ZONE_SCAN] ❌ Ошибка создания OccupiedZone из полигона {i}: {e}")
            continue

    logger.warning(f"[ZONE_SCAN] ✅ Успешно создано {len(occupied_zones)} occupied zones")
    
    # Дополнительная диагностика
    if len(occupied_zones) == 0:
        logger.warning("[ZONE_SCAN] ⚠️  ВНИМАНИЕ: Не найдено ни одной occupied zone!")
    else:
        # Показываем статистику размеров найденных зон
        widths = []
        heights = []
        for zone in occupied_zones:
            bounds = zone.bounds
            widths.append(bounds[2] - bounds[0])
            heights.append(bounds[3] - bounds[1])
        
        min_width, max_width = min(widths), max(widths)
        min_height, max_height = min(heights), max(heights)
        
        logger.info(f"[ZONE_SCAN] 📊 Статистика зон: "
                   f"ширина {min_width:.1f}-{max_width:.1f}мм, "
                   f"высота {min_height:.1f}-{max_height:.1f}мм")
    
    return occupied_zones