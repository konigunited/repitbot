# -*- coding: utf-8 -*-
"""
Payment Handlers for Telegram Bot
Handlers for payment-related functionality using Payment microservice
"""

import logging
from datetime import datetime
from decimal import Decimal
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from telegram.helpers import escape_markdown

from ..services.payment_service_client import PaymentServiceClient
from ..services.user_service_client import UserServiceClient

logger = logging.getLogger(__name__)

# Initialize service clients
payment_service = PaymentServiceClient()
user_service = UserServiceClient()

# Conversation states
ADD_PAYMENT_AMOUNT = 100
SELECT_PAYMENT_METHOD = 101
CONFIRM_PAYMENT = 102


async def start_add_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start payment addition process"""
    query = update.callback_query
    await query.answer()
    
    try:
        student_id = int(query.data.split("_")[-1])
        context.user_data['payment_student_id'] = student_id
        
        # Get student info
        student = await user_service.get_user(student_id)
        if not student:
            await query.edit_message_text("❌ Студент не найден")
            return ConversationHandler.END
        
        context.user_data['student_name'] = student.full_name
        
        await query.edit_message_text(
            f"💳 *Добавление оплаты для {escape_markdown(student.full_name, 2)}*\n\n"
            f"Введите количество оплаченных уроков:",
            parse_mode='MarkdownV2'
        )
        
        return ADD_PAYMENT_AMOUNT
        
    except Exception as e:
        logger.error(f"Error starting payment addition: {e}")
        await query.edit_message_text("❌ Произошла ошибка")
        return ConversationHandler.END


async def get_payment_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get payment amount from user"""
    try:
        lessons_count = int(update.message.text)
        
        if lessons_count <= 0:
            await update.message.reply_text("❌ Количество уроков должно быть положительным числом")
            return ADD_PAYMENT_AMOUNT
        
        if lessons_count > 100:
            await update.message.reply_text("❌ Максимальное количество уроков: 100")
            return ADD_PAYMENT_AMOUNT
        
        context.user_data['lessons_count'] = lessons_count
        
        # Show payment method selection
        keyboard = [
            [InlineKeyboardButton("💵 Наличные", callback_data="payment_method_cash")],
            [InlineKeyboardButton("💳 Карта", callback_data="payment_method_card")],
            [InlineKeyboardButton("🏦 Перевод", callback_data="payment_method_transfer")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_payment")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        student_name = context.user_data.get('student_name', 'студент')
        
        await update.message.reply_text(
            f"💳 *Оплата {lessons_count} уроков для {escape_markdown(student_name, 2)}*\n\n"
            f"Выберите способ оплаты:",
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
        
        return SELECT_PAYMENT_METHOD
        
    except ValueError:
        await update.message.reply_text("❌ Введите корректное число")
        return ADD_PAYMENT_AMOUNT
    except Exception as e:
        logger.error(f"Error getting payment amount: {e}")
        await update.message.reply_text("❌ Произошла ошибка")
        return ConversationHandler.END


async def select_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Select payment method"""
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data == "cancel_payment":
            await query.edit_message_text("❌ Добавление оплаты отменено")
            return ConversationHandler.END
        
        # Parse payment method
        method_map = {
            "payment_method_cash": ("cash", "💵 Наличные"),
            "payment_method_card": ("card", "💳 Карта"),
            "payment_method_transfer": ("transfer", "🏦 Перевод")
        }
        
        if query.data not in method_map:
            await query.edit_message_text("❌ Неверный способ оплаты")
            return ConversationHandler.END
        
        method_code, method_name = method_map[query.data]
        context.user_data['payment_method'] = method_code
        context.user_data['payment_method_name'] = method_name
        
        # Show confirmation
        student_name = context.user_data.get('student_name', 'студент')
        lessons_count = context.user_data.get('lessons_count')
        price_per_lesson = 1000.0  # Default price, should be configurable
        total_amount = lessons_count * price_per_lesson
        
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_payment")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_payment")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"💳 *Подтверждение оплаты*\n\n"
            f"👤 Студент: {escape_markdown(student_name, 2)}\n"
            f"📚 Количество уроков: {lessons_count}\n"
            f"💰 Стоимость за урок: {price_per_lesson:,.0f} ₽\n"
            f"💵 Общая сумма: {total_amount:,.0f} ₽\n"
            f"💳 Способ оплаты: {method_name}\n\n"
            f"Подтвердить оплату?",
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
        
        return CONFIRM_PAYMENT
        
    except Exception as e:
        logger.error(f"Error selecting payment method: {e}")
        await query.edit_message_text("❌ Произошла ошибка")
        return ConversationHandler.END


async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and process payment"""
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data == "cancel_payment":
            await query.edit_message_text("❌ Добавление оплаты отменено")
            return ConversationHandler.END
        
        if query.data != "confirm_payment":
            await query.edit_message_text("❌ Неверное действие")
            return ConversationHandler.END
        
        # Get payment data
        student_id = context.user_data.get('payment_student_id')
        student_name = context.user_data.get('student_name')
        lessons_count = context.user_data.get('lessons_count')
        payment_method = context.user_data.get('payment_method')
        price_per_lesson = 1000.0  # Should be configurable
        
        # Process payment via microservice
        payment = await payment_service.quick_payment(
            student_id=student_id,
            lessons_count=lessons_count,
            price_per_lesson=price_per_lesson,
            payment_method=payment_method,
            description=f"Оплата {lessons_count} уроков"
        )
        
        if payment:
            # Get updated balance
            balance = await payment_service.get_student_balance(student_id)
            current_balance = balance.current_balance if balance else 0
            
            await query.edit_message_text(
                f"✅ *Оплата успешно добавлена\\!*\n\n"
                f"👤 Студент: {escape_markdown(student_name, 2)}\n"
                f"📚 Оплачено уроков: {lessons_count}\n"
                f"💰 Сумма: {payment.amount:,.0f} ₽\n"
                f"💳 Способ: {context.user_data.get('payment_method_name')}\n"
                f"📊 Текущий баланс: {current_balance} уроков\n\n"
                f"🆔 ID платежа: `{payment.id}`",
                parse_mode='MarkdownV2'
            )
        else:
            await query.edit_message_text("❌ Не удалось обработать оплату. Попробуйте позже.")
        
        # Clear user data
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error confirming payment: {e}")
        await query.edit_message_text("❌ Произошла ошибка при обработке оплаты")
        context.user_data.clear()
        return ConversationHandler.END


async def show_student_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show student balance"""
    query = update.callback_query
    await query.answer()
    
    try:
        student_id = int(query.data.split("_")[-1])
        
        # Get student info
        student = await user_service.get_user(student_id)
        if not student:
            await query.edit_message_text("❌ Студент не найден")
            return
        
        # Get balance details
        balance = await payment_service.get_student_balance(student_id)
        
        if balance:
            balance_text = (
                f"📊 *Баланс студента {escape_markdown(student.full_name, 2)}*\n\n"
                f"💰 Текущий баланс: *{balance.current_balance} уроков*\n"
                f"📚 Всего оплачено: {balance.total_lessons_paid} уроков\n"
                f"✅ Проведено: {balance.lessons_consumed} уроков\n"
                f"💵 Сумма оплат: {balance.total_amount_paid:,.0f} ₽\n"
                f"💸 Потрачено: {balance.total_amount_spent:,.0f} ₽\n"
            )
            
            if balance.last_payment_date:
                balance_text += f"📅 Последняя оплата: {balance.last_payment_date.strftime('%d.%m.%Y')}\n"
            
            if balance.last_lesson_date:
                balance_text += f"🎓 Последний урок: {balance.last_lesson_date.strftime('%d.%m.%Y')}\n"
        else:
            balance_text = (
                f"📊 *Баланс студента {escape_markdown(student.full_name, 2)}*\n\n"
                f"💰 Текущий баланс: *0 уроков*\n"
                f"Нет данных об оплатах"
            )
        
        # Add action buttons
        keyboard = [
            [InlineKeyboardButton("💳 Добавить оплату", callback_data=f"add_payment_{student_id}")],
            [InlineKeyboardButton("📜 История платежей", callback_data=f"payment_history_{student_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"student_profile_{student_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            balance_text,
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
        
    except Exception as e:
        logger.error(f"Error showing student balance: {e}")
        await query.edit_message_text("❌ Произошла ошибка")


async def show_payment_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show payment history for student"""
    query = update.callback_query
    await query.answer()
    
    try:
        student_id = int(query.data.split("_")[-1])
        
        # Get student info
        student = await user_service.get_user(student_id)
        if not student:
            await query.edit_message_text("❌ Студент не найден")
            return
        
        # Get payment history
        payments = await payment_service.get_student_payments(student_id, per_page=10)
        
        if payments:
            history_text = f"💳 *История платежей {escape_markdown(student.full_name, 2)}*\n\n"
            
            for payment in payments[:10]:  # Show last 10 payments
                status_icon = "✅" if payment.status == "completed" else "⏳"
                method_icon = {"cash": "💵", "card": "💳", "transfer": "🏦"}.get(payment.payment_method, "💰")
                
                history_text += (
                    f"{status_icon} *{payment.payment_date.strftime('%d\\.%m\\.%Y')}*\n"
                    f"   {method_icon} {payment.lessons_paid} уроков \\- {payment.amount:,.0f} ₽\n"
                )
                if payment.description:
                    history_text += f"   📝 {escape_markdown(payment.description, 2)}\n"
                history_text += "\n"
            
            if len(payments) > 10:
                history_text += f"... и еще {len(payments) - 10} платежей\n"
        else:
            history_text = (
                f"💳 *История платежей {escape_markdown(student.full_name, 2)}*\n\n"
                f"Платежей пока нет"
            )
        
        # Add navigation buttons
        keyboard = [
            [InlineKeyboardButton("💰 Баланс", callback_data=f"student_balance_{student_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"student_profile_{student_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            history_text,
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
        
    except Exception as e:
        logger.error(f"Error showing payment history: {e}")
        await query.edit_message_text("❌ Произошла ошибка")


async def cancel_payment_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel payment conversation"""
    context.user_data.clear()
    await update.message.reply_text("❌ Добавление оплаты отменено")
    return ConversationHandler.END


# Export handlers for use in main bot file
payment_conversation_handler = ConversationHandler(
    entry_points=[],  # Will be set in main bot file
    states={
        ADD_PAYMENT_AMOUNT: [
            lambda update, context: update.message and update.message.text,
            get_payment_amount
        ],
        SELECT_PAYMENT_METHOD: [
            lambda update, context: update.callback_query and update.callback_query.data.startswith("payment_method_"),
            select_payment_method
        ],
        CONFIRM_PAYMENT: [
            lambda update, context: update.callback_query and update.callback_query.data in ["confirm_payment", "cancel_payment"],
            confirm_payment
        ]
    },
    fallbacks=[
        lambda update, context: update.message and update.message.text == "/cancel",
        cancel_payment_conversation
    ],
    conversation_timeout=300  # 5 minutes timeout
)