# RepitBot - Финальная микросервисная архитектура

## 📋 Обзор системы

RepitBot теперь представляет собой полноценную микросервисную архитектуру, состоящую из **9 основных сервисов** и **API Gateway** для централизованного управления.

### 🏗️ Архитектура системы

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Telegram Bot      │    │    Web Frontend     │    │   Mobile App        │
└─────────┬───────────┘    └─────────┬───────────┘    └─────────┬───────────┘
          │                          │                          │
          └──────────────────────────┼──────────────────────────┘
                                     │
                         ┌─────────────────────┐
                         │   API Gateway       │
                         │   (Port 8000)       │
                         └─────────┬───────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
    ┌─────┴─────┐            ┌─────┴─────┐          ┌─────┴─────┐
    │ User      │            │ Lesson    │          │ Homework  │
    │ Service   │            │ Service   │          │ Service   │
    │(Port 8001)│            │(Port 8002)│          │(Port 8003)│
    └───────────┘            └───────────┘          └───────────┘
          │                        │                        │
    ┌─────┴─────┐            ┌─────┴─────┐          ┌─────┴─────┐
    │ Payment   │            │ Material  │          │Notification│
    │ Service   │            │ Service   │          │ Service   │
    │(Port 8004)│            │(Port 8005)│          │(Port 8006)│
    └───────────┘            └───────────┘          └───────────┘
          │                        │                        │
    ┌─────┴─────┐            ┌─────┴─────┐          ┌─────┴─────┐
    │Analytics  │            │ Student   │          │  Event    │
    │ Service   │            │ Service   │          │   Bus     │
    │(Port 8007)│            │(Port 8008)│          │(RabbitMQ) │
    └───────────┘            └───────────┘          └───────────┘
          │                        │                        │
          └────────────────────────┼────────────────────────┘
                                   │
                         ┌─────────────────────┐
                         │    Infrastructure   │
                         │ PostgreSQL + Redis  │
                         │ Prometheus + Grafana│
                         └─────────────────────┘
```

## 🎯 Сервисы и их функционал

### 1. **API Gateway** (Port 8000)
- **Назначение:** Единая точка входа для всех запросов
- **Функции:**
  - Маршрутизация запросов к микросервисам
  - JWT аутентификация и авторизация
  - Rate limiting (100 запросов/минуту)
  - Circuit breaker для защиты от каскадных сбоев
  - Load balancing между экземплярами сервисов
  - CORS handling
  - Централизованное логирование

### 2. **User Service** (Port 8001)
- **Назначение:** Управление пользователями и аутентификацией
- **Функции:**
  - CRUD операции с пользователями
  - JWT токены и сессии
  - Роли и права доступа
  - Профили пользователей

### 3. **Lesson Service** (Port 8002)
- **Назначение:** Управление уроками и расписанием
- **Функции:**
  - Создание и планирование уроков
  - Управление статусами уроков
  - Интеграция с календарем
  - Отслеживание посещаемости

### 4. **Homework Service** (Port 8003)
- **Назначение:** Система домашних заданий
- **Функции:**
  - Создание и назначение заданий
  - Прием и проверка работ
  - Файловые вложения (до 50MB)
  - Система оценок

### 5. **Payment Service** (Port 8004)
- **Назначение:** Платежная система и управление балансом
- **Функции:**
  - Обработка платежей
  - Управление балансом пользователей
  - История транзакций
  - Интеграция с платежными шлюзами

### 6. **Material Service** (Port 8005)
- **Назначение:** Библиотека учебных материалов
- **Функции:**
  - Загрузка и хранение файлов
  - Категоризация по предметам и классам
  - Контроль доступа к материалам
  - Генерация превью и миниатюр

### 7. **Notification Service** (Port 8006)
- **Назначение:** Система уведомлений
- **Функции:**
  - Email уведомления
  - Telegram уведомления
  - Push уведомления (в планах)
  - Шаблоны сообщений
  - Отложенная отправка

### 8. **Analytics Service** (Port 8007)
- **Назначение:** Аналитика и отчетность
- **Функции:**
  - Сбор метрик обучения
  - Генерация отчетов
  - Графики прогресса
  - Dashboard для преподавателей
  - Экспорт данных

### 9. **Student Service** (Port 8008) ⭐ **НОВЫЙ**
- **Назначение:** Геймификация и система достижений
- **Функции:**
  - Профили студентов с уровнями
  - Система опыта (XP) и уровней
  - 15+ типов достижений (обычные, редкие, эпические, легендарные)
  - Трекинг стриков обучения
  - Персонализированные рекомендации
  - Социальные функции

## 🚀 Деплой системы

### Быстрый старт

```bash
# 1. Клонирование репозитория
git clone <repo-url>
cd repitbot

