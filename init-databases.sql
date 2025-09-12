-- Инициализация баз данных для микросервисной архитектуры RepitBot
-- Создание отдельных баз данных для каждого сервиса

-- Создание баз данных для каждого сервиса
CREATE DATABASE user_service;
CREATE DATABASE auth_service;
CREATE DATABASE lesson_service;
CREATE DATABASE homework_service;
CREATE DATABASE payment_service;
CREATE DATABASE material_service;

-- Комментарии для документации
COMMENT ON DATABASE user_service IS 'База данных для User Service - управление пользователями';
COMMENT ON DATABASE auth_service IS 'База данных для Auth Service - аутентификация и авторизация';
COMMENT ON DATABASE lesson_service IS 'База данных для Lesson Service - управление уроками';
COMMENT ON DATABASE homework_service IS 'База данных для Homework Service - управление домашними заданиями';
COMMENT ON DATABASE payment_service IS 'База данных для Payment Service - управление платежами и балансом';
COMMENT ON DATABASE material_service IS 'База данных для Material Service - управление учебными материалами';

-- Подключение к базе данных payment_service для настройки
\c payment_service;

-- Создание расширений для Payment Service
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

-- Подключение к базе данных material_service для настройки
\c material_service;

-- Создание расширений для Material Service
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

-- Полнотекстовый поиск для русского языка
CREATE TEXT SEARCH CONFIGURATION russian_ispell (COPY = russian);

-- Возврат к основной базе
\c repitbot;

-- Логирование
\echo 'Databases created successfully for RepitBot microservices:'
\echo '- user_service: User management'
\echo '- auth_service: Authentication and authorization'
\echo '- lesson_service: Lesson management'
\echo '- homework_service: Homework management'
\echo '- payment_service: Payment and balance management'
\echo '- material_service: Educational materials management'