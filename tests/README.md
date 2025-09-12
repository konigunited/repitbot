# RepitBot Microservices Test Suite

## 🧪 Comprehensive Testing Framework для микросервисной архитектуры RepitBot

Этот тест-сьют обеспечивает полное покрытие тестированием микросервисной системы RepitBot, включая все 9 микросервисов, инфраструктуру и интеграционные сценарии.

## 🎯 Цели тестирования

### ✅ Проверенные компоненты:
- **9 Микросервисов**: API Gateway, User, Lesson, Homework, Payment, Material, Notification, Analytics, Student Services
- **3 Роли пользователей**: PARENT, STUDENT, TUTOR с полным функционалом
- **Инфраструктура**: PostgreSQL, RabbitMQ, Redis, Prometheus, Grafana
- **Event-Driven архитектура**: полные цепочки событий между сервисами
- **Безопасность**: JWT authentication, RBAC, CORS, rate limiting
- **Производительность**: response times, throughput, scalability

### 🔍 Типы тестирования:

#### 🏗️ **Infrastructure Tests**
- Health checks всех 9 сервисов
- Connectivity к базам данных и очередям
- Docker containers status
- Network connectivity между сервисами
- Resource usage мониторинг

#### 🔐 **Authentication & Authorization Tests**  
- JWT token generation и validation
- Role-based access control (PARENT/STUDENT/TUTOR)
- Token expiration и security
- Cross-service authentication
- Session management

#### 👨‍👩‍👧‍👦 **Parent Dashboard Tests**
- 💰 Payment management (balance, top-up, history)
- 📅 Child schedule viewing и management  
- 📊 Child progress monitoring
- 🔔 Notification preferences
- 👨‍👩‍👧‍👦 Multiple children support

#### 🎓 **Student Dashboard Tests**
- 📚 Lesson management (schedule, attendance, history)
- 📝 Homework system (assignments, submission, grades)
- 📖 Material library access
- 🏆 Achievement system (XP, levels, badges)
- 🎮 Gamification features

#### 👨‍🏫 **Tutor Dashboard Tests**
- 📚 Lesson creation и management
- 📝 Homework assignment и grading
- 📖 Material upload и organization
- 👥 Student progress tracking
- 📊 Analytics и reporting
- 🔔 Communication tools

#### 🤝 **Contract Tests**
- API contracts между сервисами
- Request/Response schema validation
- Backward compatibility
- Error handling contracts
- Service integration contracts

#### 🔄 **Event-Driven Tests**
- RabbitMQ message publishing/consuming
- Event ordering и reliability
- Dead letter queue handling
- Cross-service event workflows
- Event deduplication

#### ⚡ **Performance Tests**
- Response time validation (<500ms health checks)
- Load testing (concurrent users)
- Resource utilization monitoring
- Bottleneck identification
- Scalability assessment

#### 🔒 **Security Tests**
- SQL injection prevention
- JWT tampering detection
- CORS policy validation
- Rate limiting verification
- HTTPS enforcement

## 🚀 Быстрый старт

### Предварительные требования

1. **Запущенная микросервисная система**:
   ```bash
   docker-compose -f docker-compose.microservices.yml up -d
   ```

2. **Python 3.8+** и зависимости:
   ```bash
   cd tests/
   pip install -r requirements.txt
   ```

3. **Проверка готовности сервисов**:
   ```bash
   # Все сервисы должны отвечать на health checks:
   curl http://localhost:8000/health  # API Gateway
   curl http://localhost:8001/health  # User Service
   curl http://localhost:8002/health  # Lesson Service
   # ... и так далее для всех 9 сервисов
   ```

### Запуск тестов

#### 🎯 Все тесты (полная проверка):
```bash
python run_tests.py --all
```

#### ⚡ Быстрая проверка (критичные тесты):
```bash
python run_tests.py --fast
```

#### 🔍 Конкретная категория:
```bash
python run_tests.py --category infrastructure
python run_tests.py --category auth
python run_tests.py --category functional
```

#### 🐍 Через pytest напрямую:
```bash
# Все тесты
pytest -v

# Конкретные категории
pytest -m infrastructure -v
pytest -m auth -v  
pytest -m functional -v
pytest -m parent -v
pytest -m student -v
pytest -m tutor -v

# Быстрые тесты
pytest -m "fast and not slow" -v

# Параллельное выполнение
pytest -n auto -v
```

## 📊 Структура тестов

