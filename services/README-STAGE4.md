# RepitBot Microservices - Stage 4: Payment & Material Services

Этап 4 реализации микросервисной архитектуры RepitBot включает в себя:
- Payment Service (управление платежами и балансами)
- Material Service (библиотека материалов и файлы)

## 🏗️ Архитектура

### Payment Service (Port 8003)
```
payment-service/
├── app/
│   ├── main.py                 # FastAPI приложение
│   ├── models/payment.py       # SQLAlchemy модели
│   ├── schemas/payment.py      # Pydantic схемы
│   ├── services/
│   │   ├── payment_service.py  # Бизнес-логика платежей
│   │   └── balance_service.py  # Логика балансов
│   ├── api/v1/payments.py      # REST API endpoints
│   ├── events/payment_events.py # События платежей
│   ├── database/connection.py  # DB подключение
│   └── core/config.py          # Конфигурация
├── alembic/                    # Database migrations
├── requirements.txt
└── Dockerfile
```

### Material Service (Port 8004)
```
material-service/
├── app/
│   ├── main.py                 # FastAPI приложение
│   ├── models/material.py      # SQLAlchemy модели
│   ├── schemas/material.py     # Pydantic схемы
│   ├── services/
│   │   ├── material_service.py # Бизнес-логика материалов
│   │   └── file_service.py     # Управление файлами
│   ├── api/v1/materials.py     # REST API endpoints
│   ├── events/material_events.py # События материалов
│   ├── storage/file_storage.py # Файловое хранилище
│   └── core/config.py          # Конфигурация
├── alembic/                    # Database migrations
├── requirements.txt
└── Dockerfile
```

## 🚀 Развертывание

### Предварительные требования
- Docker и Docker Compose
- Python 3.11+ (для разработки)
- PostgreSQL 15+ (для продакшена)

### Быстрый старт
```bash
# Клонирование репозитория
cd services/

# Сборка и запуск сервисов
docker-compose -f docker-compose.payment-material.yml up --build

# Проверка состояния сервисов
curl http://localhost:8003/health  # Payment Service
curl http://localhost:8004/health  # Material Service
```

### Локальная разработка

#### Payment Service
```bash
cd payment-service/

# Установка зависимостей
pip install -r requirements.txt

# Настройка переменных окружения
export ENVIRONMENT=development
export DATABASE_URL=sqlite+aiosqlite:///./payment_service.db

# Создание миграций
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head

# Запуск сервиса
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8003
```

#### Material Service
```bash
cd material-service/

# Установка зависимостей
pip install -r requirements.txt

# Установка системных зависимостей (Ubuntu/Debian)
sudo apt-get install libmagic1 libjpeg-dev libpng-dev

# Настройка переменных окружения
export ENVIRONMENT=development
export DATABASE_URL=sqlite+aiosqlite:///./material_service.db
export UPLOAD_DIR=./dev_uploads

# Создание миграций
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head

# Запуск сервиса
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8004
```

## 🔧 Конфигурация

### Переменные окружения

#### Payment Service
```bash
# Сервис
SERVICE_NAME=payment-service
SERVICE_VERSION=1.0.0
HOST=0.0.0.0
PORT=8003
DEBUG=false

# База данных
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/payment_db
DATABASE_POOL_SIZE=10

# Redis (кеширование)
REDIS_URL=redis://localhost:6379/2

# RabbitMQ (события)
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_EXCHANGE=repitbot_events

# Платежи
DEFAULT_PRICE_PER_LESSON=1000.00
CURRENCY=RUB
MAX_BALANCE=1000
ENABLE_NEGATIVE_BALANCE=false

# Внешние сервисы
USER_SERVICE_URL=http://localhost:8001
LESSON_SERVICE_URL=http://localhost:8002
```

#### Material Service
```bash
# Сервис
SERVICE_NAME=material-service
SERVICE_VERSION=1.0.0
HOST=0.0.0.0
PORT=8004
DEBUG=false

# База данных
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/material_db

# Файловое хранилище
STORAGE_TYPE=local
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=104857600  # 100MB
ALLOWED_FILE_TYPES=pdf,doc,docx,jpg,png,mp4

# Redis (кеширование)
REDIS_URL=redis://localhost:6379/3

# Внешние сервисы
USER_SERVICE_URL=http://localhost:8001
LESSON_SERVICE_URL=http://localhost:8002
```

## 📊 API Endpoints

### Payment Service API (http://localhost:8003)

#### Платежи
- `POST /api/v1/payments` - создание платежа
- `GET /api/v1/payments/{payment_id}` - получение платежа
- `GET /api/v1/payments` - список платежей с фильтрами
- `POST /api/v1/payments/quick` - быстрая оплата
- `POST /api/v1/payments/{payment_id}/cancel` - отмена платежа

#### Балансы
- `GET /api/v1/balances/{student_id}` - баланс студента
- `GET /api/v1/balances/{student_id}/simple` - простой баланс
- `POST /api/v1/balances/add` - пополнение баланса
- `POST /api/v1/balances/deduct` - списание с баланса
- `POST /api/v1/balances/{student_id}/recalculate` - пересчет баланса

