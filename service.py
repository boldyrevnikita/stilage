import argparse

from src.network import (Receiver, Sender, process_message_ml,
                         process_message_print)

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('--host', default='localhost', help='RabbitMQ host')
arg_parser.add_argument('--port', default=5672, help='RabbitMQ port')
arg_parser.add_argument('--input_queue', default='task_queue',
                        help='Input queue name')
arg_parser.add_argument('--output_queue', default='result_queue',
                        help='Output queue name')
arg_parser.add_argument('--output_routing_key', default='result_queue',
                        help='Input routing key')
arg_parser.add_argument('--process', default='ml',
                        help='Message processing function')
args = arg_parser.parse_args()

sender = Sender(args.host, args.port, args.output_queue,
                args.output_routing_key)
if args.process == 'ml':
    receiver = Receiver(args.host, args.port, args.input_queue,
                        process_message_ml, sender)
elif args.process == 'print':
    receiver = Receiver(args.host, args.port, args.input_queue,
                        process_message_print, sender)
else:
    raise ValueError(f'Unknown processing function: {args.process}')
receiver.receive()
receiver.close()
sender.close()
