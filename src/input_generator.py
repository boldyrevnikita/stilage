from typing import List, Tuple

import numpy as np

from src.building import Building
from src.rack import RackSection
from src.available_zone import AvailableZone


class InputGenerator:
    def __init__(self, min_building_size: float = 40,
                 max_building_size: float = 100,
                 min_distance_from_walls: float = 0.3,
                 max_distance_from_walls: float = 1,
                 min_building_num: int = 1, max_building_num: int = 3,
                 min_zone_size: float = 15, max_zone_size: float = 40,
                 min_zone_height: float = 3, max_zone_height: float = 5,
                 min_zone_num: int = 2, max_zone_num: int = 4,
                 min_rack_size: float = 0.3, max_rack_size: float = 1,
                 min_rack_height: float = 2, max_rack_height: float = 4,
                 min_rack_num: int = 200, max_rack_num: int = 400,
                 min_rack_back_connection_distance: float = 0.01,
                 max_rack_back_connection_distance: float = 0.05,
                 min_rack_pillar_width: float = 0.05,
                 max_rack_pillar_width: float = 0.1,
                 min_rack_front_distance: float = 1.0,
                 max_rack_front_distance: float = 2.0,
                 min_rack_back_distance: float = 0.5,
                 max_rack_back_distance: float = 1.0,
                 min_rack_side_distance: float = 0.5,
                 max_rack_side_distance: float = 1.0,
                 min_rack_info_num: int = 3,
                 max_rack_info_num: int = 6) -> None:
        self.min_building_size = min_building_size
        self.max_building_size = max_building_size
        self.min_distance_from_walls = min_distance_from_walls
        self.max_distance_from_walls = max_distance_from_walls
        self.min_building_num = min_building_num
        self.max_building_num = max_building_num
        self.min_zone_size = min_zone_size
        self.max_zone_size = max_zone_size
        self.min_zone_height = min_zone_height
        self.max_zone_height = max_zone_height
        self.min_zone_num = min_zone_num
        self.max_zone_num = max_zone_num
        self.min_rack_size = min_rack_size
        self.max_rack_size = max_rack_size
        self.min_rack_height = min_rack_height
        self.max_rack_height = max_rack_height
        self.min_rack_num = min_rack_num
        self.max_rack_num = max_rack_num
        self.min_rack_back_connection_distance = \
            min_rack_back_connection_distance
        self.max_rack_back_connection_distance = \
            max_rack_back_connection_distance
        self.min_rack_pillar_width = min_rack_pillar_width
        self.max_rack_pillar_width = max_rack_pillar_width
        self.min_rack_front_distance = min_rack_front_distance
        self.max_rack_front_distance = max_rack_front_distance
        self.min_rack_back_distance = min_rack_back_distance
        self.max_rack_back_distance = max_rack_back_distance
        self.min_rack_side_distance = min_rack_side_distance
        self.max_rack_side_distance = max_rack_side_distance
        self.min_rack_info_num = min_rack_info_num
        self.max_rack_info_num = max_rack_info_num

    def __generate_building(self, buildings: List[Building]) -> Building:
        """Generate a new building.

        Args:
            buildings (List[Building]): existing buildings

        Returns:
            Building: a new building
        """
        while True:
            x_0, y_0 = np.random.uniform(
                0, self.max_building_size * self.max_building_num, 2)
            x_1, y_1 = np.random.uniform(self.min_building_size,
                                         self.max_building_size, 2)
            x_1 += x_0
            y_1 += y_0

            building = Building([(x_0, y_0), (x_1, y_0),
                                 (x_1, y_1), (x_0, y_1)],
                                np.random.uniform(
                                    self.min_distance_from_walls,
                                    self.max_distance_from_walls))
            if not any(building.intersects(b.walls) for b in buildings):
                return building

    def __generate_available_zone(self, zones: List[AvailableZone],
                                  buildings: List[Building]) -> AvailableZone:
        """Generate a new available (for occupancy) zone.

        Args:
            zones (List[AvailableZone]): existing available zones
            buildings (List[Building]): existing buildings

        Returns:
            AvailableZone: a new available zone
        """
        while True:
            building_idx = np.random.randint(0, len(buildings))
            building = buildings[building_idx]
            building_bbox = building.available_space.bounds

            x_0 = np.random.uniform(building_bbox[0], building_bbox[2])
            y_0 = np.random.uniform(building_bbox[1], building_bbox[3])

            x_1 = np.random.uniform(self.min_zone_size, self.max_zone_size)
            y_1 = np.random.uniform(self.min_zone_size, self.max_zone_size)

            x_1 += x_0
            y_1 += y_0

            height = np.random.uniform(self.min_zone_height,
                                       self.max_zone_height)

            zone = AvailableZone([(x_0, y_0), (x_1, y_0),
                                  (x_1, y_1), (x_0, y_1)],
                                 height)

            if (building.contains(zone.geometry)
                and not any(z.geometry.intersects(zone.geometry)
                            for z in zones)):
                return zone

    def __generate_rack_info(self, rack_infos: List[RackSection]
                             ) -> RackSection:
        """Generate a new type of racks.

        Args:
            rack_infos (List[RackSection]): existing types of racks

        Returns:
            RackSection: a new type of racks
        """
        id = len(rack_infos)
        length = np.random.uniform(self.min_rack_size, self.max_rack_size)
        width = np.random.uniform(self.min_rack_size, self.max_rack_size)
        height = np.random.uniform(self.min_rack_height, self.max_rack_height)
        abs_quantity = np.random.randint(self.min_rack_num, self.max_rack_num)
        pillar_width = np.random.uniform(
            self.min_rack_pillar_width,
            self.max_rack_pillar_width)
        back_connection_distance = np.random.uniform(
            self.min_rack_back_connection_distance,
            self.max_rack_back_connection_distance)
        front_distance = np.random.uniform(self.min_rack_front_distance,
                                           self.max_rack_front_distance)
        back_distance = np.random.uniform(self.min_rack_back_distance,
                                          self.max_rack_back_distance)
        side_distance = np.random.uniform(self.min_rack_side_distance,
                                          self.max_rack_side_distance)

        return RackSection(id, length, width, height, abs_quantity,
                           abs_quantity, abs_quantity, 1, pillar_width,
                           back_connection_distance, front_distance,
                           back_distance, side_distance)

    def generate(self, random_seed=42) -> Tuple[List[Building],
                                                List[AvailableZone],
                                                List[RackSection]]:
        """Generate input data for the problem.

        Args:
            random_seed (int, optional): generator seed. Defaults to 42.

        Returns:
            Tuple[List[Building], List[AvailableZone], List[RackSection]]:
                buildings, available zones, and rack infos
        """
        np.random.seed(random_seed)

        buildings = []
        zones = []
        rack_infos = []

        for _ in range(np.random.randint(self.min_building_num,
                                         self.max_building_num + 1)):
            building = self.__generate_building(buildings)
            buildings.append(building)

        for _ in range(np.random.randint(self.min_zone_num,
                                         self.max_zone_num + 1)):
            zone = self.__generate_available_zone(zones, buildings)
            zones.append(zone)

        for _ in range(np.random.randint(self.min_rack_info_num,
                                         self.max_rack_info_num + 1)):
            rack_info = self.__generate_rack_info(rack_infos)
            rack_infos.append(rack_info)

        return buildings, zones, rack_infos
