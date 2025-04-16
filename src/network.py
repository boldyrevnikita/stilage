import json
import traceback
from typing import Any, Callable, Optional, Union

import pika

from src.available_zone import AvailableZone
from src.forbidden_zone import ForbiddenZone, RoadZone
from src.packer import Packer
from src.postprocess import postprocess
from src.preprocess import preprocess
from src.rack import RackSection


class Sender:
    def __init__(self, host: str, queue_name: str, routing_key: str,
                 port: Optional[Union[int, str]] = None,
                 vhost: Optional[str] = None,
                 credentials: Optional[pika.PlainCredentials] = None,
                 heartbeat: int = 1800):
        self.queue_name = queue_name
        self.routing_key = routing_key

        if port is None:
            port = pika.ConnectionParameters._DEFAULT
        if credentials is None:
            credentials = pika.ConnectionParameters._DEFAULT
        if vhost is None:
            vhost = pika.ConnectionParameters._DEFAULT

        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=host, port=port, virtual_host=vhost, credentials=credentials,
            heartbeat=heartbeat))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue_name,
                                   auto_delete=True)

    def send(self, message: Any):
        """Send message to the queue.

        Args:
            message (Any): message to send
        """
        self.channel.basic_publish(exchange='', routing_key=self.routing_key,
                                   body=json.dumps(message))

    def close(self):
        """Close the connection.
        """
        self.connection.close()


class MessageHandler:
    def __init__(self, host: str, queue_name: str,
                 msg_processor: Callable[[Any, Sender], None] =
                 lambda m, s: print(m),
                 sender: Optional[Sender] = None,
                 port: Optional[Union[int, str]] = None,
                 vhost: Optional[str] = None,
                 credentials: Optional[pika.PlainCredentials] = None,
                 heartbeat: int = 1800):
        self.queue_name = queue_name
        self.msg_processor = msg_processor
        self.sender = sender

        if port is None:
            port = pika.ConnectionParameters._DEFAULT
        if credentials is None:
            credentials = pika.ConnectionParameters._DEFAULT
        if vhost is None:
            vhost = pika.ConnectionParameters._DEFAULT

        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=host, port=port, virtual_host=vhost, credentials=credentials,
            heartbeat=heartbeat))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue_name,
                                   auto_delete=True)

    def receive(self):
        """Start receiving messages from the queue.
        """
        self.channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=self.callback,
            auto_ack=True)
        self.channel.start_consuming()

    def callback(self, ch, method, properties, body):
        """Callback function for message processing.
        """
        object_body = json.loads(body)
        self.msg_processor(object_body, self.sender)

    def close(self):
        """Close the connection.
        """
        self.connection.close()


def process_message_ml(message: Any, sender: Sender):
    """Process message from the queue.

    Args:
        message (Any): message to process
        sender (Sender): sender to send the results
    """
    available_zones = []
    forbidden_zones = []
    road_zones = []
    rack_sections = []

    print('Message received')

    try:
        for zone in message['available_zones']:
            available_zones.append(AvailableZone(zone['boundary'],
                                                 zone['height']))

        for zone in message['road_zones']:
            road_zones.append(RoadZone(zone['line'],
                                       zone['width']))

        for zone in message['restricted_zones']:
            forbidden_zones.append(ForbiddenZone(zone['boundary'],
                                                 zone['clearance']))

        for rack_section in message['rack_types']:
            rack_sections.append(RackSection(
                id=rack_section['id'],
                unit_length=rack_section['unit_length'],
                width=rack_section['width'],
                height_0=rack_section['height_0'],
                height_i=rack_section['height_i'],
                height_delta=rack_section['height_delta'],
                min_unit_shelf_quantity=rack_section[
                    'min_unit_shelf_quantity'],
                max_unit_shelf_quantity=rack_section[
                    'max_unit_shelf_quantity'],
                abs_quantity=rack_section['absolute'],
                min_quantity=rack_section['min'],
                rel_quantity=rack_section['relative'],
                max_quantity=rack_section['max'],
                pillar_width=rack_section[
                    'pillar_width'],
                back_connection_distance=rack_section[
                    'back_connection_clearance'],
                front_distance=rack_section['front_clearance'],
                side_distance=rack_section['side_clearance'],
                back_distance=rack_section['back_clearance']))

        roads_width = message['roads_width']
        available_zones, forbidden_zones, rack_sections = preprocess(
            available_zones, forbidden_zones, rack_sections, roads_width)

        packer = Packer(available_zones, rack_sections)
        rack_groups = packer.pack()
        rack_groups = postprocess(rack_groups, road_zones, forbidden_zones)

        racks = {}
        for rack_group in rack_groups:
            rack_id = str(rack_group.rack_section_info.id)

            if rack_id not in racks:
                racks[rack_id] = []

            for rack in rack_group.racks:
                rack_info = {
                    'boundary': list(zip(*rack.get_exterior().xy)),
                    'sections_in_length': rack.get_sections_in_length(),
                    'sections_in_width': rack.get_sections_in_width(),
                    'sections_in_height': rack.get_sections_in_height(),
                    'units': rack.get_shelfs_length_unit_quantity(),
                    "special_units": rack.get_shelfs_special(),
                    'orientation': 0
                }
                racks[rack_id].append(rack_info)
    except Exception:
        print(traceback.format_exc())
        output_message = {
            'task_id': message['task_id'],
            'racks': {},
            'warnings_and_errors':  traceback.format_exc(),
            'success_predict': False
        }
        sender.send(output_message)
        return

    output_message = {
        'task_id': message['task_id'],
        'racks': racks,
        'warnings_and_errors': '',
        'success_predict': True
    }

    sender.send(output_message)
    print('Results sent')


def process_message_print(message: Any, sender: Sender):
    """Process message from the queue.

    Args:
        message (Any): message to process
        sender (Sender): sender to send the results
    """
    print('Got Message')
    print(message)
