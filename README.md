# ML-cервис для расстановки стеллажей

## Установка
1. Установите Python 3.10.
2. Установите зависимости:
```
pip install -r requirements.txt
```

## Запуск сервиса
```
python app.py --host <host> --port <port> --vhost <vhost> --username <username> --password <password> --input_queue <input_queue> --output_queue <output_queue> --output_routing_key <output_routing_key> --process <process-function-for-received-message> --heartbeat <heartbeat-interval>
```

Описание аргументов:
- `host` - адрес RabbitMQ.
- `port` - порт RabbitMQ.
- `vhost` - виртуальный хост RabbitMQ.
- `username` - имя пользователя RabbitMQ.
- `password` - пароль пользователя RabbitMQ.
- `input_queue` - название очереди для входящих сообщений.
- `output_queue` - название очереди для исходящих сообщений.
- `output_routing_key` - ключ маршрутизации для исходящих сообщений.
- `process` - функция для обработки входящего сообщения (`'ml'` или `'print'`).
- `heartbeat` - heartbeat-интервал для RabbitMQ (в секундах).
