from src.rack_info import RackInfo
from src.zone import Zone
import matplotlib.pyplot as plt
from src.packer import Packer

if __name__ == '__main__':
    # -----------------------RACK GROUP TEST-----------------------

    # rack_info = RackInfo(0.6, 0.3, 2.2, 20, 10, 30, 1.0, 0.01, 0.01, 0.4,
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

    # zone = Zone([(0, 0), (1, 0), (1, 1), (0, 1)], 2.2)
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
    rack_info_1 = RackInfo(1, 0.04, 0.03, 2.2, 100, 10, 30, 1.0, 0.001, 0.001, 0.01,
                           0.01, 0.01)
    rack_info_2 = RackInfo(2, 0.03, 0.02, 3.3, 250, 20, 30, 1.0, 0.001, 0.001, 0.01,
                           0.01, 0.01)
    rack_info_3 = RackInfo(3, 0.05, 0.04, 4.1, 250, 20, 30, 1.0, 0.001, 0.001, 0.01,
                           0.01, 0.01)

    zone_1 = Zone([(0, 0), (0, 1.0), (1.0, 1.0), (1.0, 0)], 4.2)
    zone_2 = Zone([(3, 5), (3, 7), (5, 7), (5, 5)], 2.3)

    packer = Packer([zone_1, zone_2], [rack_info_1, rack_info_2, rack_info_3])
    packer.pack()

    for rack_group in packer.rack_groups:
        x, y = rack_group.restrictive_bounds.exterior.xy
        plt.plot(x, y)
        x, y = rack_group.physical_bounds.exterior.xy
        plt.plot(x, y)
        for rack in rack_group.racks:
            x, y = rack.exterior.xy
            plt.plot(x, y)
    plt.show()
