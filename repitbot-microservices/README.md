# RepitBot Microservices Architecture

Микросервисная архитектура для системы управления репетиторством RepitBot.

## Архитектура

### Сервисы

1. **user-service** (порт 8001) - Управление пользователями
2. **auth-service** (порт 8002) - Аутентификация и авторизация
3. **lesson-service** (порт 8003) - Управление уроками
4. **homework-service** (порт 8004) - Управление домашними заданиями
5. **payment-service** (порт 8005) - Управление платежами
6. **notification-service** (порт 8006) - Уведомления
7. **material-service** (порт 8007) - Библиотека материалов
8. **analytics-service** (порт 8008) - Аналитика и отчеты
9. **achievement-service** (порт 8009) - Система достижений
10. **scheduler-service** (порт 8010) - Планировщик задач

### Инфраструктура

- **PostgreSQL** - Основная база данных
- **Redis** - Кэширование и очереди сообщений
- **RabbitMQ** - Брокер сообщений для межсервисного взаимодействия
- **API Gateway** - Маршрутизация запросов
- **Prometheus + Grafana** - Мониторинг
- **Jaeger** - Распределенная трассировка
- **ELK Stack** - Централизованное логирование

## Быстрый старт

### Разработка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd repitbot-microservices
```

2. Настройте переменные окружения:
```bash
cp .env.example .env
# Отредактируйте .env файл
```

3. Запустите инфраструктуру для разработки:
```bash
cd infrastructure/docker
docker-compose -f docker-compose.dev.yml up -d
```

4. Проверьте статус сервисов:
```bash
docker-compose -f docker-compose.dev.yml ps
```

### Доступные порты в режиме разработки

- **PostgreSQL**: 5432
- **Redis**: 6379
- **RabbitMQ Management**: 15672
- **Adminer** (DB admin): 8080
- **Prometheus**: 9090
- **Grafana**: 3000
- **Jaeger UI**: 16686
- **Kibana**: 5601
- **API Gateway**: 80

### Миграция данных

Для миграции данных из монолитного приложения:

```bash
cd scripts/migration
python migrate_current_to_microservices.py \\
    --source-db sqlite:///../../repitbot.db \\
    --target-db postgresql://repitbot:repitbot_dev_password@localhost:5432/repitbot_dev \\
    --batch-size 100 \\
    --dry-run
```

После проверки выполните миграцию:
```bash
python migrate_current_to_microservices.py \\
    --source-db sqlite:///../../repitbot.db \\
    --target-db postgresql://repitbot:repitbot_dev_password@localhost:5432/repitbot_dev \\
    --batch-size 100
```

## Структура проекта

```
repitbot-microservices/
├── services/                 # Микросервисы
│   ├── user-service/        # Сервис пользователей
│   ├── auth-service/        # Сервис аутентификации
│   ├── lesson-service/      # Сервис уроков
│   ├── homework-service/    # Сервис домашних заданий
│   ├── payment-service/     # Сервис платежей
│   ├── notification-service/# Сервис уведомлений
│   ├── material-service/    # Сервис материалов
│   ├── analytics-service/   # Сервис аналитики
│   ├── achievement-service/ # Сервис достижений
│   └── scheduler-service/   # Сервис планировщика
├── shared/                  # Общие компоненты
│   ├── events/             # События для межсервисного взаимодействия
│   ├── models/             # Общие модели данных
│   ├── utils/              # Утилиты
│   └── config/             # Базовые конфигурации
├── telegram-bot/           # Telegram бот
├── infrastructure/         # Инфраструктура
│   ├── docker/            # Docker Compose файлы
│   ├── kubernetes/        # Kubernetes манифесты
│   └── monitoring/        # Конфигурация мониторинга
├── scripts/               # Скрипты
│   ├── migration/        # Миграция данных
│   └── deployment/       # Деплой скрипты
└── docs/                 # Документация
    ├── architecture/     # Архитектурная документация
    └── api/             # API документация
```

## Разработка сервисов

### Создание нового сервиса

1. Создайте директорию сервиса:
```bash
mkdir services/new-service
cd services/new-service
```

2. Создайте структуру:
```bash
mkdir -p app/{api,core,db,models,schemas,services} tests migrations config
```

3. Используйте базовые настройки из `shared/config/base_settings.py`

4. Наследуйтесь от базовых моделей из `shared/models/base.py`

5. Используйте события из `shared/events/base.py` для межсервисного взаимодействия

### Стандарты разработки

- **FastAPI** для REST API
- **SQLAlchemy 2.0** для ORM
- **Pydantic v2** для валидации данных
- **Alembic** для миграций БД
- **pytest** для тестирования
- **async/await** для асинхронного кода
- **Type hints** обязательны
- **Логирование** в JSON формате

### API Gateway

Все внешние запросы проходят через API Gateway, который:
- Маршрутизирует запросы к соответствующим сервисам
- Выполняет аутентификацию и авторизацию
- Применяет rate limiting
- Логирует все запросы
- Выполняет трансформацию запросов/ответов

### Межсервисное взаимодействие

Сервисы взаимодействуют друг с другом через:
- **Events** - асинхронные события через RabbitMQ
- **HTTP API** - синхронные запросы через внутреннюю сеть
- **Shared Database** - только для чтения общих справочников

### Мониторинг и логирование

- **Метрики**: Prometheus + Grafana
- **Трассировка**: Jaeger для отслеживания запросов
- **Логирование**: ELK Stack для централизованных логов
- **Health Checks**: Каждый сервис предоставляет `/health` endpoint

### Тестирование

```bash
# Unit тесты
pytest services/user-service/tests/

