# 🚀 STAGE 5 DEPLOYMENT GUIDE
## Notification & Analytics Services

### 📋 ОБЩИЙ ОБЗОР

Stage 5 включает в себя реализацию двух критически важных сервисов:
- **Notification Service** (порт 8006) - Управление уведомлениями
- **Analytics Service** (порт 8007) - Аналитика и отчеты

### 🏗️ АРХИТЕКТУРА СЕРВИСОВ

#### Notification Service
```
📧 Email Notifications     📱 Telegram Notifications
           ↓                           ↓
    ┌─────────────────────────────────────────┐
    │         Notification Service            │
    │                                         │
    │  ├── Email Provider (SMTP)             │
    │  ├── Telegram Provider (Bot API)       │
    │  ├── Template Engine (Jinja2)          │
    │  ├── Preference Manager                │
    │  ├── Delivery Queue (RabbitMQ)         │
    │  └── Event Processors                  │
    └─────────────────────────────────────────┘
              ↓           ↑
         PostgreSQL    RabbitMQ Events
```

#### Analytics Service
```
📊 Real-time Analytics     📈 Chart Generation     📄 Report Generation
           ↓                       ↓                       ↓
    ┌─────────────────────────────────────────────────────────────────┐
    │                    Analytics Service                            │
    │                                                                 │
    │  ├── Lesson Analytics     ├── Chart Service (Plotly)          │
    │  ├── Payment Analytics    ├── Report Service (WeasyPrint)     │
    │  ├── User Analytics       ├── Export Service                  │
    │  ├── Material Analytics   └── Cache Layer (Redis)             │
    │  └── Event Aggregators                                         │
    └─────────────────────────────────────────────────────────────────┘
                        ↓              ↑
                  PostgreSQL      RabbitMQ Events
```

### 🔧 СИСТЕМНЫЕ ТРЕБОВАНИЯ

#### Минимальные требования:
- **CPU:** 4 cores
- **RAM:** 8GB
- **Storage:** 50GB SSD
- **Network:** 100 Mbps

#### Рекомендуемые требования:
- **CPU:** 8 cores
- **RAM:** 16GB
- **Storage:** 200GB SSD
- **Network:** 1 Gbps

### 📦 КОМПОНЕНТЫ УСТАНОВКИ

#### Основные сервисы:
1. **Notification Service** - Уведомления
2. **Analytics Service** - Аналитика
3. **PostgreSQL** - База данных
4. **RabbitMQ** - Очередь сообщений
5. **Redis** - Кэширование

#### Дополнительные компоненты:
1. **Prometheus** - Метрики
2. **Grafana** - Мониторинг
3. **Nginx** - Load Balancer
4. **PgAdmin** - Управление БД (dev)

### 🚀 БЫСТРЫЙ СТАРТ

#### 1. Подготовка окружения
```bash
# Клонирование репозитория
git clone <repository-url>
cd repitbot

# Создание .env файла
cp .env.example .env
nano .env
```

#### 2. Настройка переменных окружения
```env
# Основные настройки
BOT_TOKEN=your_telegram_bot_token
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Базы данных
POSTGRES_PASSWORD=secure_password
REDIS_PASSWORD=secure_redis_password

# JWT
JWT_SECRET_KEY=your_super_secret_jwt_key

# Режим разработки
ENVIRONMENT=development
DEBUG=true
```

#### 3. Запуск полной системы
```bash
# Сборка и запуск всех сервисов
docker-compose -f docker-compose.microservices.yml up -d

# Проверка статуса
docker-compose -f docker-compose.microservices.yml ps
```

#### 4. Запуск только Stage 5 сервисов (для тестирования)
```bash
# Изолированное тестирование новых сервисов
cd services
docker-compose -f docker-compose.stage5.yml up -d

# Проверка статуса
docker-compose -f docker-compose.stage5.yml ps
```

### 🔍 ПРОВЕРКА РАЗВЕРТЫВАНИЯ

#### Health Checks
```bash
# Notification Service
curl http://localhost:8006/health

# Analytics Service
curl http://localhost:8007/health

# Telegram Bot
curl http://localhost:8000/health  # Если есть health endpoint
```

#### Проверка API
```bash
# Получение доступных типов уведомлений
curl -H "Authorization: Bearer <token>" \
     http://localhost:8006/api/v1/templates

# Получение типов графиков
curl -H "Authorization: Bearer <token>" \
     http://localhost:8007/api/v1/charts/types

# Быстрый отчет (требует аутентификации)
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8007/api/v1/reports/quick/lesson?days=7&format=pdf"
```

#### Проверка интеграции с Telegram Bot
```bash
# Отправка тестового уведомления через Telegram Bot
# (в чате с ботом выполнить команду)
/notifications
# Затем выбрать "🧪 Тестовое уведомление"

# Просмотр аналитики через бота
/analytics
# Затем выбрать нужный тип статистики
```

### 🐛 ДИАГНОСТИКА И УСТРАНЕНИЕ НЕПОЛАДОК

#### Общие проблемы и решения

**1. Сервис не запускается**
```bash
# Проверка логов
docker logs repitbot_notification_service
docker logs repitbot_analytics_service

# Проверка зависимостей
docker-compose -f docker-compose.microservices.yml ps
```

**2. Ошибки подключения к базе данных**
```bash
# Проверка статуса PostgreSQL
docker logs repitbot_postgres

# Проверка подключения
docker exec -it repitbot_postgres psql -U repitbot -d repitbot -c "\\l"
```

