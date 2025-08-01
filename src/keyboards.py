# -*- coding: utf-8 -*-
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from .database import TopicMastery, HomeworkStatus

# --- Общие клавиатуры ---
def main_menu_keyboard(user_role):
    if user_role == "tutor":
        return tutor_main_keyboard()
    elif user_role == "student":
        return student_main_keyboard()
    elif user_role == "parent":
        return parent_main_keyboard()

# --- Клавиатуры для репетитора ---
TUTOR_BUTTONS = {
    "students": "🎓 Список учеников",
    "add_student": "➕ Добавить ученика",
    "monthly_report": "📊 Отчёт за месяц",
    "library": "📚 Управление библиотекой",
    "stats": "📈 Статистика",
    "broadcast": "📣 Рассылка"
}

def tutor_main_keyboard():
    keyboard = [
        [TUTOR_BUTTONS["students"], TUTOR_BUTTONS["add_student"]],
        [TUTOR_BUTTONS["monthly_report"], TUTOR_BUTTONS["library"]],
        [TUTOR_BUTTONS["stats"], TUTOR_BUTTONS["broadcast"]]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- Клавиатуры для ученика ---
def student_main_keyboard():
    """Создает клавиатуру для главного меню ученика."""
    keyboard = [
        [
            InlineKeyboardButton("📚 Темы уроков", callback_data="lessons_history"),
            InlineKeyboardButton("🗓️ Расписание", callback_data="schedule")
        ],
        [InlineKeyboardButton("📝 Домашнее задание", callback_data="homework")],
        [InlineKeyboardButton("💰 Оплата и посещаемость", callback_data="payment_attendance")],
        [
            InlineKeyboardButton("📊 Мой прогресс", callback_data="my_progress"),
            InlineKeyboardButton("🗂️ Библиотека", callback_data="materials_library")
        ],
        [InlineKeyboardButton("💬 Связь с репетитором", callback_data="chat_with_tutor")],
    ]
    return InlineKeyboardMarkup(keyboard)

def student_select_homework_keyboard(homeworks):
    """Создает клавиатуру для выбора ДЗ для сдачи."""
    keyboard = []
    for hw in homeworks:
        if hw.status == HomeworkStatus.PENDING:
            hw_text = (hw.description[:25] + '..') if len(hw.description) > 25 else hw.description
            button = InlineKeyboardButton(
                f"📝 {hw_text}", 
                callback_data=f"student_submit_hw_{hw.id}"
            )
            keyboard.append([button])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="homework")])
    return InlineKeyboardMarkup(keyboard)

# --- Клавиатуры для родителя ---
def parent_main_keyboard():
    """Создает клавиатуру для главного меню родителя."""
    keyboard = [
        [InlineKeyboardButton("👤 Мои дети", callback_data="select_child")],
        [InlineKeyboardButton("💬 Связь с репетитором", callback_data="parent_chat_with_tutor")]
    ]
    return InlineKeyboardMarkup(keyboard)

def parent_child_selection_keyboard(children):
    keyboard = []
    for child in children:
        keyboard.append([InlineKeyboardButton(f"👤 {child.full_name}", callback_data=f"view_child_{child.id}")])
    return InlineKeyboardMarkup(keyboard)


