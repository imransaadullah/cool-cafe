from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class FilterRule(Base):
    __tablename__ = "filter_rules"

    id = Column(Integer, primary_key=True, index=True)
    
    # Branch - null means global rule
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    branch = relationship("Branch", backref="filter_rules")
    
    # Rule type: dns, process, url
    rule_type = Column(String(20), nullable=False)
    
    # Pattern to match
    pattern = Column(String(500), nullable=False)
    
    # Action: block, allow, log
    action = Column(String(20), default="block")
    
    # Priority
    priority = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Description
    description = Column(String(500), nullable=True)
    
    # Offline support
    local_id = Column(String(100), nullable=True, unique=True)
    synced = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
