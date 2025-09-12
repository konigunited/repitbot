# -*- coding: utf-8 -*-
"""
User Service - Business Logic
Бизнес-логика для управления пользователями
"""
import random
import string
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, and_, or_, desc

from ..models.user import User, UserRole, UserSession, UserActivity
from ..schemas.user import (
    UserCreate, UserUpdate, UserInDB, UserWithChildren, 
    AccessCodeValidationRequest, UserPointsUpdate, UserStreakUpdate
)

class UserService:
    """Сервис для работы с пользователями"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    @staticmethod
    def generate_access_code(length: int = 8) -> str:
        """Генерация уникального кода доступа"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    
    async def create_user(self, user_data: UserCreate) -> UserInDB:
        """Создание нового пользователя"""
        # Генерируем код доступа если не передан
        if not user_data.access_code:
            user_data.access_code = self.generate_access_code()
            
            # Проверяем уникальность кода
            while await self.get_user_by_access_code(user_data.access_code):
                user_data.access_code = self.generate_access_code()
        
        # Проверяем уникальность telegram_id
        if user_data.telegram_id:
            existing_user = await self.get_user_by_telegram_id(user_data.telegram_id)
            if existing_user:
                raise ValueError(f"User with telegram_id {user_data.telegram_id} already exists")
        
        # Создаем пользователя
        db_user = User(**user_data.model_dump())
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        
        # Логируем создание
        await self.log_user_activity(db_user.id, "USER_CREATED", f"User {db_user.full_name} created")
        
        return UserInDB.model_validate(db_user)
    
    async def get_user_by_id(self, user_id: int) -> Optional[UserInDB]:
        """Получение пользователя по ID"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        return UserInDB.model_validate(user) if user else None
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[UserInDB]:
        """Получение пользователя по Telegram ID"""
        result = await self.db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        return UserInDB.model_validate(user) if user else None
    
    async def get_user_by_access_code(self, access_code: str) -> Optional[UserInDB]:
        """Получение пользователя по коду доступа"""
        result = await self.db.execute(
            select(User).where(User.access_code == access_code)
        )
        user = result.scalar_one_or_none()
        return UserInDB.model_validate(user) if user else None
    
    async def get_users_by_role(self, role: UserRole) -> List[UserInDB]:
        """Получение пользователей по роли"""
        result = await self.db.execute(
            select(User).where(User.role == role).order_by(User.full_name)
        )
        users = result.scalars().all()
        return [UserInDB.model_validate(user) for user in users]
    
    async def get_users_with_pagination(
        self, 
        page: int = 1, 
        size: int = 20, 
        role: Optional[UserRole] = None,
        search: Optional[str] = None
    ) -> Tuple[List[UserInDB], int]:
        """Получение пользователей с пагинацией"""
        query = select(User)
        
        # Фильтр по роли
        if role:
            query = query.where(User.role == role)
        
        # Поиск по имени
        if search:
            query = query.where(User.full_name.ilike(f"%{search}%"))
        
        # Подсчет общего количества
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()
        
        # Получение страницы
        offset = (page - 1) * size
        query = query.offset(offset).limit(size).order_by(User.full_name)
        
        result = await self.db.execute(query)
        users = result.scalars().all()
        
        return [UserInDB.model_validate(user) for user in users], total
    
    async def update_user(self, user_id: int, user_update: UserUpdate) -> Optional[UserInDB]:
        """Обновление пользователя"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Обновляем поля
        for field, value in user_update.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)
        
        # Логируем обновление
        await self.log_user_activity(user_id, "USER_UPDATED", "User profile updated")
        
        return UserInDB.model_validate(user)
    
    async def delete_user(self, user_id: int) -> bool:
        """Удаление пользователя"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        # Логируем удаление перед самим удалением
        await self.log_user_activity(user_id, "USER_DELETED", f"User {user.full_name} deleted")
        
        await self.db.delete(user)
        await self.db.commit()
        return True
    
    async def validate_access_code(self, request: AccessCodeValidationRequest) -> dict:
        """Валидация кода доступа и привязка Telegram ID"""
        user = await self.get_user_by_access_code(request.access_code)
        
        if not user:
            return {
                "success": False,
                "message": "Неверный код доступа",
                "user_id": None
            }
        
        # Проверяем, не привязан ли уже Telegram ID к другому пользователю
        if request.telegram_id != user.telegram_id:
            existing_user = await self.get_user_by_telegram_id(request.telegram_id)
            if existing_user and existing_user.id != user.id:
                return {
                    "success": False,
                    "message": "Этот Telegram аккаунт уже привязан к другому пользователю",
                    "user_id": None
                }
        
        # Обновляем Telegram данные
        update_data = UserUpdate(
            telegram_id=request.telegram_id,
            username=request.username
        )
        await self.update_user(user.id, update_data)
        
        # Логируем успешную авторизацию
        await self.log_user_activity(user.id, "ACCESS_CODE_VALIDATED", "Successfully linked Telegram account")
        
        return {
            "success": True,
            "message": f"Добро пожаловать, {user.full_name}!",
            "user_id": user.id
        }
    
    async def update_user_points(self, user_id: int, points_update: UserPointsUpdate) -> Optional[UserInDB]:
        """Обновление баллов пользователя"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        
        new_points = max(0, user.points + points_update.points_to_add)
        update_data = UserUpdate(points=new_points)
        
        await self.log_user_activity(
            user_id, 
            "POINTS_UPDATED", 
            f"Points changed: {user.points} -> {new_points}. Reason: {points_update.reason or 'No reason'}"
        )
        
        return await self.update_user(user_id, update_data)
    
    async def update_user_streak(self, user_id: int, streak_update: UserStreakUpdate) -> Optional[UserInDB]:
        """Обновление streak дней пользователя"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        
        current_date = streak_update.lesson_date.date()
        
        if user.last_lesson_date:
            last_date = user.last_lesson_date.date()
            days_diff = (current_date - last_date).days
            
            if days_diff == 1:  # Урок вчера - продолжаем streak
                new_streak = user.streak_days + 1
            elif days_diff == 0:  # Урок сегодня - не увеличиваем
                new_streak = user.streak_days
            else:  # Пропуск - обнуляем streak
                new_streak = 1
        else:
            new_streak = 1
        
        update_data = UserUpdate(
            streak_days=new_streak,
            last_lesson_date=streak_update.lesson_date
        )
        
        await self.log_user_activity(
            user_id,
            "STREAK_UPDATED",
            f"Streak updated: {user.streak_days} -> {new_streak}"
        )
        
        return await self.update_user(user_id, update_data)
    
    async def get_parents_with_children(self) -> List[UserWithChildren]:
        """Получение родителей со списком их детей"""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.children))
            .where(User.role == UserRole.PARENT)
            .order_by(User.full_name)
        )
        parents = result.scalars().all()
        
        result_list = []
        for parent in parents:
            parent_dict = UserInDB.model_validate(parent).model_dump()
            parent_dict['children'] = [UserInDB.model_validate(child) for child in parent.children]
            result_list.append(UserWithChildren(**parent_dict))
        
        return result_list
    
    async def get_user_stats(self) -> dict:
        """Получение статистики пользователей"""
        # Общее количество пользователей
        total_users_result = await self.db.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar()
        
        # По ролям
        roles_stats = {}
        for role in UserRole:
            result = await self.db.execute(
                select(func.count(User.id)).where(User.role == role)
            )
            roles_stats[f"total_{role.value}s"] = result.scalar()
        
        # Активные пользователи (с привязанным Telegram)
        active_result = await self.db.execute(
            select(func.count(User.id)).where(User.telegram_id.isnot(None))
        )
        active_users = active_result.scalar()
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            **roles_stats
        }
    
    async def log_user_activity(self, user_id: int, action: str, details: str = None):
        """Логирование активности пользователя"""
        activity = UserActivity(
            user_id=user_id,
            action=action,
            details=details
        )
        self.db.add(activity)
        await self.db.commit()
    
    async def get_user_activity_log(self, user_id: int, limit: int = 50) -> List[dict]:
        """Получение журнала активности пользователя"""
        result = await self.db.execute(
            select(UserActivity)
            .where(UserActivity.user_id == user_id)
            .order_by(desc(UserActivity.created_at))
            .limit(limit)
        )
        activities = result.scalars().all()
        
        return [
            {
                "action": activity.action,
                "details": activity.details,
                "created_at": activity.created_at
            }
            for activity in activities
        ]