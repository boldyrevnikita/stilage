import json
import asyncio
import logging
import time
import uuid
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
        self.sender_id = str(uuid.uuid4())[:8]
        self.logger = logging.getLogger(f"Sender[{self.sender_id}]")
        
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
        
        self.logger.info(f"Initializing Sender: host={self.host}:{self.port}, "
                        f"vhost={self.vhost}, queue={self.queue_name}, "
                        f"routing_key={self.routing_key}, heartbeat={self.heartbeat}s")

    async def connect(self):
        """Establish robust connection to the message queue."""
        self.logger.info(f"Starting connection to RabbitMQ...")
        connect_start = time.time()
        
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
                self.logger.debug(f"Using credentials for user: {self.credentials.get('username', 'guest')}")
            else:
                self.logger.debug("No credentials provided, using defaults")
            
            self.logger.debug(f"Connection parameters: {connection_params}")
            
            self.logger.info(f"Establishing robust connection...")
            self.connection = await connect_robust(**connection_params)
            connection_time = time.time() - connect_start
            self.logger.info(f"Connection established in {connection_time:.3f}s")
            
            self.logger.info(f"Creating channel...")
            channel_start = time.time()
            self.channel = await self.connection.channel()
            channel_time = time.time() - channel_start
            self.logger.info(f"Channel created in {channel_time:.3f}s")
            
            self.logger.info(f"Declaring queue: {self.queue_name}")
            queue_start = time.time()
            self.queue = await self.channel.declare_queue(
                self.queue_name, 
                auto_delete=True
            )
            queue_time = time.time() - queue_start
            self.logger.info(f"Queue '{self.queue_name}' declared in {queue_time:.3f}s")
            
            total_connect_time = time.time() - connect_start
            self.logger.info(f"Sender fully connected in {total_connect_time:.3f}s")
            
        except Exception as e:
            connect_time = time.time() - connect_start
            self.logger.error(f"Failed to connect to RabbitMQ after {connect_time:.3f}s: {e}")
            self.logger.exception("Connection error details:")
            raise

    async def send(self, message: Any):
        """Send message to the queue.
        
        Args:
            message (Any): message to send
        """
        message_id = str(uuid.uuid4())[:8]
        self.logger.info(f"Preparing to send message [ID: {message_id}]")
        send_start = time.time()
        
        if (not self.connection or self.connection.is_closed or
            not self.channel or self.channel.is_closed):
            self.logger.warning(f"Connection/channel is closed, reconnecting...")
            reconnect_start = time.time()
            await self.connect()
            reconnect_time = time.time() - reconnect_start
            self.logger.info(f"Reconnection completed in {reconnect_time:.3f}s")
            
        try:
            self.logger.debug(f"Serializing message [ID: {message_id}]: {type(message)}")
            serialize_start = time.time()
            message_body = json.dumps(message).encode()
            serialize_time = time.time() - serialize_start
            
            message_size = len(message_body)
            self.logger.debug(f"Message [ID: {message_id}] serialized in {serialize_time:.3f}s, size: {message_size} bytes")
            
            self.logger.debug(f"Creating aio_pika Message [ID: {message_id}]")
            aio_message = Message(body=message_body)
            
            self.logger.info(f"Publishing message [ID: {message_id}] to routing_key: {self.routing_key}")
            publish_start = time.time()
            
            await self.channel.default_exchange.publish(
                aio_message,
                routing_key=self.routing_key
            )
            
            publish_time = time.time() - publish_start
            total_send_time = time.time() - send_start
            
            self.logger.info(f"Message [ID: {message_id}] sent successfully in {total_send_time:.3f}s "
                           f"(publish: {publish_time:.3f}s)")
            
        except Exception as e:
            send_time = time.time() - send_start
            self.logger.error(f"Failed to send message [ID: {message_id}] after {send_time:.3f}s: {e}")
            self.logger.exception("Send error details:")
            # connect_robust should handle reconnection automatically
            raise

    async def close(self):
        """Close the connection."""
        self.logger.info(f"Closing Sender connection...")
        close_start = time.time()
        
        if self.connection and not self.connection.is_closed:
            try:
                await self.connection.close()
                close_time = time.time() - close_start
                self.logger.info(f"Sender connection closed successfully in {close_time:.3f}s")
            except Exception as e:
                close_time = time.time() - close_start
                self.logger.error(f"Error closing Sender connection after {close_time:.3f}s: {e}")
                raise
        else:
            self.logger.warning(f"Sender connection was already closed or None")


