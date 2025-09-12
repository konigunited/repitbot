#!/usr/bin/env python3

import re

# Читаем файл docker-compose.microservices.yml
with open('docker-compose.microservices.yml', 'r', encoding='utf-8') as f:
    content = f.read()

# Убираем весь блок payment-service
pattern = r'\n  # Payment Service.*?\n  # [A-Z]'
content = re.sub(pattern, r'\n  # ', content, flags=re.DOTALL)

# Убираем все ссылки на payment-service
payment_refs = [
    '      - PAYMENT_SERVICE_URL=http://payment-service:8003\n',
    '      - PAYMENT_SERVICE_URL=http://payment-service:8004\n', 
    '      payment-service:\n        condition: service_healthy\n',
    '      - payment-service\n'
]

for ref in payment_refs:
    content = content.replace(ref, '')

# Убираем volumes связанные с payment
content = content.replace('  payment_service_data:\n    driver: local\n', '')

print("Обработка завершена")

# Записываем результат
with open('docker-compose.microservices.yml', 'w', encoding='utf-8') as f:
    f.write(content)

print("Файл docker-compose.microservices.yml обновлен без payment-service")