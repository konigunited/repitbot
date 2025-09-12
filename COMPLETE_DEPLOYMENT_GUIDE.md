# 🚀 RepitBot Microservices - Полная инструкция по развертыванию

[![Production Ready](https://img.shields.io/badge/Production-Ready-green)](https://github.com/konigunited/repitbot)
[![Microservices](https://img.shields.io/badge/Microservices-9-blue)](https://github.com/konigunited/repitbot)

> **Единая пошаговая инструкция** для полного развертывания микросервисной архитектуры RepitBot в production

---

## 📋 ОГЛАВЛЕНИЕ

1. [Обзор архитектуры](#-обзор-архитектуры)
2. [Требования к серверу](#-требования-к-серверу)  
3. [Подготовка сервера](#-этап-1-подготовка-сервера)
4. [Установка PostgreSQL](#-этап-2-установка-postgresql)
5. [Клонирование репозитория](#-этап-3-клонирование-репозитория)
6. [Настройка секретов](#-этап-4-настройка-секретов)
7. [Настройка баз данных](#-этап-5-настройка-баз-данных)
8. [Развертывание Docker](#-этап-6-развертывание-docker)
9. [Проверка и тестирование](#-этап-7-проверка-и-тестирование)
10. [Мониторинг и обслуживание](#-этап-8-мониторинг-и-обслуживание)
11. [Troubleshooting](#-troubleshooting)

---

## 🏗️ ОБЗОР АРХИТЕКТУРЫ

### Микросервисная система (9 сервисов)
```
🌐 API Gateway (8000) ──┬── 👥 User Service (8001)
                        ├── 📚 Lesson Service (8002)  
                        ├── 📝 Homework Service (8003)
                        ├── 💰 Payment Service (8004)
                        ├── 📁 Material Service (8005)
                        ├── 🔔 Notification Service (8006)
                        ├── 📊 Analytics Service (8007)
                        └── 🎯 Student Service (8008)

Infrastructure: PostgreSQL + RabbitMQ + Redis + Prometheus + Grafana
```

### Основные возможности
- **3 роли пользователей**: Родитель, Ученик, Репетитор
- **Event-driven архитектура** с RabbitMQ
- **Система достижений** и геймификация
- **Автоматические уведомления** (Telegram, Email)
- **Аналитика и отчеты** в реальном времени
- **Файловая система** для материалов и домашних заданий

---

## 💻 ТРЕБОВАНИЯ К СЕРВЕРУ

### Минимальные требования
- **OS**: Ubuntu 20.04+ LTS (рекомендуется 22.04)
- **CPU**: 4 cores (рекомендуется 8+ cores)
- **RAM**: 8 GB (рекомендуется 16+ GB)
- **Storage**: 100 GB SSD (рекомендуется 200+ GB)
- **Network**: Статический IP адрес
- **Domain**: Доменное имя для SSL сертификатов

### Сетевые порты
```
22    - SSH доступ
80    - HTTP (редирект на HTTPS)
443   - HTTPS (основной доступ)
5432  - PostgreSQL (только для внутренних подключений)
8000  - API Gateway (внутренний)
8001-8008 - Микросервисы (внутренние)
```

---

## 🛠️ ЭТАП 1: Подготовка сервера

### 1.1 Подключение к серверу
```bash
# Подключение по SSH
ssh root@YOUR_SERVER_IP
# или ssh username@YOUR_SERVER_IP
```

### 1.2 Обновление системы
```bash
# Обновить пакеты
apt update && apt upgrade -y

# Установить необходимые утилиты
apt install -y curl wget gnupg2 software-properties-common apt-transport-https \
    git vim htop tree unzip zip build-essential python3-pip

# Перезагрузка (если обновлялось ядро)
reboot
```

### 1.3 Настройка пользователя (если работаете под root)
```bash
# Создать пользователя для приложения
adduser repitbot
usermod -aG sudo repitbot

# Переключиться на нового пользователя
su - repitbot
cd ~
```

### 1.4 Настройка firewall
```bash
# Установить и настроить UFW
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw allow 5432  # PostgreSQL (временно для настройки)
sudo ufw --force enable

# Проверить статус
sudo ufw status
```

---

## 🐘 ЭТАП 2: Установка PostgreSQL

### 2.1 Добавление репозитория PostgreSQL
```bash
# Добавить GPG ключ
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Добавить репозиторий
echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list

# Обновить пакеты
sudo apt update
```

### 2.2 Установка PostgreSQL 15
```bash
# Установить PostgreSQL
sudo apt install -y postgresql-15 postgresql-client-15 postgresql-contrib-15

# Проверить статус
sudo systemctl status postgresql
sudo systemctl enable postgresql
```

### 2.3 Настройка PostgreSQL конфигурации
```bash
# Найти конфигурационный файл
sudo find /etc/postgresql -name "postgresql.conf"
# Обычно: /etc/postgresql/15/main/postgresql.conf

# Создать backup конфигурации
sudo cp /etc/postgresql/15/main/postgresql.conf /etc/postgresql/15/main/postgresql.conf.backup

# Редактировать конфигурацию
sudo nano /etc/postgresql/15/main/postgresql.conf
```

**Важные настройки в postgresql.conf:**
```ini
# ============== CONNECTION SETTINGS ==============
listen_addresses = '*'
port = 5432
max_connections = 300

# ============== MEMORY SETTINGS ==============  
shared_buffers = 512MB       # Для сервера с 8GB RAM
effective_cache_size = 2GB   # 1/4 от общей RAM
work_mem = 8MB
maintenance_work_mem = 128MB

# ============== PERFORMANCE ==============
checkpoint_completion_target = 0.9
wal_buffers = 32MB
random_page_cost = 1.1
effective_io_concurrency = 200

# ============== LOGGING ==============
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_statement = 'mod'
log_min_duration_statement = 1000

# ============== SECURITY ==============
ssl = on
password_encryption = 'scram-sha-256'
```

### 2.4 Настройка доступа (pg_hba.conf)
```bash
# Создать backup
sudo cp /etc/postgresql/15/main/pg_hba.conf /etc/postgresql/15/main/pg_hba.conf.backup

# Редактировать файл доступа
sudo nano /etc/postgresql/15/main/pg_hba.conf
```

**Добавить в конец pg_hba.conf:**
```
# ============== REPITBOT MICROSERVICES ==============
# Local connections
local   all             postgres                        peer
local   all             repitbot_admin                  scram-sha-256

# Docker containers access (localhost)
host    repitbot_users          repitbot_user_service       127.0.0.1/32    scram-sha-256
host    repitbot_lessons        repitbot_lesson_service     127.0.0.1/32    scram-sha-256
host    repitbot_homework       repitbot_homework_service   127.0.0.1/32    scram-sha-256
host    repitbot_payments       repitbot_payment_service    127.0.0.1/32    scram-sha-256
host    repitbot_materials      repitbot_material_service   127.0.0.1/32    scram-sha-256
host    repitbot_notifications  repitbot_notification_service 127.0.0.1/32  scram-sha-256
host    repitbot_analytics      repitbot_analytics_service  127.0.0.1/32    scram-sha-256
host    repitbot_students       repitbot_student_service    127.0.0.1/32    scram-sha-256
host    repitbot_gateway        repitbot_gateway            127.0.0.1/32    scram-sha-256

# Admin access
host    all                     repitbot_admin              127.0.0.1/32    scram-sha-256
```

### 2.5 Создание SSL сертификатов
```bash
# Перейти в папку PostgreSQL
cd /etc/postgresql/15/main/

# Создать приватный ключ
sudo openssl genrsa -out server.key 2048

# Создать сертификат
sudo openssl req -new -x509 -key server.key -out server.crt -days 365 -subj "/C=RU/ST=Moscow/L=Moscow/O=RepitBot/CN=localhost"

# Установить права
sudo chown postgres:postgres server.key server.crt
sudo chmod 600 server.key
sudo chmod 644 server.crt

# Перезапустить PostgreSQL
sudo systemctl restart postgresql
```

---

## 📥 ЭТАП 3: Клонирование репозитория

### 3.1 Установка Docker и Docker Compose
```bash
# Установить Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавить пользователя в группу docker
sudo usermod -aG docker $USER

# Установить Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Перезайти для применения группы docker
exit
ssh repitbot@YOUR_SERVER_IP
```

### 3.2 Клонирование репозитория
```bash
# Клонировать RepitBot репозиторий
cd ~
git clone https://github.com/konigunited/repitbot.git
cd repitbot

# Проверить структуру
ls -la
tree services/ -L 2
```

---

## 🔐 ЭТАП 4: Настройка секретов

### 4.1 Генерация сильных паролей
```bash
# Создать скрипт для генерации паролей
cat > generate_passwords.py << 'EOF'
#!/usr/bin/env python3
import secrets
import string

def generate_password(length=20):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_jwt_secret():
    return secrets.token_hex(32)

# Генерация паролей для всех сервисов
print("=== RepitBot Production Passwords ===")
print("⚠️  СОХРАНИТЕ ЭТИ ПАРОЛИ В БЕЗОПАСНОМ МЕСТЕ!")
print()

services = [
    'user', 'lesson', 'homework', 'payment', 'material', 
    'notification', 'analytics', 'student', 'gateway', 'admin'
]

passwords = {}
for service in services:
    passwords[service] = generate_password()
    print(f"DB_PASSWORD_{service.upper()}={passwords[service]}")

print()
print("=== JWT and Security Keys ===")
print(f"JWT_SECRET_KEY={generate_jwt_secret()}")
print(f"JWT_REFRESH_SECRET={generate_jwt_secret()}")
print(f"API_SECRET_KEY={generate_jwt_secret()}")
print(f"SESSION_SECRET={secrets.token_urlsafe(32)}")
print(f"WEBHOOK_SECRET={secrets.token_urlsafe(16)}")
EOF

# Выполнить генерацию
python3 generate_passwords.py > passwords.txt
chmod 600 passwords.txt

# Показать сгенерированные пароли
cat passwords.txt
```

### 4.2 Создание .env.production файла
```bash
# Скопировать шаблон
cp .env.production.example .env.production
chmod 600 .env.production

# Редактировать .env.production
nano .env.production
```

**Заполнить основные переменные в .env.production:**
```bash
# ============== GENERAL ==============
ENVIRONMENT=production
DEBUG=false

# ============== DATABASE (замените пароли на сгенерированные) ==============
DATABASE_HOST=localhost
DATABASE_URL_USER=postgresql+asyncpg://repitbot_user_service:GENERATED_PASSWORD_1@localhost:5432/repitbot_users?sslmode=require
DATABASE_URL_LESSON=postgresql+asyncpg://repitbot_lesson_service:GENERATED_PASSWORD_2@localhost:5432/repitbot_lessons?sslmode=require
DATABASE_URL_HOMEWORK=postgresql+asyncpg://repitbot_homework_service:GENERATED_PASSWORD_3@localhost:5432/repitbot_homework?sslmode=require
DATABASE_URL_PAYMENT=postgresql+asyncpg://repitbot_payment_service:GENERATED_PASSWORD_4@localhost:5432/repitbot_payments?sslmode=require
DATABASE_URL_MATERIAL=postgresql+asyncpg://repitbot_material_service:GENERATED_PASSWORD_5@localhost:5432/repitbot_materials?sslmode=require
DATABASE_URL_NOTIFICATION=postgresql+asyncpg://repitbot_notification_service:GENERATED_PASSWORD_6@localhost:5432/repitbot_notifications?sslmode=require
DATABASE_URL_ANALYTICS=postgresql+asyncpg://repitbot_analytics_service:GENERATED_PASSWORD_7@localhost:5432/repitbot_analytics?sslmode=require
DATABASE_URL_STUDENT=postgresql+asyncpg://repitbot_student_service:GENERATED_PASSWORD_8@localhost:5432/repitbot_students?sslmode=require
DATABASE_URL_GATEWAY=postgresql+asyncpg://repitbot_gateway:GENERATED_PASSWORD_9@localhost:5432/repitbot_gateway?sslmode=require

# ============== SECURITY (используйте сгенерированные ключи) ==============
JWT_SECRET_KEY=GENERATED_JWT_SECRET
JWT_REFRESH_SECRET=GENERATED_JWT_REFRESH_SECRET
API_SECRET_KEY=GENERATED_API_SECRET

# ============== TELEGRAM BOT ==============
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN_FROM_BOTFATHER

# ============== EXTERNAL SERVICES ==============
RABBITMQ_URL=amqp://repitbot:STRONG_RABBITMQ_PASSWORD@localhost:5672/repitbot_vhost
REDIS_URL=redis://localhost:6379/0

# ============== EMAIL (опционально) ==============
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# ============== CORS и SECURITY ==============
CORS_ORIGINS=https://your-domain.com
EXTERNAL_API_URL=https://your-domain.com
EXTERNAL_WEBHOOK_URL=https://your-domain.com/webhook
```

---

## 🗄️ ЭТАП 5: Настройка баз данных

### 5.1 Создание администратора БД
```bash
# Войти в PostgreSQL как postgres
sudo -u postgres psql

# Создать администратора (в psql терминале)
CREATE USER repitbot_admin WITH PASSWORD 'GENERATED_ADMIN_PASSWORD' CREATEDB CREATEROLE;
ALTER USER repitbot_admin WITH SUPERUSER;
\q
```

### 5.2 Создание всех баз данных и пользователей
```bash
# Создать SQL скрипт для всех БД
cat > setup_databases.sql << 'EOF'
-- ============== СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ ==============
CREATE USER repitbot_user_service WITH PASSWORD 'GENERATED_PASSWORD_1';
CREATE USER repitbot_lesson_service WITH PASSWORD 'GENERATED_PASSWORD_2';
CREATE USER repitbot_homework_service WITH PASSWORD 'GENERATED_PASSWORD_3';
CREATE USER repitbot_payment_service WITH PASSWORD 'GENERATED_PASSWORD_4';
CREATE USER repitbot_material_service WITH PASSWORD 'GENERATED_PASSWORD_5';
CREATE USER repitbot_notification_service WITH PASSWORD 'GENERATED_PASSWORD_6';
CREATE USER repitbot_analytics_service WITH PASSWORD 'GENERATED_PASSWORD_7';
CREATE USER repitbot_student_service WITH PASSWORD 'GENERATED_PASSWORD_8';
CREATE USER repitbot_gateway WITH PASSWORD 'GENERATED_PASSWORD_9';

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
GRANT ALL PRIVILEGES ON DATABASE repitbot_users TO repitbot_user_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_lessons TO repitbot_lesson_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_homework TO repitbot_homework_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_payments TO repitbot_payment_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_materials TO repitbot_material_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_notifications TO repitbot_notification_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_analytics TO repitbot_analytics_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_students TO repitbot_student_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_gateway TO repitbot_gateway;

-- Analytics сервису READ доступ к другим БД
GRANT CONNECT ON DATABASE repitbot_users TO repitbot_analytics_service;
GRANT CONNECT ON DATABASE repitbot_lessons TO repitbot_analytics_service;
GRANT CONNECT ON DATABASE repitbot_homework TO repitbot_analytics_service;
GRANT CONNECT ON DATABASE repitbot_payments TO repitbot_analytics_service;
GRANT CONNECT ON DATABASE repitbot_materials TO repitbot_analytics_service;
GRANT CONNECT ON DATABASE repitbot_students TO repitbot_analytics_service;

-- Проверка
SELECT datname FROM pg_database WHERE datname LIKE 'repitbot_%';
EOF

# Заменить GENERATED_PASSWORD_X на реальные пароли из passwords.txt
nano setup_databases.sql

# Выполнить скрипт
sudo -u postgres psql -f setup_databases.sql

# Удалить скрипт с паролями
rm setup_databases.sql
```

### 5.3 Проверка создания БД
```bash
# Проверить созданные базы данных
sudo -u postgres psql -c "SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database WHERE datname LIKE 'repitbot_%';"

# Тест подключения к одной из баз
PGPASSWORD='GENERATED_PASSWORD_1' psql -h localhost -U repitbot_user_service -d repitbot_users -c "SELECT current_database(), current_user;"
```

---

## 🐳 ЭТАП 6: Развертывание Docker

### 6.1 Проверка Docker конфигурации
```bash
# Проверить docker-compose файл
cat docker-compose.microservices.yml | grep -A 5 -B 5 "DATABASE_URL"

# Проверить что .env.production файл правильно настроен
grep "DATABASE_URL_USER" .env.production
```

### 6.2 Установка дополнительных зависимостей
```bash
# Установить Redis
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Установить RabbitMQ
sudo apt install -y rabbitmq-server
sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server

# Настроить RabbitMQ пользователя
sudo rabbitmqctl add_user repitbot STRONG_RABBITMQ_PASSWORD
sudo rabbitmqctl set_permissions -p / repitbot ".*" ".*" ".*"
sudo rabbitmqctl add_vhost repitbot_vhost
sudo rabbitmqctl set_permissions -p repitbot_vhost repitbot ".*" ".*" ".*"
```

### 6.3 Сборка и запуск микросервисов
```bash
# Создать необходимые папки
mkdir -p logs uploads storage

# Сборка всех Docker образов
docker-compose -f docker-compose.microservices.yml build

# Проверка образов
docker images | grep repitbot

# Запуск всех сервисов
docker-compose -f docker-compose.microservices.yml up -d

# Проверка запущенных контейнеров
docker-compose -f docker-compose.microservices.yml ps
```

### 6.4 Выполнение миграций баз данных
```bash
# Дождаться пока все контейнеры запустятся (30-60 секунд)
sleep 60

# Создать скрипт для миграций всех сервисов
cat > run_migrations.sh << 'EOF'
#!/bin/bash
echo "🔄 Выполнение миграций для всех микросервисов..."

services=(
    "user-service"
    "lesson-service" 
    "homework-service"
    "payment-service"
    "material-service"
    "notification-service"
    "analytics-service"
    "student-service"
)

for service in "${services[@]}"; do
    echo "📋 Миграция $service..."
    if [ -d "services/$service" ] && [ -f "services/$service/alembic.ini" ]; then
        cd "services/$service"
        docker-compose -f ../../docker-compose.microservices.yml exec -T "${service//-/_}" alembic upgrade head 2>/dev/null || echo "⚠️ Alembic не найден для $service"
        cd ../..
    else
        echo "⚠️ Alembic конфигурация не найдена для $service"
    fi
done

echo "✅ Миграции завершены!"
EOF

chmod +x run_migrations.sh
./run_migrations.sh
```

---

## ✅ ЭТАП 7: Проверка и тестирование

### 7.1 Проверка статуса всех сервисов
```bash
# Проверить статус контейнеров
docker-compose -f docker-compose.microservices.yml ps

# Проверить логи
docker-compose -f docker-compose.microservices.yml logs --tail=20

# Health check всех сервисов
curl http://localhost:8000/health/all
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
curl http://localhost:8005/health
curl http://localhost:8006/health
curl http://localhost:8007/health
curl http://localhost:8008/health
```

### 7.2 Проверка API Gateway
```bash
# Тест API Gateway
curl -X GET http://localhost:8000/health \
  -H "Content-Type: application/json"

# Тест маршрутизации через Gateway
curl -X GET http://localhost:8000/api/v1/users/health \
  -H "Content-Type: application/json"
```

### 7.3 Проверка баз данных
```bash
# Проверить подключения к БД
docker-compose -f docker-compose.microservices.yml exec user_service python -c "
from app.database.connection import get_db_connection
import asyncio
async def test():
    async with get_db_connection() as db:
        result = await db.execute('SELECT current_database()')
        print('✅ User Service DB:', result.fetchone())
asyncio.run(test())
"
```

### 7.4 Запуск тестов
```bash
# Установить зависимости для тестов
pip3 install -r tests/requirements.txt

# Запустить базовые тесты
cd tests/
python3 run_tests.py --fast

# Infrastructure тесты
python3 -m pytest test_infrastructure.py -v

# Functional тесты (базовые)
python3 -m pytest test_functional_parent.py::test_basic_parent_functions -v
```

---

## 📊 ЭТАП 8: Мониторинг и обслуживание

### 8.1 Настройка Nginx (reverse proxy)
```bash
# Установить Nginx
sudo apt install -y nginx

# Создать конфигурацию для RepitBot
sudo tee /etc/nginx/sites-available/repitbot << EOF
server {
    listen 80;
    server_name YOUR_DOMAIN.com www.YOUR_DOMAIN.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name YOUR_DOMAIN.com www.YOUR_DOMAIN.com;
    
    # SSL Configuration (замените на реальные пути к сертификатам)
    ssl_certificate /etc/ssl/certs/repitbot.crt;
    ssl_private_key /etc/ssl/private/repitbot.key;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # Proxy to API Gateway
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
    
    # Static files (если нужны)
    location /static/ {
        alias /home/repitbot/repitbot/uploads/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Активировать конфигурацию
sudo ln -sf /etc/nginx/sites-available/repitbot /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Проверить конфигурацию
sudo nginx -t

# Перезапустить Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 8.2 Настройка SSL сертификатов (Let's Encrypt)
```bash
# Установить Certbot
sudo apt install -y snapd
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot

# Получить SSL сертификат
sudo certbot --nginx -d YOUR_DOMAIN.com -d www.YOUR_DOMAIN.com

# Проверить автообновление
sudo certbot renew --dry-run
```

### 8.3 Мониторинг скрипты
```bash
# Создать скрипт мониторинга системы
sudo tee /usr/local/bin/repitbot_monitor.sh << 'EOF'
#!/bin/bash
echo "=== RepitBot System Status ==="
echo "Date: $(date)"
echo ""

echo "=== Docker Containers ==="
cd /home/repitbot/repitbot
docker-compose -f docker-compose.microservices.yml ps

echo ""
echo "=== Service Health Checks ==="
for port in {8000..8008}; do
    if curl -s http://localhost:$port/health > /dev/null; then
        echo "✅ Port $port: OK"
    else
        echo "❌ Port $port: FAILED"
    fi
done

echo ""
echo "=== Database Status ==="
sudo -u postgres psql -c "SELECT datname, numbackends FROM pg_stat_database WHERE datname LIKE 'repitbot_%';" 2>/dev/null || echo "❌ PostgreSQL connection failed"

echo ""
echo "=== System Resources ==="
echo "CPU: $(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1"%"}')"
echo "Memory: $(free -m | awk 'NR==2{printf "%.1f%%\n", $3*100/$2}')"
echo "Disk: $(df -h / | awk 'NR==2 {print $5}')"

echo ""
echo "=== Recent Errors ==="
tail -5 /var/log/nginx/error.log 2>/dev/null || echo "No Nginx errors"
EOF

chmod +x /usr/local/bin/repitbot_monitor.sh

# Создать cron задачу для мониторинга
echo "*/15 * * * * /usr/local/bin/repitbot_monitor.sh >> /var/log/repitbot_monitor.log 2>&1" | crontab -

# Тест скрипта
/usr/local/bin/repitbot_monitor.sh
```

### 8.4 Автоматические backup
```bash
# Создать скрипт backup
sudo tee /usr/local/bin/backup_repitbot.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/repitbot"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
mkdir -p "$BACKUP_DIR/$DATE"

echo "🔄 Starting RepitBot backup: $DATE"

# Database backup
databases=(repitbot_users repitbot_lessons repitbot_homework repitbot_payments repitbot_materials repitbot_notifications repitbot_analytics repitbot_students repitbot_gateway)
for db in "${databases[@]}"; do
    echo "📊 Backing up $db..."
    pg_dump -U repitbot_admin -h localhost "$db" | gzip > "$BACKUP_DIR/$DATE/${db}.sql.gz"
done

# Application files backup
echo "📁 Backing up application files..."
cd /home/repitbot
tar -czf "$BACKUP_DIR/$DATE/repitbot_app.tar.gz" \
    --exclude='repitbot/logs/*' \
    --exclude='repitbot/.git' \
    --exclude='repitbot/venv' \
    --exclude='repitbot/.env.production' \
    repitbot/

# Docker images backup (optional)
echo "🐳 Backing up Docker images..."
docker save $(docker images --format "table {{.Repository}}:{{.Tag}}" | grep repitbot | tr '\n' ' ') | gzip > "$BACKUP_DIR/$DATE/docker_images.tar.gz"

# Cleanup old backups (keep 7 days)
find "$BACKUP_DIR" -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true

echo "✅ Backup completed: $BACKUP_DIR/$DATE"
df -h "$BACKUP_DIR"
EOF

chmod +x /usr/local/bin/backup_repitbot.sh

# Настроить ежедневный backup в 3 утра
echo "0 3 * * * /usr/local/bin/backup_repitbot.sh >> /var/log/repitbot_backup.log 2>&1" | sudo crontab -

# Тест backup
sudo /usr/local/bin/backup_repitbot.sh
```

---

## 🚨 TROUBLESHOOTING

### Проблема: Сервис не запускается
```bash
# Проверить логи конкретного сервиса
docker-compose -f docker-compose.microservices.yml logs service-name

# Проверить переменные окружения
docker-compose -f docker-compose.microservices.yml exec service-name env | grep DATABASE

# Перезапустить сервис
docker-compose -f docker-compose.microservices.yml restart service-name
```

### Проблема: База данных недоступна
```bash
# Проверить статус PostgreSQL
sudo systemctl status postgresql

# Проверить подключения
sudo -u postgres psql -c "SELECT datname, numbackends FROM pg_stat_database WHERE datname LIKE 'repitbot_%';"

# Проверить логи PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

### Проблема: Telegram Bot не отвечает
```bash
# Проверить BOT_TOKEN в .env.production
grep BOT_TOKEN .env.production

# Проверить логи telegram-bot контейнера
docker-compose -f docker-compose.microservices.yml logs telegram-bot

# Тест webhook
curl -X POST "https://api.telegram.org/bot$BOT_TOKEN/setWebhook?url=https://YOUR_DOMAIN.com/webhook"
```

### Проблема: Медленная работа
```bash
# Проверить использование ресурсов
htop
docker stats

# Проверить медленные SQL запросы
sudo -u postgres psql repitbot_analytics -c "SELECT query, mean_exec_time, calls FROM pg_stat_statements WHERE mean_exec_time > 1000 ORDER BY mean_exec_time DESC LIMIT 10;"

# Оптимизировать PostgreSQL
sudo nano /etc/postgresql/15/main/postgresql.conf
# Увеличить shared_buffers и effective_cache_size
```

### Полезные команды для диагностики
```bash
# Статус всех сервисов
systemctl status postgresql rabbitmq-server redis-server nginx

# Сетевые подключения
sudo netstat -tlnp | grep -E "(8000|8001|8002|8003|8004|8005|8006|8007|8008|5432)"

# Использование дискового пространства
du -sh /home/repitbot/repitbot/
du -sh /var/lib/postgresql/
du -sh /var/backups/repitbot/

# Docker cleanup (если нужно место)
docker system prune -af
docker volume prune -f
```

---

## ✅ ФИНАЛЬНЫЙ CHECKLIST

### После завершения deployment проверьте:
- [ ] Все 9 микросервисов запущены и отвечают на health checks
- [ ] API Gateway доступен через https://YOUR_DOMAIN.com
- [ ] PostgreSQL работает со всеми 9 базами данных
- [ ] Telegram Bot отвечает на команды
- [ ] SSL сертификаты установлены и работают
- [ ] Nginx правильно проксирует запросы
- [ ] Мониторинг скрипты работают
- [ ] Автоматические backup настроены
- [ ] Firewall правильно настроен
- [ ] Все пароли уникальные и безопасные

### Проверочные команды:
```bash
# Общий статус системы
/usr/local/bin/repitbot_monitor.sh

# Health check всех сервисов
curl https://YOUR_DOMAIN.com/health/all

# Тест API через Gateway
curl https://YOUR_DOMAIN.com/api/v1/users/health

# Проверка SSL
curl -I https://YOUR_DOMAIN.com

# Статус backup
ls -la /var/backups/repitbot/
```

---

## 🎉 ПОЗДРАВЛЯЕМ!

**RepitBot микросервисная архитектура успешно развернута в production!** 

### 🚀 Что у вас теперь есть:
- **9 микросервисов** работают в production
- **Event-driven архитектура** полностью функциональна
- **3 роли пользователей** (Родитель/Ученик/Репетитор) поддержаны
- **Система достижений** и геймификация активны
- **Автоматические уведомления** настроены
- **Мониторинг и backup** работают автоматически
- **SSL безопасность** обеспечена

### 📞 Поддержка:
- **Мониторинг**: `/usr/local/bin/repitbot_monitor.sh`
- **Логи**: `/var/log/repitbot_*.log`
- **Backup**: `/var/backups/repitbot/`
- **GitHub**: https://github.com/konigunited/repitbot

**Система готова к эксплуатации!** 🎊