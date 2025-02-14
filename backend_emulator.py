import argparse
from src.input_generator import InputGenerator

from src.network import (Receiver, Sender, process_message_print)

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('--host', default='localhost', help='RabbitMQ host')
arg_parser.add_argument('--port', default=5672, help='RabbitMQ port')
arg_parser.add_argument('--input_queue', default='result_queue',
                        help='Input queue name')
arg_parser.add_argument('--output_queue', default='task_queue',
                        help='Output queue name')
arg_parser.add_argument('--output_routing_key', default='task_queue',
                        help='Input routing key')
arg_parser.add_argument('--random_seed', type=int, default=42)
args = arg_parser.parse_args()

input_generator = InputGenerator()
buildings, zones, rack_infos = input_generator.generate(
    random_seed=args.random_seed)

msg = {
    "task_id": 1,
    "buildings": [],
    "available_zones": [],
    "rack_types": [],
}

for idx, building in enumerate(buildings):
    building_dict = {
        "boundary": list(zip(*building.walls.exterior.xy)),
        "clearance": building.distance_from_walls,
        "id": str(idx) + str(1)
    }
    msg["buildings"].append(building_dict)

for idx, zone in enumerate(zones):
    zone_dict = {
        "boundary": list(zip(*zone.geometry.exterior.xy)),
        "height": zone.height,
        "id": str(idx) + str(2)
    }
    msg["available_zones"].append(zone_dict)

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
        "side_connection_clearance": rack_info.side_connection_distance,
        "back_connection_clearance": rack_info.back_connection_distance,
        "front_clearance": rack_info.front_distance,
        "side_clearance": rack_info.side_distance,
        "back_clearance": rack_info.back_distance
    }
    msg["rack_types"].append(rack_info_dict)

sender = Sender(args.host, args.port, args.output_queue,
                args.output_routing_key)
receiver = Receiver(args.host, args.port, args.input_queue,
                    process_message_print)

sender.send(msg)
receiver.receive()
receiver.close()
sender.close()
