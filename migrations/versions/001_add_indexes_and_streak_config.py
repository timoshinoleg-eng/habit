"""Add indexes and streak configuration

Revision ID: 001
Revises: 
Create Date: 2026-02-17 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем поле streak_break_days в таблицу users (настраиваемый сброс серии)
    op.add_column('users', sa.Column('streak_break_days', sa.Integer(), 
                                     nullable=False, server_default='2'))
    
    # Добавляем поле last_streak_check для отслеживания последней проверки
    op.add_column('users', sa.Column('last_streak_check', sa.DateTime(), 
                                     nullable=True))
    
    # Добавляем поле is_paused для привычек (вместо удаления)
    op.add_column('habits', sa.Column('is_paused', sa.Boolean(), 
                                      nullable=False, server_default='0'))
    
    # Индекс для reminder_time (partial index только для не-null значений)
    op.create_index('idx_habits_reminder_time', 'habits', ['reminder_time'], 
                    unique=False, postgresql_where=sa.text('reminder_time IS NOT NULL'))
    
    # Составной индекс для активных привычек пользователя
    op.create_index('idx_habits_user_active', 'habits', ['user_id', 'is_active'], 
                    unique=False)
    
    # Индекс для paused привычек
    op.create_index('idx_habits_paused', 'habits', ['is_paused'], 
                    unique=False)
    
    # Индекс для логов по пользователю и дате
    op.create_index('idx_logs_user_date', 'habit_logs', ['user_id', 'completed_date'], 
                    unique=False)
    
    # Индекс для логов по привычке
    op.create_index('idx_logs_habit', 'habit_logs', ['habit_id', 'completed_date'], 
                    unique=False)
    
    # Индекс для users по notification_enabled (для быстрой выборки)
    op.create_index('idx_users_notifications', 'users', ['notification_enabled'], 
                    unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем индексы
    op.drop_index('idx_users_notifications', table_name='users')
    op.drop_index('idx_logs_habit', table_name='habit_logs')
    op.drop_index('idx_logs_user_date', table_name='habit_logs')
    op.drop_index('idx_habits_paused', table_name='habits')
    op.drop_index('idx_habits_user_active', table_name='habits')
    op.drop_index('idx_habits_reminder_time', table_name='habits')
    
    # Удаляем колонки
    op.drop_column('habits', 'is_paused')
    op.drop_column('users', 'last_streak_check')
    op.drop_column('users', 'streak_break_days')
