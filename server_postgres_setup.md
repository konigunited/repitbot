# 🗄️ PostgreSQL Setup на Ubuntu Server для RepitBot

## 🎯 Цель: Настройка PostgreSQL 14+ на Ubuntu 20.04+ для микросервисной архитектуры

### 📋 Требования к серверу
- Ubuntu 20.04+ или Ubuntu 22.04 LTS (рекомендуется)
- Минимум 4 GB RAM (рекомендуется 8+ GB)
- 50+ GB свободного места
- Sudo доступ
- Интернет соединение

---

## 🚀 ШАГ 1: Подготовка Ubuntu сервера

### 1.1 Обновление системы
```bash
# Обновить пакеты
sudo apt update && sudo apt upgrade -y

# Установить необходимые утилиты
sudo apt install -y curl wget gnupg2 software-properties-common apt-transport-https
```

### 1.2 Настройка firewall (если необходимо)
```bash
# Установить UFW firewall
sudo apt install -y ufw

# Разрешить SSH
sudo ufw allow ssh

# Разрешить PostgreSQL (порт 5432)
sudo ufw allow 5432

# Включить firewall
sudo ufw enable
```

---

## 🐘 ШАГ 2: Установка PostgreSQL 14+

### 2.1 Добавление официального репозитория PostgreSQL
```bash
# Добавить GPG ключ PostgreSQL
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Добавить репозиторий PostgreSQL
echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list

# Обновить пакеты
sudo apt update
```

### 2.2 Установка PostgreSQL
```bash
# Установить PostgreSQL 15 (latest stable)
sudo apt install -y postgresql-15 postgresql-client-15 postgresql-contrib-15

# Проверить статус
sudo systemctl status postgresql

# Включить автозапуск
sudo systemctl enable postgresql
```

### 2.3 Проверка установки
```bash
# Проверить версию
sudo -u postgres psql -c "SELECT version();"

# Должен показать: PostgreSQL 15.x
```

---

## 🔧 ШАГ 3: Настройка PostgreSQL для production

### 3.1 Настройка postgresql.conf
```bash
# Найти конфигурационный файл
sudo find /etc/postgresql -name "postgresql.conf"
# Обычно: /etc/postgresql/15/main/postgresql.conf

# Редактировать конфигурацию
sudo nano /etc/postgresql/15/main/postgresql.conf
```

**Важные настройки для production:**
```ini
# ============== CONNECTION SETTINGS ==============
listen_addresses = '*'          # Слушать все интерфейсы
port = 5432                     # Стандартный порт PostgreSQL
max_connections = 200           # Увеличить для микросервисов

# ============== MEMORY SETTINGS ==============
shared_buffers = 256MB          # 1/4 от RAM (для 4GB сервера)
effective_cache_size = 1GB      # 3/4 от RAM
work_mem = 4MB                  # Для сортировки и join
maintenance_work_mem = 64MB     # Для VACUUM и INDEX

# ============== LOGGING ==============
logging_collector = on          # Включить логирование
log_directory = 'log'           # Папка логов
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_statement = 'mod'           # Логировать DDL и DML
log_min_duration_statement = 1000  # Логировать медленные запросы (1сек)

# ============== PERFORMANCE ==============
checkpoint_completion_target = 0.9
wal_buffers = 16MB
random_page_cost = 1.1          # Для SSD
effective_io_concurrency = 200  # Для SSD

# ============== SECURITY ==============
ssl = on                        # Включить SSL
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'
password_encryption = 'scram-sha-256'  # Современное шифрование
```

### 3.2 Настройка pg_hba.conf (доступ)
```bash
# Редактировать файл доступа
sudo nano /etc/postgresql/15/main/pg_hba.conf
```

