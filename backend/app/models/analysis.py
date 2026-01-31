from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)  # attach later
    channel_url = Column(String, nullable=False)
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    videos = relationship("Video", back_populates="analysis")


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analysis_runs.id"))
    video_id = Column(String)
    title = Column(String)
    views = Column(Integer)
    likes = Column(Integer)
    comments = Column(Integer)
    engagement_rate = Column(Float)

    analysis = relationship("AnalysisRun", back_populates="videos")
    source = Column(String, default="own") 