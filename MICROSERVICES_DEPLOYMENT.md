# Развертывание микросервисной архитектуры RepitBot

## Обзор архитектуры

RepitBot теперь поддерживает микросервисную архитектуру с следующими компонентами:

### Микросервисы
- **User Service** (Port 8001) - управление пользователями
- **Auth Service** (Port 8002) - аутентификация и авторизация
- **Telegram Bot** - Telegram бот с поддержкой микросервисов

### Инфраструктура
- **PostgreSQL** (Port 5432) - основная база данных
- **Redis** (Port 6379) - кэширование и сессии
- **API Gateway** (Port 8080) - Nginx reverse proxy
- **Prometheus** (Port 9090) - мониторинг метрик
- **Grafana** (Port 3000) - дашборды и визуализация

## Быстрый запуск

### 1. Предварительные требования

```bash
# Установите Docker и Docker Compose
sudo apt update
sudo apt install docker.io docker-compose
sudo usermod -aG docker $USER
```

### 2. Настройка переменных окружения

```bash
# Создайте файл .env
cp .env.example .env

# Отредактируйте .env
nano .env
```

Обязательные переменные:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
```

### 3. Развертывание

```bash
# Сделайте скрипт исполняемым
chmod +x deploy-microservices.sh

# Запустите развертывание
./deploy-microservices.sh
```

### 4. Проверка работоспособности

После развертывания проверьте:

```bash
# Статус сервисов
docker-compose -f docker-compose.microservices.yml ps

# Логи
docker-compose -f docker-compose.microservices.yml logs -f

# Health checks
curl http://localhost:8001/health  # User Service
curl http://localhost:8002/health  # Auth Service
curl http://localhost:8080/health  # API Gateway
```

## Архитектура сервисов

### User Service

**Назначение:** Управление пользователями, их данными и профилями.

**API Endpoints:**
- `GET /api/v1/users` - список пользователей
- `POST /api/v1/users` - создание пользователя
- `GET /api/v1/users/{id}` - получение пользователя
- `PUT /api/v1/users/{id}` - обновление пользователя
- `DELETE /api/v1/users/{id}` - удаление пользователя
- `POST /api/v1/users/validate-access-code` - валидация кода доступа

**Технологии:**
- FastAPI + SQLAlchemy 2.0
- PostgreSQL
- Async/await
- Pydantic v2

### Auth Service

**Назначение:** Аутентификация, авторизация, управление токенами и сессиями.

**API Endpoints:**
- `POST /api/v1/auth/login` - аутентификация по коду доступа
- `POST /api/v1/auth/refresh` - обновление токена
- `POST /api/v1/auth/validate` - валидация токена
- `POST /api/v1/auth/logout` - выход из системы
- `POST /api/v1/auth/check-permission` - проверка прав доступа

**Технологии:**
- FastAPI + JWT
- PostgreSQL
- bcrypt для хэширования
- Role-based access control

### Telegram Bot

**Назначение:** Интерфейс для пользователей через Telegram.

**Особенности:**
- HTTP клиенты для взаимодействия с микросервисами
- Fallback режим (работа с монолитом при недоступности микросервисов)
- Feature flags для переключения между режимами
- Автоматическое переключение при сбоях

## Режимы работы

### 1. Полный микросервисный режим

```python
ENABLE_MICROSERVICES = True
FALLBACK_TO_MONOLITH = False
```

Все операции выполняются через микросервисы.

### 2. Гибридный режим (рекомендуется)

```python
ENABLE_MICROSERVICES = True
FALLBACK_TO_MONOLITH = True
```

Приоритет микросервисам, fallback к монолиту при сбоях.

### 3. Монолитный режим

```python
ENABLE_MICROSERVICES = False
FALLBACK_TO_MONOLITH = True
```

Только монолитная архитектура.

## Конфигурация

### Docker Compose

Основной файл: `docker-compose.microservices.yml`

```yaml
services:
  postgres:      # База данных
  redis:         # Кэш
  user-service:  # User Service
  auth-service:  # Auth Service
  telegram-bot:  # Telegram Bot
  api-gateway:   # Nginx API Gateway
  prometheus:    # Мониторинг
  grafana:       # Дашборды
```

### Переменные окружения

#### User Service
```env
USER_SERVICE_DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
USER_SERVICE_HOST=0.0.0.0
USER_SERVICE_PORT=8001
DEBUG=false
```

#### Auth Service
```env
AUTH_SERVICE_DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
AUTH_SERVICE_HOST=0.0.0.0
AUTH_SERVICE_PORT=8002
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
```

#### Telegram Bot
```env
TELEGRAM_BOT_TOKEN=your_bot_token
USER_SERVICE_URL=http://user-service:8001
AUTH_SERVICE_URL=http://auth-service:8002
ENABLE_MICROSERVICES=true
FALLBACK_TO_MONOLITH=true
```

## Мониторинг и логирование

### Prometheus метрики

Доступно по адресу: http://localhost:9090

Собираются метрики:
- HTTP запросы и латентность
- Статус здоровья сервисов
- Использование ресурсов
- Ошибки и исключения

### Grafana дашборды

Доступно по адресу: http://localhost:3000 (admin/admin)

Предустановленные дашборды:
- Обзор системы
- Метрики микросервисов
- Мониторинг базы данных
- Статистика Telegram бота

### Логирование

```bash
# Логи всех сервисов
docker-compose -f docker-compose.microservices.yml logs -f

