# -*- coding: utf-8 -*-
"""
Исправленные функции для родителей - для замены в parent.py
"""

# Эти функции нужно добавить в parent.py взамен дублирующихся

async def show_child_progress(update, context):
    """Показывает подробный прогресс ребенка"""
    parent = check_parent_access(update)
    if not parent:
        await update.callback_query.answer("❌ Доступ запрещен")
        return
    
    student_id = int(update.callback_query.data.split("_")[-1])
    
    log_user_action(parent.telegram_id, "child_progress_view", f"Просмотр прогресса ребенка ID:{student_id}")
    
    db = SessionLocal()
    try:
        student = db.query(User).filter(
            User.id == student_id,
            User.parent_id == parent.id
        ).first()
        
        if not student:
            await update.callback_query.answer("❌ Ребенок не найден")
            return
        
        # Статистика за месяц
        month_start = datetime.now().replace(day=1)
        monthly_lessons = db.query(Lesson).filter(
            Lesson.student_id == student.id,
            Lesson.date >= month_start,
            Lesson.attendance_status == AttendanceStatus.ATTENDED
        ).count()
        
        total_monthly = db.query(Lesson).filter(
            Lesson.student_id == student.id,
            Lesson.date >= month_start
        ).count()
        
        # ДЗ за месяц
        monthly_hw = db.query(Homework).join(Lesson).filter(
            Lesson.student_id == student.id,
            Homework.created_at >= month_start
        ).count()
        
        completed_hw = db.query(Homework).join(Lesson).filter(
            Lesson.student_id == student.id,
            Homework.created_at >= month_start,
            Homework.status == HomeworkStatus.CHECKED
        ).count()
        
        # Общая статистика
        total_lessons = db.query(Lesson).filter(
            Lesson.student_id == student.id,
            Lesson.attendance_status == AttendanceStatus.ATTENDED
        ).count()
        
        balance = get_student_balance(student.id)
        
        text = f"📊 **Прогресс {student.full_name}**\n\n"
        text += f"🎯 **Общие показатели:**\n"
        text += f"   Баллы: {student.points}\n"
        text += f"   Серия: {student.streak_days} дней\n"
        text += f"   Всего уроков: {total_lessons}\n"
        text += f"   Баланс: {balance} уроков\n\n"
        
        text += f"📅 **За текущий месяц:**\n"
        text += f"   Посещено: {monthly_lessons} из {total_monthly}\n"
        
        if total_monthly > 0:
            attendance_rate = (monthly_lessons / total_monthly) * 100
            text += f"   Посещаемость: {attendance_rate:.1f}%\n"
        
        text += f"   ДЗ выполнено: {completed_hw} из {monthly_hw}\n"
        
        if monthly_hw > 0:
            hw_rate = (completed_hw / monthly_hw) * 100
            text += f"   Выполнение ДЗ: {hw_rate:.1f}%\n"
        
        keyboard = [
            [InlineKeyboardButton("📈 График прогресса", callback_data=f"parent_chart_{student.id}")],
            [InlineKeyboardButton("🔙 К ребенку", callback_data=f"parent_child_{student.id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        await update.callback_query.answer()
    
    finally:
        db.close()

print("Файл создан для копирования функций")