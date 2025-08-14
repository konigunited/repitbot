# -*- coding: utf-8 -*-
try:
    from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
except ImportError:
    # Заглушка для работы без telegram_bot_calendar
    DetailedTelegramCalendar = None
    LSTEP = None

# Мы можем предварительно настроить календарь, чтобы не делать это каждый раз в хендлерах
# LSTEP - это шаги, которые будет видеть пользователь: Год -> Месяц -> День
class CustomCalendar:
    def __init__(self, **kwargs):
        if DetailedTelegramCalendar:
            super().__init__(**kwargs)
            self.first_step = LSTEP[0]  # Год
            self.last_step = LSTEP[2]   # День

def create_calendar(year=None, month=None):
    """Создает инстанс календаря."""
    if not DetailedTelegramCalendar:
        # Заглушка - возвращаем простую клавиатуру
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 Выберите дату вручную", callback_data="manual_date")]
        ])
        return keyboard, "manual"
    
    # Локализация для кнопок
    ru_weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    ru_months = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
    
    calendar, step = CustomCalendar(
        locale='ru',
        min_date=None,
        max_date=None,
        tele_user_id=None,
        week_days_labels=ru_weekdays,
        months_labels=ru_months
    ).build()
    
    return calendar, step
