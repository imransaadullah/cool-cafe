from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey, String, Float
from sqlalchemy.orm import relationship
from .base import Base
import enum


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    
    # PC and branch
    pc_id = Column(Integer, ForeignKey("pcs.id"), nullable=False)
    pc = relationship("PC", backref="sessions")
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    branch = relationship("Branch", backref="sessions")
    
    # Code used to start session
    code_id = Column(Integer, ForeignKey("codes.id"), nullable=True)
    code = relationship("Code", backref="sessions")
    
    # Time tracking
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    total_paused_minutes = Column(Float, default=0)
    
    # Session duration in minutes
    duration_minutes = Column(Float, nullable=False)
    
    # Remaining time when paused
    remaining_minutes = Column(Float, nullable=True)
    
    # Status
    status = Column(String(20), default=SessionStatus.ACTIVE.value)
    is_active = Column(Boolean, default=True)
    
    # Billing
    amount_charged = Column(Float, default=0)
    
    # Offline support
    local_id = Column(String(100), nullable=True, unique=True)
    synced = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
