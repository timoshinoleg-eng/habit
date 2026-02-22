# -*- coding: utf-8 -*-
"""
Habit and HabitLog models
"""
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Date, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app.models.base import Base


class Habit(Base):
    """Habit model"""
    __tablename__ = "habits"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    
    # Habit details
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    emoji = Column(String(10), default='✅')
    
    # Settings
    reminder_time = Column(String(5), nullable=True)  # HH:MM
    is_active = Column(Boolean, default=True)
    target_days = Column(Integer, nullable=True)  # Target streak days
    
    # Statistics
    current_streak = Column(Integer, default=0)
    best_streak = Column(Integer, default=0)
    total_completions = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_habit_user_active', 'user_id', 'is_active'),
        Index('idx_habit_reminder', 'reminder_time', 'is_active'),
    )
    
    # Relationships
    user = relationship("User", back_populates="habits")
    logs = relationship("HabitLog", back_populates="habit", cascade="all, delete-orphan")


class HabitLog(Base):
    """Habit completion log"""
    __tablename__ = "habit_logs"
    
    id = Column(Integer, primary_key=True)
    habit_id = Column(Integer, ForeignKey("habits.id"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    
    # Log details
    completed_date = Column(Date, nullable=False, default=date.today)
    status = Column(String(20), default='completed')  # completed, skipped, missed
    note = Column(String(500), nullable=True)
    photo_path = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_log_user_date', 'user_id', 'completed_date'),
        Index('idx_log_habit_date', 'habit_id', 'completed_date'),
    )
    
    # Relationships
    habit = relationship("Habit", back_populates="logs")
    user = relationship("User", back_populates="habit_logs")
