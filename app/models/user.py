# -*- coding: utf-8 -*-
"""
User model
"""
from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    
    # Settings
    ai_enabled = Column(Boolean, default=False)
    reminder_time = Column(String(5), nullable=True)  # HH:MM format
    timezone = Column(String(50), default='Europe/Moscow')
    
    # Statistics
    current_streak = Column(Integer, default=0)
    best_streak = Column(Integer, default=0)
    total_completions = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    habits = relationship("Habit", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    achievements = relationship("Achievement", back_populates="user", cascade="all, delete-orphan")
    habit_logs = relationship("HabitLog", back_populates="user", cascade="all, delete-orphan")
