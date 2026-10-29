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


def test_create_campaign_with_csv_upload(auth_client, app):
    import io
    tid, pid = seed_template_and_participant(app)
    # Excel in many locales saves with ";" and capitalised headers.
    csv_data = ("First Name;Last Name;Email;Position\n"
                "New;Person;new.person@example.com;Sales\n"
                "P;One;P.ONE@example.com;IT\n"          # already exists
                "Broken;Row;not-an-email;IT\n")
    resp = auth_client.post("/campaigns/new", data={
        "name": "CSV camp", "template_id": tid,
        "csv_file": (io.BytesIO(csv_data.encode("cp1254")), "people.csv"),
    }, content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    cid = campaign_id_by_name(app, "CSV camp")
    with app.app_context():
        from app.models import CampaignParticipant, Participant
        emails = {cp.participant.email for cp in
                  CampaignParticipant.query.filter_by(campaign_id=cid)}
        assert emails == {"new.person@example.com", "p.one@example.com"}
        assert Participant.query.filter_by(email="p.one@example.com").count() == 1
        assert Participant.query.filter_by(
            email="new.person@example.com").first().department.name == "Sales"


def test_csv_without_email_column_shows_error(auth_client, app):
    import io
    tid, _ = seed_template_and_participant(app)
    resp = auth_client.post("/campaigns/new", data={
        "name": "Bad CSV", "template_id": tid,
        "csv_file": (io.BytesIO(b"name,phone\nA,1\n"), "x.csv"),
    }, content_type="multipart/form-data", follow_redirects=True)
    assert b"No email column found" in resp.data
    assert campaign_id_by_name(app, "Bad CSV") is None


def test_delete_imported_campaign_with_report_history(auth_client, app):
    with app.app_context():
        from app.models import Campaign, ReportRecord, STATUS_COMPLETED
        camp = Campaign(name="Imported", status=STATUS_COMPLETED,
                        is_demo=False, gophish_campaign_id=42)
        db.session.add(camp)
        db.session.flush()
        db.session.add(ReportRecord(campaign_id=camp.id, format="pdf"))
        db.session.commit()
        cid = camp.id
    resp = auth_client.post(f"/campaigns/{cid}/delete",
                            data={"next": "/dashboard"}, follow_redirects=False)
    assert resp.headers["Location"].endswith("/dashboard")
    with app.app_context():
        from app.models import Campaign, ReportRecord
        assert db.session.get(Campaign, cid) is None
        assert ReportRecord.query.one().campaign_id is None
