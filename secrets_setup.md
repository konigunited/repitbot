# 🔐 Secrets Management для RepitBot

## 🎯 Цель: Безопасное управление секретными данными

### ⚠️ КРИТИЧЕСКИ ВАЖНО
- **НЕ КОММИТИТЬ** секреты в Git
- **ИСПОЛЬЗОВАТЬ СИЛЬНЫЕ ПАРОЛИ** для всех сервисов  
- **РЕГУЛЯРНО РОТИРОВАТЬ** ключи и пароли
- **МИНИМАЛЬНЫЕ ПРАВА** доступа для каждого сервиса

## 🔑 Генерация безопасных секретов

### 1. JWT Secrets (256-bit ключи)
```bash
# JWT Secret Key
openssl rand -hex 32
# Результат: a1b2c3d4e5f6...

# JWT Refresh Secret  
openssl rand -hex 32
# Результат: f6e5d4c3b2a1...

# API Secret Key
openssl rand -hex 32
# Результат: 123abc456def...
```

### 2. Database Passwords (сильные пароли)
```bash
# Генерация сильного пароля (20 символов)
openssl rand -base64 20
# Результат: XyZ9#mN2$pQ7@vB4&kL8

# Для каждого сервиса нужен уникальный пароль:
# repitbot_user_service: 
openssl rand -base64 20

# repitbot_lesson_service:
openssl rand -base64 20

# И так далее для всех 9 сервисов...
```

### 3. Encryption Keys
```bash
# Для шифрования sensitive данных
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Результат: gAAAAABhZ2d...
```

### 4. Session Secrets
```bash
# Для Flask/FastAPI sessions
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Результат: xyz123abc...
```

## 📝 Создание production .env файла

### Шаг 1: Копирование шаблона
```bash
cp .env.production.example .env.production
```

### Шаг 2: Заполнение реальными значениями
Откройте `.env.production` и замените все `CHANGE_THIS_*` значения:

```bash
# Пример заполненного файла:
DATABASE_HOST=db.supabase.co
JWT_SECRET_KEY=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
JWT_REFRESH_SECRET=f6e5d4c3b2a1098765432109876543210987fedcba0987654321fedcba098765
BOT_TOKEN=5555555555:AAGGhhKKllMmNnOoPpQqRrSsTtUuVvWwXx
```

## 🗄️ Настройка баз данных

### PostgreSQL connection strings с реальными данными:

#### Supabase Example:
```bash
DATABASE_URL_USER=postgresql+asyncpg://repitbot_user_service:XyZ9mN2pQ7vB4kL8@db.supabase.co:5432/repitbot_users?sslmode=require
```

#### Neon Example:  
```bash
DATABASE_URL_USER=postgresql+asyncpg://repitbot_user_service:abc123def456@ep-cool-moon-123456.us-east-2.aws.neon.tech:5432/repitbot_users?sslmode=require
```

#### Railway Example:
```bash
DATABASE_URL_USER=postgresql+asyncpg://repitbot_user_service:secretpass@containers-us-west-123.railway.app:5432/repitbot_users
```

## 🔒 Безопасное хранение секретов

### Вариант 1: Environment Variables (рекомендуется для Docker)
```bash
# Экспорт переменных на сервере
export JWT_SECRET_KEY="your-secret-here"
export DATABASE_PASSWORD="your-db-password"
```

### Вариант 2: Docker Secrets (для Docker Swarm)
```bash
# Создание Docker secret
echo "your-secret-password" | docker secret create db_password -

# Использование в docker-compose
services:
  user-service:
    secrets:
      - db_password
```

### Вариант 3: Kubernetes Secrets (для K8s deployment)
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: repitbot-secrets
type: Opaque
data:
  jwt-secret: <base64-encoded-secret>
  db-password: <base64-encoded-password>
```

### Вариант 4: HashiCorp Vault (enterprise)
```bash
# Сохранение секрета в Vault
vault kv put secret/repitbot jwt_secret="your-jwt-secret"

