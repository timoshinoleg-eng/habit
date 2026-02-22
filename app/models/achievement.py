# -*- coding: utf-8 -*-
"""
Achievement model
"""
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base


class Achievement(Base):
    """User achievements"""
    __tablename__ = "achievements"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    
    # Achievement details
    achievement_type = Column(String(50), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(String(255), nullable=False)
    icon = Column(String(10), nullable=False)
    
    # When unlocked
    unlocked_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="achievements")
