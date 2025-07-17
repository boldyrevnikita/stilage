import json
from typing import Any, Callable, Optional, Union

import pika
import time
from pika import exceptions


class Sender:
    def __init__(self, host: str, queue_name: str, routing_key: str,
                 port: Optional[Union[int, str]] = None,
                 vhost: Optional[str] = None,
                 credentials: Optional[pika.PlainCredentials] = None,
                 heartbeat: int = 1800,
                 reconnection_attempts: int = 5):
        self.queue_name = queue_name
        self.routing_key = routing_key

        if port is None:
            port = pika.ConnectionParameters._DEFAULT
        if credentials is None:
            credentials = pika.ConnectionParameters._DEFAULT
        if vhost is None:
            vhost = pika.ConnectionParameters._DEFAULT

        self.host = host
        self.port = port
        self.vhost = vhost
        self.credentials = credentials
        self.heartbeat = heartbeat
        self.reconnection_attempts = reconnection_attempts
        self.connection = None
        self.channel = None
        self.connect()

    def connect(self):
        """Establish connection to the message queue.
        """
        try:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=self.host, port=self.port,
                                          virtual_host=self.vhost,
                                          credentials=self.credentials,
                                          heartbeat=self.heartbeat))
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.queue_name, auto_delete=True)
        except Exception as e:
            print(f"An error occurred: {e}")

    def send(self, message: Any):
        """Send message to the queue.

        Args:
            message (Any): message to send
        """
        attempts = 0

        while attempts < self.reconnection_attempts:
            try:
                self.channel.basic_publish(exchange='',
                                           routing_key=self.routing_key,
                                           body=json.dumps(message))
                break
            except exceptions.StreamLostError:
                print("Stream lost")
            except Exception:
                print("An error occurred while sending the message")
            finally:
                self.connect()
                attempts += 1
                time.sleep(1)

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

        self.host = host
        self.port = port
        self.vhost = vhost
        self.credentials = credentials
        self.heartbeat = heartbeat
        self.connection = None
        self.channel = None
        self.connect()

    def connect(self):
        """Establish connection to the message queue.
        """
        try:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=self.host, port=self.port,
                                          virtual_host=self.vhost,
                                          credentials=self.credentials,
                                          heartbeat=self.heartbeat))
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.queue_name, auto_delete=True)
        except Exception as e:
            print(f"An error occurred: {e}")

    def receive(self):
        """Start receiving messages from the queue.
        """
        while True:
            try:
                self.channel.basic_consume(
                    queue=self.queue_name,
                    on_message_callback=self.callback,
                    auto_ack=True)
                self.channel.start_consuming()
                break
            except exceptions.StreamLostError:
                self.connect()

    def callback(self, ch, method, properties, body):
        """Callback function for message processing.
        """
        object_body = json.loads(body)
        self.msg_processor(object_body, self.sender)

    def close(self):
        """Close the connection.
        """
        self.connection.close()
