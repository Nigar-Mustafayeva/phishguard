"""Risk Intelligence: scoring, explanations, recommendations, pages."""
from app.extensions import db


def _participant_with_clicks(app, clicks=2, submitted=False, reported=False):
    """Create a participant sent 2 campaigns; clicked in `clicks` of them."""
    with app.app_context():
        from app.models import (Campaign, EmailTemplate, Participant,
                                 CampaignEvent, STATUS_COMPLETED,
                                 EVENT_SENT, EVENT_CLICKED, EVENT_SUBMITTED,
                                 EVENT_REPORTED)
        tmpl = EmailTemplate(name="Cred", subject="s", sender_name="n",
                             sender_email="n@example.com", html_body="<p>x</p>",
                             category="credential")
        p = Participant(first_name="Risk", last_name="User",
                        email="risk.user@example.com")
        db.session.add_all([tmpl, p]); db.session.flush()
        c1 = Campaign(name="RC1", status=STATUS_COMPLETED, template=tmpl)
        c2 = Campaign(name="RC2", status=STATUS_COMPLETED, template=tmpl)
        db.session.add_all([c1, c2]); db.session.flush()
        for c in (c1, c2):
            db.session.add(CampaignEvent(campaign_id=c.id, participant_id=p.id,
                                        event_type=EVENT_SENT))
        campaigns = [c1, c2]
        for i in range(clicks):
            db.session.add(CampaignEvent(campaign_id=campaigns[i].id,
                                        participant_id=p.id, event_type=EVENT_CLICKED))
        if submitted:
            db.session.add(CampaignEvent(campaign_id=c1.id, participant_id=p.id,
                                        event_type=EVENT_SUBMITTED))
        if reported:
            db.session.add(CampaignEvent(campaign_id=c2.id, participant_id=p.id,
                                        event_type=EVENT_REPORTED))
        db.session.commit()
        return p.id


def test_high_risk_for_repeat_clicker_who_submitted(app):
    pid = _participant_with_clicks(app, clicks=2, submitted=True)
    with app.app_context():
        from app.models import Participant
        from app.services.risk_service import participant_risk
        r = participant_risk(db.session.get(Participant, pid))
        assert r["has_data"] is True
        assert r["level"] == "high"
        assert r["score"] >= 60
        # Submitting a form -> password/MFA training recommended
        assert r["rec_slug"] == "links-and-passwords"
        assert any("form" in f.lower() for f in r["factors"])


def test_low_risk_for_reporter_no_clicks(app):
    pid = _participant_with_clicks(app, clicks=0, reported=True)
    with app.app_context():
        from app.models import Participant
        from app.services.risk_service import participant_risk
        r = participant_risk(db.session.get(Participant, pid))
        assert r["level"] == "low"
        assert r["score"] < 30
        assert any("report" in f.lower() for f in r["factors"])


def test_no_data_participant(app):
    with app.app_context():
        from app.models import Participant
        from app.services.risk_service import participant_risk
        p = Participant(first_name="No", last_name="Data", email="nd@example.com")
        db.session.add(p); db.session.commit()
        r = participant_risk(p)
        assert r["has_data"] is False


def test_risk_pages_load(auth_client, app):
    pid = _participant_with_clicks(app, clicks=2, submitted=True)
    assert auth_client.get("/risk/").status_code == 200
    resp = auth_client.get(f"/risk/{pid}")
    assert resp.status_code == 200
    assert b"explanation" in resp.data.lower()


def test_org_summary_counts(app):
    _participant_with_clicks(app, clicks=2, submitted=True)   # high
    _participant_with_clicks_distinct(app)                    # low reporter
    with app.app_context():
        from app.services.risk_service import all_risk_profiles, org_summary
        s = org_summary(all_risk_profiles())
        assert s["count"] >= 1
        assert s["high"] >= 1


def _participant_with_clicks_distinct(app):
    """A second participant (distinct email) who only reported."""
    with app.app_context():
        from app.models import (Campaign, Participant, CampaignEvent,
                                 STATUS_COMPLETED, EVENT_SENT, EVENT_REPORTED)
        p = Participant(first_name="Good", last_name="User",
                        email="good.user@example.com")
        db.session.add(p); db.session.flush()
        c = Campaign(name="RC3", status=STATUS_COMPLETED)
        db.session.add(c); db.session.flush()
        db.session.add(CampaignEvent(campaign_id=c.id, participant_id=p.id,
                                    event_type=EVENT_SENT))
        db.session.add(CampaignEvent(campaign_id=c.id, participant_id=p.id,
                                    event_type=EVENT_REPORTED))
        db.session.commit()
        return p.id