#### Транзакции
- `GET /api/v1/transactions/{student_id}` - история транзакций

### Material Service API (http://localhost:8004)

#### Материалы
- `POST /api/v1/materials` - создание материала
- `GET /api/v1/materials/{material_id}` - получение материала
- `PUT /api/v1/materials/{material_id}` - обновление материала
- `DELETE /api/v1/materials/{material_id}` - удаление материала
- `GET /api/v1/materials` - поиск материалов с фильтрами
- `GET /api/v1/materials/grade/{grade}` - материалы по классу
- `GET /api/v1/materials/stats` - статистика материалов

#### Файлы
- `POST /api/v1/materials/{material_id}/files` - загрузка файла
- `GET /api/v1/files/{file_id}/download` - скачивание файла
- `PUT /api/v1/files/{file_id}` - обновление файла
- `DELETE /api/v1/files/{file_id}` - удаление файла

#### Категории
- `POST /api/v1/categories` - создание категории
- `GET /api/v1/categories` - список категорий

## 🔄 Event-Driven Architecture

### События Payment Service
```python
# Исходящие события
PaymentProcessed      # При создании платежа
BalanceUpdated       # При изменении баланса
BalanceDeducted      # При списании урока
BalanceRefunded      # При возврате урока

# Входящие события
LessonCompleted      # Из Lesson Service - списать урок
LessonCancelled      # Из Lesson Service - возврат (если excused)
StudentCreated       # Из User Service - создать баланс
```

### События Material Service
```python
# Исходящие события
MaterialCreated      # При создании материала
FileUploaded        # При загрузке файла
MaterialAccessed    # При просмотре/скачивании

# Входящие события
UserCreated         # Из User Service - настроить рекомендации
LessonCreated       # Из Lesson Service - предложить материалы
```

## 🧪 Тестирование

### Unit тесты
```bash
# Payment Service
cd payment-service/
pytest tests/unit/ -v

# Material Service
cd material-service/
pytest tests/unit/ -v
```

### Integration тесты
```bash
# Запуск тестовых сервисов
docker-compose -f docker-compose.test.yml up -d

# Payment Service интеграционные тесты
cd payment-service/
pytest tests/integration/ -v

# Material Service интеграционные тесты
cd material-service/
pytest tests/integration/ -v
```

### API тесты
```bash
# Проверка Payment Service API
curl -X POST http://localhost:8003/api/v1/payments/quick \
  -H "Content-Type: application/json" \
  -d '{"student_id": 1, "lessons_count": 4}'

# Проверка Material Service API
curl -X GET http://localhost:8004/api/v1/materials/grade/5
```

## 🔍 Мониторинг и логирование

### Health Checks
```bash
# Проверка всех сервисов
curl http://localhost:8003/health
curl http://localhost:8004/health
```

### Логи
```bash
# Docker logs
docker logs repitbot-payment-service
docker logs repitbot-material-service

# Файловые логи
tail -f payment-service/logs/payment_service.log
tail -f material-service/logs/material_service.log
```

### Метрики
- Доступны через `/metrics` endpoint каждого сервиса
- Интеграция с Prometheus/Grafana (настраивается отдельно)

## 🔒 Безопасность

### Финансовые операции (Payment Service)
- ACID транзакции для всех платежных операций
- Идемпотентность платежей
- Audit trail для всех финансовых транзакций
- Валидация балансов
- Double-entry bookkeeping принципы
- Rate limiting для платежных операций

### Файловая безопасность (Material Service)
- Валидация типов файлов
- Ограничения размера файлов
- Изоляция файлов пользователей
- Сканирование на вирусы (опционально)
- Контроль доступа к файлам

## 🚀 Развертывание в продакшене

### Docker Compose (Production)
```bash
# Создание продакшен конфигурации
cp docker-compose.payment-material.yml docker-compose.prod.yml

# Настройка переменных окружения
export ENVIRONMENT=production
export DATABASE_URL=postgresql+asyncpg://...
export SECRET_KEY=your-super-secret-key

# Запуск в продакшене
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes
```yaml
# Примеры манифестов в папке k8s/
kubectl apply -f k8s/payment-service/
kubectl apply -f k8s/material-service/
```

## 🔧 Миграция данных

### Из монолитного приложения
```bash
# Скрипт миграции платежей
python scripts/migrate_payments.py

# Скрипт миграции материалов
python scripts/migrate_materials.py
```

## 📚 Дополнительная информация

### Документация API
- Payment Service: http://localhost:8003/docs
- Material Service: http://localhost:8004/docs

### Архитектурные диаграммы
- См. папку `docs/architecture/`

### Troubleshooting
- См. `docs/troubleshooting.md`

## 🤝 Интеграция с Telegram Bot

Новые HTTP клиенты созданы в `telegram-bot/app/services/`:
- `payment_service_client.py` - клиент для Payment Service
- `material_service_client.py` - клиент для Material Service

Новые handlers созданы в `telegram-bot/app/handlers/`:
- `payment_handlers.py` - обработка платежей в боте
- `material_handlers.py` - работа с материалами в боте