"""Create lessons table

Revision ID: 0001_create_lessons
Revises: 
Create Date: 2025-09-18
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_create_lessons"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tutor_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=128), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("scheduled", "completed", "cancelled", name="lessonstatus"),
            nullable=False,
            server_default="scheduled",
        ),
        sa.Column("scheduled_at", sa.DateTime(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_lessons_tutor", "lessons", ["tutor_id"])
    op.create_index("ix_lessons_student", "lessons", ["student_id"])
    op.create_index("ix_lessons_scheduled", "lessons", ["scheduled_at"])


def downgrade() -> None:
    op.drop_index("ix_lessons_scheduled", table_name="lessons")
    op.drop_index("ix_lessons_student", table_name="lessons")
    op.drop_index("ix_lessons_tutor", table_name="lessons")
    op.drop_table("lessons")
    op.execute("DROP TYPE IF EXISTS lessonstatus")
