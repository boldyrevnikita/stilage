import json
from typing import Any, Callable, Optional, Union

import pika


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
