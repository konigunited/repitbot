# 🗄️ SQL Database Setup для RepitBot Microservices

## 🎯 Архитектура базы данных

### Database per Service Pattern
Каждый микросервис имеет свою изолированную базу данных:

```
PostgreSQL Server
├── repitbot_users          # User Service
├── repitbot_lessons        # Lesson Service  
├── repitbot_homework       # Homework Service
├── repitbot_payments       # Payment Service
├── repitbot_materials      # Material Service
├── repitbot_notifications  # Notification Service
├── repitbot_analytics      # Analytics Service
├── repitbot_students       # Student Service
└── repitbot_gateway        # API Gateway (sessions, rate limiting)
```

## 🚀 ШАГ 1: Выбор хостинга для PostgreSQL

### Вариант A: Облачные решения (рекомендуется)

#### 1. **Supabase** (бесплатно до 500MB)
- URL: https://supabase.com
- Создать новый проект
- Получить connection string
- Автоматические backup
- Built-in monitoring

#### 2. **Neon** (бесплатно до 10GB)
- URL: https://neon.tech  
- Serverless PostgreSQL
- Automatic scaling
- Branch databases для тестирования

#### 3. **Railway** (бесплатно $5 кредитов)
- URL: https://railway.app
- PostgreSQL + Redis в одном месте
- Simple deployment

#### 4. **DigitalOcean Managed Database**
- URL: https://www.digitalocean.com
- От $15/месяц
- Automatic backups
- High availability

### Вариант B: Собственный сервер
- Ubuntu 20.04+ сервер
- PostgreSQL 14+ установка
- Самостоятельное управление backup
- Больше контроля, но больше работы

## 🔧 ШАГ 2: Создание баз данных

### 2.1 Production SQL скрипт

```sql
-- ============== СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ ==============
-- Создаем пользователей для каждого сервиса (принцип least privilege)
CREATE USER repitbot_user_service WITH PASSWORD 'STRONG_PASSWORD_1';
CREATE USER repitbot_lesson_service WITH PASSWORD 'STRONG_PASSWORD_2';  
CREATE USER repitbot_homework_service WITH PASSWORD 'STRONG_PASSWORD_3';
CREATE USER repitbot_payment_service WITH PASSWORD 'STRONG_PASSWORD_4';
CREATE USER repitbot_material_service WITH PASSWORD 'STRONG_PASSWORD_5';
CREATE USER repitbot_notification_service WITH PASSWORD 'STRONG_PASSWORD_6';
CREATE USER repitbot_analytics_service WITH PASSWORD 'STRONG_PASSWORD_7';
CREATE USER repitbot_student_service WITH PASSWORD 'STRONG_PASSWORD_8';
CREATE USER repitbot_gateway WITH PASSWORD 'STRONG_PASSWORD_9';

-- Админ пользователь для миграций
CREATE USER repitbot_admin WITH PASSWORD 'SUPER_STRONG_ADMIN_PASSWORD' CREATEDB;

-- ============== СОЗДАНИЕ БАЗ ДАННЫХ ==============
CREATE DATABASE repitbot_users OWNER repitbot_user_service;
CREATE DATABASE repitbot_lessons OWNER repitbot_lesson_service;
CREATE DATABASE repitbot_homework OWNER repitbot_homework_service;
CREATE DATABASE repitbot_payments OWNER repitbot_payment_service;
CREATE DATABASE repitbot_materials OWNER repitbot_material_service;
CREATE DATABASE repitbot_notifications OWNER repitbot_notification_service;
CREATE DATABASE repitbot_analytics OWNER repitbot_analytics_service;
CREATE DATABASE repitbot_students OWNER repitbot_student_service;
CREATE DATABASE repitbot_gateway OWNER repitbot_gateway;

-- ============== ПРАВА ДОСТУПА ==============
-- Даем права только к своим БД
GRANT ALL PRIVILEGES ON DATABASE repitbot_users TO repitbot_user_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_lessons TO repitbot_lesson_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_homework TO repitbot_homework_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_payments TO repitbot_payment_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_materials TO repitbot_material_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_notifications TO repitbot_notification_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_analytics TO repitbot_analytics_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_students TO repitbot_student_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_gateway TO repitbot_gateway;

-- Админу доступ ко всем БД для миграций
GRANT ALL PRIVILEGES ON DATABASE repitbot_users TO repitbot_admin;
GRANT ALL PRIVILEGES ON DATABASE repitbot_lessons TO repitbot_admin;
GRANT ALL PRIVILEGES ON DATABASE repitbot_homework TO repitbot_admin;
GRANT ALL PRIVILEGES ON DATABASE repitbot_payments TO repitbot_admin;
GRANT ALL PRIVILEGES ON DATABASE repitbot_materials TO repitbot_admin;
GRANT ALL PRIVILEGES ON DATABASE repitbot_notifications TO repitbot_admin;
GRANT ALL PRIVILEGES ON DATABASE repitbot_analytics TO repitbot_admin;
GRANT ALL PRIVILEGES ON DATABASE repitbot_students TO repitbot_admin;
GRANT ALL PRIVILEGES ON DATABASE repitbot_gateway TO repitbot_admin;

-- ============== ANALYTICS READ-ONLY ACCESS ==============
-- Analytics сервису нужен read-only доступ к другим БД для отчетов
GRANT CONNECT ON DATABASE repitbot_users TO repitbot_analytics_service;
GRANT CONNECT ON DATABASE repitbot_lessons TO repitbot_analytics_service;
GRANT CONNECT ON DATABASE repitbot_homework TO repitbot_analytics_service;
GRANT CONNECT ON DATABASE repitbot_payments TO repitbot_analytics_service;
GRANT CONNECT ON DATABASE repitbot_materials TO repitbot_analytics_service;
GRANT CONNECT ON DATABASE repitbot_students TO repitbot_analytics_service;

-- Эти права применятся после создания таблиц в каждой БД:
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO repitbot_analytics_service;
```

