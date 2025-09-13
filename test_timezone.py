#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы временной зоны Калининграда.
"""

from datetime import datetime
import pytz
from src.timezone_utils import now, today, now_naive

def test_timezone():
    print("=== Тест настроек временной зоны Калининграда ===")

    # Текущее время UTC
    utc_now = datetime.now(pytz.UTC)
    print(f"Текущее время UTC: {utc_now}")

    # Время в Калининграде через pytz
    kaliningrad_tz = pytz.timezone('Europe/Kaliningrad')
    kaliningrad_direct = utc_now.astimezone(kaliningrad_tz)
    print(f"Время в Калининграде (прямое): {kaliningrad_direct}")

    # Время через нашу утилиту
    our_time = now()
    print(f"Время через timezone_utils.now(): {our_time}")

    # Проверяем разницу
    time_diff = abs((kaliningrad_direct - our_time).total_seconds())
    print(f"Разница между методами: {time_diff} секунд")

    # Тестируем naive время
    naive_time = now_naive()
    print(f"Naive время (без timezone): {naive_time}")

    # Сегодняшняя дата
    today_date = today()
    print(f"Сегодняшняя дата в Калининграде: {today_date}")

    # Сравнение с московским временем
    moscow_tz = pytz.timezone('Europe/Moscow')
    moscow_time = utc_now.astimezone(moscow_tz)
    print(f"Время в Москве: {moscow_time}")

    moscow_kaliningrad_diff = (moscow_time - kaliningrad_direct).total_seconds() / 3600
    print(f"Разница Москва - Калининград: {moscow_kaliningrad_diff} часов (должно быть 1)")

    print("\n=== Результат ===")
    if time_diff < 1:  # Разница меньше секунды
        print("✅ Временная зона настроена корректно!")
    else:
        print("❌ Есть проблемы с настройкой временной зоны")

    if abs(moscow_kaliningrad_diff - 1) < 0.1:  # Москва на час позже Калининграда
        print("✅ Разница с Москвой корректная!")
    else:
        print("❌ Неверная разница с московским временем")

if __name__ == "__main__":
    test_timezone()