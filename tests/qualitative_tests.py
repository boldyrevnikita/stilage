import sys
import os
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))

import argparse

import matplotlib.pyplot as plt

from src.building import Building
from src.forbidden_zone import ForbiddenZone
from src.input_generator import InputGenerator
from src.packer import Packer
from src.rack import RackSection
from src.visualizer import Visualizer
from src.available_zone import AvailableZone
from src.postprocess import postprocess


if __name__ == '__main__':
    # -----------------------RACK GROUP TEST-----------------------

    # rack_info = RackSection(0.6, 0.3, 2.2, 20, 10, 30, 1.0, 0.01, 0.01, 0.4,
    #                      0.2, 0.2)
    # rack_group = RackGroup(rack_info, 10, 6)

    # plt.subplot(121)
    # x, y = rack_group.restrictive_bounds.exterior.xy
    # plt.plot(x, y)
    # x, y = rack_group.physical_bounds.exterior.xy
    # plt.plot(x, y)

    # for rack in rack_group.racks:
    #     x, y = rack.exterior.xy
    #     plt.plot(x, y)

    # plt.subplot(122)
    # rack_group.rotate90()
    # x, y = rack_group.restrictive_bounds.exterior.xy
    # plt.plot(x, y)
    # x, y = rack_group.physical_bounds.exterior.xy
    # plt.plot(x, y)

    # for rack in rack_group.racks:
    #     x, y = rack.exterior.xy
    #     plt.plot(x, y)

    # plt.show()

    # -----------------------ZONE TEST-----------------------

    # zone = AvailableZone([(0, 0), (1, 0), (1, 1), (0, 1)], 2.2)
    # x, y = zone.geometry.exterior.xy
    # # wider lines
    # plt.plot(x, y, linewidth=4)

    # split_point = (0.51, 0.5)
    # zone_1, zone_2 = zone.split_zone(split_point)
    # x, y = zone_1.geometry.exterior.xy
    # plt.plot(x, y)
    # x, y = zone_2.geometry.exterior.xy
    # plt.plot(x, y)
    # plt.plot(*split_point, 'ro')
    # plt.show()

    # -----------------------PACKER TEST-----------------------
    # building_1 = Building([(0, 0), (10, 0), (10, 10), (20, 10), (20, 20), (0, 20)], 0.5)
    # # Random polygon up to building_1
    # building_2 = Building([(3, 23), (25, 27), (27, 36), (20, 30), (15, 35), (10, 30)], 0.5)

    # rack_info_1 = RackSection(1, 0.4, 0.3, 2.2, 100, 10, 30, 1.0, 0.01, 0.01, 0.1,
    #                        0.1, 0.1)
    # rack_info_2 = RackSection(2, 0.3, 0.2, 3.3, 250, 20, 30, 1.0, 0.01, 0.01, 0.1,
    #                        0.1, 0.1)
    # rack_info_3 = RackSection(3, 0.5, 0.4, 4.1, 250, 20, 30, 1.0, 0.01, 0.01, 0.1,
    #                        0.1, 0.1)

    # zone_1 = AvailableZone([(1, 1), (8, 1), (8, 9.0), (1, 9)], 4.2)
    # zone_2 = AvailableZone([(11, 11), (19, 11), (19, 18), (11, 18)], 2.3)
    # zone_3 = AvailableZone([(12, 26.5), (16, 26.5), (16, 30), (12, 30)], 3.4)

    # forbidden_zone_1 = ForbiddenZone([(9.8, 10), (10.2, 10), (10.2, 15), (9.8, 15)], 0.5)
    # forbidden_zone_2 = ForbiddenZone([(0, 11), (6, 11), (6, 11.4), (0, 11.4)], 0.5)
    # forbidden_zone_3 = ForbiddenZone([(11, 31), (17, 31), (17, 28), (18, 28), (18, 31.5), (11, 31.5)], 0.5)

    # packer = Packer([zone_1, zone_2, zone_3], [rack_info_1, rack_info_2, rack_info_3])
    # packer.pack()

    # visualizer = Visualizer()
    # visualizer.plot([building_1, building_2],
    #                 packer.rack_groups,
    #                 [zone_1, zone_2, zone_3],
    #                 [forbidden_zone_1, forbidden_zone_2, forbidden_zone_3])
    # visualizer.show()

    # -----------------------INPUT GENERATOR TEST-----------------------
    parser = argparse.ArgumentParser()
    parser.add_argument('--random_seed', type=int, default=42)
    args = parser.parse_args()

    input_generator = InputGenerator()
    buildings, zones, rack_infos = input_generator.generate(
        random_seed=args.random_seed)

    forbidden_zone_1 = ForbiddenZone([(65, 155), (70, 163), (72, 163), (67, 157)], 0.5)
    forbidden_zone_2 = ForbiddenZone([(73, 150), (74, 162), (75, 162), (73.5, 154)], 0.5)
    forbidden_zone_3 = ForbiddenZone([(11, 31), (17, 31), (17, 28), (18, 28), (18, 31.5), (11, 31.5)], 0.5)
    forbiden_zones = [forbidden_zone_1, forbidden_zone_2, forbidden_zone_3]
    
    packer = Packer(zones, rack_infos)
    rack_groups = packer.pack()
    rack_groups = postprocess(rack_groups, forbiden_zones)

    visualizer = Visualizer()
    visualizer.plot(buildings, packer.rack_groups, zones, forbiden_zones)
    visualizer.show()