### 2.2 Применение скрипта

#### Через psql:
```bash
# Подключение к PostgreSQL
psql -h YOUR_HOST -U postgres -d postgres

# Выполнение скрипта
\i /path/to/database_setup.sql
```

#### Через GUI (PgAdmin, DBeaver):
1. Подключиться к PostgreSQL сервер
2. Скопировать SQL скрипт
3. Выполнить

## 🔗 ШАГ 3: Connection Strings

### 3.1 Создание connection strings для каждого сервиса

```bash
# User Service
DATABASE_URL_USER=postgresql+asyncpg://repitbot_user_service:STRONG_PASSWORD_1@YOUR_HOST:5432/repitbot_users

# Lesson Service  
DATABASE_URL_LESSON=postgresql+asyncpg://repitbot_lesson_service:STRONG_PASSWORD_2@YOUR_HOST:5432/repitbot_lessons

# Homework Service
DATABASE_URL_HOMEWORK=postgresql+asyncpg://repitbot_homework_service:STRONG_PASSWORD_3@YOUR_HOST:5432/repitbot_homework

# Payment Service
DATABASE_URL_PAYMENT=postgresql+asyncpg://repitbot_payment_service:STRONG_PASSWORD_4@YOUR_HOST:5432/repitbot_payments

# Material Service
DATABASE_URL_MATERIAL=postgresql+asyncpg://repitbot_material_service:STRONG_PASSWORD_5@YOUR_HOST:5432/repitbot_materials

# Notification Service
DATABASE_URL_NOTIFICATION=postgresql+asyncpg://repitbot_notification_service:STRONG_PASSWORD_6@YOUR_HOST:5432/repitbot_notifications

# Analytics Service
DATABASE_URL_ANALYTICS=postgresql+asyncpg://repitbot_analytics_service:STRONG_PASSWORD_7@YOUR_HOST:5432/repitbot_analytics

# Student Service
DATABASE_URL_STUDENT=postgresql+asyncpg://repitbot_student_service:STRONG_PASSWORD_8@YOUR_HOST:5432/repitbot_students

# API Gateway
DATABASE_URL_GATEWAY=postgresql+asyncpg://repitbot_gateway:STRONG_PASSWORD_9@YOUR_HOST:5432/repitbot_gateway
```

### 3.2 Пример с реальным хостом (Supabase)
```bash
# Замените на ваши реальные данные
DATABASE_URL_USER=postgresql+asyncpg://repitbot_user_service:STRONG_PASSWORD_1@db.supabase.co:5432/repitbot_users?sslmode=require
```

## 🔄 ШАГ 4: Миграции баз данных

### 4.1 Запуск миграций для каждого сервиса

