from copy import deepcopy

import src.geometry_operators as gops
from src.pallet_packer.solution import ActionFailure, Solution
from src.rack import Rack
from src.reference_book import ReferenceBook
from src.zone import SpecialRoadZone


def rotate_everything_90_clockwise(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Rotates the available zone's contour 90 degrees clockwise.

    Args:
        _ (ReferenceBook): The reference book containing business
            logic related information.
        solution (Solution): The current solution containing available zones.
    """
    available_zone = solution.available_zones[solution.available_zone_idx]
    solution.rot_point = available_zone.bounds[:2]
    angle = -90

    available_zone.rotate(solution.rot_point, angle)
    for occupied_zone in solution.current_occupied_zones:
        occupied_zone.rotate(solution.rot_point, angle)
    for road_zone in solution.current_road_zones:
        road_zone.rotate(solution.rot_point, angle)

    solution.is_rotated = True

    solution.current_occupied_zones.sort(
        key=lambda x: x.bounds[0])

    solution.current_road_zones.sort(
        key=lambda x: x.bounds[0])


def rotate_everything_90_counterclockwise(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Rotates the available zone's contour 90 degrees counterclockwise.
    """
    if solution.is_rotated:
        available_zone = solution.available_zones[solution.available_zone_idx]
        angle = 90

        available_zone.rotate(solution.rot_point, angle)
        for occupied_zone in solution.current_occupied_zones:
            occupied_zone.rotate(solution.rot_point, angle)
        for road_zone in solution.current_road_zones:
            road_zone.rotate(solution.rot_point, angle)
        solution.current_rack_group.rotate(angle, solution.rot_point)

        solution.is_rotated = False

        solution.current_occupied_zones.sort(
            key=lambda x: (x.bounds[0], x.bounds[2]))

        solution.current_road_zones.sort(
            key=lambda x: (x.bounds[0], x.bounds[2]))


def set_next_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Sets the next available zone as the current one.
    """
    if solution.available_zone_idx >= len(solution.available_zones) - 1:
        raise ActionFailure("No more available zones to process.")

    solution.available_zone_idx += 1


def set_zero_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Sets the current available zone index to zero and moves to the next pallet.
    """
    solution.available_zone_idx = 0


def assert_current_rack_fits_available_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Checks if the current rack fits into the available zone.
    """
    available_zone = solution.available_zones[solution.available_zone_idx]
    current_rack = solution.current_rack_group.get_current_rack()

    if not gops.contains(
            available_zone.contour, current_rack.contour):
        raise ActionFailure(
            "Current rack does not fit into the available zone."
        )


def split_available_zone(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """
    Splits the available zone into two parts.
    """
    if len(solution.current_rack_group.racks) == 0:
        raise ActionFailure("No racks are placed.")

    current_rack_group = solution.current_rack_group
    available_zone = solution.available_zones[solution.available_zone_idx]
    split_point = list(current_rack_group.bounds[2:])
    split_point[0] += reference_book.roads_width
    split_point[1] += reference_book.roads_width
    split_point[0] = min(available_zone.bounds[2], split_point[0]) - 1
    split_point[1] = min(available_zone.bounds[3], split_point[1]) - 1

    if available_zone.contains_point(split_point):
        new_zones = available_zone.split_zone(split_point)
        solution.available_zones.extend(new_zones)

    solution.available_zones.pop(solution.available_zone_idx)
    solution.available_zone_idx -= 1


def assert_current_rack_intersecting_occupied_zones(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Asserts that the current rack intersects with at least one occupied zone.
    """
    current_rack = solution.current_rack_group.get_current_rack()

    for occupied_zone in solution.current_occupied_zones:
        first_condition = current_rack.intersects(
            occupied_zone.contour)
        second_condition = (
            current_rack.intersects(occupied_zone.contour_with_roads_width)
            and current_rack.bounds[3] < occupied_zone.contour.bounds[1]
            and current_rack.bounds[2] > occupied_zone.contour.bounds[0]
            and occupied_zone.contour.bounds[2] > current_rack.bounds[0]
        )

        if first_condition or second_condition:
            solution.intersected_special_zone = occupied_zone
            if solution.max_intersected_oz_y is None:
                solution.max_intersected_oz_y = occupied_zone.bounds[3]
            else:
                solution.max_intersected_oz_y = max(
                    occupied_zone.bounds[3],
                    solution.max_intersected_oz_y)
            return

    raise ActionFailure(
        "Current rack does not intersect with any occupied zone."
    )


def assert_current_rack_intersecting_road_zones(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that the current rack intersects with at least one road zone.
    """
    current_rack = solution.current_rack_group.get_current_rack()

    for road_zone in solution.current_road_zones:
        if current_rack.last_frame_intersects(road_zone.contour):
            if road_zone is solution.last_intersected_vertical_road:
                continue

            solution.intersected_special_zone = road_zone
            if not road_zone.is_horizontal():
                solution.last_intersected_vertical_road = road_zone

            return

    raise ActionFailure(
        "Current rack does not intersect with any road zone."
    )


def assert_intersected_road_horizontal(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that the intersected road zone is horizontal.
    """
    if not solution.intersected_special_zone.is_horizontal():
        raise ActionFailure(
            "Intersected road zone is not horizontal."
        )


def assert_current_shelf_length_enough_for_road(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Checks if the current shelf length is enough for the road width.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    current_road = solution.intersected_special_zone

    if current_rack.get_current_shelf_length() < current_road.width:
        raise ActionFailure(
            "Current shelf length is not enough for the road width."
        )


def assert_current_zone_height_enough_for_rack_bridge(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that the current zone height is enough for the rack bridge.
    """
    if solution.max_shelfs_bridge <= 0:
        raise ActionFailure(
            "Current available zone is too low for current rack bridge."
        )


def assert_both_racks_intersecting_occupied_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that both racks of the double rack intersect with the occupied
    zone.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    current_occupied_zone = solution.intersected_special_zone

    is_first_rack_intersecting = (
        gops.intersects(
            current_occupied_zone.contour,
            current_rack.rack_1.contour))
    is_second_rack_intersecting = (
        gops.intersects(
            current_occupied_zone.contour,
            current_rack.rack_2.contour))

    if not is_first_rack_intersecting:
        raise ActionFailure(
            "First rack does not intersect with the occupied zone."
        )
    if not is_second_rack_intersecting:
        raise ActionFailure(
            "Second rack does not intersect with the occupied zone."
        )


def assert_first_rack_intersecting_occupied_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that the first rack of the double rack intersects with the
    occupied zone.
    """
    is_first_rack_intersecting = (
        gops.intersects(
            solution.intersected_special_zone.contour,
            solution.current_rack_group.get_current_rack().rack_1.contour))
    if not is_first_rack_intersecting:
        raise ActionFailure(
            "First rack does not intersect with the occupied zone."
        )


def assert_second_rack_intersecting_occupied_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that the second rack of the double rack intersects with the
    occupied zone.
    """
    is_second_rack_intersecting = (
        gops.intersects(
            solution.intersected_special_zone.contour,
            solution.current_rack_group.get_current_rack().rack_2.contour))
    if not is_second_rack_intersecting:
        raise ActionFailure(
            "Second rack does not intersect with the occupied zone."
        )


def assert_last_rack_shelf_covers_occupied_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that the last shelf of the current rack covers the occupied
    zone.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    current_occupied_zone = solution.intersected_special_zone

    is_last_shelf_covers = (
        gops.contains(
            current_rack.last_shelf_contour,
            current_occupied_zone.contour))

    if not is_last_shelf_covers:
        raise ActionFailure(
            "Last shelf of the current rack does not cover the occupied zone."
        )


def assert_last_shelf_of_first_rack_covers_occupied_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that the last shelf of the first rack covers the occupied
    zone.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    current_occupied_zone = solution.intersected_special_zone

    is_last_shelf_covers = (
        gops.contains(
            current_rack.rack_1.last_shelf_contour,
            current_occupied_zone.contour))

    if not is_last_shelf_covers:
        raise ActionFailure(
            "Last shelf of the first rack does not cover the occupied zone."
        )


def assert_last_shelf_of_second_rack_covers_occupied_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that the last shelf of the second rack covers the occupied
    zone.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    current_occupied_zone = solution.intersected_special_zone

    is_last_shelf_covers = (
        gops.contains(
            current_rack.rack_2.last_shelf_contour,
            current_occupied_zone.contour))

    if not is_last_shelf_covers:
        raise ActionFailure(
            "Last shelf of the second rack does not cover the occupied zone."
        )


def set_current_occupied_zones_and_road_zones(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Retrieves the corresponding occupied zones and road zones for the current
    available zone.
    """
    available_zone = solution.available_zones[solution.available_zone_idx]

    for occupied_zone in solution.occupied_zones:
        intersects_with_clearance = (
            gops.intersects(
                available_zone.contour, occupied_zone.contour_with_clearance))
        intersects_with_roads_width = (
            gops.intersects(
                available_zone.contour, occupied_zone.contour_with_roads_width)
            )

        if (intersects_with_clearance or
                intersects_with_roads_width):
            solution.current_occupied_zones.append(deepcopy(occupied_zone))

    for road_zone in solution.road_zones:
        if gops.intersects(
                road_zone.contour, available_zone.contour):
            solution.current_road_zones.append(deepcopy(road_zone))

    solution.current_occupied_zones.sort(
        key=lambda x: (x.bounds[0], x.bounds[2]))

    solution.current_road_zones.sort(
        key=lambda x: (x.bounds[0], x.bounds[2]))


def sort_available_zones_by_area_and_height(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Sorts the current occupied zones and road zones by area and height.
    """
    solution.available_zones.sort(key=lambda x: (-x.height, -x.area))


def place_road_zone_on_right_size(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """
    Places the road zone on the right size.
    """

    available_zone = solution.available_zones[solution.available_zone_idx]

    # right road
    x_0, y_0, x_1, y_1 = available_zone.bounds
    x_0 = x_1 - reference_book.roads_width / 2
    x_1 = x_0

    new_road_zone = SpecialRoadZone(
        [(x_0, y_0), (x_1, y_1)],
        reference_book.roads_width,
    )

    solution.current_road_zones.append(new_road_zone)

    # upper road
    x_0, y_0, x_1, y_1 = available_zone.bounds
    y_0 = (y_1 - solution.pallets[solution.pallet_idx].length
           - reference_book.roads_width / 2)
    y_1 = y_0

    new_road_zone = SpecialRoadZone(
        [(x_0, y_0), (x_1, y_1)],
        reference_book.roads_width,
    )

    solution.current_road_zones.append(new_road_zone)


def assert_current_rack_not_intersecting_oz_or_rz(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Asserts that the current rack does not intersect with any occupied or road
    zones.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    intersected_special_zone = None
    min_left_bound = None

    for occupied_zone in solution.current_occupied_zones:
        if gops.intersects(
                occupied_zone.contour_with_roads_width, current_rack.contour
        ):
            current_left_bound = \
                occupied_zone.contour_with_roads_width.bounds[0]
            if (intersected_special_zone is None or
                    min_left_bound > current_left_bound):
                intersected_special_zone = occupied_zone
                min_left_bound = current_left_bound

    for road_zone in solution.current_road_zones:
        if gops.intersects(
                road_zone.contour, current_rack.contour
        ):
            current_left_bound = road_zone.bounds[0]
            if (intersected_special_zone is None or
                    min_left_bound > current_left_bound):
                intersected_special_zone = road_zone
                min_left_bound = current_left_bound

    if intersected_special_zone is not None:
        solution.intersected_special_zone = intersected_special_zone
        raise ActionFailure(
            "Current rack intersects with an occupied or road zone."
        )


def move_second_rack_higher_over_oz(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """
    Moves the second rack higher over the occupied zone.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    current_occupied_zone = solution.intersected_special_zone

    y_shift = (current_occupied_zone.contour.bounds[3] -
               current_rack.rack_2.contour.bounds[1]) + 1

    tail = y_shift % 50
    if tail != 0:
        y_shift += 50 - tail

    final_double_rack_internal_distance = y_shift + current_rack.rack_distance
    if (final_double_rack_internal_distance >
            reference_book.max_double_rack_internal_distance):
        raise ActionFailure("Internal double rack distance is too big.")

    current_rack.move_second_rack_higher(y_shift)


def remove_unavailable_rack_parts(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """
    Remove unavailable rack parts.
    """

    current_rack_group = solution.current_rack_group
    available_zone = solution.available_zones[solution.available_zone_idx]

    for i, rack in enumerate(current_rack_group.racks):
        if isinstance(rack, Rack):
            continue
        bounds = rack.bounds
        upper_point = (bounds[0] + 1, bounds[3] + reference_book.roads_width)
        if not available_zone.contains_point(upper_point):
            current_rack_group.racks[i] = rack.rack_2
