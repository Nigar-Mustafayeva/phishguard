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
    assert "Qaralama".encode() in resp.data
