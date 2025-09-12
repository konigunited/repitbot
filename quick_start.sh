#!/bin/bash

# ============================================================================
# RepitBot Quick Start Script - Быстрое развертывание за 5 минут
# ============================================================================
# Этот скрипт выполняет минимальное развертывание для быстрого тестирования
# 
# Использование:
#   curl -fsSL https://raw.githubusercontent.com/konigunited/repitbot/main/quick_start.sh | bash
#   или
#   wget -qO- https://raw.githubusercontent.com/konigunited/repitbot/main/quick_start.sh | bash
#
# Что делает:
#   - Устанавливает все зависимости
#   - Клонирует репозиторий
#   - Создает тестовые пароли
#   - Запускает все микросервисы
# ============================================================================

set -e

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# ASCII Art логотип
print_logo() {
    echo -e "${PURPLE}"
    cat << "EOF"
    ____            _ _   ____        _   
   |  _ \ ___ _ __ (_) |_| __ )  ___ | |_ 
   | |_) / _ \ '_ \| | __|  _ \ / _ \| __|
   |  _ <  __/ |_) | | |_| |_) | (_) | |_ 
   |_| \_\___| .__/|_|\__|____/ \___/ \__|
             |_|                         
    
    🚀 Microservices Quick Start 🚀
EOF
    echo -e "${NC}"
}