```
tests/
├── __init__.py                    # Test suite initialization
├── conftest.py                   # PyTest configuration & fixtures
├── pytest.ini                   # Test execution settings
├── requirements.txt              # Test dependencies
├── run_tests.py                  # Main test runner
│
├── test_infrastructure.py        # 🏗️ Infrastructure health checks
├── test_authentication.py        # 🔐 Auth & authorization tests
├── test_functional_parent.py     # 👨‍👩‍👧‍👦 Parent dashboard tests
├── test_functional_student.py    # 🎓 Student dashboard tests  
├── test_functional_tutor.py      # 👨‍🏫 Tutor dashboard tests
├── test_contract_testing.py      # 🤝 Service contract tests
├── test_events.py                # 🔄 Event-driven architecture
│
├── logs/                         # Test execution logs
├── reports/                      # HTML & JSON test reports
└── README.md                     # This documentation
```

## 🎭 Роли и их функционал

### 👨‍👩‍👧‍👦 PARENT (Родитель)
**Доступные функции:**
- 💰 Управление балансом и платежами
- 📅 Просмотр расписания ребенка
- 📊 Мониторинг успеваемости ребенка
- 🔔 Настройка уведомлений
- 📞 Связь с репетитором

**Тестируемые сценарии:**
- Пополнение баланса и история платежей
- Просмотр и отмена уроков ребенка
- Отслеживание домашних заданий и оценок
- Получение уведомлений о прогрессе

### 🎓 STUDENT (Ученик)  
**Доступные функции:**
- 📚 Участие в уроках
- 📝 Выполнение домашних заданий
- 📖 Доступ к учебным материалам
- 🏆 Система достижений и геймификация
- 📊 Отслеживание прогресса

**Тестируемые сценарии:**
- Присоединение к урокам
- Сдача домашних заданий с файлами
- Скачивание материалов
- Получение XP и разблокировка достижений

### 👨‍🏫 TUTOR (Репетитор)
**Доступные функции:**
- 📚 Создание и управление уроками
- 📝 Создание и проверка домашних заданий
- 📖 Загрузка учебных материалов
- 👥 Управление учениками
- 📊 Аналитика и отчеты
- 🔔 Отправка уведомлений

**Тестируемые сценарии:**
- Создание уроков и управление расписанием
- Создание заданий и выставление оценок
- Загрузка и организация материалов
- Отслеживание прогресса учеников

## 🔄 Event-Driven тестирование

### Основные цепочки событий:

#### 📚 Lesson Completion Workflow
```
lesson.completed → payment.processed → notification.sent → analytics.updated → xp.awarded
```

#### 📝 Homework Submission Workflow  
```
homework.submitted → tutor.notified → homework.graded → xp.awarded → achievement.checked
```

#### 💰 Payment Processing Workflow
```
payment.initiated → balance.updated → parent.notified → analytics.tracked
```

#### 🏆 Achievement Workflow
```
xp.earned → level.checked → achievement.unlocked → notification.sent
```

### Тестируемые аспекты:
- ✅ Event publishing от каждого сервиса
- ✅ Event consumption всеми подписчиками
- ✅ Event ordering и sequence
- ✅ Dead letter queue обработка
- ✅ Event deduplication
- ✅ Cross-service workflow integrity

## 📊 Отчеты и результаты

### 📋 Executive Summary
Каждый запуск тестов генерирует comprehensive отчет с:
- Overall success rate
- Breakdown по категориям тестов
- Performance metrics
- Critical issues found
- Production readiness assessment

### 📈 Detailed Results
- ✅ **Passed tests**: Успешно выполненные тесты
- ❌ **Failed tests**: Тесты с ошибками (требуют исправления)
- ⏭️ **Skipped tests**: Пропущенные тесты
- 🔥 **Error tests**: Тесты с техническими проблемами

### 💡 Recommendations
Автоматически генерируемые рекомендации по:
- 🔧 Immediate actions (критичные проблемы)
- ⚠️ Infrastructure issues (проблемы инфраструктуры)  
- ⚡ Performance improvements (оптимизация производительности)
- 🔒 Security enhancements (улучшение безопасности)

## 🎯 Quality Gates

### ✅ Production Ready (Success Rate ≥ 95%)
- Все критичные тесты проходят
- Infrastructure health checks успешны
- Authentication и authorization работают
- Основной функционал всех ролей доступен

### ⚠️ Conditional Ready (Success Rate ≥ 80%)
- Критичные проблемы устранены
- Некритичные проблемы можно исправить после деплоя
- Основной функционал работает стабильно

