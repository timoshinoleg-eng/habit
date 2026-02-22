# -*- coding: utf-8 -*-
"""
Payment and Deposit models for financial reminders
"""
from sqlalchemy import Column, Integer, BigInteger, String, Date, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app.models.base import Base


class Payment(Base):
    """Payments and deposits for user"""
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    
    # Type: 'payment' or 'deposit'
    type = Column(String(20), nullable=False, default='payment')
    
    # Bank selection
    bank = Column(String(50), nullable=False)
    
    # Amount in kopecks (stored as int)
    amount = Column(Integer, nullable=False)
    currency = Column(String(3), default='RUB')
    
    # Payment due date or deposit closing date
    date = Column(Date, nullable=False, index=True)
    
    # Deposit open date (only for deposits)
    open_date = Column(Date, nullable=True)
    
    # Description (e.g., "Credit", "Rent", "Subscription")
    description = Column(String(255), nullable=True)
    
    # Status
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Reminder flags
    reminder_3d_sent = Column(Boolean, default=False)
    reminder_1d_sent = Column(Boolean, default=False)
    reminder_today_sent = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_payment_user_date', 'user_id', 'date'),
        Index('idx_payment_reminders', 'date', 'is_completed', 'reminder_3d_sent'),
    )
    
    # Relationships
    user = relationship("User", back_populates="payments")
    reminders = relationship("PaymentReminder", back_populates="payment", cascade="all, delete-orphan")


class PaymentReminder(Base):
    """Log of sent reminders"""
    __tablename__ = "payment_reminders"
    
    id = Column(Integer, primary_key=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False, index=True)
    reminder_type = Column(String(10), nullable=False)  # '3d', '1d', 'today'
    sent_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    payment = relationship("Payment", back_populates="reminders")
