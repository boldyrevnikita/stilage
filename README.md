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

## Описание структуры репозитория
```
├── 📁 src
│   ├── 📁 network
│   │   ├── 📄 input_schema.py -- файл со схемой входных данных
│   │   ├── 📄 message_processors.py -- файл с определением функций для обработки входных сообщений
│   │   ├── 📄 network.py -- файл с определением классов `Sender` и `MessageHandler`
│   │   ├── 📄 output_generation.py -- файл с кодом приведения результатов модели к выходной схеме
│   │   ├── 📄 output_schema.py -- файл со схемой выходных данных
│   │   ├── 📄 settings.py -- файл со структрурой `Settings`, содержайщей сетевые настройки
│   │   └── 📄 utils.py -- файл с сетевыми утилитами
│   ├── 📁 pallet_packer
│   │   ├── 📁 actions -- модуль с функциями для выполнения действий по расстановке стеллажей
│   │   ├── 📄 pallet_packer.py -- файл с определением основного класса для расстановки стеллажей
│   │   ├── 📄 solution.py -- файл с определением структуры для хранения промежуточных и конечных решений
│   │   └── 📄 state_machine.py -- файл с определением класса, отвечающего за обработку графа состояний
│   ├── 📄 cargo_packer.py -- файл с кодом для упаковки грузов по соответствующим паллетам
│   ├── 📄 occupied_zone_scan.py -- файл с кодом для поиска "препятствий" в .dxf файле
│   ├── 📄 pallet.py -- файл с определением структур `PalletType`, `CargoType` и `Pallet`
│   ├── 📄 rack.py -- файл с определением классов `Rack`, `DoubleRack` и `RackGroup`
│   ├── 📄 reference_book.py -- файл с определением класса `ReferenceBook`
│   ├── 📄 utils.py
│   ├── 📄 visualize.py -- файл с кодом для отрисовки расстановки
│   └── 📄 zone.py -- файл с определением классов `AvailableZone`, `OccupiedZone`, `SpecialRoadZone`
├── 📄 app.py -- основной файл приложения (точка входа)
├── 📄 Dockerfile
├── 📄 README.md -- этот файл
└── 📄 requirements.txt -- файл с pip-зависимостями
```

Основная логика алгоритма расстановки стеллажей реализована в классах `PalletPacker`, `PalletPackerProcessor`, `StateMachine` и модуле `src/pallet_packer/actions`. `PalletPacker` является точкой входа в алгоритм, а также отвечает за создание процессов `PalletPackerProcessor`, которые выполняют действия по расстановке стеллажей. В `PalletPackerProcessor` содержится основной цикл расстановки стеллажей. В `StateMachine` реализована логика обработки переменных состояний, а в модуле `src/pallet_packer/actions` реализованы действия, которые выполняются в каждом состоянии.
