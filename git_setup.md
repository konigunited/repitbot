# 📁 Git Repository Setup для RepitBot

## 🚀 Пошаговая настройка Git репозитория

### ШАГ 1: Инициализация локального репозитория
```bash
# Переходим в папку проекта
cd C:\Users\F12$\Desktop\repitbot

# Инициализируем Git репозиторий
git init

# Настраиваем основную ветку
git branch -M main

# Настраиваем пользователя (если не настроено глобально)
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

### ШАГ 2: Первый коммит
```bash
# Добавляем все файлы (учитывая .gitignore)
git add .

# Проверяем что добавилось
git status

# Создаем первый коммит
git commit -m "Initial commit: RepitBot microservices architecture

- 9 microservices implemented (User, Lesson, Homework, Payment, Material, Notification, Analytics, Student)
- API Gateway for centralized routing
- Event-driven architecture with RabbitMQ
- Docker containerization ready
- Production-ready configuration
- Comprehensive testing suite
- 3 user roles: Parent, Student, Tutor
- Gamification system with achievements

🚀 Ready for production deployment"
```

### ШАГ 3: Создание GitHub/GitLab репозитория

#### Вариант A: GitHub
1. Идите на https://github.com
2. Нажмите "New repository"
3. Название: `repitbot-microservices`
4. Описание: `RepitBot - Educational platform with microservices architecture`
5. Выберите Public или Private
6. НЕ добавляйте README, .gitignore, license (они уже есть)
7. Нажмите "Create repository"

#### Вариант B: GitLab  
1. Идите на https://gitlab.com
2. Нажмите "New project" → "Create blank project"
3. Название: `repitbot-microservices`
4. Описание: `RepitBot - Educational platform with microservices architecture`
5. Выберите Visibility level
6. Нажмите "Create project"

### ШАГ 4: Подключение к удаленному репозиторию
```bash
# Замените URL на ваш реальный репозиторий
git remote add origin https://github.com/YOUR_USERNAME/repitbot-microservices.git

# Или для GitLab:
# git remote add origin https://gitlab.com/YOUR_USERNAME/repitbot-microservices.git

# Проверяем подключение
git remote -v
```

### ШАГ 5: Push в удаленный репозиторий
```bash
# Отправляем код в GitHub/GitLab
git push -u origin main
```

### ШАГ 6: Создание production ветки
```bash
# Создаем отдельную ветку для production
git checkout -b production

# Отправляем production ветку
git push -u origin production

# Возвращаемся на main
git checkout main
```

## 🔒 ВАЖНО: Проверка безопасности

### ЧТО ДОЛЖНО БЫТЬ В РЕПОЗИТОРИИ:
✅ Весь код микросервисов
✅ Docker конфигурации  
✅ README и документация
✅ Тесты
✅ .gitignore

### ЧТО НЕ ДОЛЖНО ПОПАСТЬ В РЕПОЗИТОРИЙ:
❌ .env файлы с паролями
❌ JWT secrets
❌ Database credentials
❌ API keys
❌ Личные данные пользователей
❌ Логи и временные файлы

### Проверка перед push:
```bash
# Проверяем что будет закоммичено
git status

# Проверяем что НЕ добавилось (должны быть ignored files)
git status --ignored

# Проверяем содержимое коммита
git diff --cached
```

## 📋 Полезные Git команды для проекта

### Ежедневная работа:
```bash
# Проверить статус
git status

# Добавить новые файлы
git add services/new-service/

# Коммит изменений
git commit -m "Add new feature: user notifications"

# Отправить в репозиторий
git push origin main
```

### Работа с ветками:
```bash
# Создать feature ветку
git checkout -b feature/payment-improvements

# Переключиться между ветками
git checkout main
git checkout feature/payment-improvements

# Merge feature в main
git checkout main
git merge feature/payment-improvements

# Удалить feature ветку после merge
git branch -d feature/payment-improvements
```

### Теги для релизов:
```bash
# Создать тег для версии
git tag -a v1.0.0 -m "Release v1.0.0: Production ready microservices"

# Отправить теги
git push origin --tags

# Посмотреть все теги
git tag -l
```

## 🚀 Готово!

После выполнения этих команд у вас будет:
✅ Настроенный Git репозиторий
✅ Код загружен на GitHub/GitLab  
✅ Production branch создан
✅ Безопасность соблюдена (секреты не попали в репозиторий)

Теперь можно переходить к настройке SQL базы данных! 💾