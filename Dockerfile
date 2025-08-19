# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Обновляем pip и устанавливаем зависимости
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Создаем директории для логов и базы данных
RUN mkdir -p logs charts

# Устанавливаем права доступа
RUN chmod +x bot.py

# Открываем порт (если нужен веб-сервер)
EXPOSE 8080

# Команда для запуска
CMD ["python", "bot.py"]