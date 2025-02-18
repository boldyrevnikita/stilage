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

Также перечисленные аргументы могут быть заданы в `.env` файле, тогда команда запуска будет выглядеть следующим образом:
```
python app.py
```

Описание аргументов:
- `host` - адрес RabbitMQ (`RABBIT_HOST`).
- `port` - порт RabbitMQ (`RABBIR_PORT`).
- `vhost` - виртуальный хост RabbitMQ (`RABBIT_VHOST`).
- `username` - имя пользователя RabbitMQ (`RABBIT_USER`).
- `password` - пароль пользователя RabbitMQ (`RABBIT_PASS`).
- `input_queue` - название очереди для входящих сообщений (`RABBIT_INPUT_QUEUE`).
- `output_queue` - название очереди для исходящих сообщений (`RABBIT_OUTPUT_QUEUE`).
- `output_routing_key` - ключ маршрутизации для исходящих сообщений (`RABBIT_OUTPUT_ROUTING_KEY`).
- `process` - функция для обработки входящего сообщения (`'ml'` или `'print'`) (`RABBIT_FUNC`).
- `heartbeat` - heartbeat-интервал для RabbitMQ (в секундах) (`RABBIT_HEARTBEAT`).


## Запуск в Docker
Перед запуском в докер обязательно должен быть задан файл `.env` с переменными окружения, описанными выше.

Для сборки контейнера требуется запусть следующую команду (данная операция необходима при первом запуске или изменение файлов проекта, в том числе и `.env`):
```
docker build --tag 'ml_racks_packer' .
```

Для запуска контейнера введите следующую команду:
```
docker run 'ml_racks_packer'
```
