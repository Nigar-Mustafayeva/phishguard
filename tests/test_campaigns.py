"""Campaign CRUD and lifecycle (launch/stop/edit/delete)."""
from app.extensions import db
from helpers import (seed_template_and_participant, create_campaign,
                           campaign_id_by_name)


def test_create_and_launch_campaign(auth_client, app):
    tid, pid = seed_template_and_participant(app)
    create_campaign(auth_client, "C1", tid, [pid])
    cid = campaign_id_by_name(app, "C1")
    with app.app_context():
        from app.models import Campaign, STATUS_DRAFT
        assert db.session.get(Campaign, cid).status == STATUS_DRAFT

    auth_client.post(f"/campaigns/{cid}/launch", follow_redirects=True)
    with app.app_context():
        from app.models import Campaign, CampaignEvent, STATUS_ACTIVE, EVENT_SENT
        assert db.session.get(Campaign, cid).status == STATUS_ACTIVE
        assert CampaignEvent.query.filter_by(campaign_id=cid,
                                             event_type=EVENT_SENT).count() == 1


def test_cannot_launch_twice(auth_client, app):
    tid, pid = seed_template_and_participant(app)
    create_campaign(auth_client, "C2", tid, [pid])
    cid = campaign_id_by_name(app, "C2")
    auth_client.post(f"/campaigns/{cid}/launch", follow_redirects=True)
    resp = auth_client.post(f"/campaigns/{cid}/launch", follow_redirects=True)
    assert b"already been launched" in resp.data


def test_launch_requires_participants(auth_client, app):
    tid, _ = seed_template_and_participant(app)
    create_campaign(auth_client, "C3", tid)
    cid = campaign_id_by_name(app, "C3")
    resp = auth_client.post(f"/campaigns/{cid}/launch", follow_redirects=True)
    assert b"Add at least one participant" in resp.data


def test_edit_draft_then_cannot_edit_after_launch(auth_client, app):
    tid, pid = seed_template_and_participant(app)
    create_campaign(auth_client, "C4", tid, [pid])
    cid = campaign_id_by_name(app, "C4")
    # edit while draft
    auth_client.post(f"/campaigns/{cid}/edit", data={
        "name": "C4 renamed", "template_id": tid, "participant_ids": [pid],
    }, follow_redirects=True)
    with app.app_context():
        from app.models import Campaign
        assert db.session.get(Campaign, cid).name == "C4 renamed"
    # launch, then editing is blocked
    auth_client.post(f"/campaigns/{cid}/launch", follow_redirects=True)
    resp = auth_client.get(f"/campaigns/{cid}/edit", follow_redirects=True)
    assert b"only draft campaigns" in resp.data.lower()


def test_stop_active_campaign(auth_client, app):
    tid, pid = seed_template_and_participant(app)
    create_campaign(auth_client, "C5", tid, [pid])
    cid = campaign_id_by_name(app, "C5")
    auth_client.post(f"/campaigns/{cid}/launch", follow_redirects=True)
    auth_client.post(f"/campaigns/{cid}/stop", follow_redirects=True)
    with app.app_context():
        from app.models import Campaign, STATUS_COMPLETED
        assert db.session.get(Campaign, cid).status == STATUS_COMPLETED


def test_analyst_cannot_delete_campaign(auth_client, analyst_client, app):
    tid, pid = seed_template_and_participant(app)
    create_campaign(auth_client, "C6", tid, [pid])
    cid = campaign_id_by_name(app, "C6")
    resp = analyst_client.post(f"/campaigns/{cid}/delete")
    assert resp.status_code == 403