# Получение секрета
vault kv get -field=jwt_secret secret/repitbot
```

## 🏭 Production Checklist

### ✅ Database Security
- [ ] Уникальные сильные пароли для всех 9 сервисов
- [ ] SSL/TLS соединения включены (sslmode=require)
- [ ] Firewall настроен (только нужные IP)
- [ ] Backup автоматические настроены
- [ ] Мониторинг подключений включен

### ✅ JWT Security  
- [ ] Генерированы новые 256-bit ключи
- [ ] Access tokens короткоживущие (30 минут)
- [ ] Refresh tokens ротируются
- [ ] Подписание алгоритм HS256 или RS256

### ✅ External Services
- [ ] Telegram Bot token получен от @BotFather
- [ ] SMTP настройки проверены
- [ ] Payment provider (Stripe) keys активированы
- [ ] File storage (S3/local) настроен

### ✅ Infrastructure
- [ ] RabbitMQ пользователи созданы
- [ ] Redis пароль установлен  
- [ ] Prometheus/Grafana passwords изменены
- [ ] SSL сертификаты получены

### ✅ Security Headers
- [ ] CORS origins настроены правильно
- [ ] Rate limiting включен
- [ ] Session security настроена
- [ ] File upload ограничения установлены

## 🔄 Secrets Rotation Plan

### Ежемесячно:
- [ ] JWT secrets ротация
- [ ] API keys обновление
- [ ] Session secrets смена

### Ежеквартально:
- [ ] Database passwords смена
- [ ] RabbitMQ/Redis passwords обновление  
- [ ] SSL сертификаты проверка

### При подозрении на компрометацию:
- [ ] Немедленная ротация всех secrets
- [ ] Аудит access logs
- [ ] Уведомление команды безопасности

## 🚨 Emergency Response

### При утечке секретов:
1. **Немедленно** сменить скомпрометированные ключи
2. **Проверить** логи на подозрительную активность  
3. **Уведомить** всех администраторов
4. **Провести** security audit
5. **Обновить** все связанные системы

### Контакты экстренного реагирования:
- Security Lead: [your-security-lead@company.com]
- DevOps Lead: [your-devops-lead@company.com]  
- Emergency Phone: [+7-xxx-xxx-xxxx]

## 📋 Scripts для автоматизации

### generate_secrets.py
```python
#!/usr/bin/env python3
import secrets
import os
from cryptography.fernet import Fernet

def generate_jwt_secret():
    return secrets.token_hex(32)

def generate_password(length=20):
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_encryption_key():
    return Fernet.generate_key().decode()

# Генерация всех секретов
secrets_config = {
    'JWT_SECRET_KEY': generate_jwt_secret(),
    'JWT_REFRESH_SECRET': generate_jwt_secret(), 
    'API_SECRET_KEY': generate_jwt_secret(),
    'ENCRYPTION_KEY': generate_encryption_key(),
    'SESSION_SECRET': secrets.token_urlsafe(32),
    'WEBHOOK_SECRET': secrets.token_urlsafe(16),
}

# Database passwords для всех сервисов
services = [
    'user', 'lesson', 'homework', 'payment', 'material', 
    'notification', 'analytics', 'student', 'gateway', 'admin'
]

for service in services:
    secrets_config[f'DB_PASSWORD_{service.upper()}'] = generate_password()

# Вывод секретов
print("# Generated secrets for RepitBot production")
print("# ⚠️  СОХРАНИТЬ В БЕЗОПАСНОМ МЕСТЕ!")
print()

for key, value in secrets_config.items():
    print(f"{key}={value}")
```

### Запуск генератора:
```bash
python3 generate_secrets.py > secrets_generated.txt
chmod 600 secrets_generated.txt  # Только owner может читать
```

## ✅ Итоговый результат

После выполнения всех шагов у вас должно быть:
- [ ] Файл `.env.production` с реальными секретами
- [ ] Все пароли сгенерированы и уникальны
- [ ] Database connection strings настроены  
- [ ] External services подключены
- [ ] Security checklist выполнен
- [ ] Backup план секретов создан
- [ ] Emergency response план готов

**ВАЖНО: Никогда не коммитьте .env.production в Git!** 🚨