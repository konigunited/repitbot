# СРОЧНОЕ ИСПРАВЛЕНИЕ: Миграция базы данных на сервере

## Проблема
```
ERROR: 'not_conducted' is not among the defined enum values. 
Enum name: lessonstatus. Possible values: NOT_CONDUCT.., CONDUCTED
```

## Быстрое решение

### 1. Подключитесь к серверу
```bash
# Через VS Code Remote-SSH или SSH терминал
ssh your-server-user@your-server-ip
```

### 2. Остановите бота
```bash
# Найти процесс бота
ps aux | grep bot.py

# Остановить бота (выберите нужную команду)
pkill -f "python.*bot.py"
# ИЛИ
sudo systemctl stop repitbot
# ИЛИ  
kill -9 PID_ПРОЦЕССА
```

### 3. Создайте бэкап базы данных
```bash
cd /path/to/repitbot
cp repitbot.db repitbot.db.backup.emergency.$(date +%Y%m%d_%H%M%S)
ls -la repitbot.db*
```

### 4. Загрузите новые файлы
```bash
# Получить последние изменения
git fetch origin
git checkout feature/student-view-fixes
git pull origin feature/student-view-fixes

# Проверить, что скрипт загружен
ls -la fix_server_lesson_status.py
```

### 5. Выполните миграцию
```bash
# Запустить скрипт исправления
python fix_server_lesson_status.py

# Ожидаемый вывод:
# Fixing enum values in lesson_status field...
# Current values:
#   not_conducted: XX lessons
# Enum values fixed successfully!
# Fixed values:
#   NOT_CONDUCTED (Not conducted): XX lessons
# SUCCESS: Enum value fix completed successfully!
```

### 6. Проверьте базу данных
```bash
# Открыть базу данных SQLite
sqlite3 repitbot.db

# Выполнить проверочный запрос
SELECT lesson_status, COUNT(*) FROM lessons GROUP BY lesson_status;

# Должно показать:
# NOT_CONDUCTED|XX
# CONDUCTED|XX (если есть проведенные уроки)

# Выйти из SQLite
.quit
```

### 7. Запустите бота
```bash
# Проверить синтаксис
python -m py_compile bot.py

# Запустить бота
python bot.py

# Если все работает, остановить (Ctrl+C) и запустить в фоне
nohup python bot.py > logs/bot.log 2>&1 &

# ИЛИ через systemd
sudo systemctl start repitbot
sudo systemctl status repitbot
```

### 8. Проверьте работу
- Зайдите в бота как репетитор
- Нажмите на ученика → "📚 Уроки ученика"  
- Должно работать без ошибок

## Если что-то пошло не так

### Откат к резервной копии
```bash
# Остановить бота
pkill -f "python.*bot.py"

# Восстановить бэкап
cp repitbot.db.backup.emergency.TIMESTAMP repitbot.db

# Вернуться к предыдущей версии
git checkout main
git pull origin main

# Запустить старую версию
python bot.py
```

## Проверка логов
```bash
# Посмотреть последние ошибки
tail -f logs/errors.log

# Посмотреть логи бота
tail -f logs/repitbot.log
```

---
**ВАЖНО**: Обязательно сделайте бэкап перед миграцией!