import os
import sys

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))

import argparse  # noqa: E402

import pika  # noqa: E402
import uuid  # noqa: E402

from src.network import (MessageHandler, Sender,  # noqa
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

msg = {
    "task_id": '1'*32,
    "file_id": 'rusichi',
    "available_zones": [],
    "restricted_zones": [],
    "road_zones": [],
    "cargos": [],
    "roads_width": 3000.0,
    "roads_height": 4000.0,
}

# msg['available_zones'].append({
#     "boundary": [(1268000, 45000),
#                  (1313000, 45000),
#                  (1313000, 103000),
#                  (1268000, 103000)],
#     "height": 10000.0,
#     "id": 12
# })
# msg['cargos'].append({
#     'id': 1,
#     'weight': 500.0,
#     'length': 700.0,
#     'width': 500.0,
#     'height': 300.0,
#     'quantity': 1000
# })

# msg['available_zones'].append({"boundary": [[59261.0, 36723.0],
#                                             [239303.0, 36723.0],
#                                             [239303.0, 131824.0],
#                                             [59261.0, 131824.0]],
#                                "height": 4000.0, "id": 12})
# msg['road_zones'].append({"line": [[34470.0, 68998.0], [271004.0, 68998.0]],
#                           "width": 3000.0, "id": 15})
# msg['cargos'].append({"weight": 1000, "length": 1000, "width": 1000,
#                       "height": 1000, "quantity": 5, "id": 14})

# msg['available_zones'].append({"boundary": [[1.1347e+7, 3103845],
#                                             [1.1467e+7, 3103845],
#                                             [1.1467e+7, 3209929],
#                                             [1.1347e+7, 3209929]],
#                                "height": 4000.0, "id": 12})
# msg['road_zones'].append({"line": [[1.1400e+7, 3103845], [1.1400e+7, 3209929]],
#                           "id": 15, "width": 7000})
# msg['road_zones'].append({"line": [[1.1347e+7, 3150000], [1.1467e+7, 3150000]],
#                           "id": 25, "width": 7000})
# msg['cargos'].append({"weight": 1000, "length": 1000, "width": 1000,
#                       "height": 1000, "quantity": 10000, "id": 14})

# msg['available_zones'].append({'boundary': [[11395953.29704532, 3161905.436713734], [11468174.29704532, 3161905.436713734], [11468174.29704532, 3103338.436713734], [11395953.29704532, 3103338.436713734]], 'height': 9000.0, 'orientation': 2, 'id': 12})
# msg['available_zones'].append({'boundary': [[11347088.29704532, 3162264.436713734], [11394875.29704532, 3162264.436713734], [11394875.29704532, 3103698.436713734], [11347088.29704532, 3103698.436713734]], 'height': 9000.0, 'orientation': 2, 'id': 22})
# msg['available_zones'].append({'boundary': [[11466736.29704532, 3210771.436713734], [11516321.29704532, 3210771.436713734], [11516321.29704532, 3103698.436713734], [11466736.29704532, 3103698.436713734]], 'height': 9000.0, 'orientation': 2, 'id': 32})
# msg['road_zones'].append({'line': [[11396065.29704532, 3145269.436713734], [11467216.29704532, 3145269.436713734]], 'width': 3000.0, 'id': 15})
# msg['road_zones'].append({'line': [[11436626.29704532, 3161985.436713734], [11436626.29704532, 3105099.436713734]], 'width': 3000.0, 'id': 25})
# msg['cargos'].append({'weight': 1000, 'length': 1200, 'width': 1000, 'height': 1000, 'quantity': 1000000000, 'id': 14})

# msg['available_zones'].append({'boundary': [[11347625.29704532, 3208768.436713734], [11393438.29704532, 3208768.436713734], [11393438.29704532, 3164219.436713734], [11347625.29704532, 3164219.436713734]], 'height': 9000.0, 'orientation': 2, 'id': 12})
# msg['available_zones'].append({'boundary': [[11396913.29704532, 3209400.436713734], [11465791.29704532, 3209400.436713734], [11465791.29704532, 3163903.436713734], [11396913.29704532, 3163903.436713734]], 'height': 9000.0, 'orientation': 1, 'id': 22})
# msg['road_zones'].append({'line': [[11359947.29704532, 3209720.436713734], [11359947.29704532, 3162008.436713734]], 'width': 3000.0, 'id': 15})
# msg['road_zones'].append({'line': [[11384275.29704532, 3210668.436713734], [11384275.29704532, 3163904.436713734]], 'width': 3000.0, 'id': 25})
# msg['road_zones'].append({'line': [[11396281.29704532, 3203716.436713734], [11466423.29704532, 3203716.436713734]], 'width': 3000.0, 'id': 35})
# msg['road_zones'].append({'line': [[11396281.29704532, 3191393.436713734], [11467055.29704532, 3191393.436713734]], 'width': 3000.0, 'id': 45})
# msg['road_zones'].append({'line': [[11397229.29704532, 3179386.436713734], [11466423.29704532, 3179386.436713734]], 'width': 3000.0, 'id': 55})
# msg['cargos'].append({'weight': 1000, 'length': 1200, 'width': 1000, 'height': 1000, 'quantity': 1000000000, 'id': 14})

msg['available_zones'].append({"boundary": [[55006.94516390018, 39265.66322391065], [74978.94516390018, 39265.66322391065], [74978.94516390018, 30479.663223910648], [55006.94516390018, 30479.663223910648]], "height": 9000.0, 'orientation': 0, "id": 12})
msg['road_zones'].append({"line": [[65989.94516390018, 39226.66322391065], [65989.94516390018, 30363.663223910648]], "width": 3000.0, "id": 15})
msg['road_zones'].append({"line": [[54762.94516390018, 34510.66322391065], [75019.94516390018, 34510.66322391065]], "width": 3000.0, "id": 25})
msg['cargos'].append({"weight": 1000, "length": 1200, "width": 800, "height": 1000, "quantity": 1000000000, "id": 14})


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
