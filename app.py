import argparse
import pika

from src.network import (MessageHandler, Sender, process_message_ml,
                         process_message_print)

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('--host', default='localhost', help='RabbitMQ host')
arg_parser.add_argument('--port', default=None, help='RabbitMQ port')
arg_parser.add_argument('--vhost', default=None, help='RabbitMQ vhost')
arg_parser.add_argument('--username', default=None,
                        help='RabbitMQ username')
arg_parser.add_argument('--password', default=None,
                        help='RabbitMQ password')
arg_parser.add_argument('--input_queue', default='task_queue',
                        help='Input queue name')
arg_parser.add_argument('--output_queue', default='result_queue',
                        help='Output queue name')
arg_parser.add_argument('--output_routing_key', default='result_queue',
                        help='Input routing key')
arg_parser.add_argument('--process', default='ml',
                        help='Message processing function')
arg_parser.add_argument('--heartbeat', default=1800,
                        help='RabbitMQ heartbeat')
args = arg_parser.parse_args()

credentials = None
if args.username and args.password:
    credentials = pika.PlainCredentials(username=args.username,
                                        password=args.password)

sender = Sender(args.host, args.output_queue,
                args.output_routing_key, args.port, args.vhost, credentials,
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