print_step() {
    echo -e "\n${BLUE}==== ШАГ: $1 ====${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Проверка операционной системы
check_system() {
    print_step "Проверка системы"
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [[ -f /etc/os-release ]]; then
            . /etc/os-release
            if [[ "$ID" == "ubuntu" ]] && [[ "${VERSION_ID}" > "20.04" || "${VERSION_ID}" == "20.04" ]]; then
                print_success "Ubuntu ${VERSION_ID} обнаружен"
            else
                print_warning "Тестировано на Ubuntu 20.04+. Текущая: $PRETTY_NAME"
            fi
        fi
    else
        print_warning "Скрипт оптимизирован для Ubuntu Linux"
    fi
    
    # Проверка sudo
    if ! sudo -n true 2>/dev/null; then
        echo "Требуется sudo доступ для установки пакетов."
        sudo -v
    fi
}

# Быстрая установка всех зависимостей
install_dependencies() {
    print_step "Установка зависимостей"
    
    # Обновление пакетов
    sudo apt update
    
    # Установка основных пакетов
    sudo apt install -y curl wget git python3 python3-pip docker.io docker-compose postgresql-15 redis-server rabbitmq-server
    
    # Добавить пользователя в группу docker
    sudo usermod -aG docker $USER
    
    # Запуск сервисов
    sudo systemctl enable --now docker postgresql redis-server rabbitmq-server
    
    print_success "Все зависимости установлены"
}

# Быстрая настройка PostgreSQL
quick_setup_postgresql() {
    print_step "Настройка PostgreSQL"
    
    # Базовая настройка
    sudo -u postgres psql << 'EOF'
ALTER USER postgres PASSWORD 'postgres';
CREATE USER repitbot WITH PASSWORD 'repitbot123' CREATEDB SUPERUSER;
EOF

    # Разрешить локальные подключения
    sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/15/main/postgresql.conf
    echo "host all all 127.0.0.1/32 md5" | sudo tee -a /etc/postgresql/15/main/pg_hba.conf
    
    sudo systemctl restart postgresql
    
    print_success "PostgreSQL настроен (пользователь: repitbot, пароль: repitbot123)"
}

# Клонирование и настройка репозитория
setup_repository() {
    print_step "Клонирование RepitBot репозитория"
    
    if [[ -d "repitbot" ]]; then
        print_warning "Папка repitbot уже существует. Обновляем..."
        cd repitbot
        git pull origin main
    else
        git clone https://github.com/konigunited/repitbot.git
        cd repitbot
    fi
    
    print_success "Репозиторий готов"
}

# Создание простого .env файла для тестирования
create_test_env() {
    print_step "Создание тестовой конфигурации"
    
    cat > .env.production << EOF
# ============== QUICK START CONFIGURATION ==============
ENVIRONMENT=development
DEBUG=true

# ============== DATABASE ==============
DATABASE_HOST=localhost
DATABASE_USER=repitbot
DATABASE_PASSWORD=repitbot123

# Простые connection strings для тестирования
DATABASE_URL_USER=postgresql+asyncpg://repitbot:repitbot123@localhost:5432/repitbot_users
DATABASE_URL_LESSON=postgresql+asyncpg://repitbot:repitbot123@localhost:5432/repitbot_lessons
DATABASE_URL_HOMEWORK=postgresql+asyncpg://repitbot:repitbot123@localhost:5432/repitbot_homework
DATABASE_URL_PAYMENT=postgresql+asyncpg://repitbot:repitbot123@localhost:5432/repitbot_payments
DATABASE_URL_MATERIAL=postgresql+asyncpg://repitbot:repitbot123@localhost:5432/repitbot_materials
DATABASE_URL_NOTIFICATION=postgresql+asyncpg://repitbot:repitbot123@localhost:5432/repitbot_notifications
DATABASE_URL_ANALYTICS=postgresql+asyncpg://repitbot:repitbot123@localhost:5432/repitbot_analytics
DATABASE_URL_STUDENT=postgresql+asyncpg://repitbot:repitbot123@localhost:5432/repitbot_students
DATABASE_URL_GATEWAY=postgresql+asyncpg://repitbot:repitbot123@localhost:5432/repitbot_gateway

# ============== SECURITY (тестовые ключи) ==============
JWT_SECRET_KEY=test_jwt_secret_key_for_development_only_change_in_production
JWT_REFRESH_SECRET=test_refresh_secret_key_for_development_only
API_SECRET_KEY=test_api_secret_key_for_development_only

# ============== EXTERNAL SERVICES ==============
BOT_TOKEN=your_bot_token_here
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
REDIS_URL=redis://localhost:6379/0

# ============== CORS ==============
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
EXTERNAL_API_URL=http://localhost:8000
EXTERNAL_WEBHOOK_URL=http://localhost:8000/webhook

# ============== QUICK START ==============
QUICK_START=true
EOF
    
    chmod 600 .env.production
    print_success "Тестовая конфигурация создана"
}

# Создание тестовых баз данных
create_test_databases() {
    print_step "Создание тестовых баз данных"
    
    PGPASSWORD=repitbot123 psql -h localhost -U repitbot -d postgres << 'EOF'
CREATE DATABASE IF NOT EXISTS repitbot_users;
CREATE DATABASE IF NOT EXISTS repitbot_lessons;
CREATE DATABASE IF NOT EXISTS repitbot_homework;
CREATE DATABASE IF NOT EXISTS repitbot_payments;
CREATE DATABASE IF NOT EXISTS repitbot_materials;
CREATE DATABASE IF NOT EXISTS repitbot_notifications;
CREATE DATABASE IF NOT EXISTS repitbot_analytics;
CREATE DATABASE IF NOT EXISTS repitbot_students;
CREATE DATABASE IF NOT EXISTS repitbot_gateway;

\l
EOF
    
    print_success "Тестовые базы данных созданы"
}

# Запуск микросервисов
quick_deploy() {
    print_step "Быстрое развертывание микросервисов"
    
    # Создать необходимые папки
    mkdir -p logs uploads storage
    
    # Проверить, что пользователь в группе docker
    if ! groups | grep -q docker; then
        print_warning "Добавляем пользователя в группу docker..."
        sudo usermod -aG docker $USER
        print_warning "Требуется перезапуск оболочки. Выполняется через newgrp..."
        newgrp docker << SUBSHELL
            docker-compose -f docker-compose.microservices.yml build --parallel
            docker-compose -f docker-compose.microservices.yml up -d
SUBSHELL
    else
        # Сборка и запуск
        docker-compose -f docker-compose.microservices.yml build --parallel
        docker-compose -f docker-compose.microservices.yml up -d
    fi
    
    print_success "Микросервисы запущены"
}

# Проверка развертывания
verify_quick_deployment() {
    print_step "Проверка развертывания"
    
    print_warning "Ожидание запуска сервисов (60 секунд)..."
    sleep 60
    
    echo "Статус Docker контейнеров:"
    docker-compose -f docker-compose.microservices.yml ps
    
    echo -e "\nПроверка health checks:"
    local success_count=0
    local total_services=9
    
    for port in {8000..8008}; do
        if timeout 5 curl -s -f "http://localhost:$port/health" >/dev/null 2>&1; then
            print_success "Сервис на порту $port: OK"
            ((success_count++))
        else
            print_warning "Сервис на порту $port: Не отвечает"
        fi
    done
    
    echo -e "\n${BLUE}==== РЕЗУЛЬТАТ ====${NC}"
    echo "✅ Успешно запущено: $success_count из $total_services сервисов"
    
    if [[ $success_count -eq $total_services ]]; then
        print_success "🎉 Все сервисы работают отлично!"
    elif [[ $success_count -ge 5 ]]; then
        print_warning "⚡ Большинство сервисов работает. Некоторые могут еще запускаться."
    else
        print_warning "⚠️  Многие сервисы не отвечают. Проверьте логи: docker-compose logs"
    fi
}

# Показать информацию о доступе
show_access_info() {
    print_step "Информация о доступе"
    
    echo -e "${GREEN}🌐 RepitBot микросервисы запущены!${NC}"
    echo
    echo "📊 Доступные сервисы:"
    echo "  • API Gateway:        http://localhost:8000"
    echo "  • User Service:       http://localhost:8001" 
    echo "  • Lesson Service:     http://localhost:8002"
    echo "  • Homework Service:   http://localhost:8003"
    echo "  • Payment Service:    http://localhost:8004"
    echo "  • Material Service:   http://localhost:8005"
    echo "  • Notification Svc:   http://localhost:8006"
    echo "  • Analytics Service:  http://localhost:8007"
    echo "  • Student Service:    http://localhost:8008"
    echo
    echo "🔧 Инфраструктура:"
    echo "  • PostgreSQL:         localhost:5432 (пользователь: repitbot)"
    echo "  • Redis:              localhost:6379"
    echo "  • RabbitMQ:           localhost:5672"
    echo
    echo "📋 Полезные команды:"
    echo "  • Статус:             docker-compose -f docker-compose.microservices.yml ps"
    echo "  • Логи:               docker-compose -f docker-compose.microservices.yml logs"
    echo "  • Остановить:         docker-compose -f docker-compose.microservices.yml down"
    echo "  • Перезапустить:      docker-compose -f docker-compose.microservices.yml restart"
    echo
    echo -e "${YELLOW}⚠️  ЭТО БЫСТРАЯ ДЕМО УСТАНОВКА!${NC}"
    echo "Для production используйте COMPLETE_DEPLOYMENT_GUIDE.md"
    echo
}

# Создание скрипта для управления
create_management_scripts() {
    print_step "Создание скриптов управления"
    
    # Скрипт для остановки
    cat > stop_repitbot.sh << 'EOF'
#!/bin/bash
echo "🛑 Остановка RepitBot микросервисов..."
cd ~/repitbot
docker-compose -f docker-compose.microservices.yml down
echo "✅ RepitBot остановлен"
EOF
    
    # Скрипт для перезапуска
    cat > restart_repitbot.sh << 'EOF'
#!/bin/bash
echo "🔄 Перезапуск RepitBot микросервисов..."
cd ~/repitbot
docker-compose -f docker-compose.microservices.yml restart
echo "✅ RepitBot перезапущен"
EOF
    
    # Скрипт для проверки статуса
    cat > status_repitbot.sh << 'EOF'
#!/bin/bash
echo "📊 Статус RepitBot микросервисов:"
cd ~/repitbot
docker-compose -f docker-compose.microservices.yml ps

echo -e "\n🔍 Health Checks:"
for port in {8000..8008}; do
    if curl -s http://localhost:$port/health >/dev/null 2>&1; then
        echo "✅ Port $port: OK"
    else
        echo "❌ Port $port: FAILED"
    fi
done
EOF
    
    chmod +x stop_repitbot.sh restart_repitbot.sh status_repitbot.sh
    
    print_success "Скрипты управления созданы:"
    echo "  • ./stop_repitbot.sh    - Остановить все сервисы"
    echo "  • ./restart_repitbot.sh - Перезапустить все сервисы"  
    echo "  • ./status_repitbot.sh  - Проверить статус"
}

# Главная функция
main() {
    clear
    print_logo
    
    echo -e "${BLUE}Добро пожаловать в RepitBot Quick Start!${NC}"
    echo "Этот скрипт развернет все 9 микросервисов за несколько минут."
    echo -e "${YELLOW}⚠️  Это демо-версия для быстрого тестирования.${NC}"
    echo "Для production используйте полную инструкцию: COMPLETE_DEPLOYMENT_GUIDE.md"
    echo
    
    read -p "Продолжить? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Отменено."
        exit 0
    fi
    
    echo -e "\n${GREEN}🚀 Начинаем быстрое развертывание...${NC}\n"
    
    # Выполнение всех шагов
    check_system
    install_dependencies
    quick_setup_postgresql
    setup_repository
    create_test_env
    create_test_databases
    quick_deploy
    verify_quick_deployment
    create_management_scripts
    show_access_info
    
    echo -e "${GREEN}🎉 RepitBot Quick Start завершен!${NC}"
    echo -e "${BLUE}Микросервисная архитектура готова к тестированию!${NC}"
}

# Обработка ошибок
trap 'echo -e "\n${RED}❌ Произошла ошибка. Проверьте логи выше.${NC}"; exit 1' ERR

# Запуск
main "$@"