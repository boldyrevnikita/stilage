from src.reference_book import ReferenceBook
from src.pallet_packer.solution import Solution, ActionStatus
import shapely


def rotate_everything_90_clockwise(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Rotates the available zone's contour 90 degrees clockwise.

    Args:
        reference_book (ReferenceBook): The reference book containin business
            logic related information.
        solution (Solution): The current solution containing available zones.
    """
    available_zone = solution.available_zones[solution.available_zone_idx]
    solution.rot_point = available_zone.bounds[:2]
    angle = 90

    available_zone.rotate(solution.rot_point, angle)
    for occupied_zone in solution.current_occupied_zones:
        occupied_zone.rotate(solution.rot_point, angle)
    for road_zone in solution.current_road_zones:
        road_zone.rotate(solution.rot_point, angle)

    solution.action_status = ActionStatus.SUCCESS


def rotate_evetything_90_counterclockwise(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Rotates the available zone's contour 90 degrees counterclockwise.

    Args:
        reference_book (ReferenceBook): The reference book containing business
            logic related information.
        solution (Solution): The current solution containing available zones.
    """
    available_zone = solution.available_zones[solution.available_zone_idx]
    angle = -90

    available_zone.rotate(solution.rot_point, angle)
    for occupied_zone in solution.current_occupied_zones:
        occupied_zone.rotate(solution.rot_point, angle)
    for road_zone in solution.current_road_zones:
        road_zone.rotate(solution.rot_point, angle)
    solution.current_rack_group.rotate(solution.rot_point, angle)


def set_next_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Sets the next available zone as the current one.
    Args:
        reference_book (ReferenceBook): The reference book containing business
            logic related information.
        solution (Solution): The current solution containing available zones.
    """
    if solution.available_zone_idx < len(solution.available_zones) - 1:
        solution.available_zone_idx += 1
        solution.action_status = ActionStatus.SUCCESS
    else:
        solution.action_status = ActionStatus.FAILED


def set_zero_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Sets the current available zone index to zero and moves to the next pallet.

    Args:
        reference_book (ReferenceBook): The reference book containing business
            logic related information.
        solution (Solution): The current solution containing available zones.
    """
    solution.available_zone_idx = 0
    solution.action_status = ActionStatus.SUCCESS


def check_if_current_rack_fits_available_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Checks if the current rack fits into the available zone.

    Args:
        reference_book (ReferenceBook): The reference book containing business
            logic related information.
        solution (Solution): The current solution containing available zones.
    """
    available_zone = solution.available_zones[solution.available_zone_idx]
    current_rack = solution.current_rack_group.get_current_rack()

    if not shapely.contains(
            available_zone.contour, current_rack.contour):
        solution.action_status = ActionStatus.FAILED
    else:
        solution.action_status = ActionStatus.SUCCESS


def split_available_zone(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """
    Splits the available zone into two parts.

    Args:
        reference_book (ReferenceBook): The reference book containing business
            logic related information.
        solution (Solution): The current solution containing available zones.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    available_zone = solution.available_zones[solution.available_zone_idx]
    new_zones = available_zone.split_zone(current_rack.bounds[2:])
    solution.available_zones.pop(solution.available_zone_idx)
    solution.available_zones.extend(new_zones)

    solution.action_status = ActionStatus.SUCCESS


def check_if_current_rack_intersecting_occupied_zones(
    _: ReferenceBook,
    solution: Solution
) -> None:
    current_rack = solution.current_rack_group.get_current_rack()

    for occupied_zone in solution.current_occupied_zones:
        if (shapely.intersects(
                occupied_zone.contour_with_clearance, current_rack.contour)
            or shapely.intersects(
                occupied_zone.contour_with_roads_width, current_rack.contour)):
            solution.intersected_special_zone = occupied_zone
            solution.action_status = ActionStatus.FAILED
            return

    solution.action_status = ActionStatus.SUCCESS


def check_if_current_rack_intersecting_road_zones(
    _: ReferenceBook,
    solution: Solution
) -> None:
    сurrent_rack = solution.current_rack_group.get_current_rack()

    for road_zone in solution.current_road_zones:
        if shapely.intersects(
                road_zone.contour, сurrent_rack.contour):
            solution.intersected_special_zone = road_zone
            solution.action_status = ActionStatus.FAILED
            return

    solution.action_status = ActionStatus.SUCCESS


def check_if_intersected_road_horizontal(
    _: ReferenceBook,
    solution: Solution
) -> None:
    if solution.intersected_special_zone.is_horizontal():
        solution.action_status = ActionStatus.SUCCESS
    else:
        solution.action_status = ActionStatus.FAILED


def check_if_current_shelf_length_enough_for_road(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Checks if the current shelf length is enough for the road width.

    Args:
        reference_book (ReferenceBook): The reference book containing business
            logic related information.
        solution (Solution): The current solution containing available zones.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    current_road = solution.intersected_special_zone

    if current_rack.get_current_shelf_length() >= current_road.width:
        solution.action_status = ActionStatus.SUCCESS
    else:
        solution.action_status = ActionStatus.FAILED


def check_if_both_racks_intersecting_occupied_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    current_rack = solution.current_rack_group.get_current_rack()
    current_occupied_zone = solution.intersected_special_zone

    is_first_rack_intersecting = (
        shapely.intersects(
            current_occupied_zone.contour_with_clearance,
            current_rack.rack_1.contour))
    is_second_rack_intersecting = (
        shapely.intersects(
            current_occupied_zone.contour_with_clearance,
            current_rack.rack_2.contour))

    if is_first_rack_intersecting and is_second_rack_intersecting:
        solution.action_status = ActionStatus.SUCCESS
    else:
        solution.action_status = ActionStatus.FAILED


def check_if_first_rack_intersecting_occupied_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    is_first_rack_intersecting = (
        shapely.intersects(
            solution.current_occupied_zones[0].contour_with_clearance,
            solution.current_rack_group.get_current_rack().rack_1.contour))
    if is_first_rack_intersecting:
        solution.action_status = ActionStatus.SUCCESS
    else:
        solution.action_status = ActionStatus.FAILED


def check_if_second_rack_intersecting_occupied_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    is_second_rack_intersecting = (
        shapely.intersects(
            solution.current_occupied_zones[0].contour_with_clearance,
            solution.current_rack_group.get_current_rack().rack_2.contour))
    if is_second_rack_intersecting:
        solution.action_status = ActionStatus.SUCCESS
    else:
        solution.action_status = ActionStatus.FAILED


def check_if_last_rack_shelf_covers_occupied_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    current_rack = solution.current_rack_group.get_current_rack()
    current_occupied_zone = solution.intersected_special_zone

    is_last_shelf_covers = (
        shapely.covers(
            current_rack.last_shelf_contour,
            current_occupied_zone.contour))

    if is_last_shelf_covers:
        solution.action_status = ActionStatus.SUCCESS
    else:
        solution.action_status = ActionStatus.FAILED


def check_if_last_shelf_of_first_rack_covers_occupied_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    current_rack = solution.current_rack_group.get_current_rack()
    current_occupied_zone = solution.intersected_special_zone

    is_last_shelf_covers = (
        shapely.covers(
            current_rack.rack_1.last_shelf_contour,
            current_occupied_zone.contour))

    if is_last_shelf_covers:
        solution.action_status = ActionStatus.SUCCESS
    else:
        solution.action_status = ActionStatus.FAILED


def check_if_last_shelf_of_second_rack_covers_occupied_zone(
    _: ReferenceBook,
    solution: Solution
) -> None:
    current_rack = solution.current_rack_group.get_current_rack()
    current_occupied_zone = solution.intersected_special_zone

    is_last_shelf_covers = (
        shapely.covers(
            current_rack.rack_2.last_shelf_contour,
            current_occupied_zone.contour))

    if is_last_shelf_covers:
        solution.action_status = ActionStatus.SUCCESS
    else:
        solution.action_status = ActionStatus.FAILED


def get_corresponding_occupied_zones_and_road_zones(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Retrieves the corresponding occupied zones and road zones for the current
    available zone.

    Args:
        reference_book (ReferenceBook): The reference book containing business
            logic related information.
        solution (Solution): The current solution containing available zones.
    """
    available_zone = solution.available_zones[solution.available_zone_idx]

    for occupied_zone in solution.occupied_zones:
        is_intersects_with_clearance = (
            shapely.intersects(
                occupied_zone.contour_with_clearance, available_zone.contour))
        is_intersects_with_roads_width = (
            shapely.intersects(
                occupied_zone.contour_with_roads_width, available_zone.contour)
            )

        if (is_intersects_with_clearance or
                is_intersects_with_roads_width):
            solution.current_occupied_zones.append(occupied_zone)

    for road_zone in solution.road_zones:
        if shapely.intersects(
                road_zone.contour, available_zone.contour):
            solution.current_road_zones.append(road_zone)


def sort_available_zones_by_area_and_height(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """
    Sorts the current occupied zones and road zones by area and height.
    Args:
        reference_book (ReferenceBook): The reference book containing business
            logic related information.
        solution (Solution): The current solution containing available zones.
    """
    solution.available_zones.sort(
        key=lambda x: (x.area, x.height))
    solution.action_status = ActionStatus.SUCCESS
