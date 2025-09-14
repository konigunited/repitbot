#!/usr/bin/env bash
# Запуск create_users.py внутри контейнера docker-compose
# Usage: ./run_create_users.sh [service_name]
SERVICE=${1:-repitbot}
PYTHON_CMD=${PYTHON_CMD:-python}

# Запускаем скрипт внутри запущенного контейнера
if docker-compose ps --services | grep -q "^$SERVICE$"; then
  docker-compose exec -T $SERVICE $PYTHON_CMD /app/create_users.py
else
  echo "Сервис $SERVICE не запущен. Запустите docker-compose up -d $SERVICE и повторите попытку."
  exit 1
fi
