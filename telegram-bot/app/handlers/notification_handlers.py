"""
Notification Handlers for Telegram Bot
Handlers for notification preferences and settings
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from typing import Dict, Any
from datetime import datetime, timedelta

from ..services.notification_service_client import notification_client

logger = logging.getLogger(__name__)

# Conversation states
NOTIFICATION_MAIN_MENU, NOTIFICATION_PREFERENCES, NOTIFICATION_SCHEDULE = range(3)

class NotificationHandlers:
    """Handlers for notification functionality"""
    
    @staticmethod
    async def notification_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show main notification menu"""
        try:
            user = update.effective_user
            chat_id = update.effective_chat.id
            
            # Check if notification service is available
            if not await notification_client.health_check():
                await context.bot.send_message(
                    chat_id,
                    "🚫 Сервис уведомлений временно недоступен. Попробуйте позже."
                )
                return ConversationHandler.END
            
            keyboard = [
                [InlineKeyboardButton("⚙️ Настройки уведомлений", callback_data="notification_preferences")],
                [InlineKeyboardButton("📱 Telegram уведомления", callback_data="telegram_notifications")],
                [InlineKeyboardButton("📧 Email уведомления", callback_data="email_notifications")],
                [InlineKeyboardButton("🔔 Напоминания", callback_data="notification_reminders")],
                [InlineKeyboardButton("📝 История уведомлений", callback_data="notification_history")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message_text = f"🔔 **Уведомления и настройки**\n\n" \
                          f"Управляйте вашими уведомлениями и предпочтениями:"
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    message_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await context.bot.send_message(
                    chat_id,
                    message_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            
            return NOTIFICATION_MAIN_MENU
            
        except Exception as e:
            logger.error(f"Error in notification main menu: {str(e)}")
            await context.bot.send_message(
                update.effective_chat.id,
                "❌ Произошла ошибка при загрузке меню уведомлений."
            )
            return ConversationHandler.END

    @staticmethod
    async def handle_notification_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle notification menu option selection"""
        try:
            query = update.callback_query
            await query.answer()
            
            option = query.data
            user_id = update.effective_user.id
            
            if option == "notification_preferences":
                return await NotificationHandlers.show_preferences(update, context)
            elif option == "telegram_notifications":
                return await NotificationHandlers.manage_telegram_notifications(update, context)
            elif option == "email_notifications":
                return await NotificationHandlers.manage_email_notifications(update, context)
            elif option == "notification_reminders":
                return await NotificationHandlers.manage_reminders(update, context)
            elif option == "notification_history":
                return await NotificationHandlers.show_history(update, context)
            else:
                await query.edit_message_text("❌ Недоступная опция.")
                return ConversationHandler.END
                
        except Exception as e:
            logger.error(f"Error handling notification option: {str(e)}")
            await update.callback_query.edit_message_text(
                "❌ Произошла ошибка при обработке запроса."
            )
            return ConversationHandler.END

    @staticmethod
    async def show_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show notification preferences"""
        try:
            query = update.callback_query
            user_id = update.effective_user.id
            
            # Get current preferences
            preferences = await notification_client.get_notification_preferences(user_id)
            
            if not preferences:
                # Default preferences
                preferences = {
                    "telegram_enabled": True,
                    "email_enabled": False,
                    "lesson_reminders": True,
                    "homework_notifications": True,
                    "payment_notifications": True,
                    "system_notifications": True,
                    "reminder_time_before_lesson": 60  # minutes
                }
            
            # Format preferences message
            message = f"⚙️ **Настройки уведомлений**\n\n"
            
            message += f"📱 **Telegram:** {'✅ Включен' if preferences.get('telegram_enabled') else '❌ Отключен'}\n"
            message += f"📧 **Email:** {'✅ Включен' if preferences.get('email_enabled') else '❌ Отключен'}\n\n"
            
            message += f"**Типы уведомлений:**\n"
            message += f"• Напоминания об уроках: {'✅' if preferences.get('lesson_reminders') else '❌'}\n"
            message += f"• Домашние задания: {'✅' if preferences.get('homework_notifications') else '❌'}\n"
            message += f"• Платежи: {'✅' if preferences.get('payment_notifications') else '❌'}\n"
            message += f"• Системные: {'✅' if preferences.get('system_notifications') else '❌'}\n\n"
            
            message += f"⏰ **Напоминание об уроке:** за {preferences.get('reminder_time_before_lesson', 60)} мин."
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        f"📱 Telegram: {'✅' if preferences.get('telegram_enabled') else '❌'}",
                        callback_data="toggle_telegram"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"📧 Email: {'✅' if preferences.get('email_enabled') else '❌'}",
                        callback_data="toggle_email"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"🔔 Уроки: {'✅' if preferences.get('lesson_reminders') else '❌'}",
                        callback_data="toggle_lessons"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"📝 ДЗ: {'✅' if preferences.get('homework_notifications') else '❌'}",
                        callback_data="toggle_homework"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"💰 Платежи: {'✅' if preferences.get('payment_notifications') else '❌'}",
                        callback_data="toggle_payments"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⏰ Время напоминания",
                        callback_data="set_reminder_time"
                    )
                ],
                [
                    InlineKeyboardButton("💾 Сохранить", callback_data="save_preferences"),
                    InlineKeyboardButton("🔙 Назад", callback_data="back_to_notifications")
                ]
            ]
            
            # Store current preferences in context
            context.user_data['notification_preferences'] = preferences
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            return NOTIFICATION_PREFERENCES
            
        except Exception as e:
            logger.error(f"Error showing preferences: {str(e)}")
            await update.callback_query.edit_message_text(
                "❌ Ошибка при загрузке настроек."
            )
            return NOTIFICATION_MAIN_MENU

    @staticmethod
    async def toggle_preference(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Toggle notification preference"""
        try:
            query = update.callback_query
            await query.answer()
            
            toggle_type = query.data.replace('toggle_', '')
            preferences = context.user_data.get('notification_preferences', {})
            
            # Toggle the preference
            preference_map = {
                'telegram': 'telegram_enabled',
                'email': 'email_enabled',
                'lessons': 'lesson_reminders',
                'homework': 'homework_notifications',
                'payments': 'payment_notifications'
            }
            
            pref_key = preference_map.get(toggle_type)
            if pref_key:
                preferences[pref_key] = not preferences.get(pref_key, False)
                context.user_data['notification_preferences'] = preferences
            
            # Refresh the preferences view
            return await NotificationHandlers.show_preferences(update, context)
            
        except Exception as e:
            logger.error(f"Error toggling preference: {str(e)}")
            await update.callback_query.edit_message_text(
                "❌ Ошибка при изменении настройки."
            )
            return NOTIFICATION_PREFERENCES

    @staticmethod
    async def save_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Save notification preferences"""
        try:
            query = update.callback_query
            await query.answer("💾 Сохраняем настройки...")
            
            user_id = update.effective_user.id
            preferences = context.user_data.get('notification_preferences', {})
            
            # Save preferences
            success = await notification_client.update_notification_preferences(
                user_id, preferences
            )
            
            if success:
                await query.edit_message_text(
                    "✅ Настройки уведомлений сохранены!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 К уведомлениям", callback_data="back_to_notifications")]
                    ])
                )
            else:
                await query.edit_message_text(
                    "❌ Ошибка при сохранении настроек.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="notification_preferences")]
                    ])
                )
            
            return NOTIFICATION_MAIN_MENU
            
        except Exception as e:
            logger.error(f"Error saving preferences: {str(e)}")
            await update.callback_query.edit_message_text(
                "❌ Ошибка при сохранении настроек."
            )
            return NOTIFICATION_PREFERENCES

    @staticmethod
    async def manage_telegram_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Manage Telegram notification settings"""
        try:
            query = update.callback_query
            user_id = update.effective_user.id
            
            message = f"📱 **Telegram уведомления**\n\n" \
                     f"Настройте получение уведомлений в Telegram:\n\n" \
                     f"• Уроки и расписание\n" \
                     f"• Домашние задания\n" \
                     f"• Платежи и счета\n" \
                     f"• Системные сообщения\n\n" \
                     f"Все уведомления будут приходить в этот чат."
            
            keyboard = [
                [InlineKeyboardButton("🧪 Тестовое уведомление", callback_data="test_telegram")],
                [InlineKeyboardButton("⚙️ Настроить типы", callback_data="notification_preferences")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_notifications")]
            ]
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            return NOTIFICATION_MAIN_MENU
            
        except Exception as e:
            logger.error(f"Error managing Telegram notifications: {str(e)}")
            await update.callback_query.edit_message_text(
                "❌ Ошибка при настройке Telegram уведомлений."
            )
            return NOTIFICATION_MAIN_MENU

    @staticmethod
    async def send_test_notification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Send test notification"""
        try:
            query = update.callback_query
            await query.answer("📤 Отправляем тестовое уведомление...")
            
            user_id = update.effective_user.id
            
            # Send test notification
            success = await notification_client.send_telegram_notification(
                user_id=user_id,
                message="🧪 Это тестовое уведомление! Все настроено правильно.",
                notification_type="test"
            )
            
            if success:
                await query.edit_message_text(
                    "✅ Тестовое уведомление отправлено!\n\n"
                    "Если вы получили сообщение, значит уведомления работают корректно.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="telegram_notifications")]
                    ])
                )
            else:
                await query.edit_message_text(
                    "❌ Ошибка при отправке тестового уведомления.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="telegram_notifications")]
                    ])
                )
            
            return NOTIFICATION_MAIN_MENU
            
        except Exception as e:
            logger.error(f"Error sending test notification: {str(e)}")
            await update.callback_query.edit_message_text(
                "❌ Ошибка при отправке тестового уведомления."
            )
            return NOTIFICATION_MAIN_MENU

    @staticmethod
    async def manage_email_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Manage email notification settings"""
        try:
            query = update.callback_query
            
            message = f"📧 **Email уведомления**\n\n" \
                     f"Получайте важные уведомления на email:\n\n" \
                     f"• Подтверждения платежей\n" \
                     f"• Еженедельные отчеты\n" \
                     f"• Важные системные уведомления\n\n" \
                     f"Убедитесь, что ваш email указан в профиле."
            
            keyboard = [
                [InlineKeyboardButton("📝 Обновить email", callback_data="update_email")],
                [InlineKeyboardButton("🧪 Тестовое письмо", callback_data="test_email")],
                [InlineKeyboardButton("⚙️ Настроить типы", callback_data="notification_preferences")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_notifications")]
            ]
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            return NOTIFICATION_MAIN_MENU
            
        except Exception as e:
            logger.error(f"Error managing email notifications: {str(e)}")
            await update.callback_query.edit_message_text(
                "❌ Ошибка при настройке email уведомлений."
            )
            return NOTIFICATION_MAIN_MENU

    @staticmethod
    async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show notification history"""
        try:
            query = update.callback_query
            user_id = update.effective_user.id
            
            # Get notification history
            history = await notification_client.get_notification_history(
                user_id=user_id,
                limit=10
            )
            
            if not history:
                await query.edit_message_text(
                    "📝 История уведомлений пуста.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_notifications")]
                    ])
                )
                return NOTIFICATION_MAIN_MENU
            
            message = f"📝 **История уведомлений**\n\n"
            
            for notification in history[:5]:  # Show last 5
                sent_at = notification.get('sent_at', '')
                if sent_at:
                    try:
                        dt = datetime.fromisoformat(sent_at.replace('Z', '+00:00'))
                        sent_at = dt.strftime('%d.%m %H:%M')
                    except:
                        sent_at = sent_at[:16]
                
                status = notification.get('status', 'unknown')
                status_emoji = {'sent': '✅', 'failed': '❌', 'pending': '⏳'}.get(status, '❓')
                
                message += f"{status_emoji} {sent_at}\n"
                message += f"  {notification.get('message', 'Нет текста')[:50]}...\n\n"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data="notification_history")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_notifications")]
            ]
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            return NOTIFICATION_MAIN_MENU
            
        except Exception as e:
            logger.error(f"Error showing notification history: {str(e)}")
            await update.callback_query.edit_message_text(
                "❌ Ошибка при загрузке истории уведомлений."
            )
            return NOTIFICATION_MAIN_MENU

    @staticmethod
    async def manage_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Manage lesson reminders"""
        try:
            query = update.callback_query
            
            message = f"🔔 **Напоминания об уроках**\n\n" \
                     f"Настройте автоматические напоминания:\n\n" \
                     f"• За 1 час до урока\n" \
                     f"• За 30 минут до урока\n" \
                     f"• За 15 минут до урока\n" \
                     f"• За 5 минут до урока\n\n" \
                     f"Выберите удобное время для напоминаний."
            
            keyboard = [
                [InlineKeyboardButton("⏰ За 1 час", callback_data="reminder_60")],
                [InlineKeyboardButton("⏰ За 30 мин", callback_data="reminder_30")],
                [InlineKeyboardButton("⏰ За 15 мин", callback_data="reminder_15")],
                [InlineKeyboardButton("⏰ За 5 мин", callback_data="reminder_5")],
                [InlineKeyboardButton("❌ Отключить", callback_data="reminder_off")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_notifications")]
            ]
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            return NOTIFICATION_MAIN_MENU
            
        except Exception as e:
            logger.error(f"Error managing reminders: {str(e)}")
            await update.callback_query.edit_message_text(
                "❌ Ошибка при настройке напоминаний."
            )
            return NOTIFICATION_MAIN_MENU

    @staticmethod
    async def set_reminder_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Set reminder time"""
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data.startswith('reminder_'):
                time_str = query.data.replace('reminder_', '')
                
                if time_str == 'off':
                    minutes = 0
                    message = "❌ Напоминания отключены."
                else:
                    minutes = int(time_str)
                    message = f"✅ Напоминания установлены за {minutes} минут до урока."
                
                # Update preferences
                preferences = context.user_data.get('notification_preferences', {})
                preferences['reminder_time_before_lesson'] = minutes
                preferences['lesson_reminders'] = minutes > 0
                context.user_data['notification_preferences'] = preferences
                
                # Save preferences
                user_id = update.effective_user.id
                await notification_client.update_notification_preferences(
                    user_id, preferences
                )
                
                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 К напоминаниям", callback_data="notification_reminders")]
                    ])
                )
            
            return NOTIFICATION_MAIN_MENU
            
        except Exception as e:
            logger.error(f"Error setting reminder time: {str(e)}")
            await update.callback_query.edit_message_text(
                "❌ Ошибка при установке времени напоминания."
            )
            return NOTIFICATION_MAIN_MENU

    @staticmethod
    async def cancel_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel notification conversation"""
        await update.callback_query.edit_message_text("❌ Операция отменена.")
        return ConversationHandler.END