"""
Analytics Handlers for Telegram Bot
Handlers for analytics and reporting functionality
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from typing import Dict, Any
from datetime import datetime, timedelta

from ..services.analytics_service_client import analytics_client

logger = logging.getLogger(__name__)

# Conversation states
ANALYTICS_MAIN_MENU, ANALYTICS_PERIOD, ANALYTICS_CHART_TYPE, ANALYTICS_REPORT = range(4)

class AnalyticsHandlers:
    """Handlers for analytics functionality"""
    
    @staticmethod
    async def analytics_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show main analytics menu"""
        try:
            user = update.effective_user
            chat_id = update.effective_chat.id
            
            # Check if analytics service is available
            if not await analytics_client.health_check():
                await context.bot.send_message(
                    chat_id,
                    "🚫 Сервис аналитики временно недоступен. Попробуйте позже."
                )
                return ConversationHandler.END
            
            # Get user role from context (assuming it's stored there)
            user_role = context.user_data.get('role', 'student')
            
            keyboard = []
            
            if user_role in ['admin', 'tutor']:
                keyboard.extend([
                    [InlineKeyboardButton("📊 Общая статистика", callback_data="analytics_overview")],
                    [InlineKeyboardButton("📈 Статистика уроков", callback_data="analytics_lessons")],
                    [InlineKeyboardButton("💰 Финансовая статистика", callback_data="analytics_payments")]
                ])
            
            if user_role == 'admin':
                keyboard.extend([
                    [InlineKeyboardButton("👥 Активность пользователей", callback_data="analytics_users")],
                    [InlineKeyboardButton("📚 Использование материалов", callback_data="analytics_materials")]
                ])
            
            if user_role in ['admin', 'tutor', 'parent', 'student']:
                keyboard.extend([
                    [InlineKeyboardButton("📊 Графики", callback_data="analytics_charts")],
                    [InlineKeyboardButton("📄 Отчеты", callback_data="analytics_reports")]
                ])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message_text = f"📊 **Аналитика и отчеты**\n\n" \
                          f"Выберите нужный раздел для просмотра статистики:"
            
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
            
            return ANALYTICS_MAIN_MENU
            
        except Exception as e:
            logger.error(f"Error in analytics main menu: {str(e)}")
            await context.bot.send_message(
                update.effective_chat.id,
                "❌ Произошла ошибка при загрузке меню аналитики."
            )
            return ConversationHandler.END

    @staticmethod
    async def handle_analytics_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle analytics menu option selection"""
        try:
            query = update.callback_query
            await query.answer()
            
            option = query.data
            user_role = context.user_data.get('role', 'student')
            user_id = update.effective_user.id
            
            if option == "analytics_overview":
                return await AnalyticsHandlers.show_overview(update, context)
            elif option == "analytics_lessons":
                return await AnalyticsHandlers.show_lesson_stats(update, context)
            elif option == "analytics_payments":
                return await AnalyticsHandlers.show_payment_stats(update, context)
            elif option == "analytics_users" and user_role == "admin":
                return await AnalyticsHandlers.show_user_activity(update, context)
            elif option == "analytics_materials":
                return await AnalyticsHandlers.show_material_usage(update, context)
            elif option == "analytics_charts":
                return await AnalyticsHandlers.show_chart_menu(update, context)
            elif option == "analytics_reports":
                return await AnalyticsHandlers.show_report_menu(update, context)
            else:
                await query.edit_message_text("❌ Недоступная опция.")
                return ConversationHandler.END
                
        except Exception as e:
            logger.error(f"Error handling analytics option: {str(e)}")
            await update.callback_query.edit_message_text(
                "❌ Произошла ошибка при обработке запроса."
            )
            return ConversationHandler.END

    @staticmethod
    async def show_overview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show analytics overview"""
        try:
            query = update.callback_query
            user_role = context.user_data.get('role', 'student')
            user_id = update.effective_user.id
            
            # Get overview data
            overview = await analytics_client.get_analytics_overview()
            
            if not overview:
                await query.edit_message_text(
                    "❌ Не удалось загрузить данные обзора.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_analytics")]
                    ])
                )
                return ANALYTICS_MAIN_MENU
            
            # Format message based on user role
            message = f"📊 **Обзор системы**\n\n"
            
            overview_data = overview.get('overview', {})
            
            if user_role == 'admin':
                message += f"📚 **Уроки:**\n"
                message += f"• Всего уроков: {overview_data.get('total_lessons', 0)}\n"
                message += f"• За эту неделю: {overview_data.get('recent_activity', {}).get('lessons_this_week', 0)}\n\n"
                
                message += f"💰 **Доходы:**\n"
                message += f"• Общая сумма: {overview_data.get('total_revenue', 0)} руб.\n"
                message += f"• За эту неделю: {overview_data.get('recent_activity', {}).get('revenue_this_week', 0)} руб.\n\n"
                
                message += f"👥 **Пользователи:**\n"
                message += f"• Активные: {overview_data.get('active_users', 0)}\n"
                message += f"• Новые за неделю: {overview_data.get('recent_activity', {}).get('new_users_this_week', 0)}\n\n"
                
                message += f"📂 **Материалы:**\n"
                message += f"• Всего материалов: {overview_data.get('total_materials', 0)}\n"
                message += f"• Загружено за неделю: {overview_data.get('recent_activity', {}).get('materials_uploaded_this_week', 0)}\n"
                
            elif user_role == 'tutor':
                message += f"📚 **Мои уроки:**\n"
                message += f"• Всего уроков: {overview_data.get('my_lessons', 0)}\n"
                message += f"• За эту неделю: {overview_data.get('recent_activity', {}).get('lessons_this_week', 0)}\n\n"
                
                message += f"💰 **Мои доходы:**\n"
                message += f"• Общая сумма: {overview_data.get('my_earnings', 0)} руб.\n"
                message += f"• За эту неделю: {overview_data.get('recent_activity', {}).get('earnings_this_week', 0)} руб.\n\n"
                
                message += f"👥 **Мои ученики:**\n"
                message += f"• Количество: {overview_data.get('my_students', 0)}\n"
                
            else:
                message += f"📚 **Мои уроки:**\n"
                message += f"• Всего уроков: {overview_data.get('my_lessons', 0)}\n"
                message += f"• Завершено: {overview_data.get('completed_lessons', 0)}\n"
                message += f"• За эту неделю: {overview_data.get('recent_activity', {}).get('lessons_this_week', 0)}\n"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data="analytics_overview")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_analytics")]
            ]
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            return ANALYTICS_MAIN_MENU
            
        except Exception as e:
            logger.error(f"Error showing overview: {str(e)}")
            await update.callback_query.edit_message_text(
                "❌ Ошибка при загрузке обзора."
            )
            return ANALYTICS_MAIN_MENU

    @staticmethod
    async def show_lesson_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show lesson statistics"""
        try:
            query = update.callback_query
            user_role = context.user_data.get('role', 'student')
            user_id = update.effective_user.id
            
            # Determine parameters based on role
            tutor_id = user_id if user_role == 'tutor' else None
            student_id = user_id if user_role == 'student' else None
            
            # Get lesson statistics
            stats = await analytics_client.get_lesson_statistics(
                tutor_id=tutor_id,
                student_id=student_id,
                days=30
            )
            
            if not stats:
                await query.edit_message_text(
                    "❌ Не удалось загрузить статистику уроков.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_analytics")]
                    ])
                )
                return ANALYTICS_MAIN_MENU
            
            message = analytics_client.format_statistics_message(stats)
            
            keyboard = [
                [InlineKeyboardButton("📊 7 дней", callback_data="lesson_stats_7")],
                [InlineKeyboardButton("📊 30 дней", callback_data="lesson_stats_30")],
                [InlineKeyboardButton("📊 90 дней", callback_data="lesson_stats_90")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_analytics")]
            ]
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            return ANALYTICS_MAIN_MENU
            
        except Exception as e:
            logger.error(f"Error showing lesson stats: {str(e)}")
            await update.callback_query.edit_message_text(
                "❌ Ошибка при загрузке статистики уроков."
            )
            return ANALYTICS_MAIN_MENU

    @staticmethod
    async def show_payment_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show payment statistics"""
        try:
            query = update.callback_query
            user_role = context.user_data.get('role', 'student')
            user_id = update.effective_user.id
            
            if user_role not in ['admin', 'tutor']:
                await query.edit_message_text(
                    "❌ У вас нет доступа к финансовой статистике.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_analytics")]
                    ])
                )
                return ANALYTICS_MAIN_MENU
            
            tutor_id = user_id if user_role == 'tutor' else None
            
            # Get payment statistics
            stats = await analytics_client.get_payment_summary(
                tutor_id=tutor_id,
                days=30
            )
            
            if not stats:
                await query.edit_message_text(
                    "❌ Не удалось загрузить финансовую статистику.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_analytics")]
                    ])
                )
                return ANALYTICS_MAIN_MENU
            
            message = analytics_client.format_statistics_message(stats)
            
            keyboard = [
                [InlineKeyboardButton("💰 7 дней", callback_data="payment_stats_7")],
                [InlineKeyboardButton("💰 30 дней", callback_data="payment_stats_30")],
                [InlineKeyboardButton("💰 90 дней", callback_data="payment_stats_90")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_analytics")]
            ]
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            return ANALYTICS_MAIN_MENU
            
        except Exception as e:
            logger.error(f"Error showing payment stats: {str(e)}")
            await update.callback_query.edit_message_text(
                "❌ Ошибка при загрузке финансовой статистики."
            )
            return ANALYTICS_MAIN_MENU

    @staticmethod
    async def show_chart_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show chart generation menu"""
        try:
            query = update.callback_query
            user_role = context.user_data.get('role', 'student')
            
            # Get available chart types
            chart_types = await analytics_client.get_available_chart_types()
            
            if not chart_types:
                await query.edit_message_text(
                    "❌ Не удалось загрузить типы графиков.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_analytics")]
                    ])
                )
                return ANALYTICS_MAIN_MENU
            
            keyboard = []
            available_charts = chart_types.get('chart_types', {})
            
            for chart_type, chart_info in available_charts.items():
                if user_role in chart_info.get('access_roles', []):
                    keyboard.append([
                        InlineKeyboardButton(
                            chart_info.get('description', chart_type),
                            callback_data=f"chart_{chart_type}"
                        )
                    ])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_analytics")])
            
            message = "📈 **Графики и визуализация**\n\n" \
                     "Выберите тип графика для генерации:"
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            return ANALYTICS_CHART_TYPE
            
        except Exception as e:
            logger.error(f"Error showing chart menu: {str(e)}")
            await update.callback_query.edit_message_text(
                "❌ Ошибка при загрузке меню графиков."
            )
            return ANALYTICS_MAIN_MENU

    @staticmethod
    async def show_report_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show report generation menu"""
        try:
            query = update.callback_query
            user_role = context.user_data.get('role', 'student')
            
            # Get available report templates
            templates = await analytics_client.get_report_templates()
            
            if not templates:
                await query.edit_message_text(
                    "❌ Не удалось загрузить шаблоны отчетов.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_analytics")]
                    ])
                )
                return ANALYTICS_MAIN_MENU
            
            keyboard = []
            available_templates = templates.get('templates', {})
            
            for template_type, template_info in available_templates.items():
                if user_role in template_info.get('access_roles', []):
                    keyboard.append([
                        InlineKeyboardButton(
                            template_info.get('name', template_type),
                            callback_data=f"report_{template_type}"
                        )
                    ])
            
            keyboard.extend([
                [InlineKeyboardButton("⚡ Быстрые отчеты", callback_data="quick_reports")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_analytics")]
            ])
            
            message = "📄 **Отчеты**\n\n" \
                     "Выберите тип отчета для генерации:"
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            return ANALYTICS_REPORT
            
        except Exception as e:
            logger.error(f"Error showing report menu: {str(e)}")
            await update.callback_query.edit_message_text(
                "❌ Ошибка при загрузке меню отчетов."
            )
            return ANALYTICS_MAIN_MENU

    @staticmethod
    async def generate_quick_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Generate quick report"""
        try:
            query = update.callback_query
            user_role = context.user_data.get('role', 'student')
            
            # Show quick report options
            keyboard = []
            
            if user_role in ['admin', 'tutor', 'parent', 'student']:
                keyboard.append([
                    InlineKeyboardButton("📊 Уроки (7 дней)", callback_data="quick_lesson_7")
                ])
            
            if user_role in ['admin', 'tutor']:
                keyboard.extend([
                    [InlineKeyboardButton("💰 Платежи (7 дней)", callback_data="quick_payment_7")],
                    [InlineKeyboardButton("📚 Материалы (7 дней)", callback_data="quick_material_7")]
                ])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="analytics_reports")])
            
            message = "⚡ **Быстрые отчеты**\n\n" \
                     "Отчеты генерируются моментально за последние 7 дней:"
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            return ANALYTICS_REPORT
            
        except Exception as e:
            logger.error(f"Error in quick report menu: {str(e)}")
            await update.callback_query.edit_message_text(
                "❌ Ошибка при загрузке быстрых отчетов."
            )
            return ANALYTICS_REPORT

    @staticmethod
    async def handle_quick_report_generation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle quick report generation"""
        try:
            query = update.callback_query
            await query.answer("⏳ Генерируем отчет...")
            
            # Parse report type and period
            data_parts = query.data.split('_')
            report_type = data_parts[1]  # lesson, payment, material
            days = int(data_parts[2])    # 7
            
            # Generate report
            report_data = await analytics_client.generate_quick_report(
                report_type=report_type,
                days=days,
                format="pdf"
            )
            
            if not report_data:
                await query.edit_message_text(
                    "❌ Не удалось сгенерировать отчет.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="quick_reports")]
                    ])
                )
                return ANALYTICS_REPORT
            
            # Send report file
            filename = f"{report_type}_report_{days}days.pdf"
            
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=report_data,
                filename=filename,
                caption=f"📄 Отчет по {report_type} за последние {days} дней"
            )
            
            await query.edit_message_text(
                "✅ Отчет успешно сгенерирован и отправлен!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад к отчетам", callback_data="analytics_reports")]
                ])
            )
            
            return ANALYTICS_REPORT
            
        except Exception as e:
            logger.error(f"Error generating quick report: {str(e)}")
            await update.callback_query.edit_message_text(
                "❌ Ошибка при генерации отчета."
            )
            return ANALYTICS_REPORT

    @staticmethod
    async def cancel_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel analytics conversation"""
        await update.callback_query.edit_message_text("❌ Операция отменена.")
        return ConversationHandler.END