# 2. Настройка переменных окружения
cp .env.example .env
# Отредактируйте .env файл

# 3. Сборка и запуск всех сервисов
docker-compose -f docker-compose.microservices.yml up --build

# 4. Проверка статуса
curl http://localhost:8000/health
```

### Пошаговый деплой

```bash
# 1. Сборка инфраструктуры
docker-compose -f docker-compose.microservices.yml up -d postgres rabbitmq redis

# 2. Ожидание готовности инфраструктуры
sleep 30

# 3. Сборка и запуск микросервисов по группам
# Базовые сервисы
docker-compose -f docker-compose.microservices.yml up -d user-service lesson-service

# Функциональные сервисы
docker-compose -f docker-compose.microservices.yml up -d homework-service payment-service material-service

# Дополнительные сервисы
docker-compose -f docker-compose.microservices.yml up -d notification-service analytics-service student-service

# API Gateway
docker-compose -f docker-compose.microservices.yml up -d api-gateway

# Telegram Bot
docker-compose -f docker-compose.microservices.yml up -d telegram-bot

# Мониторинг
docker-compose -f docker-compose.microservices.yml up -d prometheus grafana
```

## 🔧 Конфигурация

### Переменные окружения

```env
# Основные настройки
BOT_TOKEN=your_telegram_bot_token
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
DEBUG=false
ENVIRONMENT=production

# База данных
POSTGRES_DB=repitbot
POSTGRES_USER=repitbot
POSTGRES_PASSWORD=repitbot_password

# RabbitMQ
RABBITMQ_DEFAULT_USER=repitbot
RABBITMQ_DEFAULT_PASS=repitbot_password

# API Gateway настройки
RATE_LIMIT_PER_MINUTE=100
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60

# Student Service настройки
DEFAULT_LEVEL_XP_THRESHOLD=1000
XP_MULTIPLIER=1.5
MAX_LEVEL=100
```

### Порты сервисов

| Сервис | Внутренний порт | Внешний порт | Описание |
|--------|----------------|-------------|-----------|
| API Gateway | 8000 | 8000 | Единая точка входа |
| User Service | 8001 | 8001 | Пользователи |
| Lesson Service | 8002 | 8002 | Уроки |
| Homework Service | 8003 | 8003 | Домашние задания |
| Payment Service | 8004 | 8004 | Платежи |
| Material Service | 8005 | 8005 | Материалы |
| Notification Service | 8006 | 8006 | Уведомления |
| Analytics Service | 8007 | 8007 | Аналитика |
| Student Service | 8008 | 8008 | Достижения |

### Инфраструктурные порты

| Сервис | Порт | Назначение |
|--------|------|-----------|
| PostgreSQL | 5432 | База данных |
| RabbitMQ | 5672 | AMQP |
| RabbitMQ Management | 15672 | Веб-интерфейс |
| Redis | 6379 | Кеш и сессии |
| Prometheus | 9090 | Метрики |
| Grafana | 3000 | Дашборды |
| PgAdmin | 5050 | Управление БД |

## 🎮 Система достижений (Student Service)

### Типы достижений

**🥉 Обычные (Common)**
- Первый шаг - завершите первый урок
- Ученик - завершите 10 уроков
- Исполнительный - сдайте первое ДЗ

**🥈 Редкие (Rare)**
- Знаток - завершите 50 уроков
- Перфекционист - 10 идеальных ДЗ
- Активный ученик - 50 часов обучения

**🥇 Эпические (Epic)**
- Мастер - завершите 100 уроков
- Железная дисциплина - 30 дней подряд
- Продвинутый - достигните 10 уровня

**💎 Легендарные (Legendary)**
- Легенда - достигните 50 уровня

### Система опыта (XP)

- **Урок завершен:** 100-300 XP (зависит от типа и оценки)
- **ДЗ сдано:** 50 XP + бонус за оценку
- **Материал изучен:** 25 XP
- **Платеж:** До 500 XP (зависит от суммы)

### Уровни и прогрессия

- Начальный XP для уровня: 1000 XP
- Множитель роста: 1.5x
- Максимальный уровень: 100

## 📊 Event-Driven архитектура

### Типы событий

```typescript
// Пользовательские события
USER_CREATED = "user.created"
USER_UPDATED = "user.updated"

