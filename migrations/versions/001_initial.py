"""Initial migration - create all tables

Revision ID: 001
Revises: 
Create Date: 2026-02-22 20:00:00

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
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('ai_enabled', sa.Boolean(), nullable=True, default=False),
        sa.Column('reminder_time', sa.String(length=5), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=True, default='Europe/Moscow'),
        sa.Column('current_streak', sa.Integer(), nullable=True, default=0),
        sa.Column('best_streak', sa.Integer(), nullable=True, default=0),
        sa.Column('total_completions', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_active', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_id', 'users', ['id'])
    
    # Create habits table
    op.create_table(
        'habits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('emoji', sa.String(length=10), nullable=True, default='✅'),
        sa.Column('reminder_time', sa.String(length=5), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('target_days', sa.Integer(), nullable=True),
        sa.Column('current_streak', sa.Integer(), nullable=True, default=0),
        sa.Column('best_streak', sa.Integer(), nullable=True, default=0),
        sa.Column('total_completions', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_habits_id', 'habits', ['id'])
    op.create_index('ix_habits_user_id', 'habits', ['user_id'])
    op.create_index('idx_habit_user_active', 'habits', ['user_id', 'is_active'])
    op.create_index('idx_habit_reminder', 'habits', ['reminder_time', 'is_active'])
    
    # Create habit_logs table
    op.create_table(
        'habit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('habit_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('completed_date', sa.Date(), nullable=False, default=sa.func.current_date()),
        sa.Column('status', sa.String(length=20), nullable=True, default='completed'),
        sa.Column('note', sa.String(length=500), nullable=True),
        sa.Column('photo_path', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['habit_id'], ['habits.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_habit_logs_habit_id', 'habit_logs', ['habit_id'])
    op.create_index('ix_habit_logs_user_id', 'habit_logs', ['user_id'])
    op.create_index('idx_log_user_date', 'habit_logs', ['user_id', 'completed_date'])
    op.create_index('idx_log_habit_date', 'habit_logs', ['habit_id', 'completed_date'])
    
    # Create payments table
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False, default='payment'),
        sa.Column('bank', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=True, default='RUB'),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('open_date', sa.Date(), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=True, default=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('reminder_3d_sent', sa.Boolean(), nullable=True, default=False),
        sa.Column('reminder_1d_sent', sa.Boolean(), nullable=True, default=False),
        sa.Column('reminder_today_sent', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_payments_id', 'payments', ['id'])
    op.create_index('ix_payments_user_id', 'payments', ['user_id'])
    op.create_index('ix_payments_date', 'payments', ['date'])
    op.create_index('idx_payment_user_date', 'payments', ['user_id', 'date'])
    op.create_index('idx_payment_reminders', 'payments', ['date', 'is_completed', 'reminder_3d_sent'])
    
    # Create payment_reminders table
    op.create_table(
        'payment_reminders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payment_id', sa.Integer(), nullable=False),
        sa.Column('reminder_type', sa.String(length=10), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_payment_reminders_payment_id', 'payment_reminders', ['payment_id'])
    
    # Create achievements table
    op.create_table(
        'achievements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('achievement_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('icon', sa.String(length=10), nullable=False),
        sa.Column('unlocked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_achievements_id', 'achievements', ['id'])
    op.create_index('ix_achievements_user_id', 'achievements', ['user_id'])


def downgrade() -> None:
    op.drop_table('achievements')
    op.drop_table('payment_reminders')
    op.drop_table('payments')
    op.drop_table('habit_logs')
    op.drop_table('habits')
    op.drop_table('users')
