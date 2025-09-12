# -*- coding: utf-8 -*-
"""
Material Handlers for Telegram Bot
Handlers for material-related functionality using Material microservice
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from telegram.helpers import escape_markdown

from ..services.material_service_client import MaterialServiceClient
from ..services.user_service_client import UserServiceClient

logger = logging.getLogger(__name__)

# Initialize service clients
material_service = MaterialServiceClient()
user_service = UserServiceClient()

# Conversation states
ADD_MATERIAL_TITLE = 200
ADD_MATERIAL_GRADE = 201
ADD_MATERIAL_DESCRIPTION = 202
ADD_MATERIAL_LINK = 203
CONFIRM_MATERIAL = 204
SELECT_GRADE_FILTER = 205


async def show_materials_library(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show materials library main menu"""
    query = update.callback_query
    if query:
        await query.answer()
    
    try:
        # Get basic statistics
        stats = await material_service.get_material_stats()
        
        if stats:
            stats_text = (
                f"📚 *Библиотека материалов*\n\n"
                f"📖 Всего материалов: {stats['total_materials']}\n"
                f"📁 Файлов: {stats['total_files']}\n"
                f"👀 Просмотров: {stats['total_views']}\n"
                f"⬇️ Скачиваний: {stats['total_downloads']}\n\n"
            )
            
            # Show materials by grade
            if stats.get('materials_by_grade'):
                stats_text += "📊 *По классам:*\n"
                for grade, count in sorted(stats['materials_by_grade'].items()):
                    stats_text += f"   {grade} класс: {count} материалов\n"
        else:
            stats_text = "📚 *Библиотека материалов*\n\nДанные временно недоступны"
        
        # Create menu buttons
        keyboard = [
            [InlineKeyboardButton("🔍 Поиск материалов", callback_data="search_materials")],
            [InlineKeyboardButton("📊 По классам", callback_data="materials_by_grade")],
            [InlineKeyboardButton("⭐ Избранное", callback_data="featured_materials")],
            [InlineKeyboardButton("➕ Добавить материал", callback_data="add_material")],
            [InlineKeyboardButton("📁 Категории", callback_data="material_categories")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(
                stats_text,
                reply_markup=reply_markup,
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(
                stats_text,
                reply_markup=reply_markup,
                parse_mode='MarkdownV2'
            )
        
    except Exception as e:
        logger.error(f"Error showing materials library: {e}")
        error_msg = "❌ Произошла ошибка при загрузке библиотеки материалов"
        if query:
            await query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)


async def show_materials_by_grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show grade selection for materials"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Create grade selection keyboard
        keyboard = []
        for grade in range(2, 10):  # Grades 2-9
            keyboard.append([InlineKeyboardButton(f"{grade} класс", callback_data=f"grade_materials_{grade}")])
        
        keyboard.extend([
            [InlineKeyboardButton("🔙 Назад", callback_data="materials_library")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📊 *Выберите класс:*",
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
        
    except Exception as e:
        logger.error(f"Error showing grade selection: {e}")
        await query.edit_message_text("❌ Произошла ошибка")


async def show_grade_materials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show materials for specific grade"""
    query = update.callback_query
    await query.answer()
    
    try:
        grade = int(query.data.split("_")[-1])
        
        # Get materials for grade (using legacy method for compatibility)
        materials = await material_service.get_materials_by_grade(grade)
        
        if materials:
            materials_text = f"📚 *Материалы для {grade} класса*\n\n"
            
            for i, material in enumerate(materials[:10], 1):  # Show first 10
                title = escape_markdown(material.get('title', 'Без названия'), 2)
                materials_text += f"{i}\\. {title}\n"
                
                if material.get('description'):
                    desc = escape_markdown(material['description'][:50], 2)
                    materials_text += f"   📝 {desc}{'\\.\\.\\.' if len(material['description']) > 50 else ''}\n"
                
                if material.get('link'):
                    materials_text += f"   🔗 [Ссылка]({material['link']})\n"
                
                materials_text += f"   📅 {material.get('created_at', '').split('T')[0]}\n\n"
            
            if len(materials) > 10:
                materials_text += f"\\.\\.\\. и еще {len(materials) - 10} материалов\n"
        else:
            materials_text = f"📚 *Материалы для {grade} класса*\n\nМатериалы не найдены"
        
        # Add navigation buttons
        keyboard = [
            [InlineKeyboardButton("🔍 Поиск в этом классе", callback_data=f"search_grade_{grade}")],
            [InlineKeyboardButton("📊 Другой класс", callback_data="materials_by_grade")],
            [InlineKeyboardButton("🔙 В библиотеку", callback_data="materials_library")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            materials_text,
            reply_markup=reply_markup,
            parse_mode='MarkdownV2',
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error showing grade materials: {e}")
        await query.edit_message_text("❌ Произошла ошибка")


async def show_featured_materials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show featured materials"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Search for featured materials
        materials = await material_service.search_materials(
            is_featured=True,
            per_page=10
        )
        
        if materials:
            featured_text = "⭐ *Избранные материалы*\n\n"
            
            for i, material in enumerate(materials, 1):
                title = escape_markdown(material.title, 2)
                featured_text += f"{i}\\. {title} \\({material.grade} класс\\)\n"
                
                if material.description:
                    desc = escape_markdown(material.description[:50], 2)
                    featured_text += f"   📝 {desc}{'\\.\\.\\.' if len(material.description) > 50 else ''}\n"
                
                featured_text += f"   👀 {material.view_count} просмотров\n"
                featured_text += f"   ⭐ {material.average_rating:.1f}/5\\.0\n\n"
        else:
            featured_text = "⭐ *Избранные материалы*\n\nИзбранные материалы не найдены"
        
        # Add navigation
        keyboard = [
            [InlineKeyboardButton("🔙 В библиотеку", callback_data="materials_library")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            featured_text,
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
        
    except Exception as e:
        logger.error(f"Error showing featured materials: {e}")
        await query.edit_message_text("❌ Произошла ошибка")


async def start_add_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start material addition process"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "➕ *Добавление нового материала*\n\n"
        "Введите название материала:",
        parse_mode='MarkdownV2'
    )
    
    return ADD_MATERIAL_TITLE


async def get_material_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get material title from user"""
    try:
        title = update.message.text.strip()
        
        if not title or len(title) < 3:
            await update.message.reply_text("❌ Название должно содержать минимум 3 символа")
            return ADD_MATERIAL_TITLE
        
        if len(title) > 255:
            await update.message.reply_text("❌ Название слишком длинное (максимум 255 символов)")
            return ADD_MATERIAL_TITLE
        
        context.user_data['material_title'] = title
        
        # Ask for grade
        keyboard = []
        for grade in range(2, 10):
            keyboard.append([InlineKeyboardButton(f"{grade} класс", callback_data=f"material_grade_{grade}")])
        
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_material")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📚 *Материал: {escape_markdown(title, 2)}*\n\n"
            f"Выберите класс:",
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
        
        return ADD_MATERIAL_GRADE
        
    except Exception as e:
        logger.error(f"Error getting material title: {e}")
        await update.message.reply_text("❌ Произошла ошибка")
        return ConversationHandler.END


async def get_material_grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get material grade selection"""
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data == "cancel_material":
            await query.edit_message_text("❌ Добавление материала отменено")
            return ConversationHandler.END
        
        grade = int(query.data.split("_")[-1])
        context.user_data['material_grade'] = grade
        
        title = context.user_data.get('material_title')
        
        await query.edit_message_text(
            f"📚 *Материал: {escape_markdown(title, 2)}*\n"
            f"📊 *Класс: {grade}*\n\n"
            f"Введите описание материала \\(или /skip чтобы пропустить\\):",
            parse_mode='MarkdownV2'
        )
        
        return ADD_MATERIAL_DESCRIPTION
        
    except Exception as e:
        logger.error(f"Error getting material grade: {e}")
        await query.edit_message_text("❌ Произошла ошибка")
        return ConversationHandler.END


async def get_material_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get material description"""
    try:
        if update.message.text.strip() == "/skip":
            description = None
        else:
            description = update.message.text.strip()
            if len(description) > 1000:
                await update.message.reply_text("❌ Описание слишком длинное (максимум 1000 символов)")
                return ADD_MATERIAL_DESCRIPTION
        
        context.user_data['material_description'] = description
        
        title = context.user_data.get('material_title')
        grade = context.user_data.get('material_grade')
        
        desc_text = escape_markdown(description, 2) if description else "\\(без описания\\)"
        
        await update.message.reply_text(
            f"📚 *Материал: {escape_markdown(title, 2)}*\n"
            f"📊 *Класс: {grade}*\n"
            f"📝 *Описание: {desc_text}*\n\n"
            f"Введите ссылку на материал \\(или /skip чтобы пропустить\\):",
            parse_mode='MarkdownV2'
        )
        
        return ADD_MATERIAL_LINK
        
    except Exception as e:
        logger.error(f"Error getting material description: {e}")
        await update.message.reply_text("❌ Произошла ошибка")
        return ConversationHandler.END


async def get_material_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get material link"""
    try:
        if update.message.text.strip() == "/skip":
            link = None
        else:
            link = update.message.text.strip()
            # Basic URL validation
            if link and not (link.startswith('http://') or link.startswith('https://')):
                await update.message.reply_text("❌ Ссылка должна начинаться с http:// или https://")
                return ADD_MATERIAL_LINK
        
        context.user_data['material_link'] = link
        
        # Show confirmation
        title = context.user_data.get('material_title')
        grade = context.user_data.get('material_grade')
        description = context.user_data.get('material_description')
        
        confirmation_text = (
            f"✅ *Подтверждение добавления материала*\n\n"
            f"📚 *Название:* {escape_markdown(title, 2)}\n"
            f"📊 *Класс:* {grade}\n"
        )
        
        if description:
            confirmation_text += f"📝 *Описание:* {escape_markdown(description, 2)}\n"
        
        if link:
            confirmation_text += f"🔗 *Ссылка:* {escape_markdown(link, 2)}\n"
        
        confirmation_text += "\nДобавить материал?"
        
        keyboard = [
            [InlineKeyboardButton("✅ Добавить", callback_data="confirm_add_material")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_material")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            confirmation_text,
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
        
        return CONFIRM_MATERIAL
        
    except Exception as e:
        logger.error(f"Error getting material link: {e}")
        await update.message.reply_text("❌ Произошла ошибка")
        return ConversationHandler.END


async def confirm_add_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and add material"""
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data == "cancel_material":
            await query.edit_message_text("❌ Добавление материала отменено")
            context.user_data.clear()
            return ConversationHandler.END
        
        if query.data != "confirm_add_material":
            await query.edit_message_text("❌ Неверное действие")
            return ConversationHandler.END
        
        # Get material data
        title = context.user_data.get('material_title')
        grade = context.user_data.get('material_grade')
        description = context.user_data.get('material_description')
        link = context.user_data.get('material_link')
        
        # Get user ID for created_by field
        user_id = update.effective_user.id
        
        # Add material via microservice
        material = await material_service.create_material(
            title=title,
            grade=grade,
            description=description,
            link=link,
            created_by_user_id=user_id
        )
        
        if material:
            await query.edit_message_text(
                f"✅ *Материал успешно добавлен\\!*\n\n"
                f"📚 Название: {escape_markdown(material.title, 2)}\n"
                f"📊 Класс: {material.grade}\n"
                f"🆔 ID: `{material.id}`\n\n"
                f"Материал появится в библиотеке через несколько минут\\.",
                parse_mode='MarkdownV2'
            )
        else:
            await query.edit_message_text("❌ Не удалось добавить материал. Попробуйте позже.")
        
        # Clear user data
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error confirming add material: {e}")
        await query.edit_message_text("❌ Произошла ошибка при добавлении материала")
        context.user_data.clear()
        return ConversationHandler.END


async def cancel_material_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel material conversation"""
    context.user_data.clear()
    await update.message.reply_text("❌ Добавление материала отменено")
    return ConversationHandler.END


# Export handlers for use in main bot file
material_conversation_handler = ConversationHandler(
    entry_points=[],  # Will be set in main bot file
    states={
        ADD_MATERIAL_TITLE: [
            lambda update, context: update.message and update.message.text,
            get_material_title
        ],
        ADD_MATERIAL_GRADE: [
            lambda update, context: update.callback_query and update.callback_query.data.startswith("material_grade_"),
            get_material_grade
        ],
        ADD_MATERIAL_DESCRIPTION: [
            lambda update, context: update.message and update.message.text,
            get_material_description
        ],
        ADD_MATERIAL_LINK: [
            lambda update, context: update.message and update.message.text,
            get_material_link
        ],
        CONFIRM_MATERIAL: [
            lambda update, context: update.callback_query and update.callback_query.data in ["confirm_add_material", "cancel_material"],
            confirm_add_material
        ]
    },
    fallbacks=[
        lambda update, context: update.message and update.message.text == "/cancel",
        cancel_material_conversation
    ],
    conversation_timeout=600  # 10 minutes timeout
)