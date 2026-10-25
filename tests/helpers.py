"""Reusable helpers for tests (not test cases themselves)."""
from app.extensions import db


def make_template(client, name="T1"):
    return client.post("/templates/new", data={
        "name": name, "subject": "S", "sender_name": "N",
        "sender_email": "n@example.com", "category": "credential",
        "html_body": "<p>Salam {{first_name}}, <a href='#'>klik</a></p>",
    }, follow_redirects=True)


def create_campaign(client, name, template_id, participant_ids=None):
    data = {"name": name, "template_id": template_id}
    if participant_ids:
        data["participant_ids"] = participant_ids
    return client.post("/campaigns/new", data=data, follow_redirects=True)


def seed_template_and_participant(app):
    """Insert one template and one participant directly. Returns (tid, pid)."""
    with app.app_context():
        from app.models import EmailTemplate, Participant
        t = EmailTemplate(name="T", subject="S", sender_name="N",
                          sender_email="n@example.com", html_body="<p>hi</p>")
        p = Participant(first_name="P", last_name="One", email="p.one@example.com")
        db.session.add_all([t, p])
        db.session.commit()
        return t.id, p.id


def seed_training(app):
    with app.app_context():
        from app.services.training_content import seed_training as st
        st()


def campaign_id_by_name(app, name):
    with app.app_context():
        from app.models import Campaign
        c = Campaign.query.filter_by(name=name).first()
        return c.id if c else None
