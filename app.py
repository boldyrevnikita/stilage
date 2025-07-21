import argparse
import pika
from src.network import Settings

from src.network import (MessageHandler, Sender, process_message_ml,
                         process_message_print)


if __name__ == '__main__':
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

    credentials = None
    if args.username and args.password:
        credentials = pika.PlainCredentials(username=args.username,
                                            password=args.password)

    sender = Sender(args.host, args.output_queue,
                    args.output_routing_key, args.port, args.vhost,
                    credentials,
                    args.heartbeat)
    if args.process == 'ml':
        receiver = MessageHandler(args.host, args.input_queue,
                                  process_message_ml, sender,
                                  args.port, args.vhost, credentials,
                                  args.heartbeat)
    elif args.process == 'print':
        receiver = MessageHandler(args.host, args.input_queue,
                                  process_message_print, sender,
                                  args.port, args.vhost, credentials,
                                  args.heartbeat)
    else:
        raise ValueError(f'Unknown processing function: {args.process}')

    receiver.receive()
    receiver.close()
    sender.close()
