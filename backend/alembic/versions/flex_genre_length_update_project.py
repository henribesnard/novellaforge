"""Add flexible genre and length settings

Revision ID: flex_genre_length
Revises: remove_chat_messages
Create Date: 2026-02-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'flex_genre_length'
down_revision = 'remove_chat_messages'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add new columns
    op.add_column('projects', sa.Column('target_chapter_count', sa.Integer(), nullable=True))
    op.add_column('projects', sa.Column('target_chapter_length', sa.Integer(), nullable=True))
    op.add_column('projects', sa.Column('generation_mode', sa.String(length=20), server_default='standard', nullable=False))

    # Alter genre column to String(100)
    op.alter_column('projects', 'genre',
               existing_type=postgresql.ENUM(name='genre'),
               type_=sa.String(length=100),
               existing_nullable=True)

def downgrade() -> None:
    # Revert genre column to Enum
    op.alter_column('projects', 'genre',
               existing_type=sa.String(length=100),
               type_=postgresql.ENUM('werewolf', 'billionaire', 'mafia', 'fantasy', 'vengeance', 'fiction', 'scifi', 'thriller', 'romance', 'mystery', 'horror', 'historical', 'other', name='genre'),
               existing_nullable=True)

    # Drop new columns
    op.drop_column('projects', 'generation_mode')
    op.drop_column('projects', 'target_chapter_length')
    op.drop_column('projects', 'target_chapter_count')
