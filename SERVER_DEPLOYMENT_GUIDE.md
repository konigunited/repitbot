# 🚀 Репитбот - Развертывание на Windows Сервере

## 📋 Предварительные требования

### 1. Установка Python
- Скачайте Python 3.9+ с [python.org](https://python.org)
- ✅ Обязательно отметьте "Add Python to PATH"
- Проверьте установку: `python --version`

### 2. Установка Git
- Скачайте Git с [git-scm.com](https://git-scm.com)
- Настройте SSH ключи или используйте HTTPS

## 🔧 Развертывание

### Шаг 1: Клонирование репозитория
```bash
cd C:\
git clone YOUR_REPO_URL repitbot
cd repitbot
```

### Шаг 2: Автоматическое развертывание
```bash
# Запустите скрипт развертывания
deploy_server.bat
```

### Шаг 3: Настройка переменных окружения
Создайте файл `.env` в корне проекта:
```env
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=sqlite:///repitbot.db
LOG_LEVEL=INFO
LOG_DIR=logs
```

## ⚙️ Настройка Task Scheduler

### Вариант 1: Через GUI
1. Откройте **Task Scheduler** (Планировщик заданий)
2. Создайте базовую задачу:
   - **Имя**: RepitBot
   - **Триггер**: При запуске компьютера
   - **Действие**: Запустить программу
   - **Программа**: `C:\repitbot\start_bot.bat`
   - **Начать в**: `C:\repitbot`

### Вариант 2: Через PowerShell (от администратора)
```powershell
$action = New-ScheduledTaskAction -Execute "C:\repitbot\start_bot.bat" -WorkingDirectory "C:\repitbot"
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserID "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask -TaskName "RepitBot" -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Telegram RepitBot Auto-start"
```

## 🔄 Обновление на сервере

### Автоматическое обновление
```bash
# Просто запустите скрипт развертывания снова
deploy_server.bat
```

### Ручное обновление
```bash
git pull origin main
pip install -r requirements.txt
python fix_db.py
```

## 📊 Мониторинг

### Проверка статуса
```bash
# Проверить работающие процессы Python
tasklist | findstr python

# Проверить логи
type logs\repitbot.log | more
type logs\errors.log | more
```

### Просмотр Task Scheduler
1. Откройте Task Scheduler
2. Найдите задачу "RepitBot"
3. Проверьте статус и историю выполнения

## 🛠️ Устранение неполадок

### Проблема: Бот не запускается
1. Проверьте `.env` файл
2. Проверьте интернет-соединение
3. Проверьте логи: `logs\errors.log`

### Проблема: Task Scheduler не работает
1. Убедитесь, что задача создана с правами администратора
2. Проверьте путь к `start_bot.bat`
3. Проверьте, что Python доступен в системе

### Проблема: База данных
```bash
# Проверить базу данных
python fix_db.py

# Пересоздать базу (ОСТОРОЖНО - удалит данные!)
del repitbot.db
python bot.py
```

## 🚀 Файлы для развертывания

- `start_bot.bat` - Запуск бота
- `deploy_server.bat` - Автоматическое развертывание
- `fix_db.py` - Миграция базы данных
- `update_server.py` - Скрипт обновления (если есть)

## 📝 Примечания

- Логи сохраняются в папке `logs/`
- База данных: `repitbot.db`
- Для production используйте PostgreSQL вместо SQLite
- Регулярно делайте резервные копии базы данных
- Проверяйте обновления через `git pull`

## 🆘 Поддержка

При проблемах проверьте:
1. Логи ошибок: `logs\errors.log`
2. Основные логи: `logs\repitbot.log`
3. Статус в Task Scheduler
4. Доступность api.telegram.org