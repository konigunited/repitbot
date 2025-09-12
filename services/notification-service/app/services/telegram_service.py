import asyncio
import logging
from typing import Optional, Dict, Any
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class TelegramService:
    """Сервис для отправки уведомлений через Telegram Bot API"""
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.api_url = f"{settings.TELEGRAM_API_URL}/bot{self.bot_token}"
        self.timeout = 30
        
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not configured")
    
    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[Dict[str, Any]] = None,
        disable_notification: bool = False
    ) -> Dict[str, Any]:
        """
        Отправить сообщение через Telegram Bot API
        
        Args:
            chat_id: ID чата или пользователя
            text: Текст сообщения
            parse_mode: Режим разбора (HTML, Markdown, или None)
            reply_markup: Клавиатура или кнопки
            disable_notification: Отключить звук уведомления
        
        Returns:
            Ответ от Telegram API
        """
        if not self.bot_token:
            raise Exception("Telegram bot token not configured")
        
        payload = {
            "chat_id": chat_id,
            "text": text[:4096],  # Telegram limit
            "parse_mode": parse_mode,
            "disable_notification": disable_notification
        }
        
        if reply_markup:
            payload["reply_markup"] = reply_markup
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_url}/sendMessage",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                
                if not result.get("ok"):
                    raise Exception(f"Telegram API error: {result.get('description')}")
                
                logger.info(f"Message sent successfully to chat {chat_id}")
                return result
                
        except httpx.TimeoutException:
            logger.error(f"Timeout sending message to {chat_id}")
            raise Exception("Telegram API timeout")
        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending message to {chat_id}: {e}")
            raise Exception(f"Telegram API HTTP error: {e}")
        except Exception as e:
            logger.error(f"Error sending message to {chat_id}: {e}")
            raise
    
    async def send_photo(
        self,
        chat_id: str,
        photo_url: str,
        caption: Optional[str] = None,
        parse_mode: str = "HTML"
    ) -> Dict[str, Any]:
        """
        Отправить фото через Telegram Bot API
        
        Args:
            chat_id: ID чата или пользователя
            photo_url: URL фотографии
            caption: Подпись к фото
            parse_mode: Режим разбора
        
        Returns:
            Ответ от Telegram API
        """
        if not self.bot_token:
            raise Exception("Telegram bot token not configured")
        
        payload = {
            "chat_id": chat_id,
            "photo": photo_url,
            "parse_mode": parse_mode
        }
        
        if caption:
            payload["caption"] = caption[:1024]  # Telegram limit for captions
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_url}/sendPhoto",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                
                if not result.get("ok"):
                    raise Exception(f"Telegram API error: {result.get('description')}")
                
                logger.info(f"Photo sent successfully to chat {chat_id}")
                return result
                
        except Exception as e:
            logger.error(f"Error sending photo to {chat_id}: {e}")
            raise
    
    async def send_document(
        self,
        chat_id: str,
        document_url: str,
        caption: Optional[str] = None,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Отправить документ через Telegram Bot API
        
        Args:
            chat_id: ID чата или пользователя
            document_url: URL документа
            caption: Подпись к документу
            filename: Имя файла
        
        Returns:
            Ответ от Telegram API
        """
        if not self.bot_token:
            raise Exception("Telegram bot token not configured")
        
        payload = {
            "chat_id": chat_id,
            "document": document_url
        }
        
        if caption:
            payload["caption"] = caption[:1024]
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_url}/sendDocument",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                
                if not result.get("ok"):
                    raise Exception(f"Telegram API error: {result.get('description')}")
                
                logger.info(f"Document sent successfully to chat {chat_id}")
                return result
                
        except Exception as e:
            logger.error(f"Error sending document to {chat_id}: {e}")
            raise
    
    async def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
        """
        Получить информацию о чате
        
        Args:
            chat_id: ID чата
        
        Returns:
            Информация о чате
        """
        if not self.bot_token:
            raise Exception("Telegram bot token not configured")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_url}/getChat",
                    json={"chat_id": chat_id}
                )
                response.raise_for_status()
                result = response.json()
                
                if not result.get("ok"):
                    raise Exception(f"Telegram API error: {result.get('description')}")
                
                return result.get("result", {})
                
        except Exception as e:
            logger.error(f"Error getting chat info for {chat_id}: {e}")
            raise
    
    async def check_bot_status(self) -> bool:
        """
        Проверить статус бота
        
        Returns:
            True если бот активен, False иначе
        """
        if not self.bot_token:
            return False
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(f"{self.api_url}/getMe")
                response.raise_for_status()
                result = response.json()
                
                if result.get("ok"):
                    bot_info = result.get("result", {})
                    logger.info(f"Bot status: {bot_info.get('first_name')} (@{bot_info.get('username')})")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error checking bot status: {e}")
            return False
    
    def create_inline_keyboard(self, buttons: list) -> Dict[str, Any]:
        """
        Создать inline клавиатуру
        
        Args:
            buttons: Список кнопок [{"text": "Button", "callback_data": "data"}]
        
        Returns:
            Объект клавиатуры
        """
        keyboard = []
        for button in buttons:
            if isinstance(button, list):
                # Ряд кнопок
                keyboard.append(button)
            else:
                # Одна кнопка в ряду
                keyboard.append([button])
        
        return {
            "inline_keyboard": keyboard
        }
    
    def create_reply_keyboard(
        self,
        buttons: list,
        resize_keyboard: bool = True,
        one_time_keyboard: bool = False
    ) -> Dict[str, Any]:
        """
        Создать reply клавиатуру
        
        Args:
            buttons: Список кнопок
            resize_keyboard: Подогнать размер клавиатуры
            one_time_keyboard: Скрыть после использования
        
        Returns:
            Объект клавиатуры
        """
        keyboard = []
        for button in buttons:
            if isinstance(button, list):
                keyboard.append(button)
            else:
                keyboard.append([{"text": button}])
        
        return {
            "keyboard": keyboard,
            "resize_keyboard": resize_keyboard,
            "one_time_keyboard": one_time_keyboard
        }