# Integration тесты
pytest services/user-service/tests/integration/

# Contract тесты
pytest tests/contracts/

# Load тесты
locust -f tests/load/locustfile.py
```

### Деплой

#### Development
```bash
docker-compose -f infrastructure/docker/docker-compose.dev.yml up -d
```

#### Staging
```bash
docker-compose -f infrastructure/docker/docker-compose.yml --profile monitoring up -d
```

#### Production
```bash
docker stack deploy -c infrastructure/docker/docker-compose.prod.yml repitbot
```

## Переменные окружения

Основные переменные окружения для каждого сервиса:

```env
# Общие
ENVIRONMENT=development|staging|production
DEBUG=true|false
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR

# База данных
DATABASE_URL=postgresql://user:password@host:port/dbname
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://password@host:port/db
REDIS_PASSWORD=password

# RabbitMQ
MESSAGE_BROKER_URL=amqp://user:password@host:port/vhost
RABBITMQ_USER=repitbot
RABBITMQ_PASSWORD=password

# Безопасность
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
```

## API Документация

После запуска сервисов документация доступна по адресам:
- Swagger UI: `http://localhost:PORT/docs`
- ReDoc: `http://localhost:PORT/redoc`
- OpenAPI схема: `http://localhost:PORT/openapi.json`

## Мониторинг

### Grafana Dashboard
- URL: http://localhost:3000
- Логин: admin
- Пароль: repitbot_grafana_password

### Prometheus
- URL: http://localhost:9090

### Jaeger
- URL: http://localhost:16686

### RabbitMQ Management
- URL: http://localhost:15672
- Логин: repitbot
- Пароль: repitbot_rabbit_password

## Troubleshooting

### Часто встречающиеся проблемы

1. **Сервис не может подключиться к базе данных**
   ```bash
   # Проверьте статус PostgreSQL
   docker-compose -f docker-compose.dev.yml logs postgres
   
   # Проверьте переменные окружения
   docker-compose -f docker-compose.dev.yml config
   ```

2. **Ошибки миграции**
   ```bash
   # Сброс базы данных (ОСТОРОЖНО!)
   docker-compose -f docker-compose.dev.yml down -v
   docker-compose -f docker-compose.dev.yml up -d postgres
   ```

3. **Проблемы с сетью между сервисами**
   ```bash
   # Проверьте Docker сеть
   docker network inspect repitbot-microservices_repitbot-network
   ```

### Полезные команды

```bash
# Просмотр логов всех сервисов
docker-compose -f docker-compose.dev.yml logs -f

# Просмотр логов конкретного сервиса
docker-compose -f docker-compose.dev.yml logs -f user-service

# Рестарт сервиса
docker-compose -f docker-compose.dev.yml restart user-service

# Выполнение команды в контейнере
docker-compose -f docker-compose.dev.yml exec user-service bash

# Масштабирование сервиса
docker-compose -f docker-compose.dev.yml up -d --scale user-service=3
```

## Roadmap

### Этап 1: Инфраструктура (Неделя 1-2) ✅
- [x] Создание структуры проекта
- [x] Настройка Docker окружения
- [x] Shared компоненты
- [x] Скрипты миграции

### Этап 2: Базовые сервисы (Неделя 3-4)
- [ ] User Service
- [ ] Auth Service
- [ ] API Gateway
- [ ] Базовое тестирование

### Этап 3: Бизнес-сервисы (Неделя 5-6)
- [ ] Lesson Service
- [ ] Homework Service
- [ ] Payment Service
- [ ] Уведомления

### Этап 4: Дополнительные сервисы (Неделя 7-8)
- [ ] Material Service
- [ ] Achievement Service
- [ ] Analytics Service
- [ ] Scheduler Service

### Этап 5: Интеграция и оптимизация (Неделя 9-10)
- [ ] Telegram Bot интеграция
- [ ] Performance тестирование
- [ ] Мониторинг и алерты
- [ ] Production деплой

## Contributing

1. Создайте feature branch: `git checkout -b feature/new-feature`
2. Сделайте изменения и добавьте тесты
3. Убедитесь что все тесты проходят: `pytest`
4. Создайте Pull Request

## License

MIT License