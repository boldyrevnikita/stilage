import os
import sys

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))

import argparse  # noqa: E402

import pika  # noqa: E402

from src.input_generator import InputGenerator  # noqa: E402
from src.network import (MessageHandler, Sender,  # noqa: E402
                         process_message_print)

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('--host', default='localhost', help='RabbitMQ host')
arg_parser.add_argument('--port', default=None, help='RabbitMQ port')
arg_parser.add_argument('--vhost', default=None, help='RabbitMQ vhost')
arg_parser.add_argument('--username', default=None,
                        help='RabbitMQ username')
arg_parser.add_argument('--password', default=None,
                        help='RabbitMQ password')
arg_parser.add_argument('--input_queue', default='output_queue',
                        help='Input queue name')
arg_parser.add_argument('--output_queue', default='input_queue',
                        help='Output queue name')
arg_parser.add_argument('--output_routing_key', default='input_queue',
                        help='Input routing key')
arg_parser.add_argument('--random_seed', type=int, default=42)
args = arg_parser.parse_args()

input_generator = InputGenerator()
(buildings, available_zones, forbidden_zones,
 road_zones, rack_infos, roads_width) = \
    input_generator.generate(random_seed=args.random_seed)

msg = {
    "task_id": '1'*32,
    "file_id": '1'*32,
    "forbiden_zone_wall_clearance": 2.5,
    "forbiden_zone_pillar_clearance": 1.5,
    "forbiden_zone_other_clearance": 2.5,
    "buildings": [],
    "available_zones": [],
    "restricted_zones": [],
    "road_zones": [],
    "rack_types": [],
    "roads_width": roads_width
}

for idx, building in enumerate(buildings):
    building_dict = {
        "boundary": list(zip(*building.walls.exterior.xy)),
        "clearance": building.distance_from_walls,
        "id": str(idx) + str(1)
    }
    msg["buildings"].append(building_dict)

for idx, zone in enumerate(available_zones):
    zone_dict = {
        "boundary": list(zip(*zone.geometry.exterior.xy)),
        "height": zone.height,
        "id": str(idx) + str(2)
    }
    msg["available_zones"].append(zone_dict)

for idx, zone in enumerate(forbidden_zones):
    zone_dict = {
        "boundary": list(zip(*zone.geometry.exterior.xy)),
        "clearance": zone.distance_from_zone,
        "id": str(idx) + str(3)
    }
    msg["restricted_zones"].append(zone_dict)

for idx, zone in enumerate(road_zones):
    if zone.orientation == 0:
        y_0 = (zone.geometry.bounds[1] + zone.geometry.bounds[3]) / 2
        width = zone.geometry.bounds[3] - zone.geometry.bounds[1]
        x_0 = zone.geometry.bounds[0]
        x_1 = zone.geometry.bounds[2]
        y_1 = y_0
    else:
        x_0 = (zone.geometry.bounds[0] + zone.geometry.bounds[2]) / 2
        width = zone.geometry.bounds[2] - zone.geometry.bounds[0]
        y_0 = zone.geometry.bounds[1]
        y_1 = zone.geometry.bounds[3]
        x_1 = x_0
    zone_dict = {
        "line": [(x_0, y_0), (x_1, y_1)],
        "width": width,
        "id": str(idx) + str(5)
    }
    msg["road_zones"].append(zone_dict)

for idx, rack_info in enumerate(rack_infos):
    rack_info_dict = {
        "id": rack_info.id,
        "unit_length": rack_info.unit_length,
        "width": rack_info.width,
        "height_0": rack_info.height_0,
        "height_i": rack_info.height_i,
        "height_delta": rack_info.height_delta,
        "min_unit_shelf_quantity": rack_info.min_unit_shelf_quantity,
        "max_unit_shelf_quantity": rack_info.max_unit_shelf_quantity,
        "absolute": rack_info.abs_quantity,
        "min": rack_info.min_quantity,
        "relative": rack_info.rel_quantity,
        "max": rack_info.max_quantity,
        "pillar_width": rack_info.pillar_width,
        "back_connection_clearance": rack_info.back_connection_distance,
        "front_clearance": rack_info.front_distance,
        "side_clearance": rack_info.side_distance,
        "back_clearance": rack_info.back_distance
    }
    msg["rack_types"].append(rack_info_dict)

credentials = None
if args.username and args.password:
    credentials = pika.PlainCredentials(username=args.username,
                                        password=args.password)

sender = Sender(args.host, args.output_queue,
                args.output_routing_key,
                args.port, args.vhost, credentials)
receiver = MessageHandler(args.host, args.input_queue,
                          process_message_print, None,
                          args.port, args.vhost, credentials)

sender.send(msg)
receiver.receive()
receiver.close()
sender.close()
