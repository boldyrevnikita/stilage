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
buildings, available_zones, forbidden_zones, rack_infos = \
    input_generator.generate(random_seed=args.random_seed)

msg = {
    "task_id": '1'*32,
    "buildings": [],
    "available_zones": [],
    "restricted_zones": [],
    "rack_types": [],
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

for idx, rack_info in enumerate(rack_infos):
    rack_info_dict = {
        "id": rack_info.id,
        "length": rack_info.length,
        "width": rack_info.width,
        "height": rack_info.height,
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
