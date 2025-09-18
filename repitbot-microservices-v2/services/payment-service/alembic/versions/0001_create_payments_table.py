"""Create payments table

Revision ID: 0001_create_payments
Revises: 
Create Date: 2025-09-18
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_create_payments"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("tutor_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="RUB"),
        sa.Column(
            "status",
            sa.Enum("pending", "completed", "failed", "refunded", name="paymentstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("method", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("invoice_id", sa.String(length=64), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_payments_student", "payments", ["student_id"])
    op.create_index("ix_payments_tutor", "payments", ["tutor_id"])
    op.create_index("ix_payments_status", "payments", ["status"])
    op.create_index("ix_payments_invoice", "payments", ["invoice_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_payments_invoice", table_name="payments")
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_index("ix_payments_tutor", table_name="payments")
    op.drop_index("ix_payments_student", table_name="payments")
    op.drop_table("payments")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
