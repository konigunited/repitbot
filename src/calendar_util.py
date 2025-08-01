# -*- coding: utf-8 -*-
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP

# Мы можем предварительно настроить календарь, чтобы не делать это каждый раз в хендлерах
# LSTEP - это шаги, которые будет видеть пользователь: Год -> Месяц -> День
class CustomCalendar(DetailedTelegramCalendar):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.first_step = LSTEP[0]  # Год
        self.last_step = LSTEP[2]   # День

def create_calendar(year=None, month=None):
    """Создает инстанс календаря."""
    # Локализация для кнопок
    ru_weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    ru_months = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
    
    calendar, step = CustomCalendar(
        locale='ru',
        min_date=None,
        max_date=None,
        tele_user_id=None, # tele_user_id можно использовать для разделения календарей разных пользователей
        week_days_labels=ru_weekdays,
        months_labels=ru_months
    ).build()
    
    return calendar, step
