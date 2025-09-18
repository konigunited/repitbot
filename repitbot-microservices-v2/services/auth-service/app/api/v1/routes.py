from fastapi import APIRouter, HTTPException, status

from ...schemas import CredentialCreate, CredentialOut, CredentialUpdate, LoginRequest, TokenResponse
from ...services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/health", tags=["health"])
def health_check() -> dict:
    return {"status": "healthy"}


@router.post("/register", response_model=CredentialOut, status_code=status.HTTP_201_CREATED)
def register_user(payload: CredentialCreate) -> CredentialOut:
    try:
        credential = auth_service.register(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CredentialOut.model_validate(credential)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    try:
        token = auth_service.authenticate(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return token


@router.put("/users/{user_id}", response_model=CredentialOut)
def update_credentials(user_id: int, payload: CredentialUpdate) -> CredentialOut:
    credential = auth_service.update(user_id, payload)
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")
    return CredentialOut.model_validate(credential)


@router.get("/users/{user_id}", response_model=CredentialOut)
def get_credentials(user_id: int) -> CredentialOut:
    credential = auth_service.get_credentials(user_id)
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")
    return CredentialOut.model_validate(credential)
