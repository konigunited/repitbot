from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from ...schemas import UserCreate, UserOut, UserUpdate
from ...services.user_service import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/health", tags=["health"])
def health_check() -> dict:
    return {"status": "healthy"}


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate) -> UserOut:
    try:
        user = user_service.create_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UserOut.model_validate(user)


@router.get("/", response_model=list[UserOut])
def list_users(telegram_id: Optional[str] = Query(None)) -> list[UserOut]:
    if telegram_id:
        user = user_service.find_by_telegram(telegram_id)
        if not user:
            return []
        return [UserOut.model_validate(user)]
    users = user_service.get_users()
    return [UserOut.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int) -> UserOut:
    user = user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserOut.model_validate(user)


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate) -> UserOut:
    user = user_service.update_user(user_id, payload)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserOut.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(user_id: int) -> None:
    deleted = user_service.deactivate_user(user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