// События уроков
LESSON_COMPLETED = "lesson.completed"
LESSON_CANCELLED = "lesson.cancelled"

// События домашних заданий
HOMEWORK_SUBMITTED = "homework.submitted"
HOMEWORK_GRADED = "homework.graded"

// События платежей
PAYMENT_COMPLETED = "payment.completed"
BALANCE_UPDATED = "balance.updated"

// События студентов
STUDENT_LEVEL_UP = "student.level_up"
ACHIEVEMENT_EARNED = "achievement.earned"
XP_EARNED = "xp.earned"
```

### Обработка событий

Каждый сервис может:
- Публиковать события в RabbitMQ
- Подписываться на события других сервисов
- Обрабатывать события асинхронно
- Использовать correlation ID для трассировки

## 🔍 API документация

### API Gateway endpoints

```http
# Health check
GET /health
GET /health/ready
GET /health/live

# Service discovery
GET /gateway/services

# Auth proxy
POST /auth/login
POST /auth/refresh
GET /auth/me

# Service routing (примеры)
GET /api/v1/users/{id}
POST /api/v1/lessons
GET /api/v1/students/{id}/achievements
```

### Аутентификация

Все запросы к защищенным эндпоинтам требуют JWT токен:

```http
Authorization: Bearer <jwt_token>
```

## 📈 Мониторинг и метрики

### Prometheus метрики

- Количество запросов по сервисам
- Время ответа (P50, P95, P99)
- Статус Circuit Breakers
- Состояние очередей RabbitMQ
- Использование ресурсов

### Grafana дашборды

- Обзор всех сервисов
- API Gateway метрики
- Производительность баз данных
- Event-driven метрики

### Health checks

```bash
# Проверка всех сервисов
curl http://localhost:8000/health

# Проверка конкретного сервиса
curl http://localhost:8008/health  # Student Service
```

## 🧪 Тестирование

### Unit тесты

Каждый сервис содержит unit тесты для:
- Business logic
- API endpoints
- Event handlers
- Database operations

### Integration тесты

- API контракты между сервисами
- Event-driven коммуникация
- Database integration
- External service mocking

### End-to-End тесты

```bash
# Запуск E2E тестов
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## 🚨 Troubleshooting

### Частые проблемы

**1. Сервис не стартует**
```bash
# Проверка логов
docker-compose logs service-name

# Проверка зависимостей
docker-compose ps
```

**2. Circuit Breaker открыт**
```bash
# Проверка состояния
curl http://localhost:8000/gateway/metrics

# Сброс Circuit Breaker
# Через API или перезапуск сервиса
```

**3. События не обрабатываются**
```bash
# Проверка RabbitMQ
curl http://localhost:15672  # admin/admin

# Проверка очередей и exchange
```

**4. База данных недоступна**
```bash
# Проверка PostgreSQL
docker-compose exec postgres psql -U repitbot -d repitbot -c "SELECT version();"
```

### Логи

```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f student-service

# Фильтрация по уровню
docker-compose logs | grep ERROR
```

## 📋 Production Checklist

### Безопасность ✅

- [x] Все секреты в переменных окружения
- [x] JWT токены с коротким временем жизни
- [x] Rate limiting настроен
- [x] CORS правильно сконфигурирован
- [x] Circuit breakers активны

### Производительность ✅

- [x] Connection pooling для БД
- [x] Redis кеширование
- [x] Async обработка событий
- [x] Оптимизированные Docker images
- [x] Health checks для всех сервисов

### Мониторинг ✅

- [x] Prometheus metrics
- [x] Grafana dashboards
- [x] Централизованные логи
- [x] Alert rules настроены
- [x] Health endpoints

### Надежность ✅

- [x] Graceful shutdown
- [x] Auto-restart policies
- [x] Database migrations
- [x] Backup стратегия
- [x] Disaster recovery plan

## 🎉 Заключение

RepitBot теперь представляет собой полноценную **production-ready микросервисную систему** с:

- **9 специализированных сервисов**
- **API Gateway для централизованного управления**
- **Полной системой геймификации и достижений**
- **Event-driven архитектурой**
- **Comprehensive мониторингом**
- **Telegram Bot интеграцией**

Система готова к горизонтальному масштабированию, имеет все необходимые механизмы отказоустойчивости и может обслуживать тысячи пользователей одновременно.

---

**Контакты для поддержки:** 
- GitHub Issues: [репозиторий]
- Документация API: http://localhost:8000/docs
- Grafana Dashboard: http://localhost:3000
- RabbitMQ Management: http://localhost:15672