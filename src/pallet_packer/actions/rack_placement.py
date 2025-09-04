from src.reference_book import ReferenceBook
from src.pallet_packer.solution import Solution, ActionFailure
from src.rack import RackGroup, DoubleRack, Rack
from src.zone import OccupiedZone, SpecialRoadZone


def place_horizontal_rack_group(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Places a horizontal rack group in the available zone.

    Args:
        reference_book (ReferenceBook): The reference book containing business
            logic related information.
        solution (Solution): The current solution containing available zones.
    """
    available_zone = solution.available_zones[solution.available_zone_idx]

    if available_zone.orientation == 1 and solution.is_rotated:
        raise ActionFailure("Vertical rack placement is "
                            "not allowed in this zone.")
    elif available_zone.orientation == 2 and not solution.is_rotated:
        raise ActionFailure("Horizontal rack placement is "
                            "not allowed in this zone.")

    rack_group = RackGroup(
        position=available_zone.bounds[:2],
        roads_width=reference_book.roads_width,
        beam_types=solution.beam_types,
        upright_type=solution.upright_type,
        pallet=solution.pallets[solution.pallet_idx],
        max_shelfs=solution.max_shelfs,
        max_shelfs_bridge=solution.max_shelfs_bridge,
        pallet_extra_space=solution.pallet_extra_space,
        frame_height_eps=reference_book.frame_height_eps
    )

    solution.current_rack_group = rack_group


def decrease_current_frame_length(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Decreases the length of the current frame in the current rack.
    """
    current_rack = solution.current_rack_group.get_current_rack()

    if current_rack.is_possible_set_next_beam_type():
        current_rack.set_next_beam_type()
        current_rack.delete_last_frame()
        current_rack.add_frame()
    else:
        raise ActionFailure("Cannot decrease frame length further.")


def place_new_frame(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Places a new frame in the current rack.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    current_rack.add_frame()


def set_next_rack_position_higher_default(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Sets the next rack position higher than the
    current rack position.
    """
    rg_position = solution.current_rack_group.position
    nr_position = solution.current_rack_group.next_rack_placement
    current_rack = solution.current_rack_group.current_rack

    nr_position[0] = rg_position[0]
    nr_position[1] = current_rack.bounds[3] + reference_book.roads_width

    if solution.current_rack_group.racks:
        current_rack_group = solution.current_rack_group
        nr_position[1] = max(nr_position[1],
                             current_rack_group.bounds[3]
                             + reference_book.roads_width)

    if solution.max_intersected_oz_y is not None:
        nr_position[1] = max(nr_position[1],
                             solution.max_intersected_oz_y
                             + reference_book.roads_width)
        solution.max_intersected_oz_y = None

    solution.current_rack_group.next_rack_placement = nr_position


def set_next_rack_position_higher_oz(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """
    Sets the next rack position higher than the intersected occupied zone.
    """
    rg_position = solution.current_rack_group.position
    nr_position = solution.current_rack_group.next_rack_placement
    occupied_zone = solution.intersected_special_zone
    current_rack = solution.current_rack_group.current_rack

    nr_position[0] = rg_position[0]
    if len(solution.current_rack_group.racks) > 0:
        nr_position[1] = max(occupied_zone.contour.bounds[3]
                             + reference_book.roads_width + 1,
                             current_rack.bounds[3]
                             + reference_book.roads_width)
    else:
        nr_position[1] = occupied_zone.contour_with_roads_width.bounds[3] + 1

    solution.current_rack_group.next_rack_placement = nr_position


def place_new_double_rack(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Places a new double rack in the current rack group.
    """
    solution.last_intersected_vertical_road = None

    current_rack_group = solution.current_rack_group
    current_rack_group.place_double_rack()


def swap_double_rack_to_single_rack(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Swaps the current double rack to a single rack.
    """
    current_rack_group = solution.current_rack_group

    if not isinstance(current_rack_group.current_rack, DoubleRack):
        raise ActionFailure(
            "Current rack is not a DoubleRack, cannot swap to single rack."
        )

    current_rack_group.current_rack = current_rack_group.current_rack.rack_1


def move_current_rack_verticaly(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Moves the current rack vertically over the intersected
    special road zone.
    """
    road_zone = solution.intersected_special_zone
    current_rack_group = solution.current_rack_group
    current_rack = solution.current_rack_group.current_rack

    special_road_width = road_zone.width

    if current_rack_group.racks:
        usual_roads_width = reference_book.roads_width
        special_road_width -= usual_roads_width
        special_road_width = max(0, special_road_width)

    xoff, yoff = 0, special_road_width + 1
    current_rack.translate(xoff, yoff)
    current_rack_group.next_rack_placement = [
        current_rack_group.next_rack_placement[0],
        current_rack_group.next_rack_placement[1] + yoff
    ]

    solution.current_road_zones.remove(road_zone)


def set_current_frame_as_special(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Sets the current frame as a special frame in the current rack."""
    current_rack = solution.current_rack_group.current_rack
    current_rack.make_frame_bridge(
        len(current_rack) - 1
    )


def set_default_frame_size(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Sets the default frame size for the current rack."""
    current_rack = solution.current_rack_group.get_current_rack()
    current_rack.set_zero_beam_type()


def delete_last_frame(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Deletes the last frame in the current rack."""
    current_rack = solution.current_rack_group.get_current_rack()
    current_rack.delete_last_frame()


def set_next_rack_position_righter(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Sets the next rack position to the right of the current rack.
    """
    current_rack_group = solution.current_rack_group
    forbidden_zone = solution.intersected_special_zone

    nr_position = solution.current_rack_group.next_rack_placement
    if isinstance(forbidden_zone, OccupiedZone):
        nr_position[0] = forbidden_zone.contour_with_clearance.bounds[2] + 1
    elif isinstance(forbidden_zone, SpecialRoadZone):
        nr_position[0] = forbidden_zone.contour.bounds[2] + 1

    current_rack_group.next_rack_placement = nr_position


def create_new_rack(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Creates a new rack in the current rack group.
    """
    current_rack_group = solution.current_rack_group

    solution.last_intersected_vertical_road = None

    if solution.next_rack_type is Rack:
        current_rack_group.place_single_rack()
    elif solution.next_rack_type is DoubleRack:
        current_rack_group.place_double_rack()
    else:
        raise TypeError("Unknown rack type in current rack group")


def assert_current_rack_is_double(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that the current rack is a double rack.
    """
    current_rack = solution.current_rack_group.get_current_rack()

    if not isinstance(current_rack, DoubleRack):
        raise ActionFailure(
            "Current rack is not a DoubleRack, cannot perform this action."
        )


def decrease_first_rack_frame_length(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Decreases the frame length of the first rack in a double rack.
    """
    current_rack = solution.current_rack_group.get_current_rack().rack_1

    if not current_rack.is_possible_set_next_beam_type():
        raise ActionFailure(
            "Cannot decrease frame length further for the first rack."
        )

    current_rack.set_next_beam_type()
    current_rack.delete_last_frame()
    current_rack.add_frame()


def decrease_second_rack_frame_length(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Decreases the frame length of the second rack in a double rack.
    """
    current_rack = solution.current_rack_group.get_current_rack().rack_2

    if not current_rack.is_possible_set_next_beam_type():
        raise ActionFailure(
            "Cannot decrease frame length further for the second rack."
        )

    current_rack.set_next_beam_type()
    current_rack.delete_last_frame()
    current_rack.add_frame()


def disable_last_frame(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Disables the last frame in the current rack."""
    current_rack = solution.current_rack_group.get_current_rack()
    current_rack.disable_frame(len(current_rack) - 1)


def disable_last_frame_for_first_rack(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Disables the last frame in the first rack of a double rack."""
    current_rack = solution.current_rack_group.get_current_rack().rack_1
    current_rack.disable_frame(len(current_rack) - 1)


def disable_last_frame_for_second_rack(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Disables the last frame in the second rack of a double rack."""
    current_rack = solution.current_rack_group.get_current_rack().rack_2
    current_rack.disable_frame(len(current_rack) - 1)


def save_rack(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Saves the current rack in the current rack group."""
    current_rack = solution.current_rack_group.get_current_rack()
    if len(current_rack) == 0:
        return
    solution.current_rack_group.commit_current_rack()


def save_rack_group(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Saves the current rack group in the solution.
    """
    if len(solution.current_rack_group.racks) == 0:
        raise ActionFailure("Cannot save an empty rack group.")

    solution.saved_rack_groups.append(
        solution.current_rack_group
    )

    solution.max_intersected_oz_y = None


def set_next_rack_type_single(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Sets the next rack type to a single rack.
    """
    solution.next_rack_type = Rack


def set_next_rack_type_double(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Sets the next rack type to a double rack.
    """
    solution.next_rack_type = DoubleRack


def fill_with_frames(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Fills the current rack with frames until it reaches the maximum
    number of frames that can fit in the available zone.
    """
    available_zone = solution.available_zones[solution.available_zone_idx]
    current_rack = solution.current_rack_group.current_rack

    section_length = (current_rack.beam_type.length
                      + current_rack.upright_type.width)
    max_available_length = (available_zone.contour.bounds[2]
                            - current_rack.contour.bounds[2])
    frames_count = int(max_available_length // section_length)

    current_rack.add_multiple_frames(frames_count)


def delete_excess_frames_pl(
    _: ReferenceBook,
    solution: Solution
):
    """Deletes excess frames in the current rack based on maximum
    cargo quantity.
    """
    current_cargo_max_quantity = (
        solution.pallets[solution.pallet_idx].cargo.quantity)
    cargo_id = solution.pallets[solution.pallet_idx].cargo.cargo_type_id

    unplaced_cargo_left = (current_cargo_max_quantity
                           - solution.pallet_count[cargo_id])

    current_rack = solution.current_rack_group.get_current_rack()
    cargo_capacity = current_rack.calculate_pallet_capacity()

    if unplaced_cargo_left > 0 and len(current_rack) > 0:
        while unplaced_cargo_left < cargo_capacity:
            cargo_capacity -= (
                current_rack.calculate_pallet_capacity_in_ith_frame(
                    len(current_rack) - 1))
            current_rack.delete_last_frame()
            if len(current_rack) == 0:
                break


def delete_excess_frames_oz(
    reference_book: ReferenceBook,
    solution: Solution
):
    """Deletes excess frames in the current rack based on the
    maximum number of frames that can fit before the occupied zone.
    """
    current_occupied_zone = solution.intersected_special_zone
    current_rack = solution.current_rack_group.get_current_rack()

    section_length = (current_rack.beam_type.length
                      + current_rack.upright_type.width)
    occupied_zone_with_roads = current_occupied_zone.contour.buffer(
        reference_book.roads_width, join_style=2
    )

    max_available_length = max(0, (
        occupied_zone_with_roads.bounds[0] -
        current_rack.contour.bounds[0]
    ))

    frames_count = int(max_available_length // section_length)

    while len(current_rack) > frames_count:
        current_rack.delete_last_frame()