# Логи конкретного сервиса
docker-compose -f docker-compose.microservices.yml logs -f user-service
docker-compose -f docker-compose.microservices.yml logs -f auth-service
docker-compose -f docker-compose.microservices.yml logs -f telegram-bot

# Логи с фильтрацией по времени
docker-compose -f docker-compose.microservices.yml logs --since=10m user-service
```

## Управление системой

### Команды развертывания

```bash
# Полное развертывание
./deploy-microservices.sh

# Только сборка
./deploy-microservices.sh build

# Только запуск
./deploy-microservices.sh start

# Остановка
./deploy-microservices.sh stop

# Перезапуск
./deploy-microservices.sh restart

# Проверка здоровья
./deploy-microservices.sh health

# Логи
./deploy-microservices.sh logs

# Очистка
./deploy-microservices.sh clean
```

### Docker Compose команды

```bash
# Запуск всех сервисов
docker-compose -f docker-compose.microservices.yml up -d

# Остановка
docker-compose -f docker-compose.microservices.yml down

# Пересборка и запуск
docker-compose -f docker-compose.microservices.yml up -d --build

# Масштабирование сервиса
docker-compose -f docker-compose.microservices.yml up -d --scale user-service=3

# Обновление сервиса
docker-compose -f docker-compose.microservices.yml up -d --no-deps user-service
```

## Troubleshooting

### Проблемы с запуском

**PostgreSQL не стартует:**
```bash
# Проверьте логи
docker-compose -f docker-compose.microservices.yml logs postgres

# Очистите volumes
docker-compose -f docker-compose.microservices.yml down -v
```

**Микросервисы не подключаются к БД:**
```bash
# Проверьте строку подключения
docker-compose -f docker-compose.microservices.yml exec user-service env | grep DATABASE_URL

# Проверьте доступность PostgreSQL
docker-compose -f docker-compose.microservices.yml exec user-service nc -z postgres 5432
```

**Telegram Bot не работает:**
```bash
# Проверьте токен
docker-compose -f docker-compose.microservices.yml exec telegram-bot env | grep TELEGRAM_BOT_TOKEN

# Проверьте соединение с микросервисами
docker-compose -f docker-compose.microservices.yml exec telegram-bot curl http://user-service:8001/health
```

### Проблемы с производительностью

**Медленные запросы:**
1. Проверьте метрики в Prometheus
2. Увеличьте таймауты в конфигурации
3. Проверьте индексы в PostgreSQL

**Высокая нагрузка:**
1. Масштабируйте сервисы: `docker-compose up -d --scale user-service=3`
2. Настройте кэширование в Redis
3. Оптимизируйте SQL запросы

### Отладка

```bash
# Подключение к контейнеру
docker-compose -f docker-compose.microservices.yml exec user-service bash

# Проверка базы данных
docker-compose -f docker-compose.microservices.yml exec postgres psql -U repitbot -d repitbot

# Проверка Redis
docker-compose -f docker-compose.microservices.yml exec redis redis-cli

# Мониторинг ресурсов
docker stats
```

## Миграция с монолита

### Поэтапная миграция

1. **Этап 1:** Развертывание микросервисов параллельно с монолитом
2. **Этап 2:** Постепенное переключение функций на микросервисы
3. **Этап 3:** Полное отключение монолитных компонентов

### Стратегия данных

1. **Репликация:** Синхронизация данных между монолитом и микросервисами
2. **Event Sourcing:** Использование событий для синхронизации
3. **API Gateway:** Роутинг запросов между старой и новой системами

## Безопасность

### JWT токены

- Секретный ключ должен быть уникальным для каждой среды
- Время жизни access токенов: 15 минут
- Время жизни refresh токенов: 30 дней
- Токены автоматически отзываются при logout

### Сетевая безопасность

- Микросервисы изолированы в Docker сети
- API Gateway как единая точка входа
- Rate limiting на уровне Nginx
- HTTPS в production

### Мониторинг безопасности

- Логирование всех аутентификационных событий
- Мониторинг подозрительной активности
- Автоматические алерты при аномалиях

## Production готовность

### Обязательные изменения для production:

1. **Переменные окружения:**
   - Уникальные секретные ключи
   - Сложные пароли для БД
   - HTTPS сертификаты

2. **База данных:**
   - Отдельные БД для каждого сервиса
   - Репликация и бэкапы
   - Мониторинг производительности

3. **Мониторинг:**
   - Настройка алертов
   - Интеграция с внешними системами
   - Ротация логов

4. **Масштабирование:**
   - Load balancer
   - Автоскейлинг
   - Распределение по зонам доступности

## Поддержка

Для получения помощи:
1. Проверьте логи сервисов
2. Изучите метрики в Prometheus/Grafana
3. Обратитесь к документации API (/docs endpoints)
4. Создайте issue в репозитории проекта