class MessageHandler:
    """Async class for handling messages from a message queue."""
    
    def __init__(self, host: str, queue_name: str,
                 msg_processor: Callable[[Any, Optional[Sender]], None] = None,
                 sender: Optional[Sender] = None,
                 port: Optional[Union[int, str]] = None,
                 vhost: Optional[str] = None,
                 credentials: Optional[dict] = None,
                 heartbeat: int = 1800):
        self.handler_id = str(uuid.uuid4())[:8]
        self.logger = logging.getLogger(f"MessageHandler[{self.handler_id}]")
        
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
        
        self.message_count = 0
        self.start_time = None
        
        self.logger.info(f"Initializing MessageHandler: host={self.host}:{self.port}, "
                        f"vhost={self.vhost}, queue={self.queue_name}, "
                        f"heartbeat={self.heartbeat}s")
        self.logger.info(f"Processor function: {self.msg_processor.__name__ if hasattr(self.msg_processor, '__name__') else 'custom'}")
        self.logger.info(f"Sender attached: {'Yes' if self.sender else 'No'}")

    async def connect(self):
        """Establish robust connection to the message queue."""
        self.logger.info(f"Starting connection to RabbitMQ...")
        connect_start = time.time()
        
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
                self.logger.debug(f"Using credentials for user: {self.credentials.get('username', 'guest')}")
            else:
                self.logger.debug("No credentials provided, using defaults")
            
            self.logger.debug(f"Connection parameters: {connection_params}")
            
            self.logger.info(f"Establishing robust connection...")
            self.connection = await connect_robust(**connection_params)
            connection_time = time.time() - connect_start
            self.logger.info(f"Connection established in {connection_time:.3f}s")
            
            self.logger.info(f"Creating channel...")
            channel_start = time.time()
            self.channel = await self.connection.channel()
            channel_time = time.time() - channel_start
            self.logger.info(f"Channel created in {channel_time:.3f}s")
            
            self.logger.info(f"Declaring queue: {self.queue_name}")
            queue_start = time.time()
            self.queue = await self.channel.declare_queue(
                self.queue_name, 
                auto_delete=True
            )
            queue_time = time.time() - queue_start
            self.logger.info(f"Queue '{self.queue_name}' declared in {queue_time:.3f}s")
            
            total_connect_time = time.time() - connect_start
            self.logger.info(f"MessageHandler fully connected in {total_connect_time:.3f}s")
            
        except Exception as e:
            connect_time = time.time() - connect_start
            self.logger.error(f"Failed to connect to RabbitMQ after {connect_time:.3f}s: {e}")
            self.logger.exception("Connection error details:")
            raise

    async def _default_processor(self, message: Any, sender: Optional[Sender]):
        """Default message processor."""
        self.logger.info(f"Default processor received message: {message}")
        print(f"Received message: {message}")

    async def _process_message(self, message: aio_pika.IncomingMessage):
        """Process incoming message."""
        message_id = str(uuid.uuid4())[:8]
        self.message_count += 1
        
        self.logger.info(f"Received message [ID: {message_id}] (total: {self.message_count})")
        process_start = time.time()
        
        try:
            async with message.process():
                self.logger.debug(f"Processing message [ID: {message_id}]...")
                
                # Декодирование сообщения
                decode_start = time.time()
                body = json.loads(message.body.decode())
                decode_time = time.time() - decode_start
                
                message_size = len(message.body)
                self.logger.debug(f"Message [ID: {message_id}] decoded in {decode_time:.3f}s, "
                                f"size: {message_size} bytes, type: {type(body)}")
                
                # Обработка сообщения
                processor_start = time.time()
                self.logger.info(f"Starting message processor for [ID: {message_id}]...")
                
                if asyncio.iscoroutinefunction(self.msg_processor):
                    self.logger.debug(f"Running async processor for [ID: {message_id}]")
                    await self.msg_processor(body, self.sender)
                else:
                    self.logger.debug(f"Running sync processor for [ID: {message_id}]")
                    self.msg_processor(body, self.sender)
                
                processor_time = time.time() - processor_start
                total_process_time = time.time() - process_start
                
                self.logger.info(f"Message [ID: {message_id}] processed successfully in {total_process_time:.3f}s "
                               f"(processor: {processor_time:.3f}s)")
                
                # Статистика каждые 10 сообщений
                if self.message_count % 10 == 0:
                    if self.start_time:
                        elapsed = time.time() - self.start_time
                        rate = self.message_count / elapsed
                        self.logger.info(f"Processing statistics: {self.message_count} messages, "
                                       f"{elapsed:.1f}s elapsed, {rate:.2f} msg/s")
                    
        except Exception as e:
            process_time = time.time() - process_start
            self.logger.error(f"Error processing message [ID: {message_id}] after {process_time:.3f}s: {e}")
            self.logger.exception("Message processing error details:")

    async def start_consuming(self):
        """Start consuming messages from the queue."""
        self.logger.info(f"Starting message consumption...")
        self.start_time = time.time()
        
        if (not self.connection or self.connection.is_closed or
            not self.channel or self.channel.is_closed):
            self.logger.warning(f"Connection/channel is closed, reconnecting...")
            reconnect_start = time.time()
            await self.connect()
            reconnect_time = time.time() - reconnect_start
            self.logger.info(f"Reconnection completed in {reconnect_time:.3f}s")
            
        try:
            self.logger.info(f"Setting up consumer for queue: {self.queue_name}")
            consume_start = time.time()
            
            await self.queue.consume(self._process_message)
            
            consume_time = time.time() - consume_start
            self.logger.info(f"Consumer set up in {consume_time:.3f}s")
            self.logger.info(f"MessageHandler is now consuming messages from '{self.queue_name}'...")
            
            # Keep consuming forever until interrupted
            try:
                # Wait indefinitely 
                self.logger.debug(f"Entering infinite wait loop...")
                await asyncio.Future()
            except asyncio.CancelledError:
                self.logger.info(f"Message consumption was cancelled")
                pass
                
        except Exception as e:
            self.logger.error(f"Error during message consumption: {e}")
            self.logger.exception("Consumption error details:")
            raise

    async def receive(self):
        """Alias for start_consuming() for backward compatibility."""
        self.logger.debug(f"receive() called - delegating to start_consuming()")
        await self.start_consuming()

    async def close(self):
        """Close the connection."""
        self.logger.info(f"Closing MessageHandler connection...")
        close_start = time.time()
        
        if self.start_time:
            total_runtime = time.time() - self.start_time
            rate = self.message_count / total_runtime if total_runtime > 0 else 0
            self.logger.info(f"Final statistics: {self.message_count} messages processed, "
                           f"runtime: {total_runtime:.1f}s, average rate: {rate:.2f} msg/s")
        
        if self.connection and not self.connection.is_closed:
            try:
                await self.connection.close()
                close_time = time.time() - close_start
                self.logger.info(f"MessageHandler connection closed successfully in {close_time:.3f}s")
            except Exception as e:
                close_time = time.time() - close_start
                self.logger.error(f"Error closing MessageHandler connection after {close_time:.3f}s: {e}")
                raise
        else:
            self.logger.warning(f"MessageHandler connection was already closed or None")