```bash
# Переходим в каждый сервис и запускаем миграции
cd services/user-service
export DATABASE_URL="postgresql+asyncpg://repitbot_user_service:PASSWORD@HOST:5432/repitbot_users"
alembic upgrade head

cd ../lesson-service  
export DATABASE_URL="postgresql+asyncpg://repitbot_lesson_service:PASSWORD@HOST:5432/repitbot_lessons"
alembic upgrade head

# И так далее для всех сервисов...
```

### 4.2 Автоматизированный скрипт миграций

```bash
#!/bin/bash
# migrate_all_services.sh

services=(
    "user-service:repitbot_users:repitbot_user_service:PASSWORD1"
    "lesson-service:repitbot_lessons:repitbot_lesson_service:PASSWORD2"
    "homework-service:repitbot_homework:repitbot_homework_service:PASSWORD3"
    "payment-service:repitbot_payments:repitbot_payment_service:PASSWORD4"
    "material-service:repitbot_materials:repitbot_material_service:PASSWORD5"
    "notification-service:repitbot_notifications:repitbot_notification_service:PASSWORD6"
    "analytics-service:repitbot_analytics:repitbot_analytics_service:PASSWORD7"
    "student-service:repitbot_students:repitbot_student_service:PASSWORD8"
)

HOST="YOUR_DB_HOST"

for service_info in "${services[@]}"; do
    IFS=':' read -r service_dir db_name db_user db_pass <<< "$service_info"
    
    echo "Migrating $service_dir..."
    cd "services/$service_dir"
    
    export DATABASE_URL="postgresql+asyncpg://$db_user:$db_pass@$HOST:5432/$db_name"
    alembic upgrade head
    
    if [ $? -eq 0 ]; then
        echo "✅ $service_dir migrated successfully"
    else
        echo "❌ $service_dir migration failed"
    fi
    
    cd ../..
done
```

## 🔒 ШАГ 5: Безопасность базы данных

### 5.1 Checklist безопасности
- [ ] Уникальные сильные пароли для каждого пользователя
- [ ] SSL/TLS соединения (sslmode=require)
- [ ] Firewall настроен (только нужные порты)
- [ ] Регулярные backups настроены
- [ ] Мониторинг подключений включен
- [ ] Логирование включено
- [ ] Права доступа минимальные (principle of least privilege)

### 5.2 Connection pooling настройка
```python
# В каждом сервисе
DATABASE_URL = "postgresql+asyncpg://user:pass@host:5432/db?max_pool_size=20&min_pool_size=5"
```

## 📊 ШАГ 6: Мониторинг базы данных

### 6.1 Полезные запросы для мониторинга

```sql
-- Активные подключения
SELECT datname, numbackends FROM pg_stat_database;

-- Размер баз данных
SELECT datname, pg_size_pretty(pg_database_size(datname)) 
FROM pg_database 
WHERE datname LIKE 'repitbot_%';

-- Медленные запросы
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
WHERE mean_exec_time > 1000 
ORDER BY mean_exec_time DESC;
```

### 6.2 Alerts настройка
- Мониторинг CPU и Memory использования
- Alerts на медленные запросы
- Мониторинг размера баз данных
- Проверка backup статуса

## 🗄️ ШАГ 7: Backup стратегия

### 7.1 Automated backups (рекомендуется для облачных решений)
- Включить automatic backups в облачном провайдере
- Point-in-time recovery
- Cross-region backups для критических данных

### 7.2 Custom backup script
```bash
#!/bin/bash
# backup_all_databases.sh

BACKUP_DIR="/backups/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"

databases=(
    "repitbot_users"
    "repitbot_lessons" 
    "repitbot_homework"
    "repitbot_payments"
    "repitbot_materials"
    "repitbot_notifications"
    "repitbot_analytics"
    "repitbot_students"
    "repitbot_gateway"
)

for db in "${databases[@]}"; do
    pg_dump -h YOUR_HOST -U repitbot_admin -d "$db" > "$BACKUP_DIR/$db.sql"
    gzip "$BACKUP_DIR/$db.sql"
done
```

## ✅ Итоговый чеклист

### После настройки SQL базы должно быть:
- [ ] 9 изолированных баз данных созданы
- [ ] Пользователи с минимальными правами настроены
- [ ] Connection strings для всех сервисов готовы
- [ ] Миграции выполнены успешно
- [ ] SSL соединения настроены
- [ ] Backup стратегия реализована
- [ ] Мониторинг включен
- [ ] Credentials безопасно сохранены (НЕ в Git!)

Теперь SQL база данных готова для production использования! 🚀