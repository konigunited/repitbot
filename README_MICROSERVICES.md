# RepitBot - Микросервисная архитектура

## 🚀 Быстрый старт

### Этап 2: User Service & Auth Service

Данная реализация включает полноценные микросервисы для управления пользователями и аутентификации.

### ✨ Что реализовано

- ✅ **User Service** - полное управление пользователями
- ✅ **Auth Service** - JWT аутентификация и авторизация
- ✅ **HTTP клиенты** для Telegram бота
- ✅ **Fallback механизмы** для совместимости с монолитом
- ✅ **Docker конфигурации** для развертывания
- ✅ **API Gateway** с Nginx
- ✅ **Мониторинг** с Prometheus/Grafana

## 📋 Структура проекта

```
repitbot/
├── services/
│   ├── user-service/           # User Service микросервис
│   │   ├── app/
│   │   │   ├── models/         # SQLAlchemy модели
│   │   │   ├── schemas/        # Pydantic схемы
│   │   │   ├── services/       # Бизнес логика
│   │   │   ├── api/v1/         # REST API endpoints
│   │   │   ├── database/       # Подключение к БД
│   │   │   └── main.py         # FastAPI приложение
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   └── auth-service/           # Auth Service микросервис
│       ├── app/
│       │   ├── models/         # Модели токенов и сессий
│       │   ├── schemas/        # JWT схемы
│       │   ├── services/       # Логика аутентификации
│       │   ├── api/v1/         # Auth API endpoints
│       │   ├── core/           # JWT утилиты
│       │   └── main.py         # FastAPI приложение
│       ├── Dockerfile
│       └── requirements.txt
│
├── telegram-bot/
│   └── app/
│       └── services/           # HTTP клиенты для микросервисов
│           ├── api_client.py
│           ├── user_service_client.py
│           └── auth_service_client.py
│
├── docker-compose.microservices.yml
├── deploy-microservices.sh
└── MICROSERVICES_DEPLOYMENT.md
```

## 🔧 Установка и запуск

### 1. Предварительные требования

```bash
# Docker и Docker Compose
sudo apt install docker.io docker-compose

# Или для Windows
# Установите Docker Desktop
```

### 2. Настройка переменных окружения

```bash
# Скопируйте пример конфигурации
cp .env.example .env

# Отредактируйте переменные
nano .env
```

Обязательные переменные:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
```

### 3. Запуск микросервисной системы

```bash
# Сделайте скрипт исполняемым
chmod +x deploy-microservices.sh

# Запустите полное развертывание
./deploy-microservices.sh
```

Или вручную:
```bash
# Запуск через Docker Compose
docker-compose -f docker-compose.microservices.yml up -d --build
```

### 4. Проверка работоспособности

```bash
# Проверка статуса сервисов
docker-compose -f docker-compose.microservices.yml ps

# Health checks
curl http://localhost:8001/health  # User Service
curl http://localhost:8002/health  # Auth Service
curl http://localhost:8080/health  # API Gateway

