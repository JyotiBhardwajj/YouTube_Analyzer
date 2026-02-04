from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    onboarding_complete = Column(Boolean, default=False)
    role = Column(String, nullable=True)
    goal = Column(String, nullable=True)
    weekly_summary_enabled = Column(Boolean, default=True)
    competitor_alerts_enabled = Column(Boolean, default=True)
