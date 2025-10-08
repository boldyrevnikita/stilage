"""
Actions for rack placement in the pallet packing system.

This module contains functions for creating, positioning, and managing
racks during the pallet packing process.
"""

from src.reference_book import ReferenceBook
from src.pallet_packer.solution import Solution, ActionFailure
from src.rack import RackGroup, DoubleRack, Rack
from src.zone import OccupiedZone, SpecialRoadZone
import logging
import shapely

logger = logging.getLogger(__name__)


def place_horizontal_rack_group(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Places a horizontal rack group in the available zone.
    
    NEW BEHAVIOR:
    If protective racks exist and free strips are defined, the rack group
    is placed within the current free strip boundaries rather than at the
    zone corner.
    
    Args:
        reference_book (ReferenceBook): The reference book containing business
            logic related information.
        solution (Solution): The current solution containing available zones.
    
    Raises:
        ActionFailure: If rack group cannot be placed due to orientation
            restrictions or other constraints.
    """
    available_zone = solution.available_zones[solution.available_zone_idx]

    # Check orientation restrictions
    if available_zone.orientation == 1 and solution.is_rotated:
        raise ActionFailure("Vertical rack placement is "
                            "not allowed in this zone.")
    elif available_zone.orientation == 2 and not solution.is_rotated:
        raise ActionFailure("Horizontal rack placement is "
                            "not allowed in this zone.")

    # Determine starting position
    if solution.free_strips and solution.current_strip_idx < len(solution.free_strips):
        # NEW: Place in current free strip
        current_strip = solution.free_strips[solution.current_strip_idx]
        position = (available_zone.bounds[0], current_strip['y_min'])
        logger.info(f"[RACK_PLACEMENT] Placing rack group in free strip {solution.current_strip_idx}: "
                   f"y=[{current_strip['y_min']:.1f}, {current_strip['y_max']:.1f}]")
    else:
        # Fallback to original logic (no protective racks)
        position = available_zone.bounds[:2]
        logger.info(f"[RACK_PLACEMENT] Placing rack group at zone corner: {position}")

    rack_group = RackGroup(
        position=position,
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
    
    Tries to use the next (shorter) beam type from the available beam types list.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If no shorter beam types are available.
    """
    current_rack = solution.current_rack_group.get_current_rack()

    if current_rack.is_possible_set_next_beam_type():
        current_rack.set_next_beam_type()
        current_rack.delete_last_frame()
        current_rack.add_frame()
        logger.debug(f"[RACK_PLACEMENT] Decreased frame length to {current_rack.beam_type.length}mm")
    else:
        logger.warning("[RACK_PLACEMENT] Cannot decrease frame length further")
        raise ActionFailure("Cannot decrease frame length further.")


def place_new_frame(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Places a new frame in the current rack.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    current_rack.add_frame()
    logger.debug(f"[RACK_PLACEMENT] Added new frame. Total frames: {len(current_rack)}")


def set_next_rack_position_higher_default(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Sets the next rack position higher than the current rack position.
    
    NEW BEHAVIOR:
    Checks if the new position would exceed the current free strip boundary.
    If so, signals that we need to move to the next strip.
    
    Args:
        reference_book (ReferenceBook): The reference book.
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If the new position exceeds free strip boundaries.
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
    
    # NEW: Check if we exceeded the current free strip
    if solution.free_strips and solution.current_strip_idx < len(solution.free_strips):
        current_strip = solution.free_strips[solution.current_strip_idx]
        if nr_position[1] > current_strip['y_max']:
            logger.info(f"[RACK_PLACEMENT] Next rack position {nr_position[1]:.1f} exceeds "
                       f"strip boundary {current_strip['y_max']:.1f}")
            raise ActionFailure("Next rack position exceeds current free strip boundary")
    
    logger.debug(f"[RACK_PLACEMENT] Next rack position set to y={nr_position[1]:.1f}")


def set_next_rack_position_higher_oz(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Sets the next rack position higher than the intersected occupied zone.
    
    Args:
        reference_book (ReferenceBook): The reference book.
        solution (Solution): The current solution.
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
    logger.debug(f"[RACK_PLACEMENT] Next rack position set higher than OZ: y={nr_position[1]:.1f}")


def place_new_double_rack(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Places a new double rack in the current rack group.
    
    NEW BEHAVIOR:
    Checks that the new double rack does not intersect with any protective racks.
    
    Args:
        reference_book (ReferenceBook): The reference book.
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If the double rack would intersect with protective racks.
    """
    solution.last_intersected_vertical_road = None

    current_rack_group = solution.current_rack_group
    current_rack_group.place_double_rack()
    
    # NEW: Check intersection with protective racks
    new_rack = current_rack_group.current_rack
    for protective_rack in solution.protective_racks:
        if new_rack.intersects(protective_rack.contour):
            logger.warning("[RACK_PLACEMENT] New double rack intersects with protective rack")
            raise ActionFailure("Cannot place rack: intersects with protective rack")
    
    logger.debug(f"[RACK_PLACEMENT] Placed new double rack at {new_rack.bounds}")


def swap_double_rack_to_single_rack(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Swaps the current double rack to a single rack.
    
    Takes only the first half (rack_1) of the double rack and discards the second half.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If current rack is not a DoubleRack.
    """
    current_rack_group = solution.current_rack_group

    if not isinstance(current_rack_group.current_rack, DoubleRack):
        raise ActionFailure(
            "Current rack is not a DoubleRack, cannot swap to single rack."
        )

    current_rack_group.current_rack = current_rack_group.current_rack.rack_1
    logger.info("[RACK_PLACEMENT] Swapped double rack to single rack")


def move_current_rack_verticaly(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Moves the current rack vertically over the intersected special road zone.
    
    Args:
        reference_book (ReferenceBook): The reference book.
        solution (Solution): The current solution.
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
    logger.debug(f"[RACK_PLACEMENT] Moved rack vertically by {yoff:.1f}mm to clear road zone")


def set_current_frame_as_special(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Sets the current frame as a special frame (bridge) in the current rack.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    """
    current_rack = solution.current_rack_group.current_rack
    current_rack.make_frame_bridge(len(current_rack) - 1)
    logger.debug(f"[RACK_PLACEMENT] Set frame {len(current_rack) - 1} as bridge")


def set_default_frame_size(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Sets the default frame size for the current rack.
    
    Resets the beam type index to 0 (longest beam).
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    current_rack.set_zero_beam_type()
    logger.debug(f"[RACK_PLACEMENT] Reset to default beam type: {current_rack.beam_type.length}mm")


def delete_last_frame(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Deletes the last frame in the current rack.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    frames_before = len(current_rack)
    current_rack.delete_last_frame()
    logger.debug(f"[RACK_PLACEMENT] Deleted last frame. Frames: {frames_before} -> {len(current_rack)}")


def set_next_rack_position_righter(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Sets the next rack position to the right of the current rack.
    
    Positions the next rack to the right of the intersected forbidden zone.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    """
    current_rack_group = solution.current_rack_group
    forbidden_zone = solution.intersected_special_zone

    nr_position = solution.current_rack_group.next_rack_placement
    if isinstance(forbidden_zone, OccupiedZone):
        nr_position[0] = forbidden_zone.contour_with_clearance.bounds[2] + 1
    elif isinstance(forbidden_zone, SpecialRoadZone):
        nr_position[0] = forbidden_zone.contour.bounds[2] + 1

    current_rack_group.next_rack_placement = nr_position
    logger.debug(f"[RACK_PLACEMENT] Next rack position set righter: x={nr_position[0]:.1f}")


def create_new_rack(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Creates a new rack in the current rack group.
    
    The type of rack (single or double) is determined by solution.next_rack_type.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        TypeError: If next_rack_type is not set or is unknown.
        ActionFailure: If the new rack intersects with protective racks.
    """
    current_rack_group = solution.current_rack_group

    solution.last_intersected_vertical_road = None

    if solution.next_rack_type is Rack:
        current_rack_group.place_single_rack()
        logger.debug("[RACK_PLACEMENT] Created new single rack")
    elif solution.next_rack_type is DoubleRack:
        current_rack_group.place_double_rack()
        
        # NEW: Check intersection with protective racks
        new_rack = current_rack_group.current_rack
        for protective_rack in solution.protective_racks:
            if new_rack.intersects(protective_rack.contour):
                logger.warning("[RACK_PLACEMENT] New rack intersects with protective rack")
                raise ActionFailure("Cannot place rack: intersects with protective rack")
        
        logger.debug("[RACK_PLACEMENT] Created new double rack")
    else:
        raise TypeError("Unknown rack type in current rack group")


def assert_current_rack_is_double(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Asserts that the current rack is a double rack.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If current rack is not a DoubleRack.
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
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If cannot decrease frame length further.
    """
    current_rack = solution.current_rack_group.get_current_rack().rack_1

    if not current_rack.is_possible_set_next_beam_type():
        raise ActionFailure(
            "Cannot decrease frame length further for the first rack."
        )

    current_rack.set_next_beam_type()
    current_rack.delete_last_frame()
    current_rack.add_frame()
    logger.debug(f"[RACK_PLACEMENT] Decreased first rack frame length to {current_rack.beam_type.length}mm")


def decrease_second_rack_frame_length(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Decreases the frame length of the second rack in a double rack.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If cannot decrease frame length further.
    """
    current_rack = solution.current_rack_group.get_current_rack().rack_2

    if not current_rack.is_possible_set_next_beam_type():
        raise ActionFailure(
            "Cannot decrease frame length further for the second rack."
        )

    current_rack.set_next_beam_type()
    current_rack.delete_last_frame()
    current_rack.add_frame()
    logger.debug(f"[RACK_PLACEMENT] Decreased second rack frame length to {current_rack.beam_type.length}mm")


def disable_last_frame(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Disables the last frame in the current rack.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    current_rack.disable_frame(len(current_rack) - 1)
    logger.debug(f"[RACK_PLACEMENT] Disabled frame {len(current_rack) - 1}")


def disable_last_frame_for_first_rack(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Disables the last frame in the first rack of a double rack.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    """
    current_rack = solution.current_rack_group.get_current_rack().rack_1
    current_rack.disable_frame(len(current_rack) - 1)
    logger.debug(f"[RACK_PLACEMENT] Disabled frame {len(current_rack) - 1} in first rack")


def disable_last_frame_for_second_rack(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Disables the last frame in the second rack of a double rack.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    """
    current_rack = solution.current_rack_group.get_current_rack().rack_2
    current_rack.disable_frame(len(current_rack) - 1)
    logger.debug(f"[RACK_PLACEMENT] Disabled frame {len(current_rack) - 1} in second rack")


def save_rack(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Saves the current rack in the current rack group.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    """
    current_rack = solution.current_rack_group.get_current_rack()
    if len(current_rack) == 0:
        logger.warning("[RACK_PLACEMENT] Attempted to save empty rack, skipping")
        return
    solution.current_rack_group.commit_current_rack()
    logger.info(f"[RACK_PLACEMENT] Saved rack with {len(current_rack)} frames")


def save_rack_group(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Saves the current rack group in the solution.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If rack group is empty.
    """
    if len(solution.current_rack_group.racks) == 0:
        raise ActionFailure("Cannot save an empty rack group.")

    solution.saved_rack_groups.append(
        solution.current_rack_group
    )

    solution.max_intersected_oz_y = None
    
    total_racks = len(solution.current_rack_group.racks)
    logger.info(f"[RACK_PLACEMENT] Saved rack group with {total_racks} racks")


def set_next_rack_type_single(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Sets the next rack type to a single rack.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    """
    solution.next_rack_type = Rack
    logger.debug("[RACK_PLACEMENT] Next rack type set to: Single")


def set_next_rack_type_double(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Sets the next rack type to a double rack.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    """
    solution.next_rack_type = DoubleRack
    logger.debug("[RACK_PLACEMENT] Next rack type set to: Double")


def fill_with_frames(
    _: ReferenceBook, 
    solution: Solution
) -> None:
    """Fills the current rack with frames until it reaches the maximum
    number of frames that can fit in the available zone.
    
    NEW BEHAVIOR:
    If working within a free strip, respects the strip's right boundary.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    
    Raises:
        ActionFailure: If rack overflows zone during fill.
    """
    logger.info("[RACK_PLACEMENT] Filling rack with frames")
    
    az = solution.available_zones[solution.available_zone_idx]
    rack = solution.current_rack_group.current_rack

    section_len = rack.beam_type.length + rack.upright_type.width
    
    # Determine maximum length based on zone or strip
    if solution.free_strips and solution.current_strip_idx < len(solution.free_strips):
        # NEW: Use current strip boundary
        current_strip = solution.free_strips[solution.current_strip_idx]
        # Strips are defined by Y boundaries, X is still zone-wide
        max_len_bbox = az.contour.bounds[2] - rack.contour.bounds[2]
        logger.debug(f"[RACK_PLACEMENT] Filling within strip {solution.current_strip_idx}")
    else:
        # Original behavior
        max_len_bbox = az.contour.bounds[2] - rack.contour.bounds[2]
    
    frames_count = max(0, int(max_len_bbox // section_len))

    logger.info(f"[RACK_PLACEMENT] Before fill: frames={len(rack)}, "
                f"section_len={section_len:.1f}, max_len={max_len_bbox:.1f}, "
                f"adding={frames_count}")

    rack.add_multiple_frames(frames_count)

    # Verify rack fits in zone
    inside = shapely.covers(az.contour, rack.contour)
    logger.info(f"[RACK_PLACEMENT] After fill: frames={len(rack)}, inside_zone={inside}")

    if not inside:
        # Remove frames until it fits
        overflow_count = 0
        while not shapely.covers(az.contour, rack.contour) and len(rack) > 0:
            rack.delete_last_frame()
            overflow_count += 1
        logger.warning(f"[RACK_PLACEMENT] Overflow detected, removed {overflow_count} frames")
        raise ActionFailure("Rack overflowed zone during fill_with_frames")


def delete_excess_frames_pl(
    _: ReferenceBook,
    solution: Solution
) -> None:
    """Deletes excess frames in the current rack based on maximum cargo quantity.
    
    Removes frames from the end of the rack until the rack's capacity
    matches the remaining unplaced pallets.
    
    Args:
        _ (ReferenceBook): The reference book (not used).
        solution (Solution): The current solution.
    """
    current_cargo_max_quantity = (
        solution.pallets[solution.pallet_idx].cargo.quantity)
    cargo_id = solution.pallets[solution.pallet_idx].cargo.cargo_type_id

    unplaced_cargo_left = (current_cargo_max_quantity
                           - solution.pallet_count[cargo_id])

    current_rack = solution.current_rack_group.get_current_rack()
    cargo_capacity = current_rack.calculate_pallet_capacity()
    
    frames_deleted = 0
    if unplaced_cargo_left > 0 and len(current_rack) > 0:
        while unplaced_cargo_left < cargo_capacity:
            cargo_capacity -= (
                current_rack.calculate_pallet_capacity_in_ith_frame(
                    len(current_rack) - 1))
            current_rack.delete_last_frame()
            frames_deleted += 1
            if len(current_rack) == 0:
                break
    
    if frames_deleted > 0:
        logger.debug(f"[RACK_PLACEMENT] Deleted {frames_deleted} excess frames due to pallet limit")


def delete_excess_frames_oz(
    reference_book: ReferenceBook,
    solution: Solution
) -> None:
    """Deletes excess frames in the current rack based on the
    maximum number of frames that can fit before the occupied zone.
    
    Args:
        reference_book (ReferenceBook): The reference book.
        solution (Solution): The current solution.
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
    
    frames_deleted = 0
    while len(current_rack) > frames_count:
        current_rack.delete_last_frame()
        frames_deleted += 1
    
    if frames_deleted > 0:
        logger.debug(f"[RACK_PLACEMENT] Deleted {frames_deleted} excess frames due to occupied zone")