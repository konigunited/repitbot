import asyncio
import logging
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, Template, meta
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)


class TemplateService:
    """Сервис для работы с шаблонами уведомлений"""
    
    def __init__(self):
        # Настраиваем Jinja2 окружение
        template_path = Path(__file__).parent.parent / settings.TEMPLATE_DIR
        template_path.mkdir(parents=True, exist_ok=True)
        
        self.env = Environment(
            loader=FileSystemLoader(str(template_path)),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Добавляем пользовательские функции в шаблоны
        self.env.globals.update({
            'format_date': self._format_date,
            'format_currency': self._format_currency,
            'format_time': self._format_time,
        })
        
        # Кэш для скомпилированных шаблонов
        self._template_cache = {}
    
    async def render_template(
        self,
        template_content: str,
        context_data: Dict[str, Any],
        template_name: Optional[str] = None
    ) -> str:
        """
        Рендерить шаблон с данными
        
        Args:
            template_content: Содержимое шаблона
            context_data: Данные для подстановки
            template_name: Имя шаблона для кэширования
        
        Returns:
            Отрендеренный текст
        """
        try:
            # Проверяем кэш если есть имя шаблона
            cache_key = f"{template_name}_{hash(template_content)}" if template_name else None
            
            if cache_key and cache_key in self._template_cache:
                template = self._template_cache[cache_key]
            else:
                template = Template(template_content, environment=self.env)
                if cache_key:
                    self._template_cache[cache_key] = template
            
            # Рендерим шаблон
            rendered = await asyncio.to_thread(template.render, **context_data)
            return rendered
            
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {e}")
            raise Exception(f"Template rendering error: {e}")
    
    async def render_file_template(
        self,
        template_filename: str,
        context_data: Dict[str, Any]
    ) -> str:
        """
        Рендерить шаблон из файла
        
        Args:
            template_filename: Имя файла шаблона
            context_data: Данные для подстановки
        
        Returns:
            Отрендеренный текст
        """
        try:
            template = self.env.get_template(template_filename)
            rendered = await asyncio.to_thread(template.render, **context_data)
            return rendered
            
        except Exception as e:
            logger.error(f"Error rendering file template {template_filename}: {e}")
            raise Exception(f"File template rendering error: {e}")
    
    def get_template_variables(self, template_content: str) -> list:
        """
        Получить список переменных в шаблоне
        
        Args:
            template_content: Содержимое шаблона
        
        Returns:
            Список имен переменных
        """
        try:
            ast = self.env.parse(template_content)
            variables = meta.find_undeclared_variables(ast)
            return list(variables)
            
        except Exception as e:
            logger.error(f"Error parsing template variables: {e}")
            return []
    
    async def validate_template(
        self,
        template_content: str,
        sample_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Проверить корректность шаблона
        
        Args:
            template_content: Содержимое шаблона
            sample_data: Тестовые данные
        
        Returns:
            Результат валидации
        """
        result = {
            "valid": False,
            "variables": [],
            "errors": [],
            "warnings": []
        }
        
        try:
            # Проверяем синтаксис
            template = Template(template_content, environment=self.env)
            
            # Получаем переменные
            variables = self.get_template_variables(template_content)
            result["variables"] = variables
            
            # Пробуем рендерить с тестовыми данными
            if sample_data:
                try:
                    await asyncio.to_thread(template.render, **sample_data)
                except Exception as render_error:
                    result["errors"].append(f"Rendering error: {render_error}")
            else:
                # Проверяем с пустыми данными
                try:
                    await asyncio.to_thread(template.render)
                except Exception as render_error:
                    # Это может быть нормально если шаблон требует данные
                    result["warnings"].append(f"Template requires data: {render_error}")
            
            result["valid"] = len(result["errors"]) == 0
            
        except Exception as e:
            result["errors"].append(f"Template syntax error: {e}")
        
        return result
    
    def _format_date(self, date_obj, format_string: str = "%d.%m.%Y") -> str:
        """Форматировать дату"""
        if not date_obj:
            return ""
        
        try:
            from datetime import datetime
            if isinstance(date_obj, str):
                # Пытаемся парсить строку как дату
                date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
            
            if isinstance(date_obj, datetime):
                return date_obj.strftime(format_string)
            
            return str(date_obj)
            
        except Exception:
            return str(date_obj)
    
    def _format_currency(self, amount, currency: str = "₽") -> str:
        """Форматировать валюту"""
        if not amount:
            return f"0 {currency}"
        
        try:
            amount_float = float(amount)
            return f"{amount_float:,.2f} {currency}".replace(",", " ")
        except Exception:
            return f"{amount} {currency}"
    
    def _format_time(self, time_obj, format_string: str = "%H:%M") -> str:
        """Форматировать время"""
        if not time_obj:
            return ""
        
        try:
            from datetime import datetime, time
            if isinstance(time_obj, str):
                # Пытаемся парсить строку как время
                if ":" in time_obj:
                    parts = time_obj.split(":")
                    time_obj = time(int(parts[0]), int(parts[1]))
                else:
                    time_obj = datetime.fromisoformat(time_obj).time()
            
            if isinstance(time_obj, (datetime, time)):
                if hasattr(time_obj, 'time'):
                    time_obj = time_obj.time()
                return time_obj.strftime(format_string)
            
            return str(time_obj)
            
        except Exception:
            return str(time_obj)
    
    async def create_default_templates(self):
        """Создать стандартные шаблоны"""
        templates = {
            # Telegram шаблоны
            "telegram/lesson_reminder.html": """
<b>🔔 Напоминание об уроке</b>

📚 <b>Предмет:</b> {{ lesson.subject }}
👨‍🏫 <b>Преподаватель:</b> {{ tutor.name }}
🕒 <b>Время:</b> {{ format_date(lesson.start_time, '%d.%m.%Y') }} в {{ format_time(lesson.start_time) }}
⏱️ <b>Длительность:</b> {{ lesson.duration }} минут

{% if lesson.meet_link %}
🔗 <b>Ссылка на урок:</b> <a href="{{ lesson.meet_link }}">Подключиться</a>
{% endif %}

Не забудьте подготовиться к уроку! 📖
            """,
            
            "telegram/homework_assigned.html": """
<b>📝 Новое домашнее задание</b>

📚 <b>Предмет:</b> {{ homework.subject }}
👨‍🏫 <b>От:</b> {{ tutor.name }}
📅 <b>Срок сдачи:</b> {{ format_date(homework.due_date, '%d.%m.%Y') }}

<b>Задание:</b>
{{ homework.description }}

{% if homework.files %}
📎 <b>Файлы:</b>
{% for file in homework.files %}
• {{ file.name }}
{% endfor %}
{% endif %}

Удачи в выполнении! 💪
            """,
            
            "telegram/payment_processed.html": """
<b>💰 Платеж обработан</b>

✅ <b>Статус:</b> Успешно
💵 <b>Сумма:</b> {{ format_currency(payment.amount) }}
📅 <b>Дата:</b> {{ format_date(payment.created_at, '%d.%m.%Y %H:%M') }}
🆔 <b>ID транзакции:</b> {{ payment.id }}

{% if payment.description %}
📝 <b>Описание:</b> {{ payment.description }}
{% endif %}

Спасибо за оплату! 🙏
            """,
            
            # Email шаблоны
            "email/lesson_reminder_subject.txt": "Напоминание об уроке: {{ lesson.subject }}",
            
            "email/lesson_reminder_body.html": """
<h2>🔔 Напоминание об уроке</h2>

<p><strong>Предмет:</strong> {{ lesson.subject }}</p>
<p><strong>Преподаватель:</strong> {{ tutor.name }}</p>
<p><strong>Время:</strong> {{ format_date(lesson.start_time, '%d.%m.%Y') }} в {{ format_time(lesson.start_time) }}</p>
<p><strong>Длительность:</strong> {{ lesson.duration }} минут</p>

{% if lesson.meet_link %}
<p><strong>Ссылка на урок:</strong> <a href="{{ lesson.meet_link }}">{{ lesson.meet_link }}</a></p>
{% endif %}

<p>Не забудьте подготовиться к уроку!</p>

<hr>
<p><em>Это автоматическое уведомление от системы RepitBot.</em></p>
            """,
            
            "email/homework_assigned_subject.txt": "Новое домашнее задание: {{ homework.subject }}",
            
            "email/homework_assigned_body.html": """
<h2>📝 Новое домашнее задание</h2>

<p><strong>Предмет:</strong> {{ homework.subject }}</p>
<p><strong>От:</strong> {{ tutor.name }}</p>
<p><strong>Срок сдачи:</strong> {{ format_date(homework.due_date, '%d.%m.%Y') }}</p>

<h3>Задание:</h3>
<p>{{ homework.description|nl2br }}</p>

{% if homework.files %}
<h3>Прикрепленные файлы:</h3>
<ul>
{% for file in homework.files %}
<li>{{ file.name }}</li>
{% endfor %}
</ul>
{% endif %}

<p>Удачи в выполнении!</p>

<hr>
<p><em>Это автоматическое уведомление от системы RepitBot.</em></p>
            """
        }
        
        # Создаем файлы шаблонов
        template_base_path = Path(__file__).parent.parent / settings.TEMPLATE_DIR
        
        for template_path, content in templates.items():
            file_path = template_base_path / template_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if not file_path.exists():
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content.strip())
                logger.info(f"Created template: {template_path}")
    
    def clear_cache(self):
        """Очистить кэш шаблонов"""
        self._template_cache.clear()
        logger.info("Template cache cleared")