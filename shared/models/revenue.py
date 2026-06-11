from datetime import datetime, date
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Float, Date
from sqlalchemy.orm import relationship
from .base import Base


class RevenueReport(Base):
    __tablename__ = "revenue_reports"

    id = Column(Integer, primary_key=True, index=True)
    
    # Branch
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    branch = relationship("Branch", backref="revenue_reports")
    
    # Report period
    report_date = Column(Date, nullable=False)
    report_type = Column(String(20), default="daily")  # daily, weekly, monthly
    
    # Metrics
    total_revenue = Column(Float, default=0)
    total_sessions = Column(Integer, default=0)
    total_codes_used = Column(Integer, default=0)
    total_paused_sessions = Column(Integer, default=0)
    average_session_duration = Column(Float, default=0)
    
    # Peak hours
    peak_hour_start = Column(Integer, nullable=True)
    peak_hour_end = Column(Integer, nullable=True)
    
    # Offline support
    local_id = Column(String(100), nullable=True, unique=True)
    synced = Column(Boolean, default=False)
    
    generated_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
