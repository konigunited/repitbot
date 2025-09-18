from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from ...schemas import PaymentCreate, PaymentOut, PaymentStatus, PaymentUpdate
from ...services.payment_service import payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/health", tags=["health"])
def health_check() -> dict:
    return {"status": "healthy"}


@router.post("/", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(payload: PaymentCreate) -> PaymentOut:
    payment = payment_service.create_payment(payload)
    return PaymentOut.model_validate(payment)


@router.get("/", response_model=list[PaymentOut])
def list_payments(
    student_id: Optional[int] = Query(None, gt=0),
    tutor_id: Optional[int] = Query(None, gt=0),
    status: Optional[PaymentStatus] = Query(None),
) -> list[PaymentOut]:
    payments = payment_service.list_payments(student_id=student_id, tutor_id=tutor_id, status=status)
    return [PaymentOut.model_validate(payment) for payment in payments]


@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: int) -> PaymentOut:
    payment = payment_service.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return PaymentOut.model_validate(payment)


@router.put("/{payment_id}", response_model=PaymentOut)
def update_payment(payment_id: int, payload: PaymentUpdate) -> PaymentOut:
    payment = payment_service.update_payment(payment_id, payload)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return PaymentOut.model_validate(payment)


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment(payment_id: int) -> None:
    deleted = payment_service.delete_payment(payment_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
