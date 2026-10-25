"""Model package. Importing this registers every model with SQLAlchemy
so Flask-Migrate can detect them.
"""
from app.models.user import User, ROLE_ADMIN, ROLE_ANALYST
from app.models.participant import Department, Participant
from app.models.campaign import (
    EmailTemplate, Campaign, CampaignParticipant, CampaignEvent,
    STATUS_DRAFT, STATUS_SCHEDULED, STATUS_ACTIVE, STATUS_COMPLETED, STATUS_STOPPED,
    EVENT_SENT, EVENT_DELIVERED, EVENT_OPENED, EVENT_CLICKED,
    EVENT_SUBMITTED, EVENT_REPORTED,
)
from app.models.training import TrainingModule, QuizQuestion, QuizAttempt
from app.models.system import ReportRecord, AuditLog, IntegrationSetting

__all__ = [
    "User", "ROLE_ADMIN", "ROLE_ANALYST",
    "Department", "Participant",
    "EmailTemplate", "Campaign", "CampaignParticipant", "CampaignEvent",
    "STATUS_DRAFT", "STATUS_SCHEDULED", "STATUS_ACTIVE", "STATUS_COMPLETED",
    "STATUS_STOPPED",
    "EVENT_SENT", "EVENT_DELIVERED", "EVENT_OPENED", "EVENT_CLICKED",
    "EVENT_SUBMITTED", "EVENT_REPORTED",
    "TrainingModule", "QuizQuestion", "QuizAttempt",
    "ReportRecord", "AuditLog", "IntegrationSetting",
]
