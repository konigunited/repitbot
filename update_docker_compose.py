#!/usr/bin/env python3
"""
Script to update docker-compose.microservices.yml with new services
"""

def update_docker_compose():
    # Read the original file
    with open('docker-compose.microservices.yml', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Student Service configuration
    student_service = '''
  # Student Service
  student-service:
    build:
      context: ./services/student-service
      dockerfile: Dockerfile
    container_name: repitbot_student_service
    environment:
      - DATABASE_URL=postgresql+asyncpg://repitbot:repitbot_password@postgres:5432/student_service
      - RABBITMQ_URL=amqp://repitbot:repitbot_password@rabbitmq:5672/
      - REDIS_URL=redis://redis:6379/5
      - USER_SERVICE_URL=http://user-service:8001
      - LESSON_SERVICE_URL=http://lesson-service:8002
      - HOMEWORK_SERVICE_URL=http://homework-service:8003
      - NOTIFICATION_SERVICE_URL=http://notification-service:8006
      - DEFAULT_LEVEL_XP_THRESHOLD=1000
      - XP_MULTIPLIER=1.5
      - MAX_LEVEL=100
      - ENABLE_ACHIEVEMENTS=true
      - ENABLE_GAMIFICATION=true
      - ENABLE_RECOMMENDATIONS=true
      - ENABLE_SOCIAL_FEATURES=true
      - EVENT_PROCESSING_ENABLED=true
      - DEBUG=false
      - JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
    volumes:
      - student_service_data:/app/data
    ports:
      - "8008:8008"
    networks:
      - repitbot_network
    depends_on:
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
      redis:
        condition: service_healthy
      user-service:
        condition: service_healthy
      lesson-service:
        condition: service_healthy
      homework-service:
        condition: service_healthy
      notification-service:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8008/health"]
      interval: 30s
      timeout: 10s
      retries: 5

  # API Gateway
  api-gateway:
    build:
      context: ./services/api-gateway
      dockerfile: Dockerfile
    container_name: repitbot_api_gateway
    environment:
      - HOST=0.0.0.0
      - PORT=8000
      - DEBUG=false
      - ENVIRONMENT=production
      - JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
      - RATE_LIMIT_PER_MINUTE=100
      - RATE_LIMIT_BURST=20
      - REQUEST_TIMEOUT=30
      - CONNECT_TIMEOUT=5
      - CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
      - CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60
      - LOAD_BALANCER_STRATEGY=round_robin
      - HEALTH_CHECK_INTERVAL=30
      - ENABLE_CORS=true
      - ENABLE_REQUEST_LOGGING=true
      - ENABLE_RATE_LIMITING=true
      - ENABLE_CIRCUIT_BREAKER=true
    ports:
      - "8000:8000"
    networks:
      - repitbot_network
    depends_on:
      user-service:
        condition: service_healthy
      lesson-service:
        condition: service_healthy
      homework-service:
        condition: service_healthy
      payment-service:
        condition: service_healthy
      material-service:
        condition: service_healthy
      notification-service:
        condition: service_healthy
      analytics-service:
        condition: service_healthy
      student-service:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 5
'''

    # Insert services before telegram-bot
    telegram_bot_line = '  # Telegram Bot (монолит с интеграцией микросервисов)'
    content = content.replace(telegram_bot_line, student_service + '\n' + telegram_bot_line)
    
    # Update telegram bot URLs
    content = content.replace(
        '      - ANALYTICS_SERVICE_URL=http://analytics-service:8007',
        '''      - ANALYTICS_SERVICE_URL=http://analytics-service:8007
      - STUDENT_SERVICE_URL=http://student-service:8008
      - API_GATEWAY_URL=http://api-gateway:8000'''
    )
    
    # Update telegram bot dependencies
    content = content.replace(
        '''      analytics-service:
        condition: service_healthy
    restart: unless-stopped''',
        '''      analytics-service:
        condition: service_healthy
      student-service:
        condition: service_healthy
      api-gateway:
        condition: service_healthy
    restart: unless-stopped'''
    )
    
    # Add volume
    content = content.replace(
        '''  analytics_templates:
    name: repitbot_analytics_templates''',
        '''  analytics_templates:
    name: repitbot_analytics_templates
  student_service_data:
    name: repitbot_student_service_data'''
    )
    
    # Write updated content
    with open('docker-compose.microservices.yml', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Updated docker-compose.microservices.yml successfully!")

if __name__ == '__main__':
    update_docker_compose()