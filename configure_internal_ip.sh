#!/bin/bash

# ============================================================================
# RepitBot Configuration for Internal IP 192.168.88.228
# ============================================================================
# Этот скрипт настраивает RepitBot для работы с внутренним IP адресом

set -e

# Цвета
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

INTERNAL_IP="192.168.88.228"

print_step() {
    echo -e "\n${BLUE}==== ШАГ: $1 ====${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo -e "${BLUE}🔧 Настройка RepitBot для внутреннего IP: ${INTERNAL_IP}${NC}\n"

# Создание .env.production с внутренним IP
print_step "Создание конфигурации .env.production"

cat > .env.production << EOF
# ============== РЕПИТБОТ КОНФИГУРАЦИЯ ==============
ENVIRONMENT=production
DEBUG=false

# ============== СЕТЕВАЯ КОНФИГУРАЦИЯ ==============
INTERNAL_IP=${INTERNAL_IP}
EXTERNAL_API_URL=http://${INTERNAL_IP}:8000
EXTERNAL_WEBHOOK_URL=http://${INTERNAL_IP}:8000/webhook
CORS_ORIGINS=http://${INTERNAL_IP}:3000,http://${INTERNAL_IP}:8000

# ============== БАЗЫ ДАННЫХ ==============
DATABASE_HOST=${INTERNAL_IP}
DATABASE_USER=repitbot
DATABASE_PASSWORD=repitbot_secure_password_2024

# Connection strings для микросервисов
DATABASE_URL_USER=postgresql+asyncpg://repitbot:repitbot_secure_password_2024@${INTERNAL_IP}:5432/repitbot_users
DATABASE_URL_LESSON=postgresql+asyncpg://repitbot:repitbot_secure_password_2024@${INTERNAL_IP}:5432/repitbot_lessons
DATABASE_URL_HOMEWORK=postgresql+asyncpg://repitbot:repitbot_secure_password_2024@${INTERNAL_IP}:5432/repitbot_homework
DATABASE_URL_PAYMENT=postgresql+asyncpg://repitbot:repitbot_secure_password_2024@${INTERNAL_IP}:5432/repitbot_payments
DATABASE_URL_MATERIAL=postgresql+asyncpg://repitbot:repitbot_secure_password_2024@${INTERNAL_IP}:5432/repitbot_materials
DATABASE_URL_NOTIFICATION=postgresql+asyncpg://repitbot:repitbot_secure_password_2024@${INTERNAL_IP}:5432/repitbot_notifications
DATABASE_URL_ANALYTICS=postgresql+asyncpg://repitbot:repitbot_secure_password_2024@${INTERNAL_IP}:5432/repitbot_analytics
DATABASE_URL_STUDENT=postgresql+asyncpg://repitbot:repitbot_secure_password_2024@${INTERNAL_IP}:5432/repitbot_students
DATABASE_URL_GATEWAY=postgresql+asyncpg://repitbot:repitbot_secure_password_2024@${INTERNAL_IP}:5432/repitbot_gateway

# ============== БЕЗОПАСНОСТЬ ==============
JWT_SECRET_KEY=super_secure_jwt_key_for_internal_network_2024_change_this
JWT_REFRESH_SECRET=super_secure_refresh_key_for_internal_network_2024
API_SECRET_KEY=super_secure_api_key_for_internal_network_2024

# ============== ВНЕШНИЕ СЕРВИСЫ ==============
BOT_TOKEN=ВСТАВЬТЕ_ВАШ_TELEGRAM_BOT_TOKEN_ЗДЕСЬ
RABBITMQ_URL=amqp://repitbot:repitbot123@${INTERNAL_IP}:5672/
REDIS_URL=redis://:repitbot123@${INTERNAL_IP}:6379/0

# ============== МИКРОСЕРВИСЫ ENDPOINTS ==============
USER_SERVICE_URL=http://${INTERNAL_IP}:8001
LESSON_SERVICE_URL=http://${INTERNAL_IP}:8002
HOMEWORK_SERVICE_URL=http://${INTERNAL_IP}:8003
PAYMENT_SERVICE_URL=http://${INTERNAL_IP}:8004
MATERIAL_SERVICE_URL=http://${INTERNAL_IP}:8005
NOTIFICATION_SERVICE_URL=http://${INTERNAL_IP}:8006
ANALYTICS_SERVICE_URL=http://${INTERNAL_IP}:8007
STUDENT_SERVICE_URL=http://${INTERNAL_IP}:8008
GATEWAY_SERVICE_URL=http://${INTERNAL_IP}:8000

# ============== ФАЙЛОВОЕ ХРАНИЛИЩЕ ==============
UPLOAD_PATH=/app/uploads
MAX_FILE_SIZE=10485760
STORAGE_PATH=/app/storage

# ============== ЛОГИРОВАНИЕ ==============
LOG_LEVEL=INFO
LOG_FILE=/app/logs/repitbot.log
ERROR_LOG_FILE=/app/logs/errors.log

# ============== ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ ==============
INTERNAL_NETWORK=true
ALLOW_LOCALHOST=true
EOF

chmod 600 .env.production
print_success "Конфигурация .env.production создана для IP ${INTERNAL_IP}"

# Обновление docker-compose для внутреннего IP
print_step "Обновление docker-compose конфигурации"

# Создание docker-compose override для внутреннего IP
cat > docker-compose.internal.yml << EOF
# RepitBot Docker Compose Override for Internal Network
version: '3.8'

services:
  # PostgreSQL
  postgres:
    ports:
      - "${INTERNAL_IP}:5432:5432"
    environment:
      - POSTGRES_PASSWORD=repitbot_secure_password_2024
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql

  # Redis
  redis:
    ports:
      - "${INTERNAL_IP}:6379:6379"
    command: redis-server --requirepass repitbot123

  # RabbitMQ
  rabbitmq:
    ports:
      - "${INTERNAL_IP}:5672:5672"
      - "${INTERNAL_IP}:15672:15672"

  # API Gateway
  api-gateway:
    ports:
      - "${INTERNAL_IP}:8000:8000"
    environment:
      - EXTERNAL_API_URL=http://${INTERNAL_IP}:8000

  # User Service
  user-service:
    ports:
      - "${INTERNAL_IP}:8001:8001"

  # Lesson Service
  lesson-service:
    ports:
      - "${INTERNAL_IP}:8002:8002"

  # Homework Service
  homework-service:
    ports:
      - "${INTERNAL_IP}:8003:8003"

  # Payment Service
  payment-service:
    ports:
      - "${INTERNAL_IP}:8004:8004"

  # Material Service
  material-service:
    ports:
      - "${INTERNAL_IP}:8005:8005"

  # Notification Service
  notification-service:
    ports:
      - "${INTERNAL_IP}:8006:8006"

  # Analytics Service
  analytics-service:
    ports:
      - "${INTERNAL_IP}:8007:8007"

  # Student Service
  student-service:
    ports:
      - "${INTERNAL_IP}:8008:8008"

volumes:
  postgres_data:
  redis_data:
  rabbitmq_data:
  upload_data:
  storage_data:
EOF

print_success "Docker Compose конфигурация обновлена"

# Создание скрипта запуска
print_step "Создание скрипта запуска"

cat > start_repitbot_internal.sh << 'EOF'
#!/bin/bash

echo "🚀 Запуск RepitBot на внутреннем IP 192.168.88.228..."

# Остановка существующих контейнеров
echo "🛑 Остановка существующих контейнеров..."
docker-compose -f docker-compose.microservices.yml -f docker-compose.internal.yml down

# Сборка образов
echo "🔨 Сборка образов..."
docker-compose -f docker-compose.microservices.yml -f docker-compose.internal.yml build --parallel

# Запуск сервисов
echo "▶️  Запуск сервисов..."
docker-compose -f docker-compose.microservices.yml -f docker-compose.internal.yml up -d

# Ожидание запуска
echo "⏳ Ожидание запуска сервисов (30 секунд)..."
sleep 30

# Проверка статуса
echo "📊 Проверка статуса сервисов:"
docker-compose -f docker-compose.microservices.yml -f docker-compose.internal.yml ps

# Health checks
echo -e "\n🔍 Проверка health endpoints:"
for port in {8000..8008}; do
    if curl -s -f "http://192.168.88.228:$port/health" >/dev/null 2>&1; then
        echo "✅ Port $port: OK"
    else
        echo "❌ Port $port: FAILED"
    fi
done

echo -e "\n🌐 RepitBot запущен на IP: 192.168.88.228"
echo "📊 API Gateway: http://192.168.88.228:8000"
echo "💾 Админ панель PostgreSQL подключение: 192.168.88.228:5432"
echo "🔧 RabbitMQ Management: http://192.168.88.228:15672"
EOF

chmod +x start_repitbot_internal.sh
print_success "Скрипт запуска создан: ./start_repitbot_internal.sh"

# Создание скрипта проверки
cat > check_repitbot.sh << 'EOF'
#!/bin/bash

echo "🔍 Проверка статуса RepitBot на 192.168.88.228"

echo -e "\n📊 Docker контейнеры:"
docker-compose -f docker-compose.microservices.yml -f docker-compose.internal.yml ps

echo -e "\n🌐 Health Checks всех сервисов:"
for port in {8000..8008}; do
    if curl -s -f "http://192.168.88.228:$port/health" >/dev/null 2>&1; then
        echo "✅ Service on port $port: HEALTHY"
    else
        echo "❌ Service on port $port: UNHEALTHY"
    fi
done

echo -e "\n💾 Базы данных:"
if nc -z 192.168.88.228 5432; then
    echo "✅ PostgreSQL: CONNECTED"
else
    echo "❌ PostgreSQL: DISCONNECTED"
fi

if nc -z 192.168.88.228 6379; then
    echo "✅ Redis: CONNECTED"
else
    echo "❌ Redis: DISCONNECTED"  
fi

if nc -z 192.168.88.228 5672; then
    echo "✅ RabbitMQ: CONNECTED"
else
    echo "❌ RabbitMQ: DISCONNECTED"
fi

echo -e "\n🔗 Доступные endpoints:"
echo "  • API Gateway:        http://192.168.88.228:8000"
echo "  • User Service:       http://192.168.88.228:8001"
echo "  • Lesson Service:     http://192.168.88.228:8002"
echo "  • Homework Service:   http://192.168.88.228:8003"
echo "  • Payment Service:    http://192.168.88.228:8004"
echo "  • Material Service:   http://192.168.88.228:8005"
echo "  • Notification Svc:   http://192.168.88.228:8006"
echo "  • Analytics Service:  http://192.168.88.228:8007"
echo "  • Student Service:    http://192.168.88.228:8008"
EOF

chmod +x check_repitbot.sh
print_success "Скрипт проверки создан: ./check_repitbot.sh"

print_step "Финальные инструкции"

echo -e "${GREEN}🎉 Конфигурация для внутреннего IP завершена!${NC}\n"

echo "📋 Следующие шаги:"
echo "1. Укажите ваш Telegram Bot Token в .env.production:"
echo "   nano .env.production"
echo "   Найдите строку: BOT_TOKEN=ВСТАВЬТЕ_ВАШ_TELEGRAM_BOT_TOKEN_ЗДЕСЬ"
echo ""
echo "2. Запустите RepitBot:"
echo "   ./start_repitbot_internal.sh"
echo ""
echo "3. Проверьте статус:"
echo "   ./check_repitbot.sh"
echo ""
echo -e "${YELLOW}⚠️  ВАЖНО: Все сервисы будут доступны только в вашей локальной сети (192.168.88.x)${NC}"
echo -e "${BLUE}🔗 Главный endpoint: http://192.168.88.228:8000${NC}"