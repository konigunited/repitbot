#!/bin/bash
# Скрипт развертывания микросервисной архитектуры RepitBot

set -e  # Выход при любой ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода с цветом
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Проверка наличия Docker и Docker Compose
check_requirements() {
    log "Проверка требований..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker не установлен. Установите Docker и попробуйте снова."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose не установлен. Установите Docker Compose и попробуйте снова."
        exit 1
    fi
    
    log "Все требования выполнены ✓"
}

# Проверка переменных окружения
check_env() {
    log "Проверка переменных окружения..."
    
    if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
        warn "TELEGRAM_BOT_TOKEN не установлен. Проверьте файл .env"
        read -p "Введите токен Telegram бота: " TELEGRAM_BOT_TOKEN
        export TELEGRAM_BOT_TOKEN
    fi
    
    log "Переменные окружения проверены ✓"
}

# Остановка существующих контейнеров
stop_services() {
    log "Остановка существующих сервисов..."
    docker-compose -f docker-compose.microservices.yml down --remove-orphans || true
    log "Сервисы остановлены ✓"
}

# Очистка Docker
cleanup_docker() {
    log "Очистка Docker ресурсов..."
    docker system prune -f
    docker volume prune -f
    log "Очистка завершена ✓"
}

# Сборка образов
build_images() {
    log "Сборка Docker образов..."
    
    info "Сборка User Service..."
    docker-compose -f docker-compose.microservices.yml build user-service
    
    info "Сборка Auth Service..."
    docker-compose -f docker-compose.microservices.yml build auth-service
    
    info "Сборка Telegram Bot..."
    docker-compose -f docker-compose.microservices.yml build telegram-bot
    
    log "Сборка образов завершена ✓"
}

# Запуск инфраструктуры
start_infrastructure() {
    log "Запуск инфраструктуры..."
    
    info "Запуск PostgreSQL..."
    docker-compose -f docker-compose.microservices.yml up -d postgres
    
    info "Ожидание готовности PostgreSQL..."
    sleep 30
    
    info "Запуск Redis..."
    docker-compose -f docker-compose.microservices.yml up -d redis
    
    log "Инфраструктура запущена ✓"
}

# Запуск микросервисов
start_microservices() {
    log "Запуск микросервисов..."
    
    info "Запуск User Service..."
    docker-compose -f docker-compose.microservices.yml up -d user-service
    
    info "Ожидание готовности User Service..."
    sleep 20
    
    info "Запуск Auth Service..."
    docker-compose -f docker-compose.microservices.yml up -d auth-service
    
    info "Ожидание готовности Auth Service..."
    sleep 20
    
    log "Микросервисы запущены ✓"
}

# Запуск приложений
start_applications() {
    log "Запуск приложений..."
    
    info "Запуск Telegram Bot..."
    docker-compose -f docker-compose.microservices.yml up -d telegram-bot
    
    info "Запуск API Gateway..."
    docker-compose -f docker-compose.microservices.yml up -d api-gateway
    
    log "Приложения запущены ✓"
}

# Запуск мониторинга (опционально)
start_monitoring() {
    log "Запуск системы мониторинга..."
    
    read -p "Запустить мониторинг (Prometheus/Grafana)? (y/N): " start_mon
    
    if [[ $start_mon =~ ^[Yy]$ ]]; then
        info "Запуск Prometheus..."
        docker-compose -f docker-compose.microservices.yml up -d prometheus
        
        info "Запуск Grafana..."
        docker-compose -f docker-compose.microservices.yml up -d grafana
        
        log "Мониторинг запущен ✓"
        info "Grafana доступна по адресу: http://localhost:3000 (admin/admin)"
        info "Prometheus доступен по адресу: http://localhost:9090"
    else
        log "Мониторинг пропущен"
    fi
}

# Проверка здоровья сервисов
check_health() {
    log "Проверка здоровья сервисов..."
    
    services=("postgres:5432" "redis:6379" "user-service:8001" "auth-service:8002")
    
    for service in "${services[@]}"; do
        service_name=$(echo $service | cut -d':' -f1)
        service_port=$(echo $service | cut -d':' -f2)
        
        info "Проверка $service_name..."
        
        # Ждем максимум 60 секунд
        timeout=60
        while [ $timeout -gt 0 ]; do
            if docker exec repitbot-$service_name /bin/sh -c "nc -z localhost $service_port" 2>/dev/null; then
                log "$service_name работает ✓"
                break
            fi
            sleep 2
            timeout=$((timeout-2))
        done
        
        if [ $timeout -eq 0 ]; then
            error "$service_name не отвечает"
        fi
    done
}

# Вывод информации о развернутой системе
show_info() {
    log "=== СИСТЕМА РАЗВЕРНУТА ==="
    echo
    info "Доступные сервисы:"
    echo "  • API Gateway:     http://localhost:8080"
    echo "  • User Service:    http://localhost:8001"
    echo "  • Auth Service:    http://localhost:8002"
    echo "  • PostgreSQL:      localhost:5432"
    echo "  • Redis:           localhost:6379"
    echo
    info "Документация API:"
    echo "  • User Service:    http://localhost:8001/docs"
    echo "  • Auth Service:    http://localhost:8002/docs"
    echo "  • API Gateway:     http://localhost:8080/docs"
    echo
    info "Мониторинг (если запущен):"
    echo "  • Prometheus:      http://localhost:9090"
    echo "  • Grafana:         http://localhost:3000 (admin/admin)"
    echo
    info "Логи сервисов:"
    echo "  docker-compose -f docker-compose.microservices.yml logs -f [service_name]"
    echo
    info "Остановка системы:"
    echo "  docker-compose -f docker-compose.microservices.yml down"
    echo
}

# Основная функция
main() {
    log "🚀 Начало развертывания микросервисной архитектуры RepitBot"
    
    check_requirements
    check_env
    
    # Опция для полной пересборки
    read -p "Выполнить полную пересборку? (y/N): " rebuild
    
    if [[ $rebuild =~ ^[Yy]$ ]]; then
        stop_services
        cleanup_docker
        build_images
    fi
    
    start_infrastructure
    start_microservices
    start_applications
    start_monitoring
    check_health
    show_info
    
    log "✅ Развертывание завершено успешно!"
}

# Обработка аргументов командной строки
case "${1:-}" in
    "build")
        log "Только сборка образов..."
        build_images
        ;;
    "start")
        log "Только запуск сервисов..."
        start_infrastructure
        start_microservices
        start_applications
        ;;
    "stop")
        log "Остановка всех сервисов..."
        stop_services
        ;;
    "restart")
        log "Перезапуск сервисов..."
        stop_services
        start_infrastructure
        start_microservices
        start_applications
        ;;
    "health")
        log "Проверка здоровья сервисов..."
        check_health
        ;;
    "logs")
        log "Показ логов всех сервисов..."
        docker-compose -f docker-compose.microservices.yml logs -f
        ;;
    "clean")
        log "Полная очистка..."
        stop_services
        cleanup_docker
        ;;
    *)
        main
        ;;
esac