"""Metric calculations, results pages, and report generation."""
from app.extensions import db
from helpers import (seed_template_and_participant, create_campaign,
                           campaign_id_by_name)


def _campaign_with_funnel(app):
    """Create a campaign with a known event funnel. Returns its id."""
    with app.app_context():
        from app.models import (Campaign, Participant, CampaignParticipant,
                                 CampaignEvent, STATUS_COMPLETED,
                                 EVENT_SENT, EVENT_OPENED, EVENT_CLICKED)
        c = Campaign(name="Funnel", status=STATUS_COMPLETED)
        p1 = Participant(first_name="A", last_name="A", email="fa@example.com")
        p2 = Participant(first_name="B", last_name="B", email="fb@example.com")
        db.session.add_all([c, p1, p2]); db.session.flush()
        for p in (p1, p2):
            db.session.add(CampaignParticipant(campaign_id=c.id, participant_id=p.id))
            db.session.add(CampaignEvent(campaign_id=c.id, participant_id=p.id,
                                        event_type=EVENT_SENT))
        db.session.add(CampaignEvent(campaign_id=c.id, participant_id=p1.id,
                                     event_type=EVENT_OPENED))
        db.session.add(CampaignEvent(campaign_id=c.id, participant_id=p1.id,
                                     event_type=EVENT_CLICKED))
        db.session.commit()
        return c.id


def test_metrics_calculation(app):
    cid = _campaign_with_funnel(app)
    with app.app_context():
        from app.models import Campaign
        from app.services.metrics import campaign_metrics
        m = campaign_metrics(db.session.get(Campaign, cid))
        assert m["sent"] == 2
        assert m["opened"] == 1 and m["clicked"] == 1
        assert m["click_rate"] == 50.0
        assert m["open_rate"] == 50.0


def test_metrics_no_events_no_division_error(app):
    with app.app_context():
        from app.models import Campaign
        from app.services.metrics import campaign_metrics
        c = Campaign(name="Empty", status="active")
        db.session.add(c); db.session.commit()
        m = campaign_metrics(c)
        assert m["sent"] == 0 and m["click_rate"] == 0.0


def test_overall_metrics(app):
    _campaign_with_funnel(app)
    with app.app_context():
        from app.services.metrics import overall_metrics
        o = overall_metrics()
        assert o["sent"] >= 2 and o["clicked"] >= 1


def test_results_pages_load(auth_client, app):
    cid = _campaign_with_funnel(app)
    assert auth_client.get("/results/").status_code == 200
    resp = auth_client.get(f"/results/{cid}")
    assert resp.status_code == 200
    assert b"Funnel" in resp.data


def test_csv_report(auth_client, app):
    cid = _campaign_with_funnel(app)
    resp = auth_client.get(f"/reports/{cid}/csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.content_type
    assert b"Metric" in resp.data


def test_pdf_report_and_record(auth_client, app):
    cid = _campaign_with_funnel(app)
    resp = auth_client.get(f"/reports/{cid}/pdf")
    assert resp.status_code == 200
    assert resp.content_type == "application/pdf"
    assert resp.data[:4] == b"%PDF"
    with app.app_context():
        from app.models import ReportRecord
        assert ReportRecord.query.filter_by(campaign_id=cid, format="pdf").count() == 1


def test_observations_recommend_training_on_high_click_rate(app):
    with app.app_context():
        from app.services.report_service import build_observations
        obs = build_observations({"sent": 10, "click_rate": 40.0,
                                  "report_rate": 5.0, "submitted": 2})
        text = " ".join(obs)
        assert "training" in text.lower()