**Добавить в конец файла:**
```
# ============== REPITBOT MICROSERVICES ACCESS ==============
# Local connections
local   all             postgres                                peer
local   all             repitbot_admin                          scram-sha-256

# Remote connections для микросервисов (замените IP на ваши)
host    repitbot_users      repitbot_user_service      10.0.0.0/8        scram-sha-256
host    repitbot_lessons    repitbot_lesson_service    10.0.0.0/8        scram-sha-256
host    repitbot_homework   repitbot_homework_service  10.0.0.0/8        scram-sha-256
host    repitbot_payments   repitbot_payment_service   10.0.0.0/8        scram-sha-256
host    repitbot_materials  repitbot_material_service  10.0.0.0/8        scram-sha-256
host    repitbot_notifications repitbot_notification_service 10.0.0.0/8   scram-sha-256
host    repitbot_analytics  repitbot_analytics_service 10.0.0.0/8        scram-sha-256
host    repitbot_students   repitbot_student_service   10.0.0.0/8        scram-sha-256
host    repitbot_gateway    repitbot_gateway           10.0.0.0/8        scram-sha-256

# Admin access для миграций
host    all                 repitbot_admin             10.0.0.0/8        scram-sha-256

# ⚠️ ЗАМЕНИТЕ 10.0.0.0/8 на реальные IP адреса ваших серверов!
# Для single server можно использовать 127.0.0.1/32
```

### 3.3 Перезапуск PostgreSQL
```bash
# Перезапустить PostgreSQL
sudo systemctl restart postgresql

# Проверить статус
sudo systemctl status postgresql

# Проверить что слушает порт 5432
sudo ss -tlnp | grep 5432
```

---

## 🔐 ШАГ 4: Создание пользователей и баз данных

### 4.1 Вход в PostgreSQL как суперпользователь
```bash
sudo -u postgres psql
```

### 4.2 Создание администратора RepitBot
```sql
-- Создать суперпользователя для администрирования
CREATE USER repitbot_admin WITH PASSWORD 'STRONG_ADMIN_PASSWORD_HERE' CREATEDB CREATEROLE;
ALTER USER repitbot_admin WITH SUPERUSER;

-- Выйти
\q
```

### 4.3 Выполнение SQL скрипта для создания всех БД
```bash
# Создать файл с SQL командами для всех сервисов
cat > /tmp/create_repitbot_databases.sql << 'EOF'
-- ============== RepitBot Production Database Setup ==============

-- Создание пользователей для каждого сервиса (ЗАМЕНИТЕ ПАРОЛИ!)
CREATE USER repitbot_user_service WITH PASSWORD 'STRONG_PASSWORD_1';
CREATE USER repitbot_lesson_service WITH PASSWORD 'STRONG_PASSWORD_2';  
CREATE USER repitbot_homework_service WITH PASSWORD 'STRONG_PASSWORD_3';
CREATE USER repitbot_payment_service WITH PASSWORD 'STRONG_PASSWORD_4';
CREATE USER repitbot_material_service WITH PASSWORD 'STRONG_PASSWORD_5';
CREATE USER repitbot_notification_service WITH PASSWORD 'STRONG_PASSWORD_6';
CREATE USER repitbot_analytics_service WITH PASSWORD 'STRONG_PASSWORD_7';
CREATE USER repitbot_student_service WITH PASSWORD 'STRONG_PASSWORD_8';
CREATE USER repitbot_gateway WITH PASSWORD 'STRONG_PASSWORD_9';

-- Создание баз данных
CREATE DATABASE repitbot_users OWNER repitbot_user_service;
CREATE DATABASE repitbot_lessons OWNER repitbot_lesson_service;
CREATE DATABASE repitbot_homework OWNER repitbot_homework_service;
CREATE DATABASE repitbot_payments OWNER repitbot_payment_service;
CREATE DATABASE repitbot_materials OWNER repitbot_material_service;
CREATE DATABASE repitbot_notifications OWNER repitbot_notification_service;
CREATE DATABASE repitbot_analytics OWNER repitbot_analytics_service;
CREATE DATABASE repitbot_students OWNER repitbot_student_service;
CREATE DATABASE repitbot_gateway OWNER repitbot_gateway;

-- Права доступа к своим БД
GRANT ALL PRIVILEGES ON DATABASE repitbot_users TO repitbot_user_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_lessons TO repitbot_lesson_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_homework TO repitbot_homework_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_payments TO repitbot_payment_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_materials TO repitbot_material_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_notifications TO repitbot_notification_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_analytics TO repitbot_analytics_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_students TO repitbot_student_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_gateway TO repitbot_gateway;

-- Analytics сервису READ доступ к другим БД для отчетов
GRANT CONNECT ON DATABASE repitbot_users TO repitbot_analytics_service;
GRANT CONNECT ON DATABASE repitbot_lessons TO repitbot_analytics_service;
GRANT CONNECT ON DATABASE repitbot_homework TO repitbot_analytics_service;
GRANT CONNECT ON DATABASE repitbot_payments TO repitbot_analytics_service;
GRANT CONNECT ON DATABASE repitbot_materials TO repitbot_analytics_service;
GRANT CONNECT ON DATABASE repitbot_students TO repitbot_analytics_service;

-- Проверка созданных БД
SELECT datname, datconnlimit, encoding FROM pg_database WHERE datname LIKE 'repitbot_%';

-- Проверка пользователей
SELECT usename, usesuper, usecreatedb, useconnlimit FROM pg_user WHERE usename LIKE 'repitbot_%';
EOF

# Выполнить скрипт
sudo -u postgres psql -f /tmp/create_repitbot_databases.sql

# Удалить временный файл с паролями
rm /tmp/create_repitbot_databases.sql
```

