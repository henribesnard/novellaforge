"""Drop chat messages table

Revision ID: remove_chat_messages_002
Revises: add_chat_messages_001
Create Date: 2026-01-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "remove_chat_messages_002"
down_revision = "add_chat_messages_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chat_messages_created_at")
    op.execute("DROP INDEX IF EXISTS ix_chat_messages_project_id")
    op.execute("DROP INDEX IF EXISTS ix_chat_messages_user_id")
    op.execute("DROP TABLE IF EXISTS chat_messages")
    op.execute("DROP TYPE IF EXISTS messagerole")


def downgrade() -> None:
    message_role_enum = postgresql.ENUM("user", "assistant", "system", name="messagerole")
    message_role_enum.create(op.get_bind())

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("role", sa.Enum("user", "assistant", "system", name="messagerole"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])
    op.create_index("ix_chat_messages_project_id", "chat_messages", ["project_id"])
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])
