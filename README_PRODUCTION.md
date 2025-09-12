# RepitBot - Микросервисная архитектура

[![Production Status](https://img.shields.io/badge/Status-Production%20Ready-green)](https://github.com/username/repitbot)
[![Microservices](https://img.shields.io/badge/Microservices-9-blue)](https://github.com/username/repitbot)
[![Docker](https://img.shields.io/badge/Docker-Enabled-blue)](https://docker.com)

> Полнофункциональная микросервисная архитектура для образовательной платформы RepitBot

## 🏗️ Архитектура системы

### Микросервисы (9 сервисов)
```
🌐 API Gateway (8000)     ← Единая точка входа
├── 👥 User Service (8001)      - Пользователи и аутентификация
├── 📚 Lesson Service (8002)    - Уроки и расписание
├── 📝 Homework Service (8003)  - Домашние задания
├── 💰 Payment Service (8004)   - Платежи и баланс
├── 📁 Material Service (8005)  - Материалы и файлы
├── 🔔 Notification Service (8006) - Уведомления
├── 📊 Analytics Service (8007) - Аналитика и отчеты
└── 🎯 Student Service (8008)   - Достижения и геймификация
```

### Инфраструктура
- **PostgreSQL** - основная база данных (отдельная для каждого сервиса)
- **RabbitMQ** - message broker для Event-driven архитектуры
- **Redis** - кэширование и session storage
- **Prometheus** - сбор метрик
- **Grafana** - мониторинг и дашборды

## 🎭 Роли пользователей

### 👨‍👩‍👧‍👦 Кабинет РОДИТЕЛЯ
- 💰 Управление платежами и балансом
- 📊 Просмотр прогресса ребенка
- 📅 Контроль расписания уроков
- 🔔 Настройки уведомлений

### 🎓 Кабинет УЧЕНИКА
- 📚 Просмотр расписания уроков
- 📝 Выполнение домашних заданий
- 📖 Доступ к материалам
- 🏆 Система достижений (15+ наград)
- 🎮 Геймификация (XP, уровни, стрики)

### 👨‍🏫 Кабинет РЕПЕТИТОРА
- 📚 Создание и управление уроками
- 📝 Проверка домашних заданий
- 📖 Управление библиотекой материалов
- 📊 Аналитика и отчеты по ученикам
- 🔔 Коммуникация с учениками и родителями

## 🚀 Быстрый старт

### Предварительные требования
- Docker и Docker Compose
- Git
- 4+ GB RAM
- 10+ GB свободного места

### Установка и запуск

1. **Клонирование репозитория:**
```bash
git clone https://github.com/username/repitbot.git
cd repitbot
```

2. **Настройка environment variables:**
```bash
cp .env.example .env.production
# Отредактировать .env.production с production настройками
```

3. **Запуск всех микросервисов:**
```bash
docker-compose -f docker-compose.microservices.yml up -d
```

4. **Проверка статуса:**
```bash
curl http://localhost:8000/health/all
```

## 🔧 Конфигурация

### Environment Variables
Создать файл `.env.production` со следующими параметрами:

```bash
# ============== DATABASE ==============
DATABASE_HOST=your-postgres-host
DATABASE_USER=your-secure-user
DATABASE_PASSWORD=your-secure-password
DATABASE_NAME=repitbot_production

# ============== SECURITY ==============
JWT_SECRET_KEY=your-super-secret-jwt-key-256-bit
JWT_REFRESH_SECRET=your-super-secret-refresh-key-256-bit
API_SECRET_KEY=your-api-secret-key

# ============== EXTERNAL SERVICES ==============
BOT_TOKEN=your-telegram-bot-token
REDIS_URL=redis://your-redis-host:6379
RABBITMQ_URL=amqp://user:pass@your-rabbitmq-host:5672

# ============== MONITORING ==============
PROMETHEUS_ENABLED=true
GRAFANA_ADMIN_PASSWORD=your-secure-grafana-password

# ============== EMAIL ==============
SMTP_HOST=your-smtp-host
SMTP_PORT=587
SMTP_USER=your-email
SMTP_PASSWORD=your-email-password
```

## 📊 Мониторинг

### Доступные дашборды
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **RabbitMQ Management**: http://localhost:15672

### Health Checks
```bash
# Проверка всех сервисов
curl http://localhost:8000/health/all

# Проверка конкретного сервиса
curl http://localhost:8001/health  # User Service
curl http://localhost:8002/health  # Lesson Service
# ... и так далее
```

## 🧪 Тестирование

### Запуск тестов
```bash
# Все тесты
cd tests/
python run_tests.py --all

# Быстрые тесты
python run_tests.py --fast

# Тесты конкретной роли
pytest -m parent -v    # Родитель
pytest -m student -v   # Ученик
pytest -m tutor -v     # Репетитор
```

## 🔒 Безопасность

### Implemented Security Features
- ✅ JWT аутентификация с refresh tokens
- ✅ RBAC (Role-Based Access Control)
- ✅ Rate limiting на API Gateway
- ✅ Input validation и sanitization
- ✅ SQL injection protection
- ✅ XSS protection
- ✅ CORS policies
- ✅ File upload validation
- ✅ Circuit breaker для защиты от каскадных сбоев

### Security Checklist для Production
- [ ] Изменить все default пароли
- [ ] Настроить SSL/TLS для всех соединений
- [ ] Обновить JWT secrets на production ключи
- [ ] Настроить firewall rules
- [ ] Включить audit logging
- [ ] Настроить backup стратегию

## 📈 Performance

### Целевые метрики
- API Gateway: < 100ms response time
- Микросервисы: < 500ms response time  
- Database queries: < 100ms
- Event processing: < 50ms
- Throughput: > 1000 requests/sec

### Оптимизация
- Connection pooling для всех DB соединений
- Redis caching для частых запросов
- Async/await для всех I/O операций
- Database indexing на критических полях
- CDN для статических файлов

## 🔄 Event-Driven Architecture

### Типы событий
```python
# Уроки
lesson.created, lesson.updated, lesson.cancelled, lesson.completed

# Домашние задания  
homework.assigned, homework.submitted, homework.checked, homework.overdue

# Платежи
payment.processed, balance.updated, balance.low

# Достижения
achievement.unlocked, level.upgraded, xp.awarded

# Уведомления
notification.sent, notification.delivered, notification.failed
```

## 🚢 Deployment

### Production Deployment
1. **Server setup** (Ubuntu 20.04+ recommended)
2. **Docker installation**
3. **SSL certificates** получение
4. **Environment configuration**
5. **Database migration**
6. **Service deployment**
7. **Monitoring setup**

### Rollback Strategy
```bash
# Rollback к предыдущей версии
docker-compose -f docker-compose.microservices.yml down
git checkout previous-stable-tag
docker-compose -f docker-compose.microservices.yml up -d
```

## 📚 API Documentation

### Swagger/OpenAPI
- API Gateway: http://localhost:8000/docs
- User Service: http://localhost:8001/docs
- Lesson Service: http://localhost:8002/docs
- Payment Service: http://localhost:8004/docs
- И т.д. для всех сервисов

## 🤝 Contributing

### Development Workflow
1. Fork репозиторий
2. Создать feature branch
3. Внести изменения
4. Запустить тесты
5. Создать Pull Request

### Code Standards
- Python 3.11+
- Type hints обязательны
- Async/await для I/O операций
- 100% test coverage для критических компонентов
- Docker для всех сервисов

## 📞 Support

### Контакты
- Email: support@repitbot.com
- GitHub Issues: [Issues](https://github.com/username/repitbot/issues)
- Documentation: [Wiki](https://github.com/username/repitbot/wiki)

### Troubleshooting
- Проверить Docker containers: `docker ps`
- Проверить логи: `docker logs <container_name>`
- Проверить health checks: `curl localhost:8000/health/all`
- Проверить database connectivity
- Проверить RabbitMQ queues

## 📋 License

MIT License - см. [LICENSE](LICENSE) файл для деталей.

---

**RepitBot** - современная микросервисная образовательная платформа, готовая к enterprise deployment! 🚀