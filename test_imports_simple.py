#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

print("Testing imports...")

try:
    print("1. Testing keyboards...")
    from src.keyboards import TUTOR_BUTTONS, STUDENT_BUTTONS
    print("   OK - Keyboards loaded")
    
    print("2. Testing database...")
    from src.database import engine, Base
    print("   OK - Database loaded")
    
    print("3. Testing common handlers...")
    from src.handlers.common import start, handle_access_code
    print("   OK - Common handlers loaded")
    
    print("4. Testing student handlers...")
    from src.handlers.student import show_homework_menu
    print("   OK - Student handlers loaded")
    
    print("5. Testing tutor handlers...")
    from src.handlers.tutor import tutor_add_student_start
    print("   OK - Tutor handlers loaded")
    
    print("6. Testing parent handlers...")
    from src.handlers.parent import show_parent_dashboard  
    print("   OK - Parent handlers loaded")
    
    print("7. Testing shared handlers...")
    from src.handlers.shared import button_handler
    print("   OK - Shared handlers loaded")
    
    print("8. Testing full handlers import...")
    from src.handlers import start, ADD_STUDENT_NAME
    print("   OK - Full handlers import works")
    
    print("\nAll imports successful!")
    
except ImportError as e:
    print(f"Import error: {e}")
    import traceback
    traceback.print_exc()
    
except Exception as e:
    print(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()