def parent_child_menu_keyboard(child_id):
    keyboard = [
        [
            InlineKeyboardButton("📊 Прогресс", callback_data=f"child_progress_{child_id}"),
            InlineKeyboardButton("🗓️ Расписание", callback_data=f"child_schedule_{child_id}")
        ],
        [
            InlineKeyboardButton("💰 Оплаты", callback_data=f"child_payments_{child_id}"),
            InlineKeyboardButton("💬 Связь с репетитором", callback_data=f"parent_chat_with_tutor_{child_id}")
        ],
        [InlineKeyboardButton("⬅️ Выбрать другого ребенка", callback_data="select_child")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Клавиатуры для репетитора (продолжение) ---
def tutor_student_list_keyboard(students):
    keyboard = []
    for student in students:
        keyboard.append([InlineKeyboardButton(student.full_name, callback_data=f"tutor_view_student_{student.id}")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def tutor_student_profile_keyboard(student_id):
    keyboard = [
        [InlineKeyboardButton("📚 Уроки ученика", callback_data=f"tutor_lessons_list_{student_id}")],
        [InlineKeyboardButton("📈 Аналитика прогресса", callback_data=f"tutor_analytics_{student_id}")],
        [
            InlineKeyboardButton("➕ Добавить урок", callback_data=f"tutor_add_lesson_{student_id}"),
            InlineKeyboardButton("💰 Добавить оплату", callback_data=f"tutor_add_payment_{student_id}")
        ],
        [
            InlineKeyboardButton("✏️ Редактировать ФИО", callback_data=f"tutor_edit_name_{student_id}"),
            InlineKeyboardButton("❌ Удалить ученика", callback_data=f"tutor_delete_student_{student_id}")
        ],
        [InlineKeyboardButton("⬅️ К списку учеников", callback_data="tutor_student_list")]
    ]
    return InlineKeyboardMarkup(keyboard)

def tutor_lesson_list_keyboard(lessons, student_id):
    keyboard = []
    for lesson in lessons:
        date_str = lesson.date.strftime('%d.%m.%y')
        keyboard.append([InlineKeyboardButton(f"{date_str} - {lesson.topic}", callback_data=f"tutor_lesson_details_{lesson.id}")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад к профилю", callback_data=f"tutor_view_student_{student_id}")])
    return InlineKeyboardMarkup(keyboard)

def tutor_lesson_details_keyboard(lesson):
    """Создает клавиатуру для карточки урока."""
    keyboard = [
        [
            InlineKeyboardButton("✏️ Изменить статус", callback_data=f"tutor_edit_lesson_{lesson.id}")
        ]
    ]
    # Если ДЗ есть, добавляем кнопку для его просмотра/проверки
    if lesson.homeworks:
        keyboard[0].append(InlineKeyboardButton("📝 Проверить ДЗ", callback_data=f"tutor_check_hw_{lesson.id}"))
    else:
        keyboard[0].append(InlineKeyboardButton("➕ Добавить ДЗ", callback_data=f"tutor_add_hw_{lesson.id}"))

    if not lesson.is_attended:
        keyboard.insert(0, [InlineKeyboardButton("✅ Отметить как проведенный", callback_data=f"tutor_mark_attended_{lesson.id}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ К списку уроков", callback_data=f"tutor_lessons_list_{lesson.student_id}")])
    return InlineKeyboardMarkup(keyboard)

def tutor_check_homework_keyboard(homework):
    """Создает клавиатуру для проверки ДЗ."""
    keyboard = []
    # ��нопки действий показываем только если ДЗ сдано
    if homework.status == HomeworkStatus.SUBMITTED:
        keyboard.append([
            InlineKeyboardButton("⭐ Принять", callback_data=f"tutor_set_hw_status_{homework.id}_{HomeworkStatus.CHECKED.value}"),
            InlineKeyboardButton("🔸 На доработку", callback_data=f"tutor_set_hw_status_{homework.id}_{HomeworkStatus.PENDING.value}")
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад к уроку", callback_data=f"tutor_lesson_details_{homework.lesson_id}")])
    return InlineKeyboardMarkup(keyboard)


def tutor_edit_student_keyboard(student_id):
    keyboard = [
        [InlineKeyboardButton("Изменить ФИО", callback_data=f"tutor_edit_name_{student_id}")],
        [InlineKeyboardButton("⬅️ Назад к профилю", callback_data=f"tutor_view_student_{student_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def tutor_delete_confirm_keyboard(student_id):
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"tutor_delete_confirm_{student_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"tutor_view_student_{student_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def tutor_edit_lesson_status_keyboard(lesson_id):
    keyboard = [
        [InlineKeyboardButton("⚪️ Не усвоено", callback_data=f"tutor_set_mastery_{lesson_id}_{TopicMastery.NOT_LEARNED.value}")],
        [InlineKeyboardButton("🟡 Усвоено", callback_data=f"tutor_set_mastery_{lesson_id}_{TopicMastery.LEARNED.value}")],
        [InlineKeyboardButton("🟢 Закреплено", callback_data=f"tutor_set_mastery_{lesson_id}_{TopicMastery.MASTERED.value}")],
        [InlineKeyboardButton("⬅️ Назад к уроку", callback_data=f"tutor_lesson_details_{lesson_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Клавиатуры для генерации отчета ---
def tutor_select_student_for_report_keyboard(students):
    """Клавиатура для выбора ученика для отчета."""
    keyboard = []
    for student in students:
        keyboard.append([InlineKeyboardButton(student.full_name, callback_data=f"report_select_student_{student.id}")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_report")])
    return InlineKeyboardMarkup(keyboard)

def tutor_select_month_for_report_keyboard(student_id):
    """Клавиатура для выбора месяца для отчета."""
    # Здесь можно добавить логику для генерации кнопок с последними месяцами
    # Для простоты пока сделаем так
    keyboard = [
        [
            InlineKeyboardButton("Текущий месяц", callback_data=f"report_select_month_{student_id}_0"),
            InlineKeyboardButton("Прошлый месяц", callback_data=f"report_select_month_{student_id}_1")
        ],
        [InlineKeyboardButton("2 месяца назад", callback_data=f"report_select_month_{student_id}_2")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_report")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Клавиатуры для библиотеки ---
def tutor_library_management_keyboard(materials):
    """Клавиатура для управления библиотекой репетитора (просмотр, добавление, удаление)."""
    keyboard = []
    # Список материалов
    for material in materials:
        # Ограничиваем длину текста на кнопке
        title = (material.title[:30] + '..') if len(material.title) > 30 else material.title
        keyboard.append([InlineKeyboardButton(f"📖 {title}", callback_data=f"tutor_view_material_{material.id}")])
    
    # Кнопки управления
    keyboard.append([
        InlineKeyboardButton("➕ Добавить", callback_data="tutor_add_material"),
        InlineKeyboardButton("🗑️ Удалить", callback_data="tutor_delete_material_start")
    ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)

def tutor_select_material_to_delete_keyboard(materials):
    """Клавиатура для выбора материала для удаления."""
    keyboard = []
    for material in materials:
        keyboard.append([InlineKeyboardButton(material.title, callback_data=f"tutor_delete_material_{material.id}")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="tutor_manage_library")])
    return InlineKeyboardMarkup(keyboard)

def student_materials_list_keyboard(materials):
    """Клавиатура со списком материалов для ученика."""
    keyboard = []
    for material in materials:
        keyboard.append([InlineKeyboardButton(material.title, callback_data=f"student_view_material_{material.id}")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

# --- Клавиатуры для рассылки ---
def broadcast_confirm_keyboard():
    """Клавиатура для подтверждения рассылки."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Отправить", callback_data="broadcast_send"),
            InlineKeyboardButton("❌ Отмена", callback_data="broadcast_cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)