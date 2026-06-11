from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from .base import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    
    # Session
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    session = relationship("Session", backref="payments")
    
    # Branch
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    branch = relationship("Branch", backref="payments")
    
    # Amount
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="NGN")
    
    # Payment method: code, cash, konga_pay, paystack
    method = Column(String(50), nullable=False)
    
    # Reference
    reference = Column(String(255), nullable=True)
    payment_reference = Column(String(255), nullable=True)
    
    # Status
    status = Column(String(20), default="completed")
    
    # Offline support
    local_id = Column(String(100), nullable=True, unique=True)
    synced = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
