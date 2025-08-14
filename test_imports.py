#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест импортов для проверки корректности рефакторинга
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

print("🔍 Тестируем импорты после рефакторинга...")

try:
    print("✓ Тестируем src.keyboards...")
    from src.keyboards import TUTOR_BUTTONS, STUDENT_BUTTONS
    print(f"  - TUTOR_BUTTONS: {len(TUTOR_BUTTONS)} кнопок")
    print(f"  - STUDENT_BUTTONS: {len(STUDENT_BUTTONS)} кнопок")
    
    print("\n✓ Тестируем src.database...")
    from src.database import engine, Base
    print("  - Database подключена успешно")
    
    print("\n✓ Тестируем src.handlers.common...")
    from src.handlers.common import start, handle_access_code, show_main_menu
    print("  - Общие обработчики загружены")
    
    print("\n✓ Тестируем src.handlers.student...")
    from src.handlers.student import show_homework_menu, show_my_progress
    print("  - Обработчики ученика загружены")
    
    print("\n✓ Тестируем src.handlers.tutor...")
    from src.handlers.tutor import tutor_add_student_start, show_student_list
    print("  - Обработчики репетитора загружены")
    
    print("\n✓ Тестируем src.handlers.parent...")
    from src.handlers.parent import show_parent_dashboard
    print("  - Обработчики родителя загружены")
    
    print("\n✓ Тестируем src.handlers.shared...")
    from src.handlers.shared import chat_with_tutor_start, button_handler
    print("  - Общие обработчики загружены")
    
    print("\n✓ Тестируем полный импорт из src.handlers...")
    from src.handlers import (
        start, handle_access_code, show_main_menu,
        show_homework_menu, tutor_add_student_start,
        ADD_STUDENT_NAME, CHAT_WITH_TUTOR
    )
    print("  - Все основные функции импортированы успешно")
    
    print("\n🎉 Все импорты работают корректно!")
    
except ImportError as e:
    print(f"\n❌ Ошибка импорта: {e}")
    print("📝 Детали ошибки:")
    import traceback
    traceback.print_exc()
    
except Exception as e:
    print(f"\n❌ Неожиданная ошибка: {e}")
    print("📝 Детали ошибки:")
    import traceback
    traceback.print_exc()