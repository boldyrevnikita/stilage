import argparse
import asyncio
import logging
from src.network import Settings

from src.network import (MessageHandler, Sender, process_message_ml,
                         process_message_print)


async def main():
    """Асинхронная основная функция."""
    settings = Settings()
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--host', default=settings.RABBIT_HOST,
                            help='RabbitMQ host')
    arg_parser.add_argument('--port', default=settings.RABBIT_PORT,
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
    arg_parser.add_argument('--heartbeat', default=settings.RABBIT_HEARTBEAT,
                            help='RabbitMQ heartbeat')
    args = arg_parser.parse_args()

    # Настройка логирования
    logging.basicConfig(level=logging.INFO)

    # Создаем credentials как словарь для aio_pika
    credentials = None
    if args.username and args.password:
        credentials = {
            'username': args.username,
            'password': args.password
        }

    # Создаем sender
    sender = Sender(
        host=args.host,
        queue_name=args.output_queue,
        routing_key=args.output_routing_key,
        port=args.port,
        vhost=args.vhost,
        credentials=credentials,
        heartbeat=args.heartbeat
    )
    
    # Подключаемся к RabbitMQ
    await sender.connect()
    
    # Создаем receiver в зависимости от типа обработки
    if args.process == 'ml':
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
        await sender.close()
        raise ValueError(f'Unknown processing function: {args.process}')

    # Подключаем receiver
    await receiver.connect()

    try:
        logging.info(f"Starting message processing with '{args.process}' handler...")
        logging.info(f"Listening on queue: {args.input_queue}")
        logging.info(f"Output queue: {args.output_queue}")
        
        # Запускаем обработку сообщений (будет работать до прерывания)
        await receiver.receive()
        
    except KeyboardInterrupt:
        logging.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logging.error(f"Error during message processing: {e}")
        raise
    finally:
        # Корректно закрываем соединения
        logging.info("Closing connections...")
        await receiver.close()
        await sender.close()
        logging.info("Shutdown complete")


if __name__ == '__main__':
    asyncio.run(main())