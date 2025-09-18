"""Create notification tables

Revision ID: 0001_create_notifications
Revises: 
Create Date: 2025-09-18
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_create_notifications"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "channel",
            sa.Enum("telegram", "email", "sms", name="notificationchannel"),
            nullable=False,
        ),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("schedule", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_notification_preferences_user", "notification_preferences", ["user_id"])

    op.create_table(
        "notification_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "channel",
            sa.Enum(name="notificationchannel", inherit_existing=True),
            nullable=False,
        ),
        sa.Column("payload", sa.String(length=1024), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_notification_logs_user", "notification_logs", ["user_id"])
    op.create_index("ix_notification_logs_status", "notification_logs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_notification_logs_status", table_name="notification_logs")
    op.drop_index("ix_notification_logs_user", table_name="notification_logs")
    op.drop_table("notification_logs")
    op.drop_index("ix_notification_preferences_user", table_name="notification_preferences")
    op.drop_table("notification_preferences")
    op.execute("DROP TYPE IF EXISTS notificationchannel")