# Пример использования
async def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s.%(msecs)03d [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    logger = logging.getLogger("main")
    session_id = str(uuid.uuid4())[:8]
    
    logger.info(f"=" * 60)
    logger.info(f"Starting example session: {session_id}")
    logger.info(f"=" * 60)
    
    # Создание отправителя
    logger.info(f"Creating Sender...")
    sender = Sender(
        host='localhost',
        queue_name='test_queue',
        routing_key='test_queue',
        credentials={'username': 'guest', 'password': 'guest'}
    )
    
    await sender.connect()
    
    # Отправка сообщения
    logger.info(f"Sending test message...")
    await sender.send({'message': 'Hello, World!', 'timestamp': '2024-01-01'})
    
    # Создание обработчика сообщений
    async def custom_processor(message: dict, sender_instance: Sender):
        logger.info(f"Custom processor received: {message}")
        print(f"Processing: {message}")
        # Можно отправить ответ через sender_instance если нужно
        
    logger.info(f"Creating MessageHandler...")
    handler = MessageHandler(
        host='localhost',
        queue_name='test_queue',
        msg_processor=custom_processor,
        sender=sender,
        credentials={'username': 'guest', 'password': 'guest'}
    )
    
    await handler.connect()
    
    # Запуск обработки сообщений
    try:
        logger.info(f"Starting message consumption...")
        await handler.start_consuming()
        
        # Держим программу запущенной
        await asyncio.sleep(10)
        
    except KeyboardInterrupt:
        logger.info(f"Stopping session: {session_id}")
    finally:
        logger.info(f"Closing connections...")
        await handler.close()
        await sender.close()
        logger.info(f"Session {session_id} completed")


if __name__ == "__main__":
    asyncio.run(main())