# Просмотр логов
docker-compose -f docker-compose.microservices.yml logs -f
```

## 🌐 Доступные сервисы

| Сервис | URL | Документация |
|--------|-----|--------------|
| API Gateway | http://localhost:8080 | http://localhost:8080/docs |
| User Service | http://localhost:8001 | http://localhost:8001/docs |
| Auth Service | http://localhost:8002 | http://localhost:8002/docs |
| PostgreSQL | localhost:5432 | - |
| Redis | localhost:6379 | - |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3000 | admin/admin |

## 🏗️ Архитектура микросервисов

### User Service (Port 8001)

**Назначение:** Управление пользователями, профилями и данными.

**Основные функции:**
- CRUD операции с пользователями
- Валидация кодов доступа
- Управление баллами и streak
- Статистика пользователей

**API Endpoints:**
```
POST   /api/v1/users/                     # Создание пользователя
GET    /api/v1/users/                     # Список пользователей (с пагинацией)
GET    /api/v1/users/{id}                 # Получение пользователя по ID
GET    /api/v1/users/telegram/{id}        # Получение по Telegram ID
PUT    /api/v1/users/{id}                 # Обновление пользователя
DELETE /api/v1/users/{id}                 # Удаление пользователя
POST   /api/v1/users/validate-access-code # Валидация кода доступа
POST   /api/v1/users/{id}/points          # Обновление баллов
POST   /api/v1/users/{id}/streak          # Обновление streak
GET    /api/v1/users/stats                # Статистика
```

### Auth Service (Port 8002)

**Назначение:** Аутентификация, авторизация и управление токенами.

**Основные функции:**
- JWT аутентификация
- Управление токенами и сессиями
- Проверка прав доступа
- Журналирование безопасности

**API Endpoints:**
```
POST   /api/v1/auth/login                 # Логин по коду доступа
POST   /api/v1/auth/refresh               # Обновление токена
POST   /api/v1/auth/validate              # Валидация токена
POST   /api/v1/auth/logout                # Выход из системы
POST   /api/v1/auth/check-permission      # Проверка прав
GET    /api/v1/auth/me                    # Информация о пользователе
POST   /api/v1/auth/sessions              # Создание сессии
GET    /api/v1/auth/stats                 # Статистика аутентификации
```

## 🔄 Режимы работы

### 1. Микросервисный режим (по умолчанию)

```python
ENABLE_MICROSERVICES = True
FALLBACK_TO_MONOLITH = True
```

- Все запросы идут через микросервисы
- При сбое автоматический переход на монолит
- Рекомендуется для production

### 2. Только микросервисы

```python
ENABLE_MICROSERVICES = True
FALLBACK_TO_MONOLITH = False
```

- Только микросервисы, без fallback
- Для тестирования микросервисной архитектуры

### 3. Монолитный режим

```python
ENABLE_MICROSERVICES = False
FALLBACK_TO_MONOLITH = True
```

- Работа в старом режиме
- Для обратной совместимости

## 🔍 Мониторинг и отладка

### Логирование

```bash
# Все сервисы
docker-compose -f docker-compose.microservices.yml logs -f

# Конкретный сервис
docker-compose -f docker-compose.microservices.yml logs -f user-service
docker-compose -f docker-compose.microservices.yml logs -f auth-service
docker-compose -f docker-compose.microservices.yml logs -f telegram-bot

# Логи за последние 10 минут
docker-compose -f docker-compose.microservices.yml logs --since=10m
```

### Метрики (Prometheus)

Доступно по адресу: http://localhost:9090

Ключевые метрики:
- HTTP запросы и латентность
- Ошибки аутентификации
- Статус здоровья сервисов
- Использование ресурсов

### Дашборды (Grafana)

Доступно по адресу: http://localhost:3000 (admin/admin)

Доступные дашборды:
- Обзор системы
- Метрики микросервисов
- Статистика пользователей
- Мониторинг базы данных

## 🛠️ Управление системой

### Команды развертывания

```bash
./deploy-microservices.sh build     # Только сборка
./deploy-microservices.sh start     # Только запуск
./deploy-microservices.sh stop      # Остановка
./deploy-microservices.sh restart   # Перезапуск
./deploy-microservices.sh health    # Проверка здоровья
./deploy-microservices.sh logs      # Просмотр логов
./deploy-microservices.sh clean     # Полная очистка
```

### Docker Compose команды

```bash
# Запуск всех сервисов
docker-compose -f docker-compose.microservices.yml up -d

# Остановка
docker-compose -f docker-compose.microservices.yml down

# Пересборка
docker-compose -f docker-compose.microservices.yml up -d --build

# Масштабирование
docker-compose -f docker-compose.microservices.yml up -d --scale user-service=3
```

## 🔐 Безопасность

### JWT токены

- **Access tokens:** 15 минут
- **Refresh tokens:** 30 дней
- Автоматическая ротация
- Безопасное хранение в памяти

### Права доступа

- **Tutor:** полные права
- **Student:** только свои данные
- **Parent:** данные детей

### Аудит

- Логирование всех действий
- Журнал аутентификации
- Мониторинг подозрительной активности

## 🚨 Troubleshooting

### Частые проблемы

**PostgreSQL не запускается:**
```bash
docker-compose -f docker-compose.microservices.yml logs postgres
docker-compose -f docker-compose.microservices.yml down -v  # Очистка volumes
```

**Микросервисы не подключаются к БД:**
```bash
# Проверка переменных
docker-compose -f docker-compose.microservices.yml exec user-service env | grep DATABASE

