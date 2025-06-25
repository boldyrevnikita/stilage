from src.reference_book import ReferenceBook
from src.pallet_packer.solution import Solution, ActionFailure
from src.rack import RackGroup, DoubleRack, Rack


def place_horizontal_rack_group(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    available_zone = solution.available_zones[solution.available_zone_idx]

    rack_group = RackGroup(
        position=available_zone.bounds[:2],
        roads_width=reference_book.roads_width,
        beam_types=solution.beam_types,
        upright_type=solution.upright_type,
        pallet=solution.pallets[solution.pallet_idx],
        max_shelfs=solution.max_shelfs,
    )

    solution.current_rack_group = rack_group


def decrease_current_frame_length(
    _: ReferenceBook,
    solution: Solution
) -> None:
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
    current_rack = solution.current_rack_group.get_current_rack()
    current_rack.add_frame()


def set_next_rack_position_higher_default(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    rg_position = solution.current_rack_group.position
    nr_position = solution.current_rack_group.next_rack_placement
    current_rack = solution.current_rack_group.current_rack

    nr_position[0] = rg_position[0]
    nr_position[1] = current_rack.bounds[3] + reference_book.roads_width

    solution.current_rack_group.next_rack_placement = nr_position


def set_next_rack_position_higher_oz(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    rg_position = solution.current_rack_group.position
    nr_position = solution.current_rack_group.next_rack_placement
    ocupied_zone = solution.intersected_special_zone
    current_rack = solution.current_rack_group.current_rack

    nr_position[0] = rg_position[0]
    nr_position[1] = max(ocupied_zone.contour_with_clearance.bounds[3],
                         current_rack.bounds[3] + reference_book.roads_width)

    solution.current_rack_group.next_rack_placement = nr_position


def place_new_double_rack(
    _: ReferenceBook,
    solution: Solution
) -> None:
    current_rack_group = solution.current_rack_group
    current_rack_group.place_double_rack()


def swap_double_rack_to_single_rack(
    _: ReferenceBook,
    solution: Solution
) -> None:
    current_rack_group = solution.current_rack_group

    if not isinstance(current_rack_group.current_rack, DoubleRack):
        raise ActionFailure(
            "Current rack is not a DoubleRack, cannot swap to single rack."
        )

    current_rack_group.current_rack = current_rack_group.current_rack.rack_1


def move_current_rack_verticaly(
    _: ReferenceBook,
    solution: Solution
) -> None:
    road_zone = solution.intersected_special_zone
    current_rack = solution.current_rack_group.current_rack

    rack_bounds = current_rack.contour.bounds
    road_bounds = road_zone.bounds

    xoff, yoff = 0, road_bounds[3] - rack_bounds[1] + 1

    current_rack.translate(xoff, yoff)


def set_current_frame_as_special(
    _: ReferenceBook,
    solution: Solution
) -> None:
    current_rack = solution.current_rack_group.current_rack
    current_rack.made_frame_bridge(
        len(current_rack) - 1
    )


def set_default_frame_size(
    _: ReferenceBook,
    solution: Solution
) -> None:
    current_rack = solution.current_rack_group.get_current_rack()
    current_rack.set_zero_beam_type()


def delete_last_frame(
    _: ReferenceBook,
    solution: Solution
) -> None:
    current_rack = solution.current_rack_group.get_current_rack()
    current_rack.delete_last_frame()


def set_next_rack_position_righter(
    _: ReferenceBook,
    solution: Solution
) -> None:
    current_rack_group = solution.current_rack_group
    forbidden_zone = solution.intersected_special_zone

    nr_position = solution.current_rack_group.next_rack_placement
    nr_position[0] = forbidden_zone.contour_with_clearance.bounds[2]

    current_rack_group.next_rack_placement = nr_position


def create_new_rack(
    _: ReferenceBook,
    solution: Solution
) -> None:
    current_rack_group = solution.current_rack_group
    current_rack = current_rack_group.get_current_rack()

    if type(current_rack) is Rack:
        current_rack_group.place_single_rack()
    elif type(current_rack) is DoubleRack:
        current_rack_group.place_double_rack()
    else:
        raise TypeError("Unknown rack type in current rack group")


def assert_current_rack_is_double(
    _: ReferenceBook,
    solution: Solution
) -> None:
    current_rack = solution.current_rack_group.get_current_rack()

    if not isinstance(current_rack, DoubleRack):
        raise ActionFailure(
            "Current rack is not a DoubleRack, cannot perform this action."
        )


def decrease_first_rack_frame_length(
    _: ReferenceBook,
    solution: Solution
) -> None:
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
    current_rack = solution.current_rack_group.get_current_rack()
    current_rack.disable_frame(len(current_rack) - 1)


def disable_last_frame_for_first_rack(
    _: ReferenceBook,
    solution: Solution
) -> None:
    current_rack = solution.current_rack_group.get_current_rack().rack_1
    current_rack.disable_frame(len(current_rack) - 1)


def disable_last_frame_for_second_rack(
    _: ReferenceBook,
    solution: Solution
) -> None:
    current_rack = solution.current_rack_group.get_current_rack().rack_2
    current_rack.disable_frame(len(current_rack) - 1)


def save_rack(
    _: ReferenceBook,
    solution: Solution
) -> None:
    current_rack = solution.current_rack_group.get_current_rack()
    if len(current_rack) == 0:
        return
    solution.current_rack_group.commit_current_rack()


def save_rack_group(
    _: ReferenceBook,
    solution: Solution
) -> None:
    if len(solution.current_rack_group.racks) == 0:
        raise ActionFailure("Cannot save an empty rack group.")

    solution.saved_rack_groups.append(
        solution.current_rack_group
    )
