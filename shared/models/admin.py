from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True, unique=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    
    # Role: global_admin, branch_admin, sub_admin
    role = Column(String(50), nullable=False, default="branch_admin")
    
    # Branch association
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    branch = relationship("Branch", backref="admins")
    
    # For hierarchy - who created this admin
    created_by_id = Column(Integer, ForeignKey("admins.id"), nullable=True)
    created_by = relationship("Admin", remote_side="Admin.id", backref="created_admins")
    
    # Status
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
