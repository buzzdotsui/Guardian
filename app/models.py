"""
Guardian AI — SQLAlchemy Models
===============================
Defines the schema for the Incident table, which replaces the former
local JSON file artifact approach.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Text, JSON, DateTime
from app.database import Base, engine

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Core Slack Message Info
    user_id = Column(String(50), nullable=False, index=True)
    channel = Column(String(50), nullable=False)
    slack_message = Column(Text, nullable=False)
    
    # Guardian AI Analysis
    ai_reasoning = Column(Text, nullable=False)
    severity = Column(Integer, nullable=False, index=True)
    detected_by = Column(String(20), default="ai")  # 'ai' or 'regex'
    type = Column(String(20), default="system")     # 'system' or 'self_report'
    
    # GitHub Integration
    github_confirmed = Column(Boolean, default=False, index=True)
    github_evidence = Column(JSON, default=list)    # Stores the raw JSON evidence array
    github_url = Column(String(500), nullable=True) # Direct URL to the offending gist/commit
    
    # Feedback tracking
    user_feedback = Column(String(20), nullable=True) # 'dismissed', 'escalated'
    feedback_by = Column(String(50), nullable=True)
    feedback_at = Column(DateTime, nullable=True)
    
    # Policy Metadata
    policy_url = Column(String(500), nullable=True)

    def to_dict(self):
        """Converts the SQLAlchemy model into a dictionary suitable for JSON serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user": self.user_id,
            "channel": self.channel,
            "slack_message": self.slack_message,
            "ai_reasoning": self.ai_reasoning,
            "severity": self.severity,
            "detected_by": self.detected_by,
            "type": self.type,
            "github_confirmed": self.github_confirmed,
            "github_evidence": self.github_evidence,
            "github_url": self.github_url,
            "user_feedback": self.user_feedback,
            "feedback_by": self.feedback_by,
            "feedback_at": self.feedback_at.isoformat() if self.feedback_at else None,
            "policy_url": self.policy_url,
        }

# Automatically create tables if they do not exist
Base.metadata.create_all(bind=engine)
