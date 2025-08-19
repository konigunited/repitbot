# 🪟 Пошаговая установка RepitBot на Windows Server

## 📋 ДЛЯ РАЗРАБОТЧИКА (тебя) - как объяснить админу

Отправь админу файл `ADMIN_REQUIREMENTS_WINDOWS.md`, а эта инструкция - для совместной работы.

---

## 🚀 ПОШАГОВАЯ УСТАНОВКА

### Шаг 1: Подготовка (выполняет админ)
Админ должен выполнить требования из `ADMIN_REQUIREMENTS_WINDOWS.md`

### Шаг 2: Копирование файлов на сервер
```cmd
# Создать папку проекта (если админ не создал)
mkdir C:\RepitBot
cd C:\RepitBot

# Скопировать все файлы проекта в эту папку
# (через RDP, USB, сетевую папку - как удобно)
```

### Шаг 3: Создание виртуального окружения
```cmd
cd C:\RepitBot
python -m venv venv

# Активация виртуального окружения
venv\Scripts\activate.bat

# Обновление pip
python -m pip install --upgrade pip
```

### Шаг 4: Установка зависимостей  
```cmd
# Установка всех пакетов из requirements.txt
pip install -r requirements.txt
```

### Шаг 5: Настройка переменных окружения
```cmd
# Скопировать шаблон
copy .env.example .env

# Отредактировать .env файл (блокнотом или любым редактором)
notepad .env
```

В файле `.env` указать:
```env
BOT_TOKEN=твой_токен_от_BotFather
ADMIN_ACCESS_CODE=твой_код_админа
DATABASE_URL=sqlite:///repitbot.db
LOG_LEVEL=INFO
```

### Шаг 6: Создание необходимых папок
```cmd
mkdir logs
mkdir charts
mkdir data
```

### Шаг 7: Первый тестовый запуск
```cmd
# Активировать виртуальное окружение (если не активно)
venv\Scripts\activate.bat

# Запустить бота
python bot.py
```

Если все работает - увидишь сообщения в консоли о запуске бота.

---

## 🔄 НАСТРОЙКА АВТОЗАПУСКА

### Вариант 1: Windows Service с NSSM (рекомендуется)

```cmd
# Скачать и установить NSSM
# https://nssm.cc/download

# Установить службу
nssm install RepitBot

# Настройки в GUI NSSM:
# Application path: C:\RepitBot\venv\Scripts\python.exe  
# Arguments: bot.py
# Startup directory: C:\RepitBot
# Service name: RepitBot
```

### Вариант 2: Создание bat-файла для запуска

Создать файл `start_bot.bat`:
```batch
@echo off
cd /d C:\RepitBot
call venv\Scripts\activate.bat
python bot.py
pause
```

### Вариант 3: Task Scheduler
```cmd
# Открыть Task Scheduler
taskschd.msc

# Создать новую задачу:
# - Trigger: At startup
# - Action: Start program
# - Program: C:\RepitBot\venv\Scripts\python.exe
# - Arguments: bot.py  
# - Start in: C:\RepitBot
```

---

## 🔍 МОНИТОРИНГ И ОБСЛУЖИВАНИЕ

### Проверка статуса бота:
```cmd
# Через Task Manager найти процесс python.exe

# Или через PowerShell:
Get-Process python

# Проверить логи:
type C:\RepitBot\logs\repitbot.log
```

### Перезапуск бота:
```cmd
# Если запущен как служба:
net stop RepitBot
net start RepitBot

# Если запущен вручную - завершить процесс и запустить заново
```

### Обновление бота:
```cmd
# Остановить бота
# Заменить файлы новыми версиями
# Активировать окружение
venv\Scripts\activate.bat
# Обновить зависимости (если изменились)
pip install -r requirements.txt
# Запустить бота заново
```

---

## 🛡️ БЕЗОПАСНОСТЬ

### Важные моменты:
1. **Не показывай токен бота** никому
2. **Регулярно делай бэкап** файла `repitbot.db`
3. **Мониторь логи** на предмет ошибок
4. **Ограничь доступ** к папке C:\RepitBot только нужными пользователями

### Бэкап базы данных:
```cmd
# Создать папку для бэкапов
mkdir C:\RepitBot\backups

# Скопировать базу данных
copy repitbot.db backups\repitbot_backup_%date%.db
```

---

## 🆘 РЕШЕНИЕ ПРОБЛЕМ

### "ModuleNotFoundError":
```cmd
# Убедись что виртуальное окружение активно
venv\Scripts\activate.bat
# Переустанови зависимости
pip install -r requirements.txt
```

### "Permission denied":
```cmd
# Дать права на папку (выполнить как администратор)
icacls C:\RepitBot /grant Everyone:(OI)(CI)F
```

### "Connection error":
- Проверь интернет соединение
- Убедись что токен бота правильный
- Проверь что файрвол не блокирует api.telegram.org

### Бот не отвечает:
- Проверь логи в `logs\errors.log`
- Убедись что процесс python запущен
- Перезапусти бота

---

## 📊 ПОЛЕЗНЫЕ КОМАНДЫ ДЛЯ АДМИНА

```cmd
# Посмотреть запущенные процессы Python
tasklist /fi "imagename eq python.exe"

# Убить процесс бота (по PID)
taskkill /pid 1234 /f

# Посмотреть использование ресурсов
wmic process where name="python.exe" get processid,percentprocessortime,workingsetsize

# Очистить старые логи (старше 30 дней)
forfiles /p C:\RepitBot\logs /s /m *.log /d -30 /c "cmd /c del @path"
```

---

## ✅ ФИНАЛЬНАЯ ПРОВЕРКА

После установки проверь:
- [ ] Бот отвечает в Telegram
- [ ] Логи пишутся в `logs\repitbot.log`  
- [ ] База данных создается (`repitbot.db`)
- [ ] Автозапуск настроен (если нужен)
- [ ] Мониторинг работает

**Время полной установки**: 1-2 часа включая настройку автозапуска.