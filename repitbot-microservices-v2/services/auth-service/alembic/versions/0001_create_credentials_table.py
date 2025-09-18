"""Create credentials table

Revision ID: 0001_create_credentials
Revises: 
Create Date: 2025-09-18
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_create_credentials"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_credentials_user", "credentials", ["user_id"], unique=True)
    op.create_index("ix_credentials_email", "credentials", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_credentials_email", table_name="credentials")
    op.drop_index("ix_credentials_user", table_name="credentials")
    op.drop_table("credentials")