# Проверка доступности
docker-compose -f docker-compose.microservices.yml exec user-service nc -z postgres 5432
```

**Telegram Bot не работает:**
```bash
# Проверка токена
docker-compose -f docker-compose.microservices.yml exec telegram-bot env | grep TELEGRAM_BOT_TOKEN

# Проверка связи с микросервисами
docker-compose -f docker-compose.microservices.yml exec telegram-bot curl http://user-service:8001/health
```

### Отладка в контейнерах

```bash
# Подключение к контейнеру
docker-compose -f docker-compose.microservices.yml exec user-service bash

# Проверка БД
docker-compose -f docker-compose.microservices.yml exec postgres psql -U repitbot -d repitbot

# Мониторинг ресурсов
docker stats
```

## 📚 Документация API

### User Service API

Полная документация: http://localhost:8001/docs

Примеры запросов:

```bash
# Получение пользователя
curl -X GET "http://localhost:8001/api/v1/users/1"

# Валидация кода доступа
curl -X POST "http://localhost:8001/api/v1/users/validate-access-code" \
  -H "Content-Type: application/json" \
  -d '{"access_code": "ABC12345", "telegram_id": 123456789}'

# Обновление баллов
curl -X POST "http://localhost:8001/api/v1/users/1/points" \
  -H "Content-Type: application/json" \
  -d '{"points_to_add": 10, "reason": "completed homework"}'
```

### Auth Service API

Полная документация: http://localhost:8002/docs

Примеры запросов:

```bash
# Аутентификация
curl -X POST "http://localhost:8002/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"access_code": "ABC12345", "telegram_id": 123456789}'

# Валидация токена
curl -X POST "http://localhost:8002/api/v1/auth/validate" \
  -H "Content-Type: application/json" \
  -d '{"token": "your_jwt_token_here"}'

# Проверка прав
curl -X POST "http://localhost:8002/api/v1/auth/check-permission" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "resource": "users", "action": "read"}'
```

## 🔄 Миграция с монолита

### Поэтапная стратегия

1. **Этап 1:** Развертывание микросервисов параллельно
2. **Этап 2:** Постепенное переключение функций
3. **Этап 3:** Отключение монолитных компонентов

### Feature flags

Переключение режимов осуществляется через переменные окружения:

```env
ENABLE_MICROSERVICES=true      # Включить микросервисы
FALLBACK_TO_MONOLITH=true      # Разрешить fallback
```

### Совместимость данных

- Микросервисы используют те же модели данных
- Автоматическая синхронизация при fallback
- Безопасное переключение без потери данных

## 🚀 Production готовность

### Обязательные изменения:

1. **Безопасность:**
   ```env
   JWT_SECRET_KEY=random-256-bit-key
   POSTGRES_PASSWORD=strong-password
   ```

2. **Масштабирование:**
   - Load balancer
   - Автоскейлинг
   - Отдельные БД для сервисов

3. **Мониторинг:**
   - Настройка алертов
   - Интеграция с внешними системами
   - Ротация логов

## 📈 Следующие этапы

### Этап 3: Lesson Service (Недели 5-6)
- Микросервис управления уроками
- Интеграция с календарем
- Уведомления и напоминания

### Этап 4: Homework Service (Недели 7-8)
- Микросервис домашних заданий
- File storage для фото
- Автоматическая проверка

### Этап 5: Notification Service (Недели 9-10)
- Централизованные уведомления
- Email и SMS интеграция
- Push уведомления

## 🤝 Поддержка

Для получения помощи:

1. **Документация:** Изучите `MICROSERVICES_DEPLOYMENT.md`
2. **Логи:** Проверьте логи сервисов
3. **Метрики:** Посмотрите дашборды в Grafana
4. **API:** Используйте /docs endpoints для тестирования
5. **Issues:** Создайте issue в репозитории

---

**Автор:** Claude Code Assistant  
**Версия:** 1.0.0  
**Дата:** 2025-01-11