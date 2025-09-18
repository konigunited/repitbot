from typing import List, Optional

from sqlalchemy import select

from ..core.database import session_scope
from ..models import Payment, PaymentStatus
from ..schemas import PaymentCreate, PaymentUpdate


class PaymentService:
    """Business logic for payment tracking."""

    def create_payment(self, payload: PaymentCreate) -> Payment:
        with session_scope() as session:
            payment = Payment(**payload.model_dump())
            session.add(payment)
            session.flush()
            session.refresh(payment)
            return payment

    def get_payment(self, payment_id: int) -> Optional[Payment]:
        with session_scope() as session:
            return session.get(Payment, payment_id)

    def list_payments(
        self,
        student_id: Optional[int] = None,
        tutor_id: Optional[int] = None,
        status: Optional[PaymentStatus] = None,
    ) -> List[Payment]:
        with session_scope() as session:
            stmt = select(Payment)
            if student_id:
                stmt = stmt.where(Payment.student_id == student_id)
            if tutor_id:
                stmt = stmt.where(Payment.tutor_id == tutor_id)
            if status:
                stmt = stmt.where(Payment.status == status)
            stmt = stmt.order_by(Payment.created_at.desc())
            return list(session.scalars(stmt))

    def update_payment(self, payment_id: int, payload: PaymentUpdate) -> Optional[Payment]:
        with session_scope() as session:
            payment = session.get(Payment, payment_id)
            if not payment:
                return None
            update_data = payload.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(payment, field, value)
            session.add(payment)
            session.flush()
            session.refresh(payment)
            return payment

    def delete_payment(self, payment_id: int) -> bool:
        with session_scope() as session:
            payment = session.get(Payment, payment_id)
            if not payment:
                return False
            session.delete(payment)
            return True


payment_service = PaymentService()