---

## 🔒 ШАГ 5: Настройка SSL сертификатов

### 5.1 Создание самоподписанного SSL сертификата
```bash
# Перейти в папку PostgreSQL
cd /etc/postgresql/15/main/

# Создать приватный ключ
sudo openssl genrsa -out server.key 2048

# Создать сертификат (заполните данные организации)
sudo openssl req -new -x509 -key server.key -out server.crt -days 365

# Установить правильные права
sudo chown postgres:postgres server.key server.crt
sudo chmod 600 server.key
sudo chmod 644 server.crt
```

### 5.2 Проверка SSL
```bash
# Перезапустить PostgreSQL
sudo systemctl restart postgresql

# Проверить SSL подключение
sudo -u postgres psql -c "SHOW ssl;"
# Должно показать: on
```

---

## 📊 ШАГ 6: Оптимизация и мониторинг

### 6.1 Установка pg_stat_statements (для мониторинга запросов)
```bash
# Добавить в postgresql.conf
echo "shared_preload_libraries = 'pg_stat_statements'" | sudo tee -a /etc/postgresql/15/main/postgresql.conf

# Перезапустить PostgreSQL
sudo systemctl restart postgresql

# Создать расширение в каждой БД
sudo -u postgres psql repitbot_users -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
sudo -u postgres psql repitbot_lessons -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
sudo -u postgres psql repitbot_homework -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
sudo -u postgres psql repitbot_payments -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
sudo -u postgres psql repitbot_materials -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
sudo -u postgres psql repitbot_notifications -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
sudo -u postgres psql repitbot_analytics -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
sudo -u postgres psql repitbot_students -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
sudo -u postgres psql repitbot_gateway -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
```

### 6.2 Мониторинг скрипты
```bash
# Создать скрипт для мониторинга
cat > /usr/local/bin/postgres_monitor.sh << 'EOF'
#!/bin/bash
echo "=== PostgreSQL Status ==="
systemctl status postgresql --no-pager -l

echo "=== Active Connections ==="
sudo -u postgres psql -c "SELECT datname, numbackends FROM pg_stat_database WHERE datname LIKE 'repitbot_%';"

echo "=== Database Sizes ==="
sudo -u postgres psql -c "SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database WHERE datname LIKE 'repitbot_%' ORDER BY pg_database_size(datname) DESC;"

echo "=== Slow Queries (last hour) ==="
sudo -u postgres psql repitbot_analytics -c "SELECT query, mean_exec_time, calls FROM pg_stat_statements WHERE mean_exec_time > 1000 AND last_exec > NOW() - INTERVAL '1 hour' ORDER BY mean_exec_time DESC LIMIT 10;"
EOF

chmod +x /usr/local/bin/postgres_monitor.sh
```

---

## 💾 ШАГ 7: Настройка автоматических backup

### 7.1 Создание backup скрипта
```bash
# Создать папку для backup
sudo mkdir -p /var/backups/postgresql

# Создать backup скрипт
sudo cat > /usr/local/bin/backup_repitbot_databases.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/postgresql"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_PREFIX="repitbot_backup_$DATE"

# Создать папку для этого backup
mkdir -p "$BACKUP_DIR/$DATE"

# Backup каждой базы данных
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
    echo "Backing up $db..."
    pg_dump -U postgres -h localhost "$db" | gzip > "$BACKUP_DIR/$DATE/${db}.sql.gz"
    
    if [ $? -eq 0 ]; then
        echo "✅ $db backed up successfully"
    else
        echo "❌ Failed to backup $db"
    fi
done

# Создать global backup (roles, tablespaces, etc.)
pg_dumpall -U postgres -h localhost --globals-only | gzip > "$BACKUP_DIR/$DATE/globals.sql.gz"

# Удалить старые backup (старше 30 дней)
find "$BACKUP_DIR" -type d -mtime +30 -exec rm -rf {} + 2>/dev/null || true

echo "✅ Backup completed: $BACKUP_DIR/$DATE"
df -h "$BACKUP_DIR"
EOF

sudo chmod +x /usr/local/bin/backup_repitbot_databases.sh
```

### 7.2 Настройка cron для автоматических backup
```bash
# Добавить в crontab задачу backup каждый день в 2 утра
echo "0 2 * * * /usr/local/bin/backup_repitbot_databases.sh >> /var/log/postgresql_backup.log 2>&1" | sudo crontab -

# Проверить cron задачи
sudo crontab -l
```

---

## 🧪 ШАГ 8: Тестирование подключений

### 8.1 Тест подключений от микросервисов
```bash
# Тест connection string для User Service
PGPASSWORD='STRONG_PASSWORD_1' psql -h localhost -U repitbot_user_service -d repitbot_users -c "SELECT current_database(), current_user;"

# Тест connection string для Lesson Service  
PGPASSWORD='STRONG_PASSWORD_2' psql -h localhost -U repitbot_lesson_service -d repitbot_lessons -c "SELECT current_database(), current_user;"

# И так далее для всех сервисов...
```

### 8.2 Connection strings для .env.production
```bash
# После успешного тестирования, обновить .env.production:
# DATABASE_URL_USER=postgresql+asyncpg://repitbot_user_service:STRONG_PASSWORD_1@YOUR_SERVER_IP:5432/repitbot_users?sslmode=require
# DATABASE_URL_LESSON=postgresql+asyncpg://repitbot_lesson_service:STRONG_PASSWORD_2@YOUR_SERVER_IP:5432/repitbot_lessons?sslmode=require
# ... и так далее
```

---

## ✅ ФИНАЛЬНАЯ ПРОВЕРКА

### Checklist готовности PostgreSQL к production:
- [ ] PostgreSQL 15+ установлен и запущен
- [ ] Все 9 баз данных созданы
- [ ] Пользователи созданы с уникальными паролями
- [ ] SSL сертификаты настроены
- [ ] Firewall настроен (порт 5432 открыт)
- [ ] Performance настройки применены
- [ ] Автоматические backup настроены
- [ ] Мониторинг скрипты созданы
- [ ] Connection strings протестированы
- [ ] pg_hba.conf настроен для удаленного доступа

### Команды для мониторинга:
```bash
# Проверить статус
sudo systemctl status postgresql

# Мониторинг производительности  
/usr/local/bin/postgres_monitor.sh

# Ручной backup (тест)
/usr/local/bin/backup_repitbot_databases.sh

# Просмотр логов
sudo tail -f /var/log/postgresql/postgresql-*.log
```

---

## 🚨 ВАЖНЫЕ ЗАМЕЧАНИЯ

### ⚠️ ОБЯЗАТЕЛЬНО ИЗМЕНИТЕ:
1. **Все пароли** - используйте сильные уникальные пароли
2. **IP адреса** в pg_hba.conf - замените на реальные IP серверов
3. **SSL сертификаты** - для production используйте реальные сертификаты
4. **Backup расписание** - настройте под ваши требования

### 🔒 Безопасность:
- Никогда не используйте слабые пароли
- Регулярно обновляйте PostgreSQL
- Мониторьте подключения и медленные запросы
- Тестируйте backup и restore процедуры

**PostgreSQL server готов к production deployment RepitBot микросервисов!** 🚀