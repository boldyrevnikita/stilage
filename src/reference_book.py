"""
Reference book module containing business logic constants and configurations.

This module provides the ReferenceBook class which stores all business-related
constants, configuration parameters, and lookup tables for the pallet packing system.
"""

from src.pallet import PalletType
from src.rack import BeamType, UprightType


class ReferenceBook:
    """Reference book containing business logic related information
    and constants.
    
    This class serves as a central configuration store for:
    - Pallet types and their properties
    - Beam types and their load capacities
    - Upright types and their specifications
    - Distance and clearance parameters
    - Column identification thresholds (NEW)
    - Protective rack parameters (NEW)
    """

    def __init__(self):
        """Initializes the reference book with all configuration parameters."""
        
        # =====================================================================
        # UPRIGHT CONFIGURATION
        # =====================================================================
        
        # Extra width added to upright sections for structural reasons
        self.upright_width_eps = 8.0

        # =====================================================================
        # PALLET TYPES
        # =====================================================================
        
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
        
        # =====================================================================
        # BEAM AND UPRIGHT TYPES
        # =====================================================================
        
        self.beam_types: dict[int, list[BeamType]] = self.__init_beam_types()
        self.upright_types: list[UprightType] = self.__init_upright_types()

        # =====================================================================
        # SHELF HEIGHT CONFIGURATION
        # =====================================================================
        
        # Maps frame height thresholds to required pallet extra space
        # Format: (max_frame_height, pallet_extra_space)
        # Extra space is needed above pallets for forklift operation
        self.frame_height2pallet_extra_space = [
            (3000.0, 75.0),   # For frames up to 3m: 75mm extra space
            (9000.0, 125.0),  # For frames up to 9m: 125mm extra space
            (12000.0, 150.0), # For frames up to 12m: 150mm extra space
        ]

        # =====================================================================
        # DISTANCE AND CLEARANCE PARAMETERS
        # =====================================================================
        
        # Standard width of roads/aisles for forklift movement
        self.roads_width = 3000.0
        
        # Height of roads (for bridge calculations)
        self.roads_height = 5000.0
        
        # Clearance around forbidden zones (safety buffer)
        self.forbidden_zone_clearance = 250.0
        
        # Additional height buffer for frame calculations
        self.frame_height_eps = 100.0

        self.double_rack_distance_eps = 144.0
        
        # Maximum internal distance between two racks in a double rack (standard)
        self.max_double_rack_internal_distance = 1000.0

        # =====================================================================
        # NEW: COLUMN PROTECTION PARAMETERS
        # =====================================================================
        
        # Maximum internal distance for protective double racks
        # Protective racks can have wider spacing to accommodate large columns
        self.max_protective_rack_internal_distance = 2000.0
        
        # Minimum width of a free strip to be considered for rack placement
        # Strips narrower than this will be left as passages
        self.min_free_strip_width = 1200.0
        
        # =====================================================================
        # NEW: COLUMN IDENTIFICATION PARAMETERS
        # =====================================================================
        
        # Maximum size (max dimension) of an object to be considered a column
        # Objects larger than this are treated as walls or large obstacles
        self.column_identification_max_size = 2000.0
        
        # Maximum aspect ratio (max_dim / min_dim) for column identification
        # Columns are typically compact (close to square)
        # Higher ratio indicates elongated obstacles (walls, barriers)
        self.column_identification_max_aspect_ratio = 3.0

    def __init_beam_types(self) -> dict[int, list[BeamType]]:
        """Initializes the beam types with their properties
        and returns a dictionary of beam types categorized by rack type.

        Returns:
            dict[int, list[BeamType]]: Dictionary of beam types categorized by
            rack type (pallet type).
        """
        # Available beam lengths (mm)
        beam_lengths = [1850.0, 2300.0, 2700.0, 3300.0, 3600.0]
        
        # Available beam cross-sections (height, thickness)
        beam_sections = [
            (85.0, 1.5), 
            (100.0, 1.5),
            (110.0, 1.5), 
            (125.0, 1.5),
            (140.0, 1.5), 
            (160.0, 1.5),
            (160.0, 2.0)
        ]
        
        # Load capacity table [section_index][length_index] = capacity_kg
        beam_max_shelf_load_capacity_kg_table = [
            [2200.0, 1700.0, 1300.0, 800.0, 800.0],
            [3600.0, 2600.0, 2200.0, 1400.0, 1100.0],
            [3700.0, 3000.0, 2500.0, 1700.0, 1400.0],
            [3700.0, 3500.0, 3000.0, 2000.0, 1700.0],
            [5000.0, 4200.0, 3800.0, 2700.0, 2100.0],
            [5500.0, 5000.0, 4300.0, 3400.0, 2800.0],
            [6000.0, 5300.0, 4800.0, 4200.0, 4000.0]
        ]
        
        # Maximum number of pallets per shelf for each beam length
        beam_max_rack_load_capacity_pallets = [2, 2, 3, 3, 4]

        # Mapping of pallet types to compatible beam length indices
        pallet_types2beam_types = {
            1: [4, 2, 0],  # Pallet type 1: use beam indices 4, 2, 0
            2: [3, 1]      # Pallet type 2: use beam indices 3, 1
        }

        # Initialize beam types dictionary
        beam_types = {
            1: [],  # Beams for pallet type 1
            2: [],  # Beams for pallet type 2
        }
        
        # Generate all beam type combinations
        for i in range(len(beam_lengths)):
            for j in range(len(beam_sections)):
                beam_type_id = i * 100 + j

                # Determine which rack type (pallet type) this beam is for
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
        
        # Sort beam types by length (descending) and capacity (ascending)
        for key in beam_types.keys():
            beam_types[key].sort(
                key=lambda x: (
                    0 if x.length == 2700.0 else 1,  # Приоритет: 2700 идет первой
                    -x.length,                        # Остальные по убыванию длины
                    x.max_shelf_load_capacity_kg      # При равной длине - по возрастанию грузоподъемности
                ))

        return beam_types

    def __init_upright_types(self) -> list[UprightType]:
        """Initializes the upright types with their properties
        and returns a list of upright types.
        
        Returns:
            list[UprightType]: List of upright types.
        """
        # Maximum shelf heights for different upright types
        upright_max_shelf_height = [
            750.0, 1000.0, 1250.0,
            1500.0, 1750.0, 2000.0
        ]
        
        # Upright cross-sections (width, depth, thickness)
        upright_sections = [
            (80.0, 75.0, 2.0), 
            (100.0, 75.0, 2.0),
            (120.0, 75.0, 2.0), 
            (140.0, 75.0, 2.0),
            (120.0, 100.0, 2.0), 
            (120.0, 75.0, 2.5),
            (140.0, 75.0, 2.5), 
            (120.0, 100.0, 2.5),
            (140.0, 100.0, 2.5), 
            (160.0, 100.0, 2.5)
        ]
        
        # Load capacity table [section_index][height_index] = capacity_kg
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

        # Minimum and maximum rack heights for each upright section
        min_rack_heights = [2000, 2000, 6000, 6000, 6000,
                            6000, 6000, 6000, 6000, 6000]
        max_rack_heights = [8000, 10000, 12000, 12000, 12000,
                            12000, 12000, 12000, 12000, 12000]

        # Add upright_width_eps to upright_width for structural reasons
        for us_idx, us in enumerate(upright_sections):
            upright_sections[us_idx] = (us[0] + self.upright_width_eps,
                                        us[1], us[2])

        upright_types = []
        
        # Generate all upright type combinations
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
        
        # Sort upright types by shelf height and load capacity
        upright_types.sort(
            key=lambda x: (x.max_shelf_height,
                           x.max_frame_load_capacity_kg)
        )
        return upright_types

    def get_pallet_types(self) -> dict[int, PalletType]:
        """Returns the dictionary of pallet types.

        Returns:
            dict[int, PalletType]: Dictionary of pallet types with their IDs.
        """
        return self.pallet_types.copy()
    
    def get_beam_types_for_pallet(self, pallet_type_id: int) -> list[BeamType]:
        """Returns beam types compatible with the given pallet type.
        
        Args:
            pallet_type_id (int): The pallet type ID.
        
        Returns:
            list[BeamType]: List of compatible beam types.
        
        Raises:
            KeyError: If pallet type ID is not found.
        """
        if pallet_type_id not in self.beam_types:
            raise KeyError(f"Pallet type {pallet_type_id} not found in beam types.")
        return self.beam_types[pallet_type_id].copy()
    
    def get_upright_types(self) -> list[UprightType]:
        """Returns all available upright types.
        
        Returns:
            list[UprightType]: List of upright types.
        """
        return self.upright_types.copy()
    
    def get_pallet_extra_space_for_height(self, frame_height: float) -> float:
        """Returns the required pallet extra space for a given frame height.
        
        Args:
            frame_height (float): The frame height in millimeters.
        
        Returns:
            float: The required extra space above pallets in millimeters.
        """
        for max_height, extra_space in self.frame_height2pallet_extra_space:
            if frame_height <= max_height:
                return extra_space
        # Return maximum extra space if height exceeds all thresholds
        return self.frame_height2pallet_extra_space[-1][1]
    
    def is_column(self, width: float, height: float, 
                  should_be_available: bool = False) -> bool:
        """Determines if an obstacle with given dimensions should be 
        classified as a column.
        
        Args:
            width (float): Width of the obstacle in millimeters.
            height (float): Height of the obstacle in millimeters.
            should_be_available (bool): Whether the zone is marked as available.
        
        Returns:
            bool: True if the obstacle should be treated as a column.
        """
        if should_be_available:
            return False
        
        if min(width, height) == 0:
            return False
        
        aspect_ratio = max(width, height) / min(width, height)
        max_dimension = max(width, height)
        
        is_compact = aspect_ratio <= self.column_identification_max_aspect_ratio
        is_small = max_dimension <= self.column_identification_max_size
        
        return is_compact and is_small
    
    def __repr__(self) -> str:
        """Returns a string representation of the ReferenceBook.
        
        Returns:
            str: String with key configuration parameters.
        """
        return (f"ReferenceBook("
                f"pallet_types={len(self.pallet_types)}, "
                f"beam_types={sum(len(v) for v in self.beam_types.values())}, "
                f"upright_types={len(self.upright_types)}, "
                f"roads_width={self.roads_width}, "
                f"max_protective_distance={self.max_protective_rack_internal_distance}, "
                f"column_max_size={self.column_identification_max_size}"
                f")")