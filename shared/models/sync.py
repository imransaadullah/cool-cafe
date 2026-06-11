from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from .base import Base


class OfflineQueue(Base):
    __tablename__ = "offline_queue"

    id = Column(Integer, primary_key=True, index=True)
    
    # Action type: create, update, delete
    action_type = Column(String(20), nullable=False)
    
    # Table name
    table_name = Column(String(100), nullable=False)
    
    # Record ID
    record_id = Column(String(100), nullable=False)
    
    # Payload as JSON
    payload = Column(Text, nullable=False)
    
    # Status
    synced = Column(Boolean, default=False)
    synced_at = Column(DateTime, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
