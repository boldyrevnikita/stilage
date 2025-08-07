from src.pallet import PalletType
from src.rack import BeamType, UprightType


class ReferenceBook:
    """Reference book containing business logic related information
    and constants."""

    def __init__(self):
        self.upright_width_eps = 8.0

        self.pallet_types = {
            1: PalletType(
                pallet_type_id=1,
                width=800.0,
                length=1200.0,
                height=145.0,
                weight=25.0
            ),
            2: PalletType(
                pallet_type_id=2,
                width=1000.0,
                length=1200.0,
                height=145.0,
                weight=30.0
            )
        }
        self.beam_types: dict[int, list[BeamType]] = self.__init_beam_types()
        self.upright_types: list[UprightType] = self.__init_upright_types()

        self.frame_height2pallet_extra_space = [
            (3000.0, 75.0),
            (9000.0, 125.0),
            (12000.0, 150.0),
        ]

        self.roads_width = 3000.0
        self.roads_height = 5000.0
        self.forbidden_zone_clearance = 250.0
        self.frame_height_eps = 100.0
        self.max_double_rack_internal_distance = 1000.0

    def __init_beam_types(self) -> dict[int, list[BeamType]]:
        """Initializes the beam types with their properties
        and returns a dictionary of beam types categorized by rack type

        Returns:
            dict[int, list[BeamType]]: Dictionary of beam types categorized by
            rack type.
        """
        beam_lengths = [1850.0, 2300.0, 2700.0,
                        3300.0, 3600.0]
        beam_sections = [(85.0, 1.5), (100.0, 1.5),
                         (110.0, 1.5), (125.0, 1.5),
                         (140.0, 1.5), (160.0, 1.5),
                         (160.0, 2.0)]
        beam_max_shelf_load_capacity_kg_table = [
            [2200.0, 1700.0, 1300.0, 800.0, 800.0],
            [3600.0, 2600.0, 2200.0, 1400.0, 1100.0],
            [3700.0, 3000.0, 2500.0, 1700.0, 1400.0],
            [3700.0, 3500.0, 3000.0, 2000.0, 1700.0],
            [5000.0, 4200.0, 3800.0, 2700.0, 2100.0],
            [5500.0, 5000.0, 4300.0, 3400.0, 2800.0],
            [6000.0, 5300.0, 4800.0, 4200.0, 4000.0]
        ]
        beam_max_rack_load_capacity_pallets = [2, 2, 3, 3, 4]

        pallet_types2beam_types = {
            1: [4, 2, 0],
            2: [3, 1]
        }

        beam_types = {
            1: [],
            2: [],
        }
        for i in range(len(beam_lengths)):
            for j in range(len(beam_sections)):
                beam_type_id = i * 100 + j

                rack_type = -1
                if i in pallet_types2beam_types[1]:
                    rack_type = 1
                elif i in pallet_types2beam_types[2]:
                    rack_type = 2

                beam_types[rack_type].append(
                    BeamType(
                        beam_type_id=beam_type_id,
                        length=beam_lengths[i],
                        beam_section=beam_sections[j],
                        max_shelf_load_capacity_kg=(
                            beam_max_shelf_load_capacity_kg_table[j][i]),
                        max_shelf_load_capacity_pallets=(
                            beam_max_rack_load_capacity_pallets[i])
                    )
                )
        for key in beam_types.keys():
            beam_types[key].sort(
                key=lambda x: (-x.length,
                               x.max_shelf_load_capacity_kg))

        return beam_types

    def __init_upright_types(self) -> list[UprightType]:
        """Initializes the upright types with their properties
        and returns a list of upright types.
        Returns:
            list[UprightType]: List of upright types.
        """
        upright_max_shelf_height = [750.0, 1000.0, 1250.0,
                                    1500.0, 1750.0, 2000.0]
        upright_sections = [(80.0, 75.0, 2.0), (100.0, 75.0, 2.0),
                            (120.0, 75.0, 2.0), (140.0, 75.0, 2.0),
                            (120.0, 100.0, 2.0), (120.0, 75.0, 2.5),
                            (140.0, 75.0, 2.5), (120.0, 100.0, 2.5),
                            (140.0, 100.0, 2.5), (160.0, 100.0, 2.5)]
        uprigth_max_frame_load_capacity_kg_table = [
            [11600.0, 11500.0, 10500.0, 10000.0, 9600.0, 8500.0],
            [16500.0, 16100.0, 15300.0, 14400.0, 13500.0, 12800.0],
            [18800.0, 18000.0, 17700.0, 16500.0, 16000.0, 15800.0],
            [19800.0, 19200.0, 18400.0, 17700.0, 17000.0, 16300.0],
            [20200.0, 19500.0, 18700.0, 18100.0, 17300.0, 16700.0],
            [21000.0, 20800.0, 20500.0, 19600.0, 18900.0, 18000.0],
            [23500.0, 23500.0, 23500.0, 22900.0, 22200.0, 21800.0],
            [25100.0, 24400.0, 23800.0, 23000.0, 22300.0, 21700.0],
            [26700.0, 26100.0, 25400.0, 24600.0, 24000.0, 23200.0],
            [28300.0, 27700.0, 27100.0, 26300.0, 25600.0, 25000.0]
        ]

        min_rack_heights = [2000, 2000, 6000, 6000, 6000,
                            6000, 6000, 6000, 6000, 6000]
        max_rack_heights = [10000, 10000, 12000, 12000, 12000,
                            12000, 12000, 12000, 12000, 12000]

        # add upright_width_eps to upright_width
        for us_idx, us in enumerate(upright_sections):
            upright_sections[us_idx] = (us[0] + self.upright_width_eps,
                                        us[1], us[2])

        upright_types = []
        for i in range(len(upright_max_shelf_height)):
            for j in range(len(upright_sections)):
                upright_type_id = i * 100 + j
                upright_types.append(
                    UprightType(
                        upright_type_id=upright_type_id,
                        upright_section=upright_sections[j],
                        max_shelf_height=upright_max_shelf_height[i],
                        max_frame_load_capacity_kg=(
                            uprigth_max_frame_load_capacity_kg_table[j][i]
                        ),
                        min_rack_height=min_rack_heights[j],
                        max_rack_height=max_rack_heights[j]
                    )
                )
        upright_types.sort(
            key=lambda x: (x.max_shelf_height,
                           x.max_frame_load_capacity_kg)
        )
        return upright_types

    def get_pallet_types(self) -> dict[int, PalletType]:
        """
        Returns the dictionary of pallet types.

        Returns:
            dict[int, PalletType]: Dictionary of pallet types with their IDs.
        """
        return self.pallet_types.copy()
