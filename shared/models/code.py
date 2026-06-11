from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from .base import Base


class Code(Base):
    __tablename__ = "codes"

    id = Column(Integer, primary_key=True, index=True)
    
    # Code value
    code = Column(String(20), nullable=False, unique=True, index=True)
    
    # Duration
    duration_minutes = Column(Float, nullable=False)
    
    # Batch this code belongs to
    batch_id = Column(Integer, ForeignKey("code_batches.id"), nullable=True)
    batch = relationship("CodeBatch", backref="codes")
    
    # Branch
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    branch = relationship("Branch", backref="codes")
    
    # Usage tracking
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)
    used_by_session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    
    # Value in currency
    value = Column(Float, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class CodeBatch(Base):
    __tablename__ = "code_batches"

    id = Column(Integer, primary_key=True, index=True)
    
    # Branch
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    branch = relationship("Branch", backref="code_batches")
    
    # Created by
    created_by_id = Column(Integer, ForeignKey("admins.id"), nullable=True)
    created_by = relationship("Admin", backref="code_batches")
    
    # Batch info
    batch_name = Column(String(100), nullable=True)
    count = Column(Integer, nullable=False)
    duration_minutes = Column(Float, nullable=False)
    value_per_code = Column(Float, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    printed = Column(Boolean, default=False)
    printed_at = Column(DateTime, nullable=True)
    
    # Offline support
    local_id = Column(String(100), nullable=True, unique=True)
    synced = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
