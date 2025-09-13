"""
Утилиты для работы с временными зонами.
Все функции возвращают время в часовом поясе Калининграда (Europe/Kaliningrad).
"""

from datetime import datetime, date, timedelta
import pytz

# Временная зона Калининграда (UTC+2)
KALININGRAD_TZ = pytz.timezone('Europe/Kaliningrad')

def now() -> datetime:
    """Возвращает текущее время в часовом поясе Калининграда."""
    return datetime.now(KALININGRAD_TZ)

def today() -> date:
    """Возвращает текущую дату в часовом поясе Калининграда."""
    return now().date()

def now_naive() -> datetime:
    """Возвращает текущее время в часовом поясе Калининграда без информации о временной зоне."""
    return now().replace(tzinfo=None)

def to_kaliningrad(dt: datetime) -> datetime:
    """Конвертирует datetime в часовой пояс Калининграда."""
    if dt.tzinfo is None:
        # Если время без временной зоны, считаем его UTC
        dt = pytz.UTC.localize(dt)
    return dt.astimezone(KALININGRAD_TZ)

def from_kaliningrad(dt: datetime) -> datetime:
    """Конвертирует время из часового пояса Калининграда в UTC."""
    if dt.tzinfo is None:
        dt = KALININGRAD_TZ.localize(dt)
    return dt.astimezone(pytz.UTC)

def localize_kaliningrad(dt: datetime) -> datetime:
    """Добавляет информацию о временной зоне Калининграда к naive datetime."""
    if dt.tzinfo is not None:
        raise ValueError("datetime уже содержит информацию о временной зоне")
    return KALININGRAD_TZ.localize(dt)