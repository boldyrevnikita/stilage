from src.network.output_schema import ModelOutput, RackOutput
from src.pallet_packer.solution import Solution
from src.rack import DoubleRack
from src.reference_book import ReferenceBook
from collections import defaultdict


def generate_output(solution: Solution,
                    reference_book: ReferenceBook,
                    task_id: str,
                    warnings_and_errors: str,
                    success_predict: bool) -> ModelOutput:
    racks = defaultdict(list)
    for rack_group in solution.saved_rack_groups:
        for rack in rack_group.racks:
            cargo_id = str(rack.pallet.cargo.cargo_type_id)
            boundary = [(int(x), int(y))
                        for x, y in zip(*rack.contour.exterior.xy)]
            sections_in_length = len(rack)
            sections_in_width = 1 if not isinstance(rack, DoubleRack) else 2
            sections_in_height = rack.max_shelfs
            sections_in_height_special = rack.max_shelfs_bridge
            orientation = rack.orientation

            # substract upright_width_eps from upright_width
            upright_section = rack.upright_type.upright_section
            upright_section = (upright_section[0]
                               - reference_book.upright_width_eps,
                               upright_section[1], upright_section[2])

            beam_section = rack.beam_type.beam_section
            pallet_size = (rack.pallet.pallet_type.width,
                           rack.pallet.pallet_type.length)

            if isinstance(rack, DoubleRack):
                subracks2handle = [rack.rack_1, rack.rack_2]
            else:
                subracks2handle = [rack]

            units = []
            special_units = []
            beam_lengths = []

            for subrack in subracks2handle:
                units.append([beam.max_shelf_load_capacity_pallets
                              for beam in subrack.beams])
                special_units.append([status.value
                                      for status in subrack.deck_status])
                beam_lengths.append([beam.length for beam in subrack.beams])

            rack_distance = (rack.rack_distance if isinstance(rack, DoubleRack)
                             else None)

            racks[cargo_id].append(
                RackOutput(
                    boundary=boundary,
                    sections_in_length=sections_in_length,
                    sections_in_width=sections_in_width,
                    sections_in_height=sections_in_height,
                    sections_in_height_special=sections_in_height_special,
                    pallet_with_cargo_height=rack.pallet.height,
                    beam_height=rack.beam_type.height,
                    pallet_with_cargo_extra_height=(
                        rack_group.pallet_extra_space),
                    frame_height_eps=rack_group.frame_height_eps,
                    metric_frame_height=(
                        rack_group.calculate_max_frame_height()),
                    metric_special_frame_height=(
                        rack_group.calculate_max_frame_height()),
                    orientation=orientation,
                    upright_section=upright_section,
                    beam_section=beam_section,
                    pallet_size=pallet_size,
                    units=units,
                    special_units=special_units,
                    beam_lengths=beam_lengths,
                    rack_distance=rack_distance
                )
            )

    return ModelOutput(
        task_id=task_id,
        racks=dict(racks),
        warnings_and_errors=warnings_and_errors,
        success_predict=success_predict
    )
