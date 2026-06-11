from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .base import Base
import enum


class PCStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"


class PC(Base):
    __tablename__ = "pcs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    pc_number = Column(Integer, nullable=False)
    
    # Branch association
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    branch = relationship("Branch", backref="pcs")
    
    # Network info
    ip_address = Column(String(50), nullable=True)
    mac_address = Column(String(50), nullable=True)
    
    # Status
    status = Column(String(20), default=PCStatus.OFFLINE.value)
    last_heartbeat_at = Column(DateTime, nullable=True)
    
    # Current session
    current_session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    current_session = relationship("Session", backref="current_pc", foreign_keys=[current_session_id])
    
    # Config
    config = Column(String(500), nullable=True, default="{}")
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
