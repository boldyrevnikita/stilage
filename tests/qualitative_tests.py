import sys
import os
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))

import argparse  # noqa: E402

from src.input_generator import InputGenerator  # noqa: E402
from src.packer import Packer  # noqa: E402
from src.visualizer import Visualizer  # noqa: E402
from src.postprocess import postprocess  # noqa: E402
from src.preprocess import preprocess  # noqa: E402


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--random_seed', type=int, default=42)
    args = parser.parse_args()

    input_generator = InputGenerator()
    buildings, available_zones, forbiden_zones, rack_infos, roads_width = \
        input_generator.generate(random_seed=args.random_seed)
    available_zones, forbiden_zones, rack_infos = preprocess(
        available_zones, forbiden_zones, rack_infos, roads_width)

    packer = Packer(available_zones, rack_infos)
    rack_groups = packer.pack()
    rack_groups = postprocess(rack_groups, forbiden_zones)

    visualizer = Visualizer()
    visualizer.plot(buildings, packer.rack_groups,
                    available_zones, forbiden_zones)
    visualizer.show()
