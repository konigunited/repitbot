-- Инициализация базы данных для микросервисной архитектуры RepitBot
-- Создается единая БД с отдельными схемами для каждого сервиса

-- Создание схем для сервисов
CREATE SCHEMA IF NOT EXISTS user_service;
CREATE SCHEMA IF NOT EXISTS auth_service;
CREATE SCHEMA IF NOT EXISTS lesson_service;
CREATE SCHEMA IF NOT EXISTS homework_service;
CREATE SCHEMA IF NOT EXISTS payment_service;
CREATE SCHEMA IF NOT EXISTS material_service;
CREATE SCHEMA IF NOT EXISTS notification_service;
CREATE SCHEMA IF NOT EXISTS analytics_service;

-- Создание пользователей для сервисов (в production должны быть отдельные пользователи)
-- В development режиме используем общего пользователя

-- Права доступа для схем
GRANT ALL PRIVILEGES ON SCHEMA user_service TO repitbot;
GRANT ALL PRIVILEGES ON SCHEMA auth_service TO repitbot;
GRANT ALL PRIVILEGES ON SCHEMA lesson_service TO repitbot;
GRANT ALL PRIVILEGES ON SCHEMA homework_service TO repitbot;
GRANT ALL PRIVILEGES ON SCHEMA payment_service TO repitbot;
GRANT ALL PRIVILEGES ON SCHEMA material_service TO repitbot;
GRANT ALL PRIVILEGES ON SCHEMA notification_service TO repitbot;
GRANT ALL PRIVILEGES ON SCHEMA analytics_service TO repitbot;

-- Настройка search_path по умолчанию
ALTER USER repitbot SET search_path = user_service, auth_service, lesson_service, homework_service, payment_service, material_service, notification_service, analytics_service, public;

-- Создание расширений
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Комментарии для документации
COMMENT ON SCHEMA user_service IS 'Схема для User Service - управление пользователями';
COMMENT ON SCHEMA auth_service IS 'Схема для Auth Service - аутентификация и авторизация';
COMMENT ON SCHEMA lesson_service IS 'Схема для Lesson Service - управление уроками';
COMMENT ON SCHEMA homework_service IS 'Схема для Homework Service - управление домашними заданиями';
COMMENT ON SCHEMA payment_service IS 'Схема для Payment Service - платежи и биллинг';
COMMENT ON SCHEMA material_service IS 'Схема для Material Service - управление материалами';
COMMENT ON SCHEMA notification_service IS 'Схема для Notification Service - уведомления';
COMMENT ON SCHEMA analytics_service IS 'Схема для Analytics Service - аналитика и отчеты';

-- Логирование
\echo 'Database schemas created successfully for RepitBot microservices'
\echo 'Core Services: user_service, auth_service, lesson_service, homework_service'
\echo 'Additional Services: payment_service, material_service, notification_service, analytics_service'