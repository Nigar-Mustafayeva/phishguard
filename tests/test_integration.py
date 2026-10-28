"""GoPhish integration service: demo mode, status, sync, failure handling."""
from app.extensions import db
from helpers import (seed_template_and_participant, create_campaign,
                           campaign_id_by_name)


def test_check_status_demo_by_default(app):
    with app.app_context():
        from app.services.gophish_service import check_status, demo_mode_active
        assert demo_mode_active() is True
        assert check_status()["mode"] == "demo"


def test_live_mode_unreachable_handled(app):
    """With DEMO_MODE off and a bogus GoPhish URL, status is unreachable (no crash)."""
    with app.app_context():
        from flask import current_app
        from app.services.gophish_service import check_status
        current_app.config.update(
            DEMO_MODE=False,
            GOPHISH_API_URL="https://127.0.0.1:1",  # nothing listening
            GOPHISH_API_KEY="x",
        )
        status = check_status()
        assert status["mode"] == "live"
        assert status["reachable"] is False


def test_integration_page_shows_demo(auth_client):
    resp = auth_client.get("/integration/")
    assert resp.status_code == 200
    assert b"Demo" in resp.data


def test_demo_sync_generates_events(auth_client, app):
    tid, pid = seed_template_and_participant(app)
    create_campaign(auth_client, "SyncC", tid, [pid])
    cid = campaign_id_by_name(app, "SyncC")
    auth_client.post(f"/campaigns/{cid}/launch", follow_redirects=True)
    resp = auth_client.post(f"/campaigns/{cid}/sync", follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        from app.models import CampaignEvent
        assert CampaignEvent.query.filter_by(campaign_id=cid).count() >= 1


def test_cannot_sync_draft(auth_client, app):
    tid, pid = seed_template_and_participant(app)
    create_campaign(auth_client, "DraftSync", tid, [pid])
    cid = campaign_id_by_name(app, "DraftSync")
    resp = auth_client.post(f"/campaigns/{cid}/sync", follow_redirects=True)
    assert b"draft campaign cannot be synced" in resp.data


# Sample GoPhish /api/campaigns/{id} payload (trimmed to what we use).
SAMPLE_GOPHISH_CAMPAIGN = {
    "id": 7,
    "name": "Q4 Awareness Test",
    "status": "Completed",
    "launch_date": "2026-10-01T09:00:00Z",
    "results": [
        {"email": "ali@corp.example", "first_name": "Ali", "last_name": "V"},
        {"email": "sara@corp.example", "first_name": "Sara", "last_name": "K"},
    ],
    "timeline": [
        {"email": "ali@corp.example", "message": "Email Sent", "time": "2026-10-01T09:00:00Z"},
        {"email": "ali@corp.example", "message": "Email Opened", "time": "2026-10-01T09:05:00Z"},
        {"email": "ali@corp.example", "message": "Clicked Link", "time": "2026-10-01T09:06:00Z"},
        {"email": "sara@corp.example", "message": "Email Sent", "time": "2026-10-01T09:00:00Z"},
        {"email": "sara@corp.example", "message": "Email Reported", "time": "2026-10-01T09:10:00Z"},
    ],
}


def test_import_gophish_campaign(app, monkeypatch):
    with app.app_context():
        from flask import current_app
        from app.services import gophish_service
        from app.models import (Campaign, Participant, CampaignEvent,
                                 EVENT_CLICKED, EVENT_REPORTED)
        # Put the service in live mode and stub the network call.
        current_app.config.update(DEMO_MODE=False,
                                  GOPHISH_API_URL="https://gophish.example",
                                  GOPHISH_API_KEY="k")
        monkeypatch.setattr(gophish_service, "fetch_campaign",
                            lambda gid: SAMPLE_GOPHISH_CAMPAIGN)

        msg = gophish_service.import_campaign(7)
        assert "import" in msg.lower()

        camp = Campaign.query.filter_by(gophish_campaign_id=7).first()
        assert camp is not None and camp.name == "Q4 Awareness Test"
        assert Participant.query.filter_by(email="ali@corp.example").count() == 1
        assert CampaignEvent.query.filter_by(campaign_id=camp.id,
                                             event_type=EVENT_CLICKED).count() == 1
        assert CampaignEvent.query.filter_by(campaign_id=camp.id,
                                             event_type=EVENT_REPORTED).count() == 1

        # Re-import must not duplicate participants.
        gophish_service.import_campaign(7)
        assert Participant.query.filter_by(email="ali@corp.example").count() == 1


def test_dashboard_shows_only_imported_campaigns(auth_client, app, monkeypatch):
    # A locally created, launched campaign must NOT appear on the dashboard.
    tid, pid = seed_template_and_participant(app)
    create_campaign(auth_client, "Local Campaign", tid, [pid])
    cid = campaign_id_by_name(app, "Local Campaign")
    auth_client.post(f"/campaigns/{cid}/launch", follow_redirects=True)

    resp = auth_client.get("/dashboard")
    assert b"No imported campaigns yet" in resp.data
    assert b"Local Campaign" not in resp.data

    with app.app_context():
        from flask import current_app
        from app.services import gophish_service
        current_app.config.update(DEMO_MODE=False,
                                  GOPHISH_API_URL="https://gophish.example",
                                  GOPHISH_API_KEY="k")
        monkeypatch.setattr(gophish_service, "fetch_campaign",
                            lambda gid: SAMPLE_GOPHISH_CAMPAIGN)
        gophish_service.import_campaign(7)

    resp = auth_client.get("/dashboard")
    assert b"Q4 Awareness Test" in resp.data
    assert b"Local Campaign" not in resp.data