### ❌ Not Ready (Success Rate < 80%)
- Значительные проблемы требуют исправления
- Рекомендуется тщательное тестирование и отладка

## 🔧 Настройка и кастомизация

### Конфигурация сервисов
В `conftest.py` настраиваются:
```python
class TestConfig:
    # Service URLs
    API_GATEWAY_URL = "http://localhost:8000"
    USER_SERVICE_URL = "http://localhost:8001"
    # ... другие сервисы
    
    # Timeouts
    REQUEST_TIMEOUT = 30
    HEALTH_CHECK_TIMEOUT = 10
    
    # Performance thresholds  
    MAX_RESPONSE_TIME_MS = 1000
    LOAD_TEST_CONCURRENT_USERS = 100
```

### Добавление новых тестов
1. Создайте новый файл `test_[category].py`
2. Добавьте соответствующие маркеры в `pytest.ini`
3. Используйте существующие fixtures из `conftest.py`
4. Обновите `run_tests.py` для включения новой категории

### Custom маркеры
```python
@pytest.mark.custom_marker
@pytest.mark.slow
@pytest.mark.critical
async def test_new_functionality():
    # Your test implementation
    pass
```

## 🐛 Troubleshooting

### Частые проблемы:

#### 🔌 "Connection refused" ошибки
```bash
# Проверьте что все сервисы запущены
docker-compose -f docker-compose.microservices.yml ps

# Перезапустите проблемные сервисы
docker-compose -f docker-compose.microservices.yml restart user-service
```

#### 🔑 Authentication failures
```bash
# Проверьте что User Service доступен
curl http://localhost:8001/health

# Проверьте JWT secret в конфигурации
```

#### 📨 RabbitMQ connection issues  
```bash
# Проверьте RabbitMQ Management UI
open http://localhost:15672
# Login: repitbot / repitbot_password
```

#### 🐘 PostgreSQL connection issues
```bash
# Проверьте подключение к базе
docker exec -it repitbot_postgres psql -U repitbot -d repitbot -c "SELECT 1;"
```

### Логи и отладка
```bash
# Логи тестов
tail -f tests/logs/pytest.log

# Логи сервисов
docker-compose -f docker-compose.microservices.yml logs -f user-service

# Verbose test execution
pytest -v -s --log-cli-level=DEBUG
```

## 📚 Дополнительные возможности

### Параллельное выполнение
```bash
# Запуск тестов в несколько потоков
pytest -n 4 -v

# Автоматический выбор количества процессов
pytest -n auto -v
```

### Покрытие кода
```bash
# Генерация HTML отчета покрытия
pytest --cov=repitbot --cov-report=html

# Открыть отчет
open htmlcov/index.html
```

### Профилирование производительности  
```bash
# Benchmark тесты
pytest --benchmark-only

# Memory profiling
pytest --memory-profiler
```

### Генерация тестовых данных
```python
from tests.conftest import generate_test_user

# Создание тестового пользователя
user_data = generate_test_user("STUDENT")
```

## 🤝 Contributing

### Добавление новых тестов:
1. Определите категорию теста
2. Создайте соответствующий файл или добавьте в существующий  
3. Используйте правильные маркеры pytest
4. Добавьте документацию
5. Обновите этот README при необходимости

### Code Style:
- Используйте async/await для HTTP запросов
- Добавляйте четкие docstrings
- Используйте типизацию
- Следуйте паттернам существующих тестов

## 📞 Support

При возникновении проблем:
1. Проверьте логи в `tests/logs/`
2. Убедитесь что все сервисы запущены и доступны
3. Проверьте конфигурацию в `conftest.py`
4. Запустите тесты с подробным выводом: `pytest -v -s`

---

## ⭐ Заключение

Этот comprehensive test suite обеспечивает полное покрытие тестированием микросервисной архитектуры RepitBot, включая:

- ✅ **9 микросервисов** полностью протестированы
- ✅ **3 роли пользователей** со всем функционалом
- ✅ **Event-driven архитектура** с полными workflow
- ✅ **Infrastructure** health и connectivity
- ✅ **Security** authentication и authorization  
- ✅ **Performance** response times и scalability
- ✅ **Contract testing** между сервисами
- ✅ **Automated reporting** с рекомендациями

**Production Ready Assessment**: Система готова к продакшену при success rate ≥ 95%

🚀 **Happy Testing!** 🧪