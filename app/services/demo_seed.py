"""Idempotent demo-data seeding, safe for repeated runs on deploy.

seed_demo(reset=False) only seeds when the database has no campaigns yet, so a
service restart never wipes data. seed_demo(reset=True) clears demo rows first
(used by the local seed.py script).
"""
from datetime import datetime, timedelta

from app.extensions import db
from app.models import (Department, Participant, EmailTemplate, Campaign,
                        CampaignParticipant, CampaignEvent,
                        STATUS_ACTIVE, STATUS_COMPLETED, STATUS_DRAFT,
                        EVENT_SENT, EVENT_OPENED, EVENT_CLICKED,
                        EVENT_SUBMITTED, EVENT_REPORTED)
from app.services.training_content import seed_training

DEPARTMENTS = ["IT", "Finance", "HR", "Sales"]

PARTICIPANTS = [
    ("Aysel", "Məmmədova", "IT"), ("Rauf", "Əliyev", "IT"),
    ("Nigar", "Hüseynova", "Finance"), ("Elvin", "Quliyev", "Finance"),
    ("Günel", "Rəhimova", "HR"), ("Tural", "İsmayılov", "HR"),
    ("Leyla", "Kərimova", "Sales"), ("Orxan", "Babayev", "Sales"),
]

TEMPLATES = [
    dict(name="IT Password Reset", subject="Action required: your password expires today",
         sender_name="IT Support", sender_email="it-support@example.com",
         category="credential",
         html_body="<p>Dear {{first_name}}, your password will be reset within "
                   "24 hours. <a href='#'>Click here to keep your current password</a>.</p>"),
    dict(name="Software Update Notice", subject="Urgent: security update required",
         sender_name="System Administrator", sender_email="updates@example.com",
         category="update",
         html_body="<p>Hi {{first_name}}, a critical security update is "
                   "available for your device. <a href='#'>Install it now</a>.</p>"),
]


# Old (Azerbaijani) demo values -> English, for databases seeded earlier.
_LEGACY_DEPARTMENTS = {"Maliyyə": "Finance", "Satış": "Sales"}
_LEGACY_DESCRIPTIONS = {"Demo kampaniya (nümunə data).": "Demo campaign (sample data)."}


def refresh_demo_text() -> None:
    """Update demo rows created by older seeds to the current English text.

    Only touches demo templates (matched by name), the two renamed demo
    departments and the demo campaign description. Idempotent.
    """
    for t in TEMPLATES:
        row = EmailTemplate.query.filter_by(name=t["name"], is_demo=True).first()
        if row:
            for key in ("subject", "sender_name", "html_body"):
                setattr(row, key, t[key])
    for old, new in _LEGACY_DEPARTMENTS.items():
        dept = Department.query.filter_by(name=old).first()
        if dept and not Department.query.filter_by(name=new).first():
            dept.name = new
    for old, new in _LEGACY_DESCRIPTIONS.items():
        Campaign.query.filter_by(description=old, is_demo=True).update({"description": new})
    db.session.commit()


def _clear_demo():
    CampaignEvent.query.delete()
    CampaignParticipant.query.delete()
    Campaign.query.filter_by(is_demo=True).delete()
    EmailTemplate.query.filter_by(is_demo=True).delete()
    Participant.query.filter_by(is_demo=True).delete()
    Department.query.delete()
    db.session.commit()


def seed_demo(reset: bool = False) -> bool:
    """Seed demo data. Returns True if it seeded, False if it skipped."""
    if reset:
        _clear_demo()
    elif Campaign.query.count() > 0:
        # Data already present — do not duplicate or wipe.
        refresh_demo_text()
        seed_training()
        return False

    depts = {name: Department(name=name) for name in DEPARTMENTS}
    db.session.add_all(depts.values())
    db.session.flush()

    participants = []
    for first, last, dept in PARTICIPANTS:
        p = Participant(
            first_name=first, last_name=last,
            email=f"{first.lower()}.{last.lower()}@example.com".replace("ə", "e"),
            department=depts[dept], is_demo=True)
        participants.append(p)
    db.session.add_all(participants)

    templates = [EmailTemplate(is_demo=True, **t) for t in TEMPLATES]
    db.session.add_all(templates)
    db.session.flush()

    camp = Campaign(name="IT Password Reset",
                    description="Demo campaign (sample data).",
                    status=STATUS_COMPLETED, template=templates[0], is_demo=True,
                    launched_at=datetime.utcnow() - timedelta(days=20))
    db.session.add(camp)
    db.session.flush()

    base = datetime.utcnow() - timedelta(days=20)
    for i, p in enumerate(participants):
        db.session.add(CampaignParticipant(campaign_id=camp.id, participant_id=p.id))
        db.session.add(CampaignEvent(campaign_id=camp.id, participant_id=p.id,
                                     event_type=EVENT_SENT, source="demo",
                                     occurred_at=base))
        if i < 6:
            db.session.add(CampaignEvent(campaign_id=camp.id, participant_id=p.id,
                                         event_type=EVENT_OPENED, source="demo",
                                         occurred_at=base + timedelta(hours=1)))
        if i < 3:
            db.session.add(CampaignEvent(campaign_id=camp.id, participant_id=p.id,
                                         event_type=EVENT_CLICKED, source="demo",
                                         occurred_at=base + timedelta(hours=2)))
        if i == 0:
            db.session.add(CampaignEvent(campaign_id=camp.id, participant_id=p.id,
                                         event_type=EVENT_SUBMITTED, source="demo",
                                         occurred_at=base + timedelta(hours=2, minutes=5)))
        if i in (6, 7):
            db.session.add(CampaignEvent(campaign_id=camp.id, participant_id=p.id,
                                         event_type=EVENT_REPORTED, source="demo",
                                         occurred_at=base + timedelta(hours=3)))

    db.session.add(Campaign(name="HR Bonus Notice", status=STATUS_ACTIVE,
                            template=templates[1], is_demo=True,
                            launched_at=datetime.utcnow() - timedelta(days=3)))
    db.session.add(Campaign(name="Software Update", status=STATUS_DRAFT,
                            template=templates[1], is_demo=True))
    db.session.commit()

    seed_training()
    return True
