import json
import traceback
from typing import Any, Callable, Optional, Union

import pika

from src.available_zone import AvailableZone
from src.packer import Packer
from src.rack_info import RackInfo


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
    rack_infos = []

    print('Message received')

    try:
        for zone in message['available_zones']:
            available_zones.append(AvailableZone(zone['boundary'],
                                                 zone['height']))

        for rack_info in message['rack_types']:
            rack_infos.append(RackInfo(
                id=rack_info['id'],
                length=rack_info['length'],
                width=rack_info['width'],
                height=rack_info['height'],
                abs_quantity=rack_info['absolute'],
                min_quantity=rack_info['min'],
                rel_quantity=rack_info['relative'],
                max_quantity=rack_info['max'],
                side_connection_distance=rack_info[
                    'side_connection_clearance'],
                back_connection_distance=rack_info[
                    'back_connection_clearance'],
                front_distance=rack_info['front_clearance'],
                side_distance=rack_info['side_clearance'],
                back_distance=rack_info['back_clearance']))

        packer = Packer(available_zones, rack_infos)
        packer.pack()

        racks = {}
        for rack_group in packer.rack_groups:
            rack_id = str(rack_group.rack_info.id)

            if rack_id not in racks:
                racks[rack_id] = []

            for rack in rack_group.racks:
                racks[rack_id].append(
                    list(zip(*rack.exterior.xy)))
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
