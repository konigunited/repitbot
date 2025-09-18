"""Create homeworks table

Revision ID: 0001_create_homeworks
Revises: 
Create Date: 2025-09-18
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_create_homeworks"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "homeworks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("tutor_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("resources", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "assigned",
                "submitted",
                "reviewed",
                "completed",
                name="homeworkstatus",
            ),
            nullable=False,
            server_default="assigned",
        ),
        sa.Column("deadline", sa.DateTime(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_homeworks_student", "homeworks", ["student_id"])
    op.create_index("ix_homeworks_tutor", "homeworks", ["tutor_id"])
    op.create_index("ix_homeworks_status", "homeworks", ["status"])


def downgrade() -> None:
    op.drop_index("ix_homeworks_status", table_name="homeworks")
    op.drop_index("ix_homeworks_tutor", table_name="homeworks")
    op.drop_index("ix_homeworks_student", table_name="homeworks")
    op.drop_table("homeworks")
    op.execute("DROP TYPE IF EXISTS homeworkstatus")
