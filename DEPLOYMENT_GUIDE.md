# RepitBot - Руководство по развертыванию на сервере

## Обновление кода на сервере с VS Code

### 1. Подключение к серверу через VS Code

1. **Установите расширение Remote-SSH** в VS Code
2. **Добавьте SSH конфигурацию:**
   - Нажмите `Ctrl+Shift+P` → `Remote-SSH: Open SSH Configuration File`
   - Добавьте конфигурацию сервера:
   ```
   Host your-server
       HostName your-server-ip
       User your-username
       Port 22
   ```
3. **Подключитесь к серверу:**
   - `Ctrl+Shift+P` → `Remote-SSH: Connect to Host`
   - Выберите ваш сервер

### 2. Обновление кода

```bash
# Перейти в директорию проекта
cd /path/to/repitbot

# Остановить бота (если работает)
pkill -f "python.*bot.py" || sudo systemctl stop repitbot

# Создать бэкап текущей базы данных
cp repitbot.db repitbot.db.backup.$(date +%Y%m%d_%H%M%S)

# Получить последние изменения
git fetch origin
git checkout feature/student-view-fixes
git pull origin feature/student-view-fixes

# Выполнить миграцию базы данных (ВАЖНО!)
python migrate_lesson_status.py
```

### 3. Проверка и запуск

```bash
# Проверить синтаксис
python -m py_compile bot.py
python -m py_compile src/database.py
python -m py_compile src/handlers/tutor.py
python -m py_compile src/handlers/parent.py
python -m py_compile src/handlers/shared.py

# Проверить зависимости
pip install -r requirements.txt

# Запустить бота (тестовый режим)
python bot.py

# Если все работает, остановить (Ctrl+C) и запустить в фоне
nohup python bot.py > logs/bot.log 2>&1 &

# Или через systemd (если настроен)
sudo systemctl start repitbot
sudo systemctl status repitbot
```

### 4. Проверка работоспособности

После развертывания проверьте:

1. **Репетитор:**
   - ✅ Создание нового урока → статус "Не проведен"
   - ✅ Просмотр деталей урока → только поле "✅ Проведение"
   - ✅ Изменение статуса урока на "Проведен"
   - ✅ Отсутствие кнопки "📅 Запланировать уроки"

2. **Родитель:**
   - ✅ Кнопки детей работают и не "залипают"
   - ✅ Открытие карточек учеников
   - ✅ Просмотр прогресса, расписания, оплат

3. **Общее:**
   - ✅ Напоминания об оплате (1 урок вместо 2)
   - ✅ Рассылка работает
   - ✅ Статистика и графики строятся

## Основные изменения в версии

### ✨ Новые возможности
- **Система статусов уроков**: Отслеживание проведения уроков
- **Упрощенное создание уроков**: Убрана функция массового планирования
- **Исправлены кнопки родителей**: Все функции родительского интерфейса работают

### 🔧 Технические улучшения
- Микросервисная архитектура обработчиков
- Добавлено поле `lesson_status` в базу данных
- Исправлена обработка callback'ов родителей
- Оптимизированы уведомления об оплате

### 📚 Документация
- Полная документация системы рассылок
- Руководство по миграции базы данных

## Откат изменений (если нужен)

```bash
# Остановить бота
pkill -f "python.*bot.py" || sudo systemctl stop repitbot

# Восстановить бэкап базы данных
cp repitbot.db.backup.YYYYMMDD_HHMMSS repitbot.db

# Вернуться к предыдущей версии
git checkout main  # или другой стабильный branch
git pull origin main

# Запустить
python bot.py
```

## Мониторинг

```bash
# Просмотр логов
tail -f logs/repitbot.log
tail -f logs/errors.log

# Проверка процесса
ps aux | grep bot.py

# Проверка использования ресурсов
htop
df -h
```

## Файлы конфигурации

Убедитесь, что существуют:
- `config.py` - настройки бота и токены
- `repitbot.db` - база данных SQLite
- `logs/` - директория для логов

## Поддержка

При возникновении проблем:
1. Проверьте логи в `logs/errors.log`
2. Убедитесь, что миграция базы данных выполнена
3. Проверьте права доступа к файлам
4. Перезапустите бота

---
*Версия: feature/student-view-fixes*
*Дата: 25.08.2025*