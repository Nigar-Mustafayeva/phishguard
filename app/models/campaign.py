"""Email templates, campaigns, their participants and tracked events."""
from datetime import datetime

from app.extensions import db

# Campaign status values
STATUS_DRAFT = "draft"
STATUS_SCHEDULED = "scheduled"
STATUS_ACTIVE = "active"
STATUS_COMPLETED = "completed"
STATUS_STOPPED = "stopped"

# Event types we track. NOTE: no passwords or form field values are ever stored.
EVENT_SENT = "sent"
EVENT_DELIVERED = "delivered"
EVENT_OPENED = "opened"
EVENT_CLICKED = "clicked"
EVENT_SUBMITTED = "submitted"   # user submitted the training form (fact only)
EVENT_REPORTED = "reported"     # user reported the email as phishing


class EmailTemplate(db.Model):
    __tablename__ = "email_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    sender_name = db.Column(db.String(120), nullable=False)
    sender_email = db.Column(db.String(255), nullable=False)
    html_body = db.Column(db.Text, nullable=False, default="")
    category = db.Column(db.String(60), nullable=True)   # e.g. "credential", "update"
    is_demo = db.Column(db.Boolean, nullable=False, default=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    campaigns = db.relationship("Campaign", back_populates="template")

    def __repr__(self) -> str:
        return f"<EmailTemplate {self.name}>"


class Campaign(db.Model):
    __tablename__ = "campaigns"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_DRAFT)
    template_id = db.Column(
        db.Integer, db.ForeignKey("email_templates.id"), nullable=True
    )
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    scheduled_at = db.Column(db.DateTime, nullable=True)
    launched_at = db.Column(db.DateTime, nullable=True)
    is_demo = db.Column(db.Boolean, nullable=False, default=True)
    # Links this campaign to a GoPhish campaign (live mode). Null in demo mode.
    gophish_campaign_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    template = db.relationship("EmailTemplate", back_populates="campaigns")
    participants = db.relationship(
        "CampaignParticipant", back_populates="campaign",
        cascade="all, delete-orphan",
    )
    events = db.relationship(
        "CampaignEvent", back_populates="campaign",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Campaign {self.name} ({self.status})>"


class CampaignParticipant(db.Model):
    """Join table: which participants are targeted by a campaign."""
    __tablename__ = "campaign_participants"
    __table_args__ = (
        db.UniqueConstraint("campaign_id", "participant_id",
                            name="uq_campaign_participant"),
    )

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(
        db.Integer, db.ForeignKey("campaigns.id"), nullable=False, index=True
    )
    participant_id = db.Column(
        db.Integer, db.ForeignKey("participants.id"), nullable=False, index=True
    )

    campaign = db.relationship("Campaign", back_populates="participants")
    participant = db.relationship("Participant")


class CampaignEvent(db.Model):
    """One tracked interaction. Stores the FACT of an event, never credentials."""
    __tablename__ = "campaign_events"

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(
        db.Integer, db.ForeignKey("campaigns.id"), nullable=False, index=True
    )
    participant_id = db.Column(
        db.Integer, db.ForeignKey("participants.id"), nullable=True, index=True
    )
    event_type = db.Column(db.String(20), nullable=False, index=True)
    source = db.Column(db.String(20), nullable=False, default="demo")  # demo|gophish|manual
    occurred_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # Safe, non-sensitive metadata only (e.g. user-agent category). Never passwords.
    detail = db.Column(db.Text, nullable=True)

    campaign = db.relationship("Campaign", back_populates="events")
    participant = db.relationship("Participant")

    def __repr__(self) -> str:
        return f"<CampaignEvent {self.event_type} c={self.campaign_id}>"
