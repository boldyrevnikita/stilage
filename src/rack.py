import shapely
from shapely import Polygon
from src.pallet import Pallet
from enum import Enum


class BeamType:
    def __init__(self, beam_type_id: int, length: float,
                 beam_section: tuple[float, float],
                 max_shelf_load_capacity_kg: float,
                 max_shelf_load_capacity_pallets: int):
        self.beam_type_id = beam_type_id
        self.length = length
        self.beam_section = beam_section
        self.max_shelf_load_capacity_kg = max_shelf_load_capacity_kg
        self.max_shelf_load_capacity_pallets = max_shelf_load_capacity_pallets

    @property
    def height(self) -> float:
        """Height of the beam"""
        return self.beam_section[0]


class UprightType:
    def __init__(self, upright_type_id: int,
                 upright_section: tuple[float, float, float],
                 max_shelf_height: float,
                 max_frame_load_capacity_kg: float):
        self.upright_type_id = upright_type_id
        self.upright_section = upright_section
        self.max_shelf_height = max_shelf_height
        self.max_frame_load_capacity_kg = max_frame_load_capacity_kg

    @property
    def width(self) -> float:
        """Width of the upright"""
        return self.upright_section[0]


class PillarStatus(Enum):
    ENABLED = 1
    DISABLED = 2


class DeckStatus(Enum):
    ENABLED = 1
    DISABLED = 2
    RACK_BRIDGE = 3