**3. Проблемы с RabbitMQ**
```bash
# Проверка статуса RabbitMQ
docker logs repitbot_rabbitmq

# Проверка очередей
curl -u repitbot:repitbot_password http://localhost:15672/api/queues
```

**4. Уведомления не отправляются**
```bash
# Проверка настроек email
docker exec -it repitbot_notification_service cat /app/.env

# Проверка Telegram Bot токена
echo $BOT_TOKEN

# Проверка логов уведомлений
docker logs repitbot_notification_service | grep "notification"
```

**5. Аналитика не генерируется**
```bash
# Проверка событий в RabbitMQ
docker exec -it repitbot_rabbitmq rabbitmqctl list_queues

# Проверка Redis
docker exec -it repitbot_redis redis-cli ping

# Проверка обработки событий
docker logs repitbot_analytics_service | grep "event"
```

### 📈 МОНИТОРИНГ И МЕТРИКИ

#### Prometheus Metrics
- **Notification Service:** `http://localhost:8006/metrics`
- **Analytics Service:** `http://localhost:8007/metrics`

#### Grafana Dashboards
- **URL:** `http://localhost:3000`
- **Credentials:** admin/admin
- **Dashboards:** Автоматически загружаются из `config/grafana/dashboards/`

#### Ключевые метрики для мониторинга:
1. **Notification Service:**
   - Успешность доставки уведомлений
   - Время обработки уведомлений
   - Размер очереди уведомлений

2. **Analytics Service:**
   - Время генерации отчетов
   - Количество активных пользователей
   - Размер кэша Redis

### 🔒 БЕЗОПАСНОСТЬ

#### Основные меры безопасности:
1. **JWT токены:** Аутентификация между сервисами
2. **Environment variables:** Хранение секретов
3. **Network isolation:** Docker networks
4. **Input validation:** Валидация всех входных данных

#### Production настройки:
```env
# Production environment
ENVIRONMENT=production
DEBUG=false

# Secure JWT key
JWT_SECRET_KEY=generate_a_very_long_random_string_here

# Secure database passwords
POSTGRES_PASSWORD=very_secure_database_password
REDIS_PASSWORD=very_secure_redis_password

# Email encryption
EMAIL_USE_TLS=true
EMAIL_PORT=587
```

### 🧪 ТЕСТИРОВАНИЕ

#### Unit Tests
```bash
# Analytics Service
cd services/analytics-service
python -m pytest tests/ -v

# Notification Service
cd services/notification-service
python -m pytest tests/ -v
```

#### Integration Tests
```bash
# Запуск интеграционных тестов
cd services
docker-compose -f docker-compose.stage5.yml --profile testing up -d
```

#### Load Testing
```bash
# Нагрузочное тестирование
docker-compose -f docker-compose.stage5.yml run load-tester
```

### 📊 ПРОИЗВОДИТЕЛЬНОСТЬ

#### Benchmark результаты (примерные):
- **Notification delivery:** < 5 секунд
- **Analytics dashboard:** < 2 секунды
- **Chart generation:** < 3 секунды
- **Quick reports:** < 10 секунд
- **Full reports:** < 60 секунд

#### Оптимизация производительности:
1. **Redis caching** для аналитических данных
2. **Connection pooling** для баз данных
3. **Async processing** для уведомлений
4. **Background tasks** для генерации отчетов

### 🔄 ОБНОВЛЕНИЯ И МИГРАЦИИ

#### Процедура обновления:
```bash
# 1. Остановка сервисов
docker-compose -f docker-compose.microservices.yml down

# 2. Создание backup
docker exec repitbot_postgres pg_dump -U repitbot repitbot > backup.sql

# 3. Обновление кода
git pull origin main

# 4. Пересборка контейнеров
docker-compose -f docker-compose.microservices.yml build --no-cache

# 5. Запуск с миграциями
docker-compose -f docker-compose.microservices.yml up -d
```

#### Rollback процедура:
```bash
# 1. Откат к предыдущей версии
git checkout <previous-commit>

# 2. Восстановление backup
docker exec -i repitbot_postgres psql -U repitbot repitbot < backup.sql

# 3. Перезапуск сервисов
docker-compose -f docker-compose.microservices.yml restart
```

### 📞 ПОДДЕРЖКА

#### Контакты команды:
- **Technical Lead:** [contact information]
- **DevOps:** [contact information]
- **Documentation:** [wiki/docs link]

#### Полезные ссылки:
- **API Documentation:** `http://localhost:8006/docs`, `http://localhost:8007/docs`
- **RabbitMQ Management:** `http://localhost:15672`
- **Grafana Dashboards:** `http://localhost:3000`
- **Prometheus Metrics:** `http://localhost:9090`

---

## ✅ ЧЕКЛИСТ РАЗВЕРТЫВАНИЯ

### Предварительная подготовка:
- [ ] Настроены переменные окружения
- [ ] Получен Telegram Bot токен
- [ ] Настроена почта для уведомлений
- [ ] Проверены системные требования

### Основное развертывание:
- [ ] Запущены все сервисы
- [ ] Проверены health checks
- [ ] Настроен мониторинг
- [ ] Проведены базовые тесты

### Интеграционное тестирование:
- [ ] Telegram Bot интеграция работает
- [ ] Уведомления доставляются
- [ ] Аналитика генерируется
- [ ] Отчеты создаются

### Production готовность:
- [ ] Настроена безопасность
- [ ] Созданы backups
- [ ] Настроены алерты
- [ ] Подготовлена документация

**🎉 STAGE 5 ГОТОВ К ЭКСПЛУАТАЦИИ!**