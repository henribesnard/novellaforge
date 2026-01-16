"""Add chat messages table

Revision ID: add_chat_messages_001
Revises:
Create Date: 2025-01-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_chat_messages_001'
down_revision = None  # Remplacez par l'ID de votre dernière migration si elle existe
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create message_role enum
    message_role_enum = postgresql.ENUM('user', 'assistant', 'system', name='messagerole')
    message_role_enum.create(op.get_bind())

    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('role', sa.Enum('user', 'assistant', 'system', name='messagerole'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Create indexes
    op.create_index(
        'ix_chat_messages_user_id',
        'chat_messages',
        ['user_id']
    )
    op.create_index(
        'ix_chat_messages_project_id',
        'chat_messages',
        ['project_id']
    )
    op.create_index(
        'ix_chat_messages_created_at',
        'chat_messages',
        ['created_at']
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_chat_messages_created_at', table_name='chat_messages')
    op.drop_index('ix_chat_messages_project_id', table_name='chat_messages')
    op.drop_index('ix_chat_messages_user_id', table_name='chat_messages')

    # Drop table
    op.drop_table('chat_messages')

    # Drop enum
    message_role_enum = postgresql.ENUM('user', 'assistant', 'system', name='messagerole')
    message_role_enum.drop(op.get_bind())
