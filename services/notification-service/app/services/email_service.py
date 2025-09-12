import asyncio
import logging
from typing import Optional, List, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import aiosmtplib
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Сервис для отправки email уведомлений"""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_use_tls = settings.SMTP_USE_TLS
        self.from_email = settings.FROM_EMAIL
        
        if not all([self.smtp_username, self.smtp_password, self.from_email]):
            logger.warning("Email configuration incomplete")
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Отправить email
        
        Args:
            to_email: Email получателя
            subject: Тема письма
            body_text: Текстовое содержимое
            body_html: HTML содержимое
            attachments: Список вложений [{"filename": str, "content": bytes, "content_type": str}]
            cc: Список адресов для копии
            bcc: Список адресов для скрытой копии
        
        Returns:
            Результат отправки
        """
        if not self._is_configured():
            raise Exception("Email service not configured")
        
        try:
            # Создаем сообщение
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.from_email
            message["To"] = to_email
            
            if cc:
                message["Cc"] = ", ".join(cc)
            
            # Добавляем текстовую часть
            text_part = MIMEText(body_text, "plain", "utf-8")
            message.attach(text_part)
            
            # Добавляем HTML часть если есть
            if body_html:
                html_part = MIMEText(body_html, "html", "utf-8")
                message.attach(html_part)
            
            # Добавляем вложения если есть
            if attachments:
                for attachment in attachments:
                    await self._add_attachment(message, attachment)
            
            # Список всех получателей
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            # Отправляем
            await self._send_message(message, recipients)
            
            logger.info(f"Email sent successfully to {to_email}")
            return {
                "success": True,
                "message": "Email sent successfully",
                "recipient": to_email
            }
            
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return {
                "success": False,
                "error": str(e),
                "recipient": to_email
            }
    
    async def send_bulk_email(
        self,
        recipients: List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Массовая отправка email
        
        Args:
            recipients: Список email получателей
            subject: Тема письма
            body_text: Текстовое содержимое
            body_html: HTML содержимое
            batch_size: Размер батча
        
        Returns:
            Результат массовой отправки
        """
        if not self._is_configured():
            raise Exception("Email service not configured")
        
        results = {
            "total": len(recipients),
            "sent": 0,
            "failed": 0,
            "errors": []
        }
        
        # Отправляем батчами
        for i in range(0, len(recipients), batch_size):
            batch = recipients[i:i + batch_size]
            tasks = []
            
            for email in batch:
                task = self.send_email(email, subject, body_text, body_html)
                tasks.append(task)
            
            # Ждем выполнения батча
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    results["failed"] += 1
                    results["errors"].append(str(result))
                elif result.get("success"):
                    results["sent"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(result.get("error", "Unknown error"))
            
            # Небольшая пауза между батчами
            if i + batch_size < len(recipients):
                await asyncio.sleep(1)
        
        logger.info(f"Bulk email completed: {results['sent']}/{results['total']} sent")
        return results
    
    async def send_template_email(
        self,
        to_email: str,
        template_subject: str,
        template_body: str,
        template_html: Optional[str],
        context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Отправить email используя шаблон
        
        Args:
            to_email: Email получателя
            template_subject: Шаблон темы
            template_body: Шаблон тела (текст)
            template_html: Шаблон тела (HTML)
            context_data: Данные для подстановки
        
        Returns:
            Результат отправки
        """
        try:
            # Рендерим шаблоны
            from app.services.template_service import TemplateService
            template_service = TemplateService()
            
            subject = await template_service.render_template(template_subject, context_data)
            body_text = await template_service.render_template(template_body, context_data)
            body_html = None
            
            if template_html:
                body_html = await template_service.render_template(template_html, context_data)
            
            return await self.send_email(to_email, subject, body_text, body_html)
            
        except Exception as e:
            logger.error(f"Error sending template email to {to_email}: {e}")
            return {
                "success": False,
                "error": str(e),
                "recipient": to_email
            }
    
    async def _send_message(self, message: MIMEMultipart, recipients: List[str]):
        """Отправить сообщение через SMTP"""
        try:
            smtp = aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=self.smtp_use_tls
            )
            
            await smtp.connect()
            
            if self.smtp_username and self.smtp_password:
                await smtp.login(self.smtp_username, self.smtp_password)
            
            await smtp.send_message(message, recipients=recipients)
            await smtp.quit()
            
        except Exception as e:
            logger.error(f"SMTP error: {e}")
            raise
    
    async def _add_attachment(self, message: MIMEMultipart, attachment: Dict[str, Any]):
        """Добавить вложение к сообщению"""
        try:
            filename = attachment.get("filename", "attachment")
            content = attachment.get("content")
            content_type = attachment.get("content_type", "application/octet-stream")
            
            if not content:
                logger.warning(f"Empty attachment content for {filename}")
                return
            
            part = MIMEBase("application", "octet-stream")
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {filename}"
            )
            
            message.attach(part)
            
        except Exception as e:
            logger.error(f"Error adding attachment {attachment.get('filename')}: {e}")
            raise
    
    def _is_configured(self) -> bool:
        """Проверить конфигурацию email сервиса"""
        return all([
            self.smtp_host,
            self.smtp_port,
            self.smtp_username,
            self.smtp_password,
            self.from_email
        ])
    
    async def check_connection(self) -> bool:
        """
        Проверить соединение с SMTP сервером
        
        Returns:
            True если соединение работает, False иначе
        """
        if not self._is_configured():
            return False
        
        try:
            smtp = aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=self.smtp_use_tls,
                timeout=10
            )
            
            await smtp.connect()
            
            if self.smtp_username and self.smtp_password:
                await smtp.login(self.smtp_username, self.smtp_password)
            
            await smtp.quit()
            
            logger.info("SMTP connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False
    
    def create_html_template(self, body_text: str, title: str = "Уведомление") -> str:
        """
        Создать базовый HTML шаблон
        
        Args:
            body_text: Текст сообщения
            title: Заголовок
        
        Returns:
            HTML контент
        """
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #f4f4f4; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #fff; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{title}</h1>
                </div>
                <div class="content">
                    {body_text.replace('\n', '<br>')}
                </div>
                <div class="footer">
                    <p>Это автоматическое сообщение от системы RepitBot.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html_template