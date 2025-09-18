FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /bot

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ../shared/python /opt/shared
ENV PYTHONPATH="/bot:/opt/shared"

COPY app ./app

CMD ["python", "-m", "app.main"]
