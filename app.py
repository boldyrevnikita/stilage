import argparse
import asyncio
import logging
import time
import uuid
import sys
from datetime import datetime
from src.network import Settings

from src.network import (MessageHandler, Sender, process_message_ml,
                         process_message_print)


def setup_detailed_logging():
    """Настройка детального логирования с временными метками."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s.%(msecs)03d [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    logging.getLogger('aio_pika').setLevel(logging.INFO)
    logging.getLogger('aiormq').setLevel(logging.INFO)


async def main():
    """Асинхронная основная функция с детальным логированием."""
    session_id = str(uuid.uuid4())[:8]
    
    setup_detailed_logging()
    logger = logging.getLogger(__name__)
    
    logger.info(f"=" * 60)
    logger.info(f"Starting application session: {session_id}")
    logger.info(f"Start time: {datetime.now().isoformat()}")
    logger.info(f"=" * 60)
    
    start_time = time.time()
    
    try:
        logger.info(f"[{session_id}] Loading settings...")
        settings = Settings()
        logger.info(f"[{session_id}] Settings loaded successfully")
        
        logger.info(f"[{session_id}] Parsing command line arguments...")
        arg_parser = argparse.ArgumentParser()
        arg_parser.add_argument('--host', default=settings.RABBIT_HOST,
                                help='RabbitMQ host')
        arg_parser.add_argument('--port', type=int, default=settings.RABBIT_PORT,
                            help='RabbitMQ port')
        arg_parser.add_argument('--vhost', default=settings.RABBIT_VHOST,
                                help='RabbitMQ vhost')
        arg_parser.add_argument('--username', default=settings.RABBIT_USER,
                                help='RabbitMQ username')
        arg_parser.add_argument('--password', default=settings.RABBIT_PASS,
                                help='RabbitMQ password')
        arg_parser.add_argument('--input_queue',
                                default=settings.RABBIT_INPUT_QUEUE,
                                help='Input queue name')
        arg_parser.add_argument('--output_queue',
                                default=settings.RABBIT_OUTPUT_QUEUE,
                                help='Output queue name')
        arg_parser.add_argument('--output_routing_key',
                                default=settings.RABBIT_OUTPUT_ROUTING_KEY,
                                help='Input routing key')
        arg_parser.add_argument('--process', default=settings.PROCCESS_FUNC,
                                help='Message processing function')
        arg_parser.add_argument('--heartbeat', type=int, default=settings.RABBIT_HEARTBEAT,
                            help='RabbitMQ heartbeat')
        args = arg_parser.parse_args()
        
        logger.info(f"[{session_id}] Arguments parsed successfully")
        logger.info(f"[{session_id}] Configuration:")
        logger.info(f"   - Host: {args.host}:{args.port}")
        logger.info(f"   - VHost: {args.vhost}")
        logger.info(f"   - Username: {args.username}")
        logger.info(f"   - Input Queue: {args.input_queue}")
        logger.info(f"   - Output Queue: {args.output_queue}")
        logger.info(f"   - Process Type: {args.process}")
        logger.info(f"   - Heartbeat: {args.heartbeat}s")

        # Создание credentials
        logger.info(f"[{session_id}] Setting up credentials...")
        credentials = None
        if args.username and args.password:
            credentials = {
                'username': args.username,
                'password': args.password
            }
            logger.info(f"[{session_id}] Credentials configured")
        else:
            logger.warning(f"[{session_id}] No credentials provided")

        # Создание и подключение Sender
        logger.info(f"[{session_id}] Creating Sender...")
        sender_start = time.time()
        
        sender = Sender(
            host=args.host,
            queue_name=args.output_queue,
            routing_key=args.output_routing_key,
            port=args.port,
            vhost=args.vhost,
            credentials=credentials,
            heartbeat=args.heartbeat
        )
        
        logger.info(f"[{session_id}] Sender created in {time.time() - sender_start:.3f}s")
        
        # Подключение к RabbitMQ для отправки
        logger.info(f"[{session_id}] Connecting Sender to RabbitMQ...")
        connect_start = time.time()
        
        await sender.connect()
        
        connect_time = time.time() - connect_start
        logger.info(f"[{session_id}] Sender connected in {connect_time:.3f}s")
        
        # Создание MessageHandler
        logger.info(f"[{session_id}] Creating MessageHandler for process type: {args.process}")
        handler_start = time.time()
        
        if args.process == 'ml':
            logger.info(f"[{session_id}] Setting up ML message processor...")
            receiver = MessageHandler(
                host=args.host,
                queue_name=args.input_queue,
                msg_processor=process_message_ml,
                sender=sender,
                port=args.port,
                vhost=args.vhost,
                credentials=credentials,
                heartbeat=args.heartbeat
            )
        elif args.process == 'print':
            logger.info(f"[{session_id}] Setting up Print message processor...")
            receiver = MessageHandler(
                host=args.host,
                queue_name=args.input_queue,
                msg_processor=process_message_print,
                sender=sender,
                port=args.port,
                vhost=args.vhost,
                credentials=credentials,
                heartbeat=args.heartbeat
            )
        else:
            logger.error(f"[{session_id}] Unknown processing function: {args.process}")
            await sender.close()
            raise ValueError(f'Unknown processing function: {args.process}')

        handler_time = time.time() - handler_start
        logger.info(f"[{session_id}] MessageHandler created in {handler_time:.3f}s")

        # Подключение receiver
        logger.info(f"[{session_id}] Connecting MessageHandler to RabbitMQ...")
        receiver_connect_start = time.time()
        
        await receiver.connect()
        
        receiver_connect_time = time.time() - receiver_connect_start
        logger.info(f"[{session_id}] MessageHandler connected in {receiver_connect_time:.3f}s")

        total_setup_time = time.time() - start_time
        logger.info(f"[{session_id}] Total setup time: {total_setup_time:.3f}s")
        
        logger.info(f"=" * 60)
        logger.info(f" [{session_id}] Starting message processing...")
        logger.info(f" Processing type: {args.process}")
        logger.info(f" Listening on queue: {args.input_queue}")
        logger.info(f" Output queue: {args.output_queue}")
        logger.info(f" Heartbeat interval: {args.heartbeat}s")
        logger.info(f"=" * 60)
        
        processing_start = time.time()
        logger.info(f" [{session_id}] Entering message receive loop...")
        
        async def log_status():
            while True:
                await asyncio.sleep(30)  # Каждые 30 секунд
                uptime = time.time() - processing_start
                logger.info(f" [{session_id}] Service is alive, uptime: {uptime:.1f}s")
        
        status_task = asyncio.create_task(log_status())
        
        try:
            await receiver.receive()
        finally:
            status_task.cancel()
            try:
                await status_task
            except asyncio.CancelledError:
                pass
        
    except KeyboardInterrupt:
        logger.info(f"  [{session_id}] Received interrupt signal (Ctrl+C)")
        logger.info(f" [{session_id}] Initiating graceful shutdown...")
        
    except Exception as e:
        logger.error(f" [{session_id}] Critical error during message processing:")
        logger.error(f"   Error type: {type(e).__name__}")
        logger.error(f"   Error message: {str(e)}")
        logger.exception(f"   Full traceback:")
        raise
        
    finally:
        # Корректное закрытие соединений
        logger.info(f" [{session_id}] Closing connections...")
        cleanup_start = time.time()
        
        try:
            if 'receiver' in locals():
                logger.info(f" [{session_id}] Closing receiver connection...")
                await receiver.close()
                logger.info(f" [{session_id}] Receiver connection closed")
            else:
                logger.warning(f"  [{session_id}] Receiver was not initialized")
        except Exception as e:
            logger.error(f" [{session_id}] Error closing receiver: {e}")
        
        try:
            if 'sender' in locals():
                logger.info(f" [{session_id}] Closing sender connection...")
                await sender.close()
                logger.info(f" [{session_id}] Sender connection closed")
            else:
                logger.warning(f"  [{session_id}] Sender was not initialized")
        except Exception as e:
            logger.error(f" [{session_id}] Error closing sender: {e}")
        
        cleanup_time = time.time() - cleanup_start
        total_time = time.time() - start_time
        
        logger.info(f" [{session_id}] Cleanup completed in {cleanup_time:.3f}s")
        logger.info(f"  [{session_id}] Total session time: {total_time:.3f}s")
        logger.info(f" [{session_id}] Shutdown complete")
        logger.info(f"=" * 60)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.critical(f"💀 Fatal error in main: {e}")
        sys.exit(1)