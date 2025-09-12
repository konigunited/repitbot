-- Создание баз данных для минимальной версии RepitBot
-- Выполняется автоматически при запуске PostgreSQL контейнера

-- Основные базы данных для микросервисов
CREATE DATABASE repitbot_users;
CREATE DATABASE repitbot_lessons;  
CREATE DATABASE repitbot_homework;
CREATE DATABASE repitbot_materials;
CREATE DATABASE repitbot_notifications;
CREATE DATABASE repitbot_gateway;

-- Опциональные базы для будущего расширения
CREATE DATABASE repitbot_analytics;
CREATE DATABASE repitbot_students;

-- Создание пользователя с правами доступа ко всем базам
CREATE USER repitbot WITH ENCRYPTED PASSWORD 'repitbot_secure_password_2024';

-- Предоставление всех привилегий пользователю repitbot
GRANT ALL PRIVILEGES ON DATABASE repitbot_users TO repitbot;
GRANT ALL PRIVILEGES ON DATABASE repitbot_lessons TO repitbot;
GRANT ALL PRIVILEGES ON DATABASE repitbot_homework TO repitbot;
GRANT ALL PRIVILEGES ON DATABASE repitbot_materials TO repitbot;
GRANT ALL PRIVILEGES ON DATABASE repitbot_notifications TO repitbot;
GRANT ALL PRIVILEGES ON DATABASE repitbot_gateway TO repitbot;
GRANT ALL PRIVILEGES ON DATABASE repitbot_analytics TO repitbot;
GRANT ALL PRIVILEGES ON DATABASE repitbot_students TO repitbot;

-- Сделать пользователя суперпользователем для миграций
ALTER USER repitbot CREATEDB;
ALTER USER repitbot SUPERUSER;
