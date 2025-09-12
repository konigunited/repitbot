# -*- coding: utf-8 -*-
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from .database import TopicMastery, HomeworkStatus, AttendanceStatus, LessonStatus

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

# --- Клавиатуры для ученика ---
STUDENT_BUTTONS = {
    "lessons_history": "📚 Мои уроки",
    "schedule": "🗓️ Расписание",
    "homework": "📝 Домашние задания",
    "progress": "📊 Мой прогресс",
    "library": "🗂️ Библиотека",
    "payment": "💰 Баланс уроков",
    "achievements": "🏆 Достижения",
    "chat": "💬 Связь с репетитором"
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
        [STUDENT_BUTTONS["lessons_history"], STUDENT_BUTTONS["schedule"]],
        [STUDENT_BUTTONS["homework"], STUDENT_BUTTONS["progress"]],
        [STUDENT_BUTTONS["payment"], STUDENT_BUTTONS["achievements"]],
        [STUDENT_BUTTONS["library"], STUDENT_BUTTONS["chat"]]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def student_inline_menu():
    """Создает inline-клавиатуру для дополнительных функций ученика."""
    keyboard = [
        [InlineKeyboardButton("💰 Оплата и посещаемость", callback_data="payment_attendance")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="student_settings")],
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
    
    # Добавляем кнопку для добавления нового ученика
    keyboard.append([InlineKeyboardButton("➕ Добавить ученика", callback_data="add_student")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def tutor_student_profile_keyboard(student_id, has_parent=False, has_second_parent=False):
    keyboard = [
        [InlineKeyboardButton("📚 Уроки ученика", callback_data=f"tutor_lessons_list_{student_id}")],
        [InlineKeyboardButton("📈 Аналитика прогресса", callback_data=f"tutor_analytics_{student_id}")],
        [
            InlineKeyboardButton("➕ Добавить урок", callback_data=f"tutor_add_lesson_{student_id}"),
            InlineKeyboardButton("💰 Добавить оплату", callback_data=f"tutor_add_payment_{student_id}")
        ],
        [InlineKeyboardButton("📅 Настроить расписание", callback_data=f"tutor_schedule_setup_{student_id}")],
        [InlineKeyboardButton("✏️ Редактировать ФИО", callback_data=f"tutor_edit_name_{student_id}")],
    ]
    
    # Динамически добавляем кнопки родителей
    parent_buttons = []
    if not has_parent:
        parent_buttons.append(InlineKeyboardButton("👨‍👩‍👧‍👦 Добавить родителя", callback_data=f"tutor_add_parent_{student_id}"))
    elif not has_second_parent:
        parent_buttons.append(InlineKeyboardButton("👨‍👩‍👧‍👦 Добавить 2-го родителя", callback_data=f"tutor_add_second_parent_{student_id}"))
    else:
        # Есть оба родителя - добавляем кнопки управления
        parent_buttons.append(InlineKeyboardButton("✏️ Заменить 2-го родителя", callback_data=f"tutor_replace_second_parent_{student_id}"))
        parent_buttons.append(InlineKeyboardButton("❌ Удалить 2-го родителя", callback_data=f"tutor_remove_second_parent_{student_id}"))
    
    if parent_buttons:
        if len(parent_buttons) == 1:
            keyboard.append(parent_buttons)
        else:
            # Если 2 кнопки, размещаем их в одной строке
            keyboard.append(parent_buttons)
    
    keyboard.append([
        InlineKeyboardButton("❌ Удалить ученика", callback_data=f"tutor_delete_student_{student_id}"),
        InlineKeyboardButton("⬅️ К списку учеников", callback_data="tutor_student_list")
    ])
    
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
    keyboard = []
    
    # Кнопки посещаемости
    attendance_buttons = []
    if lesson.attendance_status != AttendanceStatus.ATTENDED:
        attendance_buttons.append(InlineKeyboardButton("✅ Проведен", callback_data=f"tutor_set_attendance_{lesson.id}_attended"))
    if lesson.attendance_status != AttendanceStatus.EXCUSED_ABSENCE:
        attendance_buttons.append(InlineKeyboardButton("Отмена (уваж.)", callback_data=f"tutor_confirm_cancel_{lesson.id}_excused_absence"))
    if lesson.attendance_status != AttendanceStatus.UNEXCUSED_ABSENCE:
        attendance_buttons.append(InlineKeyboardButton("Отмена (неуваж.)", callback_data=f"tutor_confirm_cancel_{lesson.id}_unexcused_absence"))
    if lesson.attendance_status != AttendanceStatus.RESCHEDULED:
        attendance_buttons.append(InlineKeyboardButton("📅 Перенести", callback_data=f"tutor_confirm_cancel_{lesson.id}_rescheduled"))
    
    # Добавляем кнопки посещаемости по две в ряд
    if len(attendance_buttons) > 0:
        if len(attendance_buttons) <= 2:
            keyboard.append(attendance_buttons)
        else:
            keyboard.append(attendance_buttons[:2])
            keyboard.append(attendance_buttons[2:])
    
    # Кнопки управления уроком
    management_row = [
        InlineKeyboardButton("✏️ Изменить статус", callback_data=f"tutor_edit_lesson_{lesson.id}"),
        InlineKeyboardButton("🗑️ Удалить урок", callback_data=f"tutor_delete_lesson_{lesson.id}")
    ]
    keyboard.append(management_row)
    
    # Если ДЗ есть, добавляем кнопку для его просмотра/проверки
    homework_row = []
    if lesson.homeworks:
        homework_row.append(InlineKeyboardButton("📝 Проверить ДЗ", callback_data=f"tutor_check_hw_{lesson.id}"))
    else:
        homework_row.append(InlineKeyboardButton("➕ Добавить ДЗ", callback_data=f"tutor_add_hw_{lesson.id}"))
    
    if homework_row:
        keyboard.append(homework_row)
    
    keyboard.append([InlineKeyboardButton("⬅️ К списку уроков", callback_data=f"tutor_lessons_list_{lesson.student_id}")])
    return InlineKeyboardMarkup(keyboard)

def tutor_delete_lesson_keyboard(lesson_id):
    """Клавиатура подтверждения удаления урока."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"tutor_confirm_delete_lesson_{lesson_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"tutor_lesson_details_{lesson_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def tutor_cancel_confirmation_keyboard(lesson_id, status):
    """Клавиатура подтверждения отмены урока с предупреждением о сдвиге тем."""
    status_names = {
        'excused_absence': 'уважительной причине',
        'unexcused_absence': 'неуважительной причине', 
        'rescheduled': 'переносе'
    }
    
    keyboard = [
        [InlineKeyboardButton(f"✅ Да, отменить по {status_names.get(status, status)}", 
                             callback_data=f"tutor_set_attendance_{lesson_id}_{status}")],
        [InlineKeyboardButton("❌ Нет, вернуться к уроку", 
                             callback_data=f"tutor_lesson_details_{lesson_id}")]
    ]
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
    """Клавиатура для выбора типа статуса (посещаемость, проведение или усвоение)."""
    keyboard = [
        [InlineKeyboardButton("👥 Изменить посещаемость", callback_data=f"tutor_edit_attendance_{lesson_id}")],
        [InlineKeyboardButton("🎯 Изменить статус проведения", callback_data=f"tutor_edit_lesson_conduct_{lesson_id}")],
        [InlineKeyboardButton("📚 Изменить усвоение темы", callback_data=f"tutor_edit_mastery_{lesson_id}")],
        [InlineKeyboardButton("⬅️ Назад к уроку", callback_data=f"tutor_lesson_details_{lesson_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def tutor_edit_attendance_keyboard(lesson_id, current_status):
    """Клавиатура для изменения статуса посещаемости урока."""
    keyboard = []
    
    # Все возможные статусы посещаемости
    status_options = [
        (AttendanceStatus.ATTENDED, "✅ Проведен"),
        (AttendanceStatus.EXCUSED_ABSENCE, "🏥 Отмена (уваж. причина)"),
        (AttendanceStatus.UNEXCUSED_ABSENCE, "❌ Отмена (неуваж. причина)"),
        (AttendanceStatus.RESCHEDULED, "📅 Перенесен")
    ]
    
    for status, text in status_options:
        if status != current_status:
            keyboard.append([InlineKeyboardButton(text, callback_data=f"tutor_set_attendance_{lesson_id}_{status.value}")])
        else:
            # Показываем текущий статус с галочкой, но неактивный
            keyboard.append([InlineKeyboardButton(f"🔘 {text} (текущий)", callback_data=f"noop")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад к выбору статуса", callback_data=f"tutor_edit_lesson_{lesson_id}")])
    return InlineKeyboardMarkup(keyboard)

def tutor_edit_lesson_conduct_keyboard(lesson_id, current_status):
    """Клавиатура для изменения статуса проведения урока."""
    keyboard = []
    
    # Все возможные статусы проведения урока
    status_options = [
        (LessonStatus.NOT_CONDUCTED, "⚪️ Не проведен"),
        (LessonStatus.CONDUCTED, "✅ Проведен")
    ]
    
    for status, text in status_options:
        if status != current_status:
            keyboard.append([InlineKeyboardButton(text, callback_data=f"tutor_set_lesson_conduct_{lesson_id}_{status.value}")])
        else:
            # Показываем текущий статус с галочкой, но неактивный
            keyboard.append([InlineKeyboardButton(f"🔘 {text} (текущий)", callback_data=f"noop")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад к выбору статуса", callback_data=f"tutor_edit_lesson_{lesson_id}")])
    return InlineKeyboardMarkup(keyboard)

def tutor_edit_mastery_keyboard(lesson_id):
    """Клавиатура для изменения уровня усвоения темы."""
    keyboard = [
        [InlineKeyboardButton("⚪️ Не усвоено", callback_data=f"tutor_set_mastery_{lesson_id}_{TopicMastery.NOT_LEARNED.value}")],
        [InlineKeyboardButton("🟡 Усвоено", callback_data=f"tutor_set_mastery_{lesson_id}_{TopicMastery.LEARNED.value}")],
        [InlineKeyboardButton("🟢 Закреплено", callback_data=f"tutor_set_mastery_{lesson_id}_{TopicMastery.MASTERED.value}")],
        [InlineKeyboardButton("⬅️ Назад к выбору статуса", callback_data=f"tutor_edit_lesson_{lesson_id}")]
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
def library_grade_selection_keyboard(is_tutor=True):
    """Клавиатура для выбора класса в библиотеке."""
    keyboard = []
    # Добавляем кнопки для классов 2-9
    row = []
    for grade in range(2, 10):
        callback_prefix = "tutor_library_grade" if is_tutor else "student_library_grade"
        row.append(InlineKeyboardButton(f"{grade} кл", callback_data=f"{callback_prefix}_{grade}"))
        if len(row) == 4:  # 4 кнопки в ряду
            keyboard.append(row)
            row = []
    if row:  # Добавляем оставшиеся кнопки
        keyboard.append(row)
    
    # Кнопка "Все классы"
    callback_prefix = "tutor_library_grade" if is_tutor else "student_library_grade"
    keyboard.append([InlineKeyboardButton("📚 Все классы", callback_data=f"{callback_prefix}_all")])
    
    # Кнопка "Назад"
    keyboard.append([InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)

def grade_selection_keyboard_for_add_material():
    """Клавиатура для выбора класса при добавлении материала."""
    keyboard = []
    # Добавляем кнопки для классов 2-9
    row = []
    for grade in range(2, 10):
        row.append(InlineKeyboardButton(f"{grade} кл", callback_data=f"select_grade_{grade}"))
        if len(row) == 4:  # 4 кнопки в ряду
            keyboard.append(row)
            row = []
    if row:  # Добавляем оставшиеся кнопки
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

def tutor_library_management_keyboard(materials, grade=None):
    """Клавиатура для управления библиотекой репетитора (просмотр, добавление, удаление)."""
    keyboard = []
    # Список материалов с указанием класса
    for material in materials:
        # Ограничиваем длину текста на кнопке
        title = (material.title[:25] + '..') if len(material.title) > 25 else material.title
        grade_text = f"[{material.grade}кл]" if hasattr(material, 'grade') else ""
        keyboard.append([InlineKeyboardButton(f"📖 {grade_text} {title}", callback_data=f"tutor_view_material_{material.id}")])
    
    # Кнопки управления
    if grade and grade != "all":
        # Если мы в определенном классе, передаем его в callback
        add_callback = f"tutor_add_material_grade_{grade}"
    else:
        add_callback = "tutor_add_material"
        
    keyboard.append([
        InlineKeyboardButton("➕ Добавить", callback_data=add_callback),
        InlineKeyboardButton("🗑️ Удалить", callback_data="tutor_delete_material_start")
    ])
    
    # Кнопки навигации
    if grade:
        keyboard.append([InlineKeyboardButton("🔙 Выбор класса", callback_data="tutor_library")])
    else:
        keyboard.append([InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)

def tutor_select_material_to_delete_keyboard(materials):
    """Клавиатура для выбора материала для удаления."""
    keyboard = []
    for material in materials:
        keyboard.append([InlineKeyboardButton(material.title, callback_data=f"tutor_delete_material_{material.id}")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="tutor_manage_library")])
    return InlineKeyboardMarkup(keyboard)

def student_materials_list_keyboard(materials, grade=None):
    """Клавиатура со списком материалов для ученика."""
    keyboard = []
    for material in materials:
        # Ограничиваем длину текста на кнопке
        title = (material.title[:25] + '..') if len(material.title) > 25 else material.title
        grade_text = f"[{material.grade}кл]" if hasattr(material, 'grade') else ""
        keyboard.append([InlineKeyboardButton(f"📖 {grade_text} {title}", callback_data=f"student_view_material_{material.id}")])
    
    # Кнопки навигации
    if grade:
        keyboard.append([InlineKeyboardButton("🔙 Выбор класса", callback_data="student_library")])
    else:
        keyboard.append([InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def student_lesson_list_keyboard(lessons):
    """Клавиатура со списком уроков для ученика (только просмотр)."""
    keyboard = []
    for lesson in lessons:
        date_str = lesson.date.strftime('%d.%m.%y')
        
        # Эмодзи для статуса посещаемости
        attendance_emoji = {
            AttendanceStatus.ATTENDED: "✅",
            AttendanceStatus.EXCUSED_ABSENCE: "😷",
            AttendanceStatus.UNEXCUSED_ABSENCE: "❌",
            AttendanceStatus.RESCHEDULED: "📅"
        }.get(lesson.attendance_status, "✅")
        
        mastery_emoji = {
            TopicMastery.NOT_LEARNED: "⚪",
            TopicMastery.LEARNED: "🟡", 
            TopicMastery.MASTERED: "🟢"
        }.get(lesson.mastery_level, "⚪")
        
        button_text = f"{date_str} {attendance_emoji}{mastery_emoji} {lesson.topic}"
        if len(button_text) > 50:
            button_text = button_text[:47] + "..."
            
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"student_view_lesson_{lesson.id}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def student_lesson_details_keyboard(lesson):
    """Клавиатура для детального просмотра урока студентом."""
    keyboard = []
    
    # Если есть ДЗ к уроку
    if lesson.homeworks:
        for hw in lesson.homeworks:
            if hw.status == HomeworkStatus.PENDING:
                keyboard.append([InlineKeyboardButton("📝 Сдать ДЗ", callback_data=f"student_submit_hw_{hw.id}")])
            else:
                keyboard.append([InlineKeyboardButton("👁️ Посмотреть ДЗ", callback_data=f"student_view_hw_{hw.id}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ К урокам", callback_data="lessons_history")])
    return InlineKeyboardMarkup(keyboard)

# --- Клавиатуры для родителей ---
PARENT_BUTTONS = {
    "dashboard": "👨‍👩‍👧‍👦 Мои дети",
    "chat": "💬 Связь с репетитором"
}

def parent_main_keyboard():
    """Главная клавиатура для родителя."""
    keyboard = [
        [PARENT_BUTTONS["dashboard"]],
        [PARENT_BUTTONS["chat"]]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def parent_child_selection_keyboard(children):
    """Клавиатура для выбора ребенка."""
    keyboard = []
    for child in children:
        keyboard.append([InlineKeyboardButton(
            f"👨‍🎓 {child.full_name}", 
            callback_data=f"parent_child_{child.id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔄 Обновить", callback_data="parent_dashboard")])
    return InlineKeyboardMarkup(keyboard)

def parent_child_menu_keyboard(student_id):
    """Клавиатура для меню конкретного ребенка."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Прогресс", callback_data=f"parent_progress_{student_id}"),
            InlineKeyboardButton("📅 Расписание", callback_data=f"parent_schedule_{student_id}")
        ],
        [
            InlineKeyboardButton("💰 Оплаты", callback_data=f"parent_payments_{student_id}"),
            InlineKeyboardButton("💬 Чат с репетитором", callback_data="parent_chat_with_tutor")
        ],
        [
            InlineKeyboardButton("⬅️ Назад к выбору", callback_data="parent_dashboard"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]
    ]
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

# --- Клавиатуры для родителей ---
def parent_choice_keyboard():
    """Клавиатура выбора: создать нового или выбрать существующего родителя."""
    keyboard = [
        [InlineKeyboardButton("👤 Создать нового", callback_data="parent_create_new")],
        [InlineKeyboardButton("👥 Выбрать существующего", callback_data="parent_select_existing")],
        [InlineKeyboardButton("❌ Отмена", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def second_parent_choice_keyboard():
    """Клавиатура выбора для второго родителя: создать нового или выбрать существующего."""
    keyboard = [
        [InlineKeyboardButton("👤 Создать нового", callback_data="second_parent_create_new")],
        [InlineKeyboardButton("👥 Выбрать существующего", callback_data="second_parent_select_existing")],
        [InlineKeyboardButton("❌ Отмена", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def existing_parents_keyboard(parents):
    """Клавиатура со списком существующих родителей."""
    keyboard = []
    for parent in parents:
        # Показываем имя и количество детей
        try:
            children_count = len(parent.children) if hasattr(parent, 'children') and parent.children else 0
        except:
            children_count = 0
            
        text = f"{parent.full_name}"
        if children_count > 0:
            text += f" ({children_count} дет.)"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"parent_select_{parent.id}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="parent_back_to_choice")])
    return InlineKeyboardMarkup(keyboard)


def existing_second_parents_keyboard(parents, current_parent_id=None):
    """Клавиатура со списком существующих родителей для выбора второго родителя."""
    keyboard = []
    for parent in parents:
        # Исключаем уже привязанного основного родителя
        if current_parent_id and parent.id == current_parent_id:
            continue
            
        # Показываем имя и количество детей
        try:
            children_count = len(parent.children) if hasattr(parent, 'children') and parent.children else 0
        except:
            children_count = 0
            
        text = f"{parent.full_name}"
        if children_count > 0:
            text += f" ({children_count} дет.)"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"second_parent_select_{parent.id}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="second_parent_back_to_choice")])
    return InlineKeyboardMarkup(keyboard)

def tutor_schedule_setup_keyboard():
    """Клавиатура выбора дней недели для расписания."""
    weekdays = [
        ("Понедельник", "monday"),
        ("Вторник", "tuesday"), 
        ("Среда", "wednesday"),
        ("Четверг", "thursday"),
        ("Пятница", "friday"),
        ("Суббота", "saturday"),
        ("Воскресенье", "sunday")
    ]
    
    keyboard = []
    for day_name, day_key in weekdays:
        keyboard.append([InlineKeyboardButton(f"📅 {day_name}", callback_data=f"schedule_day_{day_key}")])
    
    keyboard.append([InlineKeyboardButton("✅ Завершить настройку", callback_data="schedule_finish")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="schedule_cancel")])
    return InlineKeyboardMarkup(keyboard)

def tutor_schedule_time_keyboard():
    """Клавиатура выбора времени урока."""
    times = [
        "09:00", "10:00", "11:00", "12:00", 
        "13:00", "14:00", "15:00", "16:00",
        "17:00", "18:00", "19:00", "20:00"
    ]
    
    keyboard = []
    row = []
    for i, time in enumerate(times):
        row.append(InlineKeyboardButton(time, callback_data=f"schedule_time_{time}"))
        if len(row) == 3 or i == len(times) - 1:
            keyboard.append(row)
            row = []
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="schedule_cancel")])
    return InlineKeyboardMarkup(keyboard)

def tutor_schedule_confirm_keyboard(student_id):
    """Клавиатура подтверждения создания расписания."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Создать уроки", callback_data=f"schedule_create_{student_id}"),
            InlineKeyboardButton("✏️ Изменить", callback_data=f"tutor_schedule_setup_{student_id}")
        ],
        [InlineKeyboardButton("❌ Отмена", callback_data=f"tutor_view_student_{student_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)