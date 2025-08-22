# -*- coding: utf-8 -*-
"""
Модуль обработчиков для Telegram бота репетитора.
Разделен на микросервисы по ролям пользователей.
"""

# Общие обработчики и утилиты
from .common import (
    start, handle_access_code, show_main_menu, cancel_conversation,
    check_user_role, generate_access_code
)

# Обработчики для учеников
from .student import (
    show_homework_menu, show_my_progress, show_schedule, show_materials_library,
    show_lesson_history, show_student_achievements, show_payment_and_attendance,
    student_submit_homework_start, student_get_homework_submission, student_view_homework,
    student_view_lesson_details, student_library_by_grade, SUBMIT_HOMEWORK_FILE
)

# Обработчики для репетитора
from .tutor import (
    # Управление учениками
    tutor_add_student_start, tutor_get_student_name, tutor_get_parent_code,
    tutor_edit_name_start, tutor_get_new_name, tutor_add_parent_start, tutor_get_parent_name,
    tutor_select_parent_type, tutor_select_existing_parent,
    tutor_delete_student_start, tutor_delete_student_confirm, show_student_list, show_student_profile,
    
    # Управление уроками  
    tutor_add_lesson_start, tutor_get_lesson_topic, tutor_get_lesson_date, tutor_get_lesson_skills,
    tutor_edit_lesson_start, tutor_edit_lesson_get_status, tutor_edit_lesson_get_comment,
    tutor_edit_attendance_status, tutor_edit_mastery_status, tutor_set_attendance_in_conversation,
    tutor_mark_lesson_attended, tutor_set_lesson_attendance,
    
    # Управление ДЗ
    tutor_add_hw_start, tutor_get_hw_description, tutor_get_hw_deadline, 
    tutor_get_hw_link, tutor_get_hw_photos, tutor_check_homework, tutor_set_homework_status,
    
    # Управление оплатами
    tutor_add_payment_start, tutor_get_payment_amount,
    
    # Отчеты и аналитика
    show_tutor_stats, show_tutor_dashboard, report_start, report_select_student, 
    report_select_month_and_generate, report_cancel,
    
    # Библиотека материалов
    tutor_manage_library, tutor_add_material_start, tutor_add_material_with_grade, tutor_get_material_grade, tutor_get_material_title,
    tutor_get_material_link, tutor_get_material_description, tutor_library_by_grade,
    
    # Рассылка
    broadcast_start, broadcast_get_message, broadcast_cancel, broadcast_send,
    
    # Состояния ConversationHandler
    ADD_STUDENT_NAME, ADD_PARENT_CODE, ADD_PARENT_NAME, ADD_PAYMENT_AMOUNT,
    ADD_LESSON_TOPIC, ADD_LESSON_DATE, ADD_LESSON_SKILLS, RESCHEDULE_LESSON_DATE,
    EDIT_STUDENT_NAME, EDIT_LESSON_STATUS, EDIT_LESSON_COMMENT,
    ADD_HW_DESC, ADD_HW_DEADLINE, ADD_HW_LINK, ADD_HW_PHOTOS,
    SELECT_STUDENT_FOR_REPORT, SELECT_MONTH_FOR_REPORT,
    ADD_MATERIAL_GRADE, ADD_MATERIAL_TITLE, ADD_MATERIAL_LINK, ADD_MATERIAL_DESC,
    BROADCAST_MESSAGE, BROADCAST_CONFIRM, SELECT_PARENT_TYPE, SELECT_EXISTING_PARENT
)

# Обработчики для родителей
from .parent import (
    show_parent_dashboard, show_child_menu, show_child_progress,
    show_child_schedule, show_child_payments, parent_generate_chart
)

# Общие обработчики (чат, календарь)
from .shared import (
    chat_with_tutor_start, forward_message_to_tutor, handle_tutor_reply,
    handle_calendar_selection, button_handler, CHAT_WITH_TUTOR
)

# Экспорт всех необходимых функций
__all__ = [
    # Common
    'start', 'handle_access_code', 'show_main_menu', 'cancel_conversation',
    'check_user_role', 'generate_access_code',
    
    # Student
    'show_homework_menu', 'show_my_progress', 'show_schedule', 'show_materials_library',
    'show_lesson_history', 'show_student_achievements', 'show_payment_and_attendance', 
    'student_submit_homework_start', 'student_get_homework_submission', 'student_view_homework',
    'student_view_lesson_details', 'student_library_by_grade', 'SUBMIT_HOMEWORK_FILE',
    
    # Tutor
    'tutor_add_student_start', 'tutor_get_student_name', 'tutor_get_parent_code',
    'tutor_edit_name_start', 'tutor_get_new_name', 'tutor_add_parent_start', 'tutor_get_parent_name',
    'tutor_select_parent_type', 'tutor_select_existing_parent',
    'tutor_delete_student_start', 'tutor_delete_student_confirm', 'show_student_list', 'show_student_profile',
    'tutor_add_lesson_start', 'tutor_get_lesson_topic', 'tutor_get_lesson_date', 'tutor_get_lesson_skills',
    'tutor_edit_lesson_start', 'tutor_edit_lesson_get_status', 'tutor_edit_lesson_get_comment',
    'tutor_edit_attendance_status', 'tutor_edit_mastery_status', 'tutor_set_attendance_in_conversation',
    'tutor_mark_lesson_attended', 'tutor_set_lesson_attendance',
    'tutor_add_hw_start', 'tutor_get_hw_description', 'tutor_get_hw_deadline', 
    'tutor_get_hw_link', 'tutor_get_hw_photos', 'tutor_check_homework', 'tutor_set_homework_status',
    'tutor_add_payment_start', 'tutor_get_payment_amount',
    'show_tutor_stats', 'show_tutor_dashboard', 'report_start', 'report_select_student', 
    'report_select_month_and_generate', 'report_cancel',
    'tutor_manage_library', 'tutor_add_material_start', 'tutor_add_material_with_grade', 'tutor_get_material_grade', 'tutor_get_material_title',
    'tutor_get_material_link', 'tutor_get_material_description', 'tutor_library_by_grade',
    'broadcast_start', 'broadcast_get_message', 'broadcast_cancel', 'broadcast_send',
    
    # Parent
    'show_parent_dashboard', 'show_child_menu', 'show_child_progress',
    'show_child_schedule', 'show_child_payments', 'parent_generate_chart',
    
    # Shared
    'chat_with_tutor_start', 'forward_message_to_tutor', 'handle_tutor_reply',
    'handle_calendar_selection', 'button_handler',
    
    # States
    'ADD_STUDENT_NAME', 'ADD_PARENT_CODE', 'ADD_PARENT_NAME', 'ADD_PAYMENT_AMOUNT',
    'ADD_LESSON_TOPIC', 'ADD_LESSON_DATE', 'ADD_LESSON_SKILLS', 'RESCHEDULE_LESSON_DATE',
    'EDIT_STUDENT_NAME', 'EDIT_LESSON_STATUS', 'EDIT_LESSON_COMMENT',
    'ADD_HW_DESC', 'ADD_HW_DEADLINE', 'ADD_HW_LINK', 'ADD_HW_PHOTOS',
    'SELECT_STUDENT_FOR_REPORT', 'SELECT_MONTH_FOR_REPORT', 
    'ADD_MATERIAL_GRADE', 'ADD_MATERIAL_TITLE', 'ADD_MATERIAL_LINK', 'ADD_MATERIAL_DESC',
    'BROADCAST_MESSAGE', 'BROADCAST_CONFIRM', 'SELECT_PARENT_TYPE', 'SELECT_EXISTING_PARENT', 
    'CHAT_WITH_TUTOR', 'SUBMIT_HOMEWORK_FILE'
]