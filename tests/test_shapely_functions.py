import shapely
from pytest import fixture

from src.geometry_operators import contains, intersects


@fixture
def rectangular_polygon():
    return shapely.geometry.Polygon(
        [(0, 0), (10, 0), (10, 10), (0, 10)]
    )


@fixture
def inner_polygon():
    return shapely.geometry.Polygon(
        [(1, 1), (7, 1), (9, 9), (1, 9)]
    )


@fixture
def inner_polygon_with_overlapping_boundary():
    return shapely.geometry.Polygon(
        [(0, 0), (5, 0), (5, 7), (0, 5)]
    )


@fixture
def outer_polygon():
    return shapely.geometry.Polygon(
        [(11, 11), (15, 11), (11, 15)]
    )


@fixture
def outer_polygon_with_overlapping_boundary():
    return shapely.geometry.Polygon(
        [(10, 10), (15, 10), (15, 15), (10, 15)]
    )


@fixture
def crossing_polygon():
    return shapely.geometry.Polygon(
        [(5, 0), (5, 10), (15, 10), (15, 0)]
    )


@fixture
def inner_point():
    return shapely.geometry.Point(5, 5)


@fixture
def outer_point():
    return shapely.geometry.Point(15, 15)


@fixture
def border_point():
    return shapely.geometry.Point(5, 0)


def test_polygon_intersects_inner_polygon(rectangular_polygon, inner_polygon):
    assert intersects(rectangular_polygon, inner_polygon)


def test_polygon_intersects_crossing_polygon(rectangular_polygon, crossing_polygon):
    assert intersects(rectangular_polygon, crossing_polygon)


def test_polygon_does_not_intersect_outer_polygon(rectangular_polygon, outer_polygon):
    assert not intersects(rectangular_polygon, outer_polygon)


def test_polygon_does_not_intersect_outer_polygon_with_overlapping_boundary(
        rectangular_polygon, outer_polygon_with_overlapping_boundary):
    assert not intersects(rectangular_polygon, outer_polygon_with_overlapping_boundary)


def test_polygon_contains_inner_polygon(rectangular_polygon, inner_polygon):
    assert contains(rectangular_polygon, inner_polygon)


def test_polygon_contains_inner_polygon_with_overlapping_boundary(
        rectangular_polygon, inner_polygon_with_overlapping_boundary):
    assert contains(rectangular_polygon, inner_polygon_with_overlapping_boundary)


def test_polygon_does_not_contain_outer_polygon(rectangular_polygon, outer_polygon):
    assert not contains(rectangular_polygon, outer_polygon)


def test_polygon_does_not_contain_crossing_polygon(rectangular_polygon,
                                                   crossing_polygon):
    assert not contains(rectangular_polygon, crossing_polygon)


def test_polygon_contains_inner_point(rectangular_polygon, inner_point):
    assert contains(rectangular_polygon, inner_point)


def test_polygon_does_not_contain_outer_point(rectangular_polygon, outer_point):
    assert not contains(rectangular_polygon, outer_point)


def test_polygon_does_not_contain_border_point(rectangular_polygon, border_point):
    assert not contains(rectangular_polygon, border_point)


def test_polygon_constains_itself(rectangular_polygon):
    assert contains(rectangular_polygon, rectangular_polygon)