class Rack:
    def __init__(self, beam_types: list[BeamType], upright_type: UprightType,
                 pallet: Pallet, max_shelfs: int,
                 max_shelfs_bridge: int,
                 position: tuple[float, float] = (0.0, 0.0)):
        self.beam_types = beam_types
        self.beam_types.sort(key=lambda x: -x.length)

        self.beam_type_idx = 0
        self.beam_type: BeamType = self.beam_types[self.beam_type_idx]
        self.upright_type = upright_type
        self.pallet = pallet
        self.max_shelfs = max_shelfs
        self.max_shelfs_bridge = max_shelfs_bridge
        self.rack_position = position
        self.next_element_position = position
        self.decks: list[Polygon] = []
        self.beams: list[BeamType] = []
        self.pillars: list[Polygon] = []
        self.deck_status: list[DeckStatus] = []
        self.pillar_status: list[PillarStatus] = []
        self.contour: Polygon | None = None
        self.__init_first_frame()
        self.__update_contour()

        self.orientation = 0  # 0 - horizontal, 1 - vertical

    def add_frame(self) -> None:
        if not self.decks:
            self.__init_first_frame()
            return

        self.__append_deck()
        self.__append_pillar()
        self.__update_contour()

    def add_multiple_frames(self, count: int) -> None:
        for _ in range(count):
            self.__append_deck()
            self.__append_pillar()
        self.__update_contour()

    def disable_frame(self, frame_idx: int) -> None:
        """Disables the frame at the given index."""
        if frame_idx < 0 or frame_idx >= len(self.decks):
            raise IndexError("Frame index out of range.")

        self.deck_status[frame_idx] = DeckStatus.DISABLED

        if frame_idx == 0:
            self.pillar_status[frame_idx] = PillarStatus.DISABLED
        elif frame_idx == len(self.decks) - 1:
            self.pillar_status[frame_idx + 1] = PillarStatus.DISABLED

        if (frame_idx > 0
                and self.deck_status[frame_idx-1] == DeckStatus.DISABLED):
            self.pillar_status[frame_idx] = PillarStatus.DISABLED
        if (frame_idx < len(self.decks) - 1
                and self.deck_status[frame_idx+1] == DeckStatus.DISABLED):
            self.pillar_status[frame_idx + 1] = PillarStatus.DISABLED

    def made_frame_bridge(self, frame_idx: int) -> None:
        """Makes the frame at the given index a bridge."""
        if frame_idx < 0 or frame_idx >= len(self.decks):
            raise IndexError("Frame index out of range.")
        self.deck_status[frame_idx] = DeckStatus.RACK_BRIDGE

    def rotate(self, angle: float,
               rot_point: tuple[float, float] = (0.0, 0.0)) -> None:
        """Rotates the rack around a point."""
        self.contour = shapely.affinity.rotate(self.contour, angle,
                                               origin=rot_point)
        for i in range(len(self.decks)):
            self.decks[i] = shapely.affinity.rotate(self.decks[i], angle,
                                                    origin=rot_point)
        for i in range(len(self.pillars)):
            self.pillars[i] = shapely.affinity.rotate(self.pillars[i], angle,
                                                      origin=rot_point)

        self.orientation = abs(self.orientation - 1)

    def is_possible_set_next_beam_type(self) -> bool:
        if self.beam_type_idx < len(self.beam_types) - 1:
            return True
        return False

    def set_next_beam_type(self) -> None:
        """Sets the next beam type for the rack."""
        if self.is_possible_set_next_beam_type():
            self.beam_type_idx += 1
            self.beam_type = self.beam_types[self.beam_type_idx]
        else:
            raise IndexError("No more beam types available.")

    def set_zero_beam_type(self) -> None:
        """Sets the beam type index to zero."""
        self.beam_type_idx = 0
        self.beam_type = self.beam_types[self.beam_type_idx]

    def delete_last_frame(self) -> None:
        """Deletes the last frame from the rack."""
        if not self.decks:
            raise IndexError("No frames to delete.")

        self.decks.pop()
        self.deck_status.pop()
        self.beams.pop()
        self.pillars.pop()
        self.pillar_status.pop()

        if self.decks:
            self.next_element_position = (
                self.pillars[-1].bounds[2],
                self.next_element_position[1])
        else:
            self.pillars.pop()
            self.pillar_status.pop()

            self.next_element_position = (
                self.rack_position[0], self.rack_position[1])

        self.__update_contour()

    def get_current_shelf_length(self) -> float:
        """Returns the length of the current shelf."""
        return self.beam_type.length

    def translate(self, xoff: float, yoff: float) -> None:
        """Translates the rack by a given offset."""
        self.rack_position = (self.rack_position[0] + xoff,
                              self.rack_position[1] + yoff)
        self.next_element_position = (self.next_element_position[0] + xoff,
                                      self.next_element_position[1] + yoff)

        self.contour = shapely.affinity.translate(self.contour, xoff, yoff)
        for i in range(len(self.decks)):
            self.decks[i] = shapely.affinity.translate(
                self.decks[i], xoff, yoff)
        for i in range(len(self.pillars)):
            self.pillars[i] = shapely.affinity.translate(
                self.pillars[i], xoff, yoff)

    def calculate_pallet_capacity(self) -> int:
        """Calculates the total number of pallets
            that can be stored in the rack."""
        total_pallets = 0
        for frame_idx in range(len(self.decks)):
            frame_capacity = self.calculate_pallet_capacity_in_ith_frame(
                frame_idx)
            total_pallets += frame_capacity
        return total_pallets

    def calculate_pallet_capacity_in_ith_frame(self, frame_idx: int) -> int:
        if frame_idx < 0 or frame_idx >= len(self.decks):
            raise IndexError("Frame index out of range.")

        beam_type = self.beams[frame_idx]
        frame_status = self.deck_status[frame_idx]
        if frame_status == DeckStatus.ENABLED:
            return beam_type.max_shelf_load_capacity_pallets * self.max_shelfs
        elif frame_status == DeckStatus.RACK_BRIDGE:
            return (beam_type.max_shelf_load_capacity_pallets
                    * self.max_shelfs_bridge)
        else:
            return 0

    def __len__(self) -> int:
        return len(self.decks)

    @property
    def last_shelf_contour(self) -> Polygon | None:
        """Returns the contour of the last shelf."""
        if not self.decks:
            return None
        return self.decks[-1]

    @property
    def last_pillar_contour(self) -> Polygon | None:
        """Returns the contour of the last pillar."""
        if not self.pillars:
            return None
        return self.pillars[-1]

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Returns the bounds of the rack."""
        if self.contour is None:
            return (0.0, 0.0, 0.0, 0.0)
        return self.contour.bounds

    def __init_first_frame(self) -> None:
        """Initializes a simple rack with one deck and two pillars."""
        self.__append_pillar()
        self.__append_deck()
        self.__append_pillar()

    def __update_contour(self) -> None:
        """Initializes the contour of the rack."""
        if not self.decks or not self.pillars:
            return
        min_x, min_y, max_x, max_y = self.pillars[0].bounds
        for pillar in self.pillars:
            min_x = min(min_x, pillar.bounds[0])
            min_y = min(min_y, pillar.bounds[1])
            max_x = max(max_x, pillar.bounds[2])
            max_y = max(max_y, pillar.bounds[3])

        for deck in self.decks:
            min_x = min(min_x, deck.bounds[0])
            min_y = min(min_y, deck.bounds[1])
            max_x = max(max_x, deck.bounds[2])
            max_y = max(max_y, deck.bounds[3])

        self.contour = Polygon([(min_x, min_y), (max_x, min_y),
                                (max_x, max_y), (min_x, max_y)])

    def __append_pillar(self) -> None:
        """Appends a pillar to the rack."""
        self.pillars.append(
            self.__create_pillar(self.next_element_position))
        self.pillar_status.append(PillarStatus.ENABLED)

        self.next_element_position = (
            self.pillars[-1].bounds[2],
            self.next_element_position[1])

    def __append_deck(self) -> None:
        """Appends a deck to the rack."""
        self.decks.append(
            self.__create_deck(self.next_element_position))
        self.deck_status.append(DeckStatus.ENABLED)
        self.beams.append(self.beam_type)

        self.next_element_position = (
            self.decks[-1].bounds[2],
            self.next_element_position[1])

    def __create_pillar(self, position: tuple[float, float]) -> Polygon:
        length = self.upright_type.width
        depth = self.pallet.length

        pillar = Polygon([
            (position[0], position[1]),
            (position[0] + length, position[1]),
            (position[0] + length, position[1] + depth),
            (position[0], position[1] + depth),
        ])

        return pillar

    def __create_deck(self, position: tuple[float, float]) -> Polygon:
        length = self.beam_type.length
        depth = self.pallet.length

        deck = Polygon([
            (position[0], position[1]),
            (position[0] + length, position[1]),
            (position[0] + length, position[1] + depth),
            (position[0], position[1] + depth),
        ])

        return deck


class DoubleRack():
    def __init__(self, beam_types: list[BeamType], upright_type: UprightType,
                 pallet: Pallet, max_shelfs: int,
                 max_shelfs_bridge: int,
                 position: tuple[float, float] = (0.0, 0.0),
                 rack_distance: float = 200.0):
        self.beam_type = beam_types[0]
        self.upright_type = upright_type
        self.pallet = pallet
        self.max_shelfs = max_shelfs
        self.max_shelfs_bridge = max_shelfs_bridge

        self.rack_distance = rack_distance

        self.first_rack_position = position
        self.rack_1 = Rack(beam_types, upright_type, pallet, max_shelfs,
                           max_shelfs_bridge, self.first_rack_position)

        self.second_rack_position = self.__calculate_2nd_rack_position()
        self.rack_2 = Rack(beam_types, upright_type, pallet, max_shelfs,
                           max_shelfs_bridge, self.second_rack_position)

        self.contour = None
        self.__update_contour()
        self.orientation = 0  # 0 - horizontal, 1 - vertical

    def add_frame(self) -> None:
        """Adds a frame to both racks."""
        self.rack_1.add_frame()
        self.rack_2.add_frame()
        self.__update_contour()

    def add_multiple_frames(self, count: int) -> None:
        """Adds multiple frames to both racks."""
        self.rack_1.add_multiple_frames(count)
        self.rack_2.add_multiple_frames(count)
        self.__update_contour()

    def made_frame_bridge(self, frame_idx: int) -> None:
        """Makes the frame at the given index a bridge in both racks."""
        self.rack_1.made_frame_bridge(frame_idx)
        self.rack_2.made_frame_bridge(frame_idx)

    def rotate(self, angle: float,
               rot_point: tuple[float, float] = (0.0, 0.0)) -> None:
        """Rotates the double rack around a point."""
        self.contour = shapely.affinity.rotate(self.contour, angle,
                                               origin=rot_point)
        self.rack_1.rotate(angle, rot_point)
        self.rack_2.rotate(angle, rot_point)
        self.orientation = abs(self.orientation - 1)

    def is_possible_set_next_beam_type(self) -> bool:
        """Checks if the next beam type can be set for both racks."""
        return (self.rack_1.is_possible_set_next_beam_type() and
                self.rack_2.is_possible_set_next_beam_type())

    def set_next_beam_type(self) -> None:
        """Sets the next beam type for both racks."""
        if self.is_possible_set_next_beam_type():
            self.rack_1.set_next_beam_type()
            self.rack_2.set_next_beam_type()
        else:
            raise IndexError("No more beam types "
                             "available for one of the racks.")

    def set_zero_beam_type(self) -> None:
        """Sets the beam type index to zero for both racks."""
        self.rack_1.set_zero_beam_type()
        self.rack_2.set_zero_beam_type()

    def delete_last_frame(self) -> None:
        """Deletes the last frame from both racks."""
        self.rack_1.delete_last_frame()
        self.rack_2.delete_last_frame()
        self.__update_contour()

    def get_current_shelf_length(self) -> float:
        """Returns the length of the current shelf for both racks."""
        return min(self.rack_1.get_current_shelf_length(),
                   self.rack_2.get_current_shelf_length())

    def translate(self, xoff: float, yoff: float) -> None:
        """Translates the double rack by a given offset."""
        self.contour = shapely.affinity.translate(self.contour, xoff, yoff)
        self.rack_1.translate(xoff, yoff)
        self.rack_2.translate(xoff, yoff)

    def calculate_pallet_capacity(self) -> int:
        """Calculates the total number of pallets
            that can be stored in both racks."""
        return (self.rack_1.calculate_pallet_capacity() +
                self.rack_2.calculate_pallet_capacity())

    def calculate_pallet_capacity_in_ith_frame(self, frame_idx: int) -> int:
        """Calculates the pallet capacity in the ith frame of both racks."""
        if frame_idx < 0 or frame_idx >= len(self.rack_1) or \
                frame_idx >= len(self.rack_2):
            raise IndexError("Frame index out of range.")
        return (self.rack_1.calculate_pallet_capacity_in_ith_frame(frame_idx) +
                self.rack_2.calculate_pallet_capacity_in_ith_frame(frame_idx))

    def __len__(self) -> int:
        """Returns the frame length of the double rack."""
        return max(len(self.rack_1), len(self.rack_2))

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        return self.contour.bounds

    def __calculate_2nd_rack_position(self) -> tuple[float, float]:
        """Calculates the position of the second rack in a double rack."""
        rack_1_bounds = self.rack_1.bounds
        x, y = rack_1_bounds[0], rack_1_bounds[3]
        return (x, y + self.rack_distance)

    def __update_contour(self) -> None:
        """Updates the contour of the double rack."""
        min_x = min(self.rack_1.bounds[0], self.rack_2.bounds[0])
        min_y = min(self.rack_1.bounds[1], self.rack_2.bounds[1])
        max_x = max(self.rack_1.bounds[2], self.rack_2.bounds[2])
        max_y = max(self.rack_1.bounds[3], self.rack_2.bounds[3])
        self.contour = Polygon([(min_x, min_y), (max_x, min_y),
                                (max_x, max_y), (min_x, max_y)])


class RackGroup():
    def __init__(self, position: tuple[float, float],
                 roads_width: float,
                 beam_types: list[BeamType],
                 upright_type: UprightType,
                 pallet: Pallet,
                 max_shelfs: int,
                 max_shelfs_bridge: int,
                 pallet_extra_space: float,
                 frame_height_eps: float):
        self.beam_types = beam_types
        self.upright_type = upright_type
        self.pallet = pallet
        self.max_shelfs = max_shelfs
        self.max_shelfs_bridge = max_shelfs_bridge
        self.pallet_extra_space = pallet_extra_space
        self.frame_height_eps = frame_height_eps

        self.position = position
        self.roads_width = roads_width
        self.next_rack_placement = list(self.position)

        self.current_rack: Rack | DoubleRack | None = None
        self.place_single_rack()

        self.racks: list[Rack | DoubleRack] = []

    def get_current_rack(self) -> Rack | DoubleRack:
        """Returns the current rack in the group."""
        if self.current_rack is None:
            raise ValueError("No current rack set.")
        return self.current_rack

    def commit_current_rack(self) -> None:
        """Commits the current rack to the group."""
        if self.current_rack is None:
            raise ValueError("No current rack to commit.")
        self.racks.append(self.current_rack)

    def place_single_rack(self) -> None:
        """Places the first rack in the group."""
        self.current_rack = Rack(self.beam_types, self.upright_type,
                                 self.pallet, self.max_shelfs,
                                 self.max_shelfs_bridge,
                                 self.next_rack_placement)

    def place_double_rack(self) -> None:
        """Places a double rack in the group."""
        self.current_rack = DoubleRack(self.beam_types, self.upright_type,
                                       self.pallet, self.max_shelfs,
                                       self.max_shelfs_bridge,
                                       self.next_rack_placement)

    def rotate(self, angle: float,
               rot_point: tuple[float, float] = (0.0, 0.0)) -> None:
        """Rotates the rack group around a point."""
        for rack in self.racks:
            rack.rotate(angle, rot_point)

    def calculate_max_frame_height(self) -> float:
        """Calculates the maximum height of the frames in the group."""
        shelf_height = (self.pallet.height + self.pallet_extra_space
                        + self.beam_types[0].height)
        return self.max_shelfs * shelf_height + self.frame_height_eps

    def calculate_max_bridge_height(self) -> float:
        """Calculates the maximum height of the bridge in the group."""
        shelf_height = (self.pallet.height + self.pallet_extra_space
                        + self.beam_types[0].height)
        return self.max_shelfs_bridge * shelf_height + self.frame_height_eps

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        if not self.racks:
            return [self.position[0], self.position[1],
                    self.position[0], self.position[1]]
        min_x, min_y, max_x, max_y = self.racks[0].bounds
        for rack in self.racks:
            min_x = min(min_x, rack.bounds[0])
            min_y = min(min_y, rack.bounds[1])
            max_x = max(max_x, rack.bounds[2])
            max_y = max(max_y, rack.bounds[3])

        return min_x, min_y, max_x, max_y

    @property
    def area(self) -> float:
        bounds = self.bounds
        return abs((bounds[0] - bounds[2])
                   * (bounds[1] - bounds[3]))
