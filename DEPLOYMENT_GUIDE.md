# 🚀 Руководство по развертыванию RepitBot на сервере

## 📋 Что понадобится

1. **Сервер** с Ubuntu/CentOS/Debian
2. **Токен Telegram бота** (получить у @BotFather)
3. **SSH доступ** к серверу
4. **Docker и docker-compose** (или Python 3.11+)

---

## 🔧 Вариант 1: Развертывание с Docker (Рекомендуется)

### Шаг 1: Подготовка сервера
```bash
# Подключение к серверу
ssh your_username@your_server_ip

# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Установка docker-compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Перезагрузка для применения изменений
sudo reboot
```

### Шаг 2: Загрузка кода на сервер
```bash
# Создание директории для проекта
mkdir ~/repitbot && cd ~/repitbot

# Способ A: Клонирование из Git (если есть репозиторий)
git clone your_repository_url .

# Способ B: Загрузка файлов через SCP
# На локальной машине:
# scp -r /path/to/repitbot/* username@server_ip:~/repitbot/
```

### Шаг 3: Настройка переменных окружения
```bash
# Копирование примера файла окружения
cp .env.example .env

# Редактирование файла с переменными
nano .env

# Укажите:
# BOT_TOKEN=ваш_токен_от_BotFather
# ADMIN_ACCESS_CODE=ваш_код_администратора
# DB_PASSWORD=пароль_для_postgresql (если используете)
```

### Шаг 4: Создание директорий для данных
```bash
mkdir -p data logs charts
```

### Шаг 5: Запуск бота
```bash
# Сборка и запуск контейнеров
docker-compose up -d

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f repitbot
```

---

## 🐍 Вариант 2: Развертывание без Docker

### Шаг 1: Установка Python и зависимостей
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python 3.11
sudo apt install python3.11 python3.11-venv python3.11-dev python3-pip -y

# Создание виртуального окружения
python3.11 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

### Шаг 2: Настройка переменных окружения
```bash
cp .env.example .env
nano .env
```

### Шаг 3: Создание systemd сервиса
```bash
sudo nano /etc/systemd/system/repitbot.service
```

Содержимое файла:
```ini
[Unit]
Description=RepitBot Telegram Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/repitbot
Environment=PATH=/home/your_username/repitbot/venv/bin
ExecStart=/home/your_username/repitbot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Шаг 4: Запуск сервиса
```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable repitbot

# Запуск сервиса
sudo systemctl start repitbot

# Проверка статуса
sudo systemctl status repitbot

# Просмотр логов
sudo journalctl -u repitbot -f
```

---

## 🗄️ Настройка базы данных PostgreSQL (опционально)

Если хотите использовать PostgreSQL вместо SQLite:

```bash
# Установка PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Создание пользователя и базы данных
sudo -u postgres psql
CREATE DATABASE repitbot;
CREATE USER repitbot WITH PASSWORD 'ваш_пароль';
GRANT ALL PRIVILEGES ON DATABASE repitbot TO repitbot;
\q

# В файле .env измените DATABASE_URL:
# DATABASE_URL=postgresql://repitbot:ваш_пароль@localhost:5432/repitbot
```

---

## 🔄 Обновление бота

### С Docker:
```bash
cd ~/repitbot
docker-compose down
git pull  # или загрузите новые файлы
docker-compose build
docker-compose up -d
```

### Без Docker:
```bash
cd ~/repitbot
sudo systemctl stop repitbot
source venv/bin/activate
git pull  # или загрузите новые файлы
pip install -r requirements.txt
sudo systemctl start repitbot
```

---

## 🔍 Полезные команды для мониторинга

```bash
# Просмотр логов (Docker)
docker-compose logs -f repitbot

# Просмотр логов (systemd)
sudo journalctl -u repitbot -f

# Перезапуск бота (Docker)
docker-compose restart repitbot

# Перезапуск бота (systemd)
sudo systemctl restart repitbot

# Проверка использования ресурсов
htop
df -h
```

---

## ⚡ Автоматическое обновление через GitHub Actions (опционально)

Если хотите настроить автоматическое развертывание при обновлении кода:

1. Настройте SSH ключи для GitHub Actions
2. Создайте `.github/workflows/deploy.yml`
3. Добавьте секреты в репозиторий GitHub

---

## 🆘 Решение проблем

### Бот не запускается:
- Проверьте токен в `.env`
- Убедитесь, что все зависимости установлены
- Проверьте логи: `docker-compose logs repitbot`

### Ошибки базы данных:
- Убедитесь, что файл базы данных доступен для записи
- Для PostgreSQL проверьте подключение и права

### Нет доступа к файлам:
```bash
# Исправление прав доступа
sudo chown -R $USER:$USER ~/repitbot
chmod +x bot.py
```

---

## 🎯 Готово!

Ваш бот теперь работает на сервере 24/7! 

- Логи сохраняются в папке `logs/`
- База данных в `data/` (для Docker) или `repitbot.db` (для обычной установки)
- Графики прогресса в `charts/`

**Не забудьте:**
- Регулярно делать бэкапы базы данных
- Мониторить использование ресурсов сервера
- Обновлять зависимости для безопасности