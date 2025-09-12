# -*- coding: utf-8 -*-
"""
Telegram Bot - User Service Client
HTTP клиент для взаимодействия с User Service
"""
import logging
from typing import Optional, Dict, Any, List
from .api_client import BaseApiClient, ServiceUnavailableError, with_fallback, service_registry

logger = logging.getLogger(__name__)

class UserServiceClient(BaseApiClient):
    """Клиент для взаимодействия с User Service"""
    
    def __init__(self):
        config = service_registry.get_service_config('user')
        super().__init__(
            base_url=config.get('url', 'http://localhost:8001'),
            service_name='user-service',
            timeout=config.get('timeout', 10),
            max_retries=config.get('retries', 3)
        )
    
    # === User Management ===
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение пользователя по ID"""
        try:
            return await self.get(f'/api/v1/users/{user_id}')
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получение пользователя по Telegram ID"""
        try:
            return await self.get(f'/api/v1/users/telegram/{telegram_id}')
        except Exception as e:
            logger.error(f"Failed to get user by telegram_id {telegram_id}: {e}")
            return None
    
    async def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создание нового пользователя"""
        try:
            return await self.post('/api/v1/users/', data=user_data)
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return None
    
    async def update_user(self, user_id: int, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновление пользователя"""
        try:
            return await self.put(f'/api/v1/users/{user_id}', data=update_data)
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            return None
    
    async def delete_user(self, user_id: int) -> bool:
        """Удаление пользователя"""
        try:
            await self.delete(f'/api/v1/users/{user_id}')
            return True
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False
    
    # === User Lists ===
    
    async def get_users_by_role(self, role: str) -> List[Dict[str, Any]]:
        """Получение пользователей по роли"""
        try:
            return await self.get(f'/api/v1/users/by-role/{role}')
        except Exception as e:
            logger.error(f"Failed to get users by role {role}: {e}")
            return []
    
    async def get_students(self) -> List[Dict[str, Any]]:
        """Получение всех студентов"""
        return await self.get_users_by_role('student')
    
    async def get_parents(self) -> List[Dict[str, Any]]:
        """Получение всех родителей"""
        return await self.get_users_by_role('parent')
    
    async def get_parents_with_children(self) -> List[Dict[str, Any]]:
        """Получение родителей со списком детей"""
        try:
            return await self.get('/api/v1/users/parents-with-children')
        except Exception as e:
            logger.error(f"Failed to get parents with children: {e}")
            return []
    
    async def get_users_with_pagination(
        self, 
        page: int = 1, 
        size: int = 20,
        role: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Получение пользователей с пагинацией"""
        try:
            params = {'page': page, 'size': size}
            if role:
                params['role'] = role
            if search:
                params['search'] = search
            
            return await self.get('/api/v1/users/', params=params)
        except Exception as e:
            logger.error(f"Failed to get users with pagination: {e}")
            return {'users': [], 'total': 0, 'page': page, 'size': size, 'pages': 0}
    
    # === Access Code Validation ===
    
    async def validate_access_code(
        self, 
        access_code: str, 
        telegram_id: int,
        username: Optional[str] = None
    ) -> Dict[str, Any]:
        """Валидация кода доступа"""
        try:
            data = {
                'access_code': access_code,
                'telegram_id': telegram_id
            }
            if username:
                data['username'] = username
            
            return await self.post('/api/v1/users/validate-access-code', data=data)
        except Exception as e:
            logger.error(f"Failed to validate access code: {e}")
            return {'success': False, 'message': 'Service unavailable'}
    
    # === Points and Gamification ===
    
    async def update_user_points(
        self, 
        user_id: int, 
        points_to_add: int,
        reason: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Обновление баллов пользователя"""
        try:
            data = {
                'points_to_add': points_to_add,
                'reason': reason
            }
            return await self.post(f'/api/v1/users/{user_id}/points', data=data)
        except Exception as e:
            logger.error(f"Failed to update points for user {user_id}: {e}")
            return None
    
    async def update_user_streak(
        self, 
        user_id: int, 
        lesson_date: str
    ) -> Optional[Dict[str, Any]]:
        """Обновление streak дней пользователя"""
        try:
            data = {'lesson_date': lesson_date}
            return await self.post(f'/api/v1/users/{user_id}/streak', data=data)
        except Exception as e:
            logger.error(f"Failed to update streak for user {user_id}: {e}")
            return None
    
    # === Statistics ===
    
    async def get_user_stats(self) -> Dict[str, Any]:
        """Получение статистики пользователей"""
        try:
            return await self.get('/api/v1/users/stats')
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            return {}
    
    async def get_user_activity_log(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Получение журнала активности пользователя"""
        try:
            params = {'limit': limit}
            return await self.get(f'/api/v1/users/{user_id}/activity', params=params)
        except Exception as e:
            logger.error(f"Failed to get activity log for user {user_id}: {e}")
            return []

# Создаем экземпляр клиента
user_service_client = UserServiceClient()

# === Fallback функции для работы с локальной БД ===

async def _fallback_get_user_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Fallback: получение пользователя через локальную БД"""
    try:
        from ...src.database import get_user_by_telegram_id
        user = get_user_by_telegram_id(telegram_id)
        
        if user:
            return {
                'id': user.id,
                'telegram_id': user.telegram_id,
                'username': user.username,
                'full_name': user.full_name,
                'role': user.role.value,
                'access_code': user.access_code,
                'points': user.points,
                'streak_days': user.streak_days,
                'total_study_hours': user.total_study_hours,
                'created_at': user.created_at.isoformat() if user.created_at else None
            }
        return None
    except Exception as e:
        logger.error(f"Fallback failed for get_user_by_telegram_id: {e}")
        return None

async def _fallback_get_all_students() -> List[Dict[str, Any]]:
    """Fallback: получение всех студентов через локальную БД"""
    try:
        from ...src.database import get_all_students
        students = get_all_students()
        
        return [
            {
                'id': student.id,
                'telegram_id': student.telegram_id,
                'username': student.username,
                'full_name': student.full_name,
                'role': student.role.value,
                'points': student.points,
                'streak_days': student.streak_days
            }
            for student in students
        ]
    except Exception as e:
        logger.error(f"Fallback failed for get_all_students: {e}")
        return []

async def _fallback_validate_access_code(
    access_code: str, 
    telegram_id: int,
    username: Optional[str] = None
) -> Dict[str, Any]:
    """Fallback: валидация кода доступа через локальную БД"""
    try:
        from ...src.database import SessionLocal, User
        
        db = SessionLocal()
        try:
            # Ищем пользователя с таким кодом доступа
            user = db.query(User).filter(User.access_code == access_code).first()
            
            if user:
                # Привязываем Telegram ID
                user.telegram_id = telegram_id
                user.username = username
                db.commit()
                
                return {
                    'success': True,
                    'user_id': user.id,
                    'message': f'Добро пожаловать, {user.full_name}!'
                }
            else:
                return {
                    'success': False,
                    'message': 'Неверный код доступа'
                }
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Fallback failed for validate_access_code: {e}")
        return {
            'success': False,
            'message': 'Ошибка при проверке кода доступа'
        }

# === Обёрнутые в fallback функции ===

@with_fallback(_fallback_get_user_by_telegram_id)
async def get_user_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Получение пользователя по Telegram ID с fallback"""
    async with user_service_client:
        return await user_service_client.get_user_by_telegram_id(telegram_id)

@with_fallback(_fallback_get_all_students)
async def get_all_students() -> List[Dict[str, Any]]:
    """Получение всех студентов с fallback"""
    async with user_service_client:
        return await user_service_client.get_students()

@with_fallback(_fallback_validate_access_code)
async def validate_access_code(
    access_code: str, 
    telegram_id: int,
    username: Optional[str] = None
) -> Dict[str, Any]:
    """Валидация кода доступа с fallback"""
    async with user_service_client:
        return await user_service_client.validate_access_code(
            access_code, telegram_id, username
        )

# === Дополнительные функции без fallback ===

async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Получение пользователя по ID"""
    async with user_service_client:
        return await user_service_client.get_user_by_id(user_id)

async def create_user(user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Создание нового пользователя"""
    async with user_service_client:
        return await user_service_client.create_user(user_data)

async def update_user(user_id: int, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Обновление пользователя"""
    async with user_service_client:
        return await user_service_client.update_user(user_id, update_data)

async def update_user_points(
    user_id: int, 
    points_to_add: int,
    reason: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Обновление баллов пользователя"""
    async with user_service_client:
        return await user_service_client.update_user_points(user_id, points_to_add, reason)

async def get_parents_with_children() -> List[Dict[str, Any]]:
    """Получение родителей со списком детей"""
    async with user_service_client:
        return await user_service_client.get_parents_with_children()

async def check_user_service_health() -> bool:
    """Проверка здоровья User Service"""
    async with user_service_client:
        return await user_service_client.health_check()