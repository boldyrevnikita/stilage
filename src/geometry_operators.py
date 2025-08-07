import shapely
from shapely.geometry.base import BaseGeometry


def contains(geom1: BaseGeometry, geom2: BaseGeometry) -> bool:
    """Check if geom1 contains geom2.

    Args:
        geom1 (BaseGeometry): The geometry to check for containment.
        geom2 (BaseGeometry): The geometry to check if contained.

    Returns:
        bool: True if geom1 contains geom2, False otherwise.
    """
    return shapely.contains(geom1, geom2)


def intersects(geom1: BaseGeometry, geom2: BaseGeometry) -> bool:
    """Check if geom1 intersects geom2 without touching.
    Args:
        geom1 (BaseGeometry): The first geometry.
        geom2 (BaseGeometry): The second geometry.
    Returns:
        bool: True if geom1 intersects geom2 without touching, False otherwise.
    """
    return shapely.intersects(geom1, geom2) and not shapely.touches(geom1, geom2)
