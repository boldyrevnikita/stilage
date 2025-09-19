import json
import asyncio
import logging
from typing import Any, Callable, Optional, Union

import aio_pika
from aio_pika import connect_robust, Message
from aio_pika.abc import AbstractConnection, AbstractChannel, AbstractQueue


class Sender:
    """Async class for sending messages to a message queue."""
    
    def __init__(self, host: str, queue_name: str, routing_key: str,
                 port: Optional[Union[int, str]] = None,
                 vhost: Optional[str] = None,
                 credentials: Optional[dict] = None,
                 heartbeat: int = 1800):
        self.host = host
        self.port = port or 5672
        self.vhost = vhost or '/'
        self.credentials = credentials
        self.queue_name = queue_name
        self.routing_key = routing_key
        self.heartbeat = heartbeat
        
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.queue: Optional[AbstractQueue] = None

    async def connect(self):
        """Establish robust connection to the message queue."""
        try:
            connection_params = {
                'host': self.host,
                'port': self.port,
                'virtualhost': self.vhost,
                'heartbeat': self.heartbeat
            }
            
            if self.credentials:
                connection_params.update({
                    'login': self.credentials.get('username', 'guest'),
                    'password': self.credentials.get('password', 'guest')
                })
            
            self.connection = await connect_robust(**connection_params)
            self.channel = await self.connection.channel()
            self.queue = await self.channel.declare_queue(
                self.queue_name, 
                auto_delete=True
            )
            
        except Exception as e:
            logging.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def send(self, message: Any):
        """Send message to the queue.
        
        Args:
            message (Any): message to send
        """
        if not self.connection or self.connection.is_closed:
            await self.connect()
            
        try:
            message_body = json.dumps(message).encode()
            aio_message = Message(body=message_body)
            
            await self.channel.default_exchange.publish(
                aio_message,
                routing_key=self.routing_key
            )
            
        except Exception as e:
            logging.error(f"Failed to send message: {e}")
            # connect_robust should handle reconnection automatically
            raise

    async def close(self):
        """Close the connection."""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()


class RobustMessageHandler:
    """Async class for handling messages from a message queue."""
    
    def __init__(self, host: str, queue_name: str,
                 msg_processor: Callable[[Any, Optional[RobustSender]], None] = None,
                 sender: Optional[RobustSender] = None,
                 port: Optional[Union[int, str]] = None,
                 vhost: Optional[str] = None,
                 credentials: Optional[dict] = None,
                 heartbeat: int = 1800):
        self.host = host
        self.port = port or 5672
        self.vhost = vhost or '/'
        self.credentials = credentials
        self.queue_name = queue_name
        self.heartbeat = heartbeat
        
        self.msg_processor = msg_processor or self._default_processor
        self.sender = sender
        
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.queue: Optional[AbstractQueue] = None

    async def connect(self):
        """Establish robust connection to the message queue."""
        try:
            connection_params = {
                'host': self.host,
                'port': self.port,
                'virtualhost': self.vhost,
                'heartbeat': self.heartbeat
            }
            
            if self.credentials:
                connection_params.update({
                    'login': self.credentials.get('username', 'guest'),
                    'password': self.credentials.get('password', 'guest')
                })
            
            self.connection = await connect_robust(**connection_params)
            self.channel = await self.connection.channel()
            self.queue = await self.channel.declare_queue(
                self.queue_name, 
                auto_delete=True
            )
            
        except Exception as e:
            logging.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def _default_processor(self, message: Any, sender: Optional[RobustSender]):
        """Default message processor."""
        print(f"Received message: {message}")

    async def _process_message(self, message: aio_pika.IncomingMessage):
        """Process incoming message."""
        try:
            async with message.process():
                body = json.loads(message.body.decode())
                
                if asyncio.iscoroutinefunction(self.msg_processor):
                    await self.msg_processor(body, self.sender)
                else:
                    self.msg_processor(body, self.sender)
                    
        except Exception as e:
            logging.error(f"Error processing message: {e}")

    async def start_consuming(self):
        """Start consuming messages from the queue."""
        if not self.connection or self.connection.is_closed:
            await self.connect()
            
        try:
            await self.queue.consume(self._process_message)
            
        except Exception as e:
            logging.error(f"Error during message consumption: {e}")
            raise

    async def close(self):
        """Close the connection."""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()


async def main():
    logging.basicConfig(level=logging.INFO)
    
    sender = RobustSender(
        host='localhost',
        queue_name='test_queue',
        routing_key='test_queue',
        credentials={'username': 'guest', 'password': 'guest'}
    )
    
    await sender.connect()
    
    await sender.send({'message': 'Hello, World!', 'timestamp': '2024-01-01'})
    
    async def custom_processor(message: dict, sender_instance: RobustSender):
        print(f"Processing: {message}")
        
    handler = RobustMessageHandler(
        host='localhost',
        queue_name='test_queue',
        msg_processor=custom_processor,
        sender=sender,
        credentials={'username': 'guest', 'password': 'guest'}
    )
    
    await handler.connect()
    
    try:
        print("Starting message consumption...")
        await handler.start_consuming()
        
        await asyncio.sleep(10)
        
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        await handler.close()
        await sender.close()


if __name__ == "__main__":
    asyncio.run(main())