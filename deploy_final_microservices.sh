#!/bin/bash
# -*- coding: utf-8 -*-
# RepitBot - Final Microservices Deployment Script
# Финальный скрипт деплоя микросервисной архитектуры

set -e  # Выход при первой ошибке

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
COMPOSE_FILE="docker-compose.microservices.yml"
MAX_WAIT_TIME=300  # 5 minutes
HEALTH_CHECK_INTERVAL=10

# Print banner
print_banner() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    RepitBot Microservices                    ║"
    echo "║                   Final Deployment Script                    ║"
    echo "║                                                              ║"
    echo "║  🚀 9 Services + API Gateway + Full Infrastructure          ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed!"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed!"
        exit 1
    fi
    
    # Check if compose file exists
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Docker Compose file '$COMPOSE_FILE' not found!"
        exit 1
    fi
    
    # Check .env file
    if [ ! -f ".env" ]; then
        log_warning ".env file not found. Creating from example..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_info "Please edit .env file with your settings before continuing."
            read -p "Press Enter to continue after editing .env file..."
        else
            log_error ".env.example file not found!"
            exit 1
        fi
    fi
    
    log_success "Prerequisites check passed"
}

# Stop existing services
stop_existing() {
    log_info "Stopping existing services..."
    docker-compose -f "$COMPOSE_FILE" down --remove-orphans || true
    log_success "Existing services stopped"
}

# Build all images
build_images() {
    log_info "Building all service images..."
    docker-compose -f "$COMPOSE_FILE" build --parallel --no-cache
    log_success "All images built successfully"
}

# Start infrastructure services
start_infrastructure() {
    log_info "Starting infrastructure services..."
    
    # Start PostgreSQL, RabbitMQ, Redis
    docker-compose -f "$COMPOSE_FILE" up -d postgres rabbitmq redis
    
    # Wait for infrastructure to be ready
    log_info "Waiting for infrastructure services to be ready..."
    
    local wait_time=0
    while [ $wait_time -lt $MAX_WAIT_TIME ]; do
        # Check PostgreSQL
        if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U repitbot &>/dev/null; then
            postgres_ready=true
        else
            postgres_ready=false
        fi
        
        # Check RabbitMQ
        if docker-compose -f "$COMPOSE_FILE" exec -T rabbitmq rabbitmq-diagnostics check_running &>/dev/null; then
            rabbitmq_ready=true
        else
            rabbitmq_ready=false
        fi
        
        # Check Redis
        if docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping | grep -q PONG; then
            redis_ready=true
        else
            redis_ready=false
        fi
        
        if [ "$postgres_ready" = true ] && [ "$rabbitmq_ready" = true ] && [ "$redis_ready" = true ]; then
            log_success "All infrastructure services are ready"
            return 0
        fi
        
        log_info "Infrastructure services not ready yet... waiting"
        sleep $HEALTH_CHECK_INTERVAL
        wait_time=$((wait_time + HEALTH_CHECK_INTERVAL))
    done
    
    log_error "Infrastructure services failed to start within $MAX_WAIT_TIME seconds"
    exit 1
}

# Start core services
start_core_services() {
    log_info "Starting core microservices..."
    
    # Start User and Lesson services first (they are dependencies)
    docker-compose -f "$COMPOSE_FILE" up -d user-service lesson-service
    
    # Wait and check health
    sleep 20
    check_service_health "user-service" "8001"
    check_service_health "lesson-service" "8002"
    
    log_success "Core services started"
}

# Start functional services
start_functional_services() {
    log_info "Starting functional microservices..."
    
    # Start Homework, Payment, Material services
    docker-compose -f "$COMPOSE_FILE" up -d homework-service payment-service material-service
    
    # Wait and check health
    sleep 30
    check_service_health "homework-service" "8003"
    check_service_health "payment-service" "8004"
    check_service_health "material-service" "8005"
    
    log_success "Functional services started"
}

# Start additional services
start_additional_services() {
    log_info "Starting additional microservices..."
    
    # Start Notification, Analytics, Student services
    docker-compose -f "$COMPOSE_FILE" up -d notification-service analytics-service student-service
    
    # Wait and check health
    sleep 30
    check_service_health "notification-service" "8006"
    check_service_health "analytics-service" "8007"
    check_service_health "student-service" "8008"
    
    log_success "Additional services started"
}

# Start API Gateway
start_api_gateway() {
    log_info "Starting API Gateway..."
    
    docker-compose -f "$COMPOSE_FILE" up -d api-gateway
    
    # Wait and check health
    sleep 20
    check_service_health "api-gateway" "8000"
    
    log_success "API Gateway started"
}

# Start Telegram Bot
start_telegram_bot() {
    log_info "Starting Telegram Bot..."
    
    docker-compose -f "$COMPOSE_FILE" up -d telegram-bot
    
    sleep 10
    log_success "Telegram Bot started"
}

# Start monitoring
start_monitoring() {
    log_info "Starting monitoring services..."
    
    docker-compose -f "$COMPOSE_FILE" up -d prometheus grafana
    
    sleep 10
    log_success "Monitoring services started"
}

# Health check function
check_service_health() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    log_info "Checking health of $service_name..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -sf "http://localhost:$port/health" >/dev/null 2>&1; then
            log_success "$service_name is healthy"
            return 0
        fi
        
        log_info "$service_name health check attempt $attempt/$max_attempts..."
        sleep 10
        attempt=$((attempt + 1))
    done
    
    log_error "$service_name failed health check"
    return 1
}

# Run system tests
run_system_tests() {
    log_info "Running system tests..."
    
    if command -v python3 &> /dev/null; then
        if [ -f "test_microservices_system.py" ]; then
            # Install required packages
            pip3 install httpx asyncio > /dev/null 2>&1 || true
            
            log_info "Executing comprehensive system test..."
            python3 test_microservices_system.py
            
            if [ $? -eq 0 ]; then
                log_success "System tests passed!"
            else
                log_warning "Some system tests failed. Check the logs."
            fi
        else
            log_warning "System test script not found. Skipping tests."
        fi
    else
        log_warning "Python3 not found. Skipping system tests."
    fi
}

# Print service status
print_service_status() {
    echo
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                       SERVICE STATUS                        ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
    
    # Services with their ports
    local services=(
        "API Gateway:8000"
        "User Service:8001"
        "Lesson Service:8002" 
        "Homework Service:8003"
        "Payment Service:8004"
        "Material Service:8005"
        "Notification Service:8006"
        "Analytics Service:8007"
        "Student Service:8008"
    )
    
    for service in "${services[@]}"; do
        IFS=':' read -r name port <<< "$service"
        if curl -sf "http://localhost:$port/health" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ $name${NC} - http://localhost:$port"
        else
            echo -e "${RED}❌ $name${NC} - http://localhost:$port"
        fi
    done
    
    echo
    echo -e "${BLUE}Infrastructure Services:${NC}"
    echo -e "${GREEN}🗄️  PostgreSQL${NC}       - localhost:5432"
    echo -e "${GREEN}📨 RabbitMQ${NC}          - http://localhost:15672 (admin/admin)"
    echo -e "${GREEN}🔑 Redis${NC}             - localhost:6379"
    echo -e "${GREEN}📊 Prometheus${NC}        - http://localhost:9090"
    echo -e "${GREEN}📈 Grafana${NC}           - http://localhost:3000 (admin/admin)"
    echo
}

# Print access URLs
print_access_urls() {
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                        ACCESS URLS                          ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${BLUE}🌐 Main API Gateway:${NC}     http://localhost:8000"
    echo -e "${BLUE}📚 API Documentation:${NC}    http://localhost:8000/docs"
    echo -e "${BLUE}🔍 Service Discovery:${NC}    http://localhost:8000/gateway/services"
    echo -e "${BLUE}💊 Health Checks:${NC}        http://localhost:8000/health"
    echo
    echo -e "${BLUE}📊 Monitoring:${NC}"
    echo -e "   Grafana Dashboard:    http://localhost:3000"
    echo -e "   Prometheus Metrics:   http://localhost:9090" 
    echo -e "   RabbitMQ Management:  http://localhost:15672"
    echo
    echo -e "${BLUE}🔧 Development:${NC}"
    echo -e "   PgAdmin:              http://localhost:5050"
    echo
}

# Main deployment function
main() {
    print_banner
    
    # Check if user wants to continue
    echo -e "${YELLOW}This will deploy the complete RepitBot microservices architecture.${NC}"
    echo -e "${YELLOW}This includes 9 services + API Gateway + infrastructure.${NC}"
    echo
    read -p "Do you want to continue? (y/N): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 0
    fi
    
    echo
    log_info "Starting RepitBot microservices deployment..."
    
    # Step 1: Prerequisites
    check_prerequisites
    
    # Step 2: Stop existing
    stop_existing
    
    # Step 3: Build images
    build_images
    
    # Step 4: Start infrastructure
    start_infrastructure
    
    # Step 5: Start services in order
    start_core_services
    start_functional_services  
    start_additional_services
    
    # Step 6: Start API Gateway
    start_api_gateway
    
    # Step 7: Start Telegram Bot
    start_telegram_bot
    
    # Step 8: Start monitoring
    start_monitoring
    
    # Step 9: Run tests
    run_system_tests
    
    # Final status
    print_service_status
    print_access_urls
    
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                   🎉 DEPLOYMENT COMPLETE! 🎉                ║"
    echo "║                                                              ║"
    echo "║  RepitBot microservices architecture is now running!        ║"
    echo "║                                                              ║"
    echo "║  Main API Gateway: http://localhost:8000                    ║"
    echo "║  Documentation:    http://localhost:8000/docs               ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    log_success "Deployment completed successfully!"
}

# Handle script interruption
trap 'log_error "Deployment interrupted!"; exit 130' INT

# Run main function
main "$@"