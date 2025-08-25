# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from telegram.ext import Application
from telegram.error import Forbidden
from .database import SessionLocal, Lesson, User, UserRole, Payment, get_student_balance, Homework, HomeworkStatus
from sqlalchemy import func

# --- Константы ---
LOW_BALANCE_THRESHOLD = 1 # Напоминание только когда остается 1 урок

async def send_reminders(application: Application):
    """Отправляет напоминания о предстоящих уроках за 24 часа."""
    db = SessionLocal()
    try:
        now = datetime.now()
        reminder_time_start = now + timedelta(hours=23, minutes=55)
        reminder_time_end = now + timedelta(hours=24, minutes=5)

        upcoming_lessons = db.query(Lesson).filter(
            Lesson.date >= reminder_time_start,
            Lesson.date <= reminder_time_end,
            Lesson.student.has(User.telegram_id.isnot(None)) # Выбираем только студентов с telegram_id
        ).all()

        for lesson in upcoming_lessons:
            student = lesson.student
            try:
                await application.bot.send_message(
                    chat_id=student.telegram_id,
                    text=f"🔔 *Напоминание: у вас завтра урок!*\n\n"
                         f"📚 *Тема:* {lesson.topic or 'Не указана'}\n"
                         f"🗓️ *Дата:* {lesson.date.strftime('%d.%m.%Y в %H:%M')}\n\n"
                         "Пожалуйста, подготовьтесь и не опаздывайте.",
                    parse_mode='Markdown'
                )
            except Forbidden:
                print(f"Не удалось отправить напоминание студенту {student.full_name} (ID: {student.id}): бот заблокирован.")
            except Exception as e:
                print(f"Не удалось отправить напоминание студенту {student.full_name} (ID: {student.id}): {e}")
    finally:
        db.close()


async def send_payment_reminders(application: Application):
    """
    Отправляет напоминания о низком балансе занятий.
    Отправляет родителю, если он есть, иначе - студенту.
    """
    db = SessionLocal()
    try:
        # Выбираем всех студентов, чтобы проверить их баланс
        students = db.query(User).filter(User.role == UserRole.STUDENT).all()

        for student in students:
            balance = get_student_balance(student.id)

            if balance == LOW_BALANCE_THRESHOLD:
                # Определяем, кому отправлять сообщение
                target_user = student.parent if student.parent and student.parent.telegram_id else student
                
                if not target_user.telegram_id:
                    continue # Пропускаем, если ни у родителя, ни у студента нет telegram_id

                message = (
                    f"💰 *Напоминание о балансе*\n\n"
                    f"У ученика *{student.full_name}* остался *{balance}* оплаченный урок.\n\n"
                    "Пожалуйста, не забудьте пополнить баланс для продолжения обучения."
                )
                
                try:
                    await application.bot.send_message(
                        chat_id=target_user.telegram_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                except Forbidden:
                    print(f"Не удалось отправить напоминание о балансе для {student.full_name} (ID: {student.id}) пользователю {target_user.full_name} (ID: {target_user.id}): бот заблокирован.")
                except Exception as e:
                    print(f"Не удалось отправить напоминание о балансе для {student.full_name} (ID: {student.id}): {e}")
    finally:
        db.close()

async def send_homework_deadline_reminders(application: Application):
    """Отправляет напоминания о приближающемся дедлайне ДЗ."""
    db = SessionLocal()
    try:
        now = datetime.now()
        reminder_time_start = now + timedelta(hours=23, minutes=55)
        reminder_time_end = now + timedelta(hours=24, minutes=5)

        # Ищем ДЗ в статусе "В работе", у которых дедлайн наступает в ближайшие 24 часа
        pending_homeworks = db.query(Homework).join(Lesson).join(User).filter(
            Homework.status == HomeworkStatus.PENDING,
            Homework.deadline >= reminder_time_start,
            Homework.deadline <= reminder_time_end,
            User.telegram_id.isnot(None)
        ).all()

        for hw in pending_homeworks:
            student = hw.lesson.student
            try:
                await application.bot.send_message(
                    chat_id=student.telegram_id,
                    text=f"🔥 *Напоминание: дедлайн близко!*\n\n"
                         f"У вас осталось 24 часа, чтобы сдать домашнее задание по теме:\n"
                         f"*{hw.lesson.topic or 'Без темы'}*\n\n"
                         f"*{hw.description}*\n\n"
                         "Не забудьте отправить его на проверку!",
                    parse_mode='Markdown'
                )
            except Forbidden:
                print(f"Не удалось отправить напоминание о ДЗ студенту {student.full_name} (ID: {student.id}): бот заблокирован.")
            except Exception as e:
                print(f"Не удалось отправить напоминание о ДЗ студенту {student.full_name} (ID: {student.id}): {e}")
    finally:
        db.close()