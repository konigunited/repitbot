#!/bin/bash

# ============================================================================
# RepitBot Microservices - Automated Deployment Script
# ============================================================================
# Этот скрипт автоматизирует весь процесс развертывания RepitBot
# 
# Использование:
#   chmod +x deploy.sh
#   ./deploy.sh
#
# Требования:
#   - Ubuntu 20.04+ server
#   - Sudo доступ
#   - Интернет соединение
# ============================================================================

set -e  # Остановить при любой ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для вывода
print_header() {
    echo -e "\n${BLUE}============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Проверка прав sudo
check_sudo() {
    if ! sudo -n true 2>/dev/null; then
        print_error "Этот скрипт требует sudo доступа. Запустите с правами администратора."
        exit 1
    fi
}

# Проверка операционной системы
check_os() {
    if [[ ! -f /etc/os-release ]]; then
        print_error "Не удалось определить операционную систему"
        exit 1
    fi
    
    . /etc/os-release
    if [[ "$ID" != "ubuntu" ]] || [[ "${VERSION_ID}" < "20.04" ]]; then
        print_error "Требуется Ubuntu 20.04 или новее. Текущая: $PRETTY_NAME"
        exit 1
    fi
    
    print_success "Операционная система: $PRETTY_NAME"
}

# Обновление системы
update_system() {
    print_header "Обновление системы"
    
    sudo apt update
    sudo apt upgrade -y
    sudo apt install -y curl wget gnupg2 software-properties-common apt-transport-https \
        git vim htop tree unzip zip build-essential python3-pip jq
    
    print_success "Система обновлена"
}

# Настройка firewall
setup_firewall() {
    print_header "Настройка Firewall"
    
    sudo ufw --force reset
    sudo ufw allow ssh
    sudo ufw allow http
    sudo ufw allow https
    sudo ufw allow 5432  # PostgreSQL
    sudo ufw --force enable
    
    print_success "Firewall настроен"
}

# Установка Docker
install_docker() {
    print_header "Установка Docker"
    
    if command -v docker &> /dev/null; then
        print_warning "Docker уже установлен"
        return
    fi
    
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    
    # Установка Docker Compose
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    print_success "Docker установлен"
    print_warning "Перезайдите в систему для применения группы docker"
}

# Установка PostgreSQL
install_postgresql() {
    print_header "Установка PostgreSQL 15"
    
    if systemctl is-active --quiet postgresql; then
        print_warning "PostgreSQL уже запущен"
        return
    fi
    
    # Добавить репозиторий PostgreSQL
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
    echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list
    
    sudo apt update
    sudo apt install -y postgresql-15 postgresql-client-15 postgresql-contrib-15
    
    sudo systemctl enable postgresql
    sudo systemctl start postgresql
    
    print_success "PostgreSQL 15 установлен и запущен"
}

# Настройка PostgreSQL
configure_postgresql() {
    print_header "Настройка PostgreSQL"
    
    local pg_config="/etc/postgresql/15/main/postgresql.conf"
    local pg_hba="/etc/postgresql/15/main/pg_hba.conf"
    
    # Backup конфигураций
    sudo cp "$pg_config" "$pg_config.backup"
    sudo cp "$pg_hba" "$pg_hba.backup"
    
    # Настройка postgresql.conf
    sudo tee -a "$pg_config" << EOF

# ============== RepitBot Production Settings ==============
listen_addresses = '*'
max_connections = 300
shared_buffers = 512MB
effective_cache_size = 2GB
work_mem = 8MB
maintenance_work_mem = 128MB
checkpoint_completion_target = 0.9
wal_buffers = 32MB
random_page_cost = 1.1
effective_io_concurrency = 200
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_statement = 'mod'
log_min_duration_statement = 1000
ssl = on
password_encryption = 'scram-sha-256'
EOF

    # Настройка pg_hba.conf
    sudo tee -a "$pg_hba" << EOF

# ============== RepitBot Microservices ==============
local   all             repitbot_admin                  scram-sha-256
host    repitbot_users          repitbot_user_service       127.0.0.1/32    scram-sha-256
host    repitbot_lessons        repitbot_lesson_service     127.0.0.1/32    scram-sha-256
host    repitbot_homework       repitbot_homework_service   127.0.0.1/32    scram-sha-256
host    repitbot_payments       repitbot_payment_service    127.0.0.1/32    scram-sha-256
host    repitbot_materials      repitbot_material_service   127.0.0.1/32    scram-sha-256
host    repitbot_notifications  repitbot_notification_service 127.0.0.1/32  scram-sha-256
host    repitbot_analytics      repitbot_analytics_service  127.0.0.1/32    scram-sha-256
host    repitbot_students       repitbot_student_service    127.0.0.1/32    scram-sha-256
host    repitbot_gateway        repitbot_gateway            127.0.0.1/32    scram-sha-256
host    all                     repitbot_admin              127.0.0.1/32    scram-sha-256
EOF
    
    sudo systemctl restart postgresql
    print_success "PostgreSQL настроен"
}

# Установка Redis и RabbitMQ
install_services() {
    print_header "Установка Redis и RabbitMQ"
    
    # Redis
    sudo apt install -y redis-server
    sudo systemctl enable redis-server
    sudo systemctl start redis-server
    
    # RabbitMQ
    sudo apt install -y rabbitmq-server
    sudo systemctl enable rabbitmq-server
    sudo systemctl start rabbitmq-server
    
    print_success "Redis и RabbitMQ установлены"
}

# Клонирование репозитория
clone_repository() {
    print_header "Клонирование RepitBot репозитория"
    
    local repo_dir="/home/$USER/repitbot"
    
    if [[ -d "$repo_dir" ]]; then
        print_warning "Репозиторий уже существует. Обновляем..."
        cd "$repo_dir"
        git pull origin main
    else
        cd "/home/$USER"
        git clone https://github.com/konigunited/repitbot.git
        cd repitbot
    fi
    
    print_success "Репозиторий готов: $repo_dir"
}

# Генерация паролей
generate_passwords() {
    print_header "Генерация безопасных паролей"
    
    python3 << 'EOF' > passwords_generated.txt
import secrets
import string

def generate_password(length=20):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_jwt_secret():
    return secrets.token_hex(32)

print("=== RepitBot Production Passwords ===")
print("⚠️  СОХРАНИТЕ ЭТИ ПАРОЛИ В БЕЗОПАСНОМ МЕСТЕ!")
print()

services = ['user', 'lesson', 'homework', 'payment', 'material', 'notification', 'analytics', 'student', 'gateway', 'admin']

for service in services:
    password = generate_password()
    print(f"DB_PASSWORD_{service.upper()}={password}")

print()
print("=== Security Keys ===")
print(f"JWT_SECRET_KEY={generate_jwt_secret()}")
print(f"JWT_REFRESH_SECRET={generate_jwt_secret()}")
print(f"API_SECRET_KEY={generate_jwt_secret()}")
print(f"SESSION_SECRET={secrets.token_urlsafe(32)}")
print(f"WEBHOOK_SECRET={secrets.token_urlsafe(16)}")
EOF

    chmod 600 passwords_generated.txt
    print_success "Пароли сгенерированы: passwords_generated.txt"
    print_warning "СОХРАНИТЕ ФАЙЛ passwords_generated.txt В БЕЗОПАСНОМ МЕСТЕ!"
}

# Создание .env.production файла
create_env_file() {
    print_header "Создание .env.production файла"
    
    if [[ -f ".env.production" ]]; then
        print_warning ".env.production уже существует. Создаю backup..."
        cp .env.production .env.production.backup.$(date +%s)
    fi
    
    cp .env.production.example .env.production
    chmod 600 .env.production
    
    print_success ".env.production создан"
    print_warning "НЕОБХОДИМО ЗАПОЛНИТЬ .env.production файл реальными значениями!"
    print_info "Используйте пароли из passwords_generated.txt"
}

# Создание баз данных
create_databases() {
    print_header "Создание баз данных и пользователей"
    
    print_warning "Для создания БД нужны пароли из passwords_generated.txt"
    read -p "Продолжить создание БД? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Пропускаем создание БД. Создайте вручную позже."
        return
    fi
    
    print_info "Пожалуйста, отредактируйте скрипт setup_databases.sql с реальными паролями"
    
    cat > setup_databases.sql << 'EOF'
-- ЗАМЕНИТЕ ВСЕ GENERATED_PASSWORD_X НА РЕАЛЬНЫЕ ПАРОЛИ!

CREATE USER repitbot_user_service WITH PASSWORD 'GENERATED_PASSWORD_1';
CREATE USER repitbot_lesson_service WITH PASSWORD 'GENERATED_PASSWORD_2';
CREATE USER repitbot_homework_service WITH PASSWORD 'GENERATED_PASSWORD_3';
CREATE USER repitbot_payment_service WITH PASSWORD 'GENERATED_PASSWORD_4';
CREATE USER repitbot_material_service WITH PASSWORD 'GENERATED_PASSWORD_5';
CREATE USER repitbot_notification_service WITH PASSWORD 'GENERATED_PASSWORD_6';
CREATE USER repitbot_analytics_service WITH PASSWORD 'GENERATED_PASSWORD_7';
CREATE USER repitbot_student_service WITH PASSWORD 'GENERATED_PASSWORD_8';
CREATE USER repitbot_gateway WITH PASSWORD 'GENERATED_PASSWORD_9';
CREATE USER repitbot_admin WITH PASSWORD 'GENERATED_ADMIN_PASSWORD' CREATEDB CREATEROLE;

CREATE DATABASE repitbot_users OWNER repitbot_user_service;
CREATE DATABASE repitbot_lessons OWNER repitbot_lesson_service;
CREATE DATABASE repitbot_homework OWNER repitbot_homework_service;
CREATE DATABASE repitbot_payments OWNER repitbot_payment_service;
CREATE DATABASE repitbot_materials OWNER repitbot_material_service;
CREATE DATABASE repitbot_notifications OWNER repitbot_notification_service;
CREATE DATABASE repitbot_analytics OWNER repitbot_analytics_service;
CREATE DATABASE repitbot_students OWNER repitbot_student_service;
CREATE DATABASE repitbot_gateway OWNER repitbot_gateway;

GRANT ALL PRIVILEGES ON DATABASE repitbot_users TO repitbot_user_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_lessons TO repitbot_lesson_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_homework TO repitbot_homework_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_payments TO repitbot_payment_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_materials TO repitbot_material_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_notifications TO repitbot_notification_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_analytics TO repitbot_analytics_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_students TO repitbot_student_service;
GRANT ALL PRIVILEGES ON DATABASE repitbot_gateway TO repitbot_gateway;

GRANT CONNECT ON DATABASE repitbot_users TO repitbot_analytics_service;
GRANT CONNECT ON DATABASE repitbot_lessons TO repitbot_analytics_service;
GRANT CONNECT ON DATABASE repitbot_homework TO repitbot_analytics_service;
GRANT CONNECT ON DATABASE repitbot_payments TO repitbot_analytics_service;
GRANT CONNECT ON DATABASE repitbot_materials TO repitbot_analytics_service;
GRANT CONNECT ON DATABASE repitbot_students TO repitbot_analytics_service;

SELECT datname FROM pg_database WHERE datname LIKE 'repitbot_%';
EOF

    print_warning "Отредактируйте setup_databases.sql и выполните:"
    print_info "sudo -u postgres psql -f setup_databases.sql"
}

# Запуск микросервисов
deploy_microservices() {
    print_header "Развертывание микросервисов"
    
    if [[ ! -f ".env.production" ]]; then
        print_error ".env.production файл не найден!"
        return 1
    fi
    
    # Создать необходимые папки
    mkdir -p logs uploads storage
    
    # Проверить Docker группу
    if ! groups | grep -q docker; then
        print_error "Пользователь не в группе docker. Перезайдите в систему."
        return 1
    fi
    
    print_info "Сборка Docker образов..."
    docker-compose -f docker-compose.microservices.yml build
    
    print_info "Запуск всех сервисов..."
    docker-compose -f docker-compose.microservices.yml up -d
    
    print_success "Микросервисы запущены"
}

# Проверка развертывания
verify_deployment() {
    print_header "Проверка развертывания"
    
    sleep 30  # Дать время сервисам запуститься
    
    print_info "Проверка статуса контейнеров..."
    docker-compose -f docker-compose.microservices.yml ps
    
    print_info "Проверка health checks..."
    local failed=0
    
    for port in {8000..8008}; do
        if curl -s -f "http://localhost:$port/health" >/dev/null 2>&1; then
            print_success "Порт $port: OK"
        else
            print_error "Порт $port: FAILED"
            ((failed++))
        fi
    done
    
    if [[ $failed -eq 0 ]]; then
        print_success "Все сервисы работают!"
    else
        print_warning "$failed сервисов не отвечают. Проверьте логи."
    fi
}

# Создание мониторинг скриптов
create_monitoring() {
    print_header "Создание мониторинг скриптов"
    
    sudo tee /usr/local/bin/repitbot_monitor.sh << 'EOF' >/dev/null
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
echo "=== System Resources ==="
echo "CPU: $(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1"%"}')"
echo "Memory: $(free -m | awk 'NR==2{printf "%.1f%%\n", $3*100/$2}')"
echo "Disk: $(df -h / | awk 'NR==2 {print $5}')"
EOF

    sudo chmod +x /usr/local/bin/repitbot_monitor.sh
    
    print_success "Мониторинг скрипт создан: /usr/local/bin/repitbot_monitor.sh"
}

# Главное меню
main_menu() {
    while true; do
        clear
        echo -e "${BLUE}"
        echo "============================================"
        echo "    RepitBot Microservices Deployment"
        echo "============================================"
        echo -e "${NC}"
        echo "1. Полная установка (рекомендуется)"
        echo "2. Обновление системы"
        echo "3. Установка Docker"
        echo "4. Установка PostgreSQL"
        echo "5. Клонирование репозитория"
        echo "6. Генерация паролей"
        echo "7. Создание .env файла"
        echo "8. Развертывание микросервисов"
        echo "9. Проверка статуса"
        echo "10. Создать мониторинг"
        echo "0. Выход"
        echo
        read -p "Выберите опцию (0-10): " choice
        
        case $choice in
            1)
                full_installation
                ;;
            2)
                update_system
                ;;
            3)
                install_docker
                ;;
            4)
                install_postgresql
                configure_postgresql
                ;;
            5)
                clone_repository
                ;;
            6)
                generate_passwords
                ;;
            7)
                create_env_file
                ;;
            8)
                deploy_microservices
                ;;
            9)
                verify_deployment
                ;;
            10)
                create_monitoring
                ;;
            0)
                print_success "До свидания!"
                exit 0
                ;;
            *)
                print_error "Неверный выбор. Попробуйте снова."
                ;;
        esac
        
        echo
        read -p "Нажмите Enter для продолжения..."
    done
}

# Полная автоматическая установка
full_installation() {
    print_header "RepitBot - Полная автоматическая установка"
    
    check_sudo
    check_os
    update_system
    setup_firewall
    install_docker
    install_postgresql
    configure_postgresql
    install_services
    clone_repository
    generate_passwords
    create_env_file
    create_databases
    create_monitoring
    
    print_header "Установка завершена!"
    print_success "RepitBot успешно установлен!"
    print_warning "Следующие шаги:"
    print_info "1. Заполните .env.production файл паролями из passwords_generated.txt"
    print_info "2. Создайте базы данных: sudo -u postgres psql -f setup_databases.sql"
    print_info "3. Перезайдите в систему для применения группы docker"
    print_info "4. Запустите: ./deploy.sh и выберите 'Развертывание микросервисов'"
    print_info "5. Настройте Nginx и SSL сертификаты"
}

# Проверка аргументов командной строки
if [[ $# -eq 0 ]]; then
    main_menu
else
    case $1 in
        --full|-f)
            full_installation
            ;;
        --help|-h)
            echo "RepitBot Deployment Script"
            echo "Использование:"
            echo "  ./deploy.sh          - Интерактивное меню"
            echo "  ./deploy.sh --full   - Полная автоматическая установка"
            echo "  ./deploy.sh --help   - Показать эту справку"
            ;;
        *)
            print_error "Неизвестный аргумент: $1"
            print_info "Используйте --help для справки"
            exit 1
            ;;
    esac
fi

#!/usr/bin/env bash
# Скрипт деплоя: локальный коммит/пуш + удалённый git pull и перезапуск docker-compose
# Использование: перед запуском экспортируйте переменные SSH_USER_HOST и SERVER_PROJECT_PATH
# Пример:
# export SSH_USER_HOST="user@your_server"
# export SERVER_PROJECT_PATH="/home/user/repitbot"
# ./deploy.sh "Commit message"

set -euo pipefail
MSG=${1:-"Deploy from local"}
GIT_REMOTE=${GIT_REMOTE:-origin}
GIT_BRANCH=${GIT_BRANCH:-main}
SSH_USER_HOST=${SSH_USER_HOST:-}
SERVER_PROJECT_PATH=${SERVER_PROJECT_PATH:-}
COMPOSE_SERVICE=${COMPOSE_SERVICE:-repitbot}

# Локальный коммит и пуш
git add .
git commit -m "$MSG" || echo "No changes to commit"
git push $GIT_REMOTE $GIT_BRANCH

if [ -z "$SSH_USER_HOST" ] || [ -z "$SERVER_PROJECT_PATH" ]; then
  echo "SSH_USER_HOST или SERVER_PROJECT_PATH не заданы. Выполните деплой вручную на сервере или экспортируйте переменные и запустите снова."
  exit 0
fi

# На сервере: pull и перезапуск
ssh -o StrictHostKeyChecking=no "$SSH_USER_HOST" bash -c "'
  set -euo pipefail
  cd $SERVER_PROJECT_PATH
  git fetch $GIT_REMOTE
  git reset --hard $GIT_REMOTE/$GIT_BRANCH
  # Обновляем образ/контейнеры и поднимаем сервис
  if [ -f docker-compose.yml ]; then
    docker-compose pull || true
    docker-compose build --no-cache $COMPOSE_SERVICE || true
    docker-compose up -d --remove-orphans $COMPOSE_SERVICE
  else
    echo 'docker-compose.yml не найден в $SERVER_PROJECT_PATH'
    exit 1
  fi
'"

echo "Deploy completed"