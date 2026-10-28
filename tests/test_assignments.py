"""Adaptive training assignments, public training links, effectiveness,
dashboard campaign filter and removal of imported campaigns."""
import copy
import re

from app.extensions import db
from helpers import (seed_template_and_participant, create_campaign,
                     campaign_id_by_name, seed_training)
from test_integration import SAMPLE_GOPHISH_CAMPAIGN


def _import(app, monkeypatch, payload=SAMPLE_GOPHISH_CAMPAIGN, gid=7):
    with app.app_context():
        from flask import current_app
        from app.services import gophish_service
        current_app.config.update(DEMO_MODE=False,
                                  GOPHISH_API_URL="https://gophish.example",
                                  GOPHISH_API_KEY="k")
        monkeypatch.setattr(gophish_service, "fetch_campaign", lambda _gid: payload)
        gophish_service.import_campaign(gid)
        from app.models import Campaign
        return Campaign.query.filter_by(gophish_campaign_id=gid).first().id


def _pid(app, email):
    with app.app_context():
        from app.models import Participant
        return Participant.query.filter_by(email=email).first().id


def test_rules_recommendation_assign_and_complete(auth_client, app, monkeypatch):
    seed_training(app)
    _import(app, monkeypatch)
    ali = _pid(app, "ali@corp.example")

    # Page lists risk profiles; analyzing without an API key falls back to rules.
    assert b"Who needs training" in auth_client.get("/assignments/").data
    resp = auth_client.post("/assignments/analyze", data={"pid": [ali], "mode": "ai"})
    assert resp.status_code == 200
    assert b"rule-based recommendations" in resp.data

    resp = auth_client.post("/assignments/create", data={
        "pid": [ali], f"m1_{ali}": "phishing-basics", f"m2_{ali}": "",
        f"reason_{ali}": "You clicked a link.", f"source_{ali}": "rules",
        f"risk_{ali}": "55", "send": "0"}, follow_redirects=True)
    assert b"1 training assignments created" in resp.data

    with app.app_context():
        from app.models import TrainingAssignment
        a = TrainingAssignment.query.one()
        token, qs = a.token, {f"q{q.id}": q.correct_option for q in a.module.questions}
        total = len(a.module.questions)

    # Public link works without logging in and records completion.
    public = app.test_client()
    page = public.get(f"/learn/{token}")
    assert page.status_code == 200 and b"Why this module for you" in page.data
    done = public.post(f"/learn/{token}", data=qs)
    assert f"{total}/{total}".encode() in done.data
    with app.app_context():
        from app.models import TrainingAssignment, QuizAttempt
        a = TrainingAssignment.query.one()
        assert a.status == "completed" and a.score == total and a.opened_at
        assert QuizAttempt.query.filter_by(participant_id=ali).count() == 1

    eff = auth_client.get("/assignments/effectiveness")
    assert eff.status_code == 200 and b"100.0" in eff.data   # completion rate


def test_duplicate_open_assignment_not_created(auth_client, app, monkeypatch):
    seed_training(app)
    _import(app, monkeypatch)
    ali = _pid(app, "ali@corp.example")
    data = {"pid": [ali], f"m1_{ali}": "phishing-basics", f"m2_{ali}": "phishing-basics",
            "send": "0"}
    auth_client.post("/assignments/create", data=data)
    auth_client.post("/assignments/create", data=data)
    with app.app_context():
        from app.models import TrainingAssignment
        assert TrainingAssignment.query.count() == 1


def test_ai_recommendations_used_when_available(auth_client, app, monkeypatch):
    seed_training(app)
    _import(app, monkeypatch)
    ali = _pid(app, "ali@corp.example")
    from app.services import assignment_service
    monkeypatch.setattr(assignment_service, "ai_available", lambda: True)
    monkeypatch.setattr(assignment_service, "_ai_recommendations", lambda profiles: {
        ali: {"slugs": ["bec-invoice-fraud"], "reason": "AI says practise invoices.",
              "source": "ai"}})
    resp = auth_client.post("/assignments/analyze", data={"pid": [ali], "mode": "ai"})
    assert b"AI says practise invoices." in resp.data
    assert b'value="bec-invoice-fraud" selected' in resp.data
    assert b"AI explanation" in resp.data


def test_ai_failure_falls_back_to_rules(auth_client, app, monkeypatch):
    seed_training(app)
    _import(app, monkeypatch)
    ali = _pid(app, "ali@corp.example")
    from app.services import assignment_service

    def boom(_profiles):
        raise RuntimeError("network down")
    monkeypatch.setattr(assignment_service, "ai_available", lambda: True)
    monkeypatch.setattr(assignment_service, "_ai_recommendations", boom)
    resp = auth_client.post("/assignments/analyze", data={"pid": [ali], "mode": "ai"})
    assert resp.status_code == 200
    assert b"could not be reached" in resp.data


def test_invitation_email_sent_over_smtp(auth_client, app, monkeypatch):
    seed_training(app)
    _import(app, monkeypatch)
    ali = _pid(app, "ali@corp.example")
    sent = []

    class FakeSMTP:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): pass
        def login(self, u, p): pass
        def sendmail(self, frm, to, body): sent.append((frm, to, body))

    import app.services.assignment_service as svc
    monkeypatch.setattr(svc.smtplib, "SMTP", FakeSMTP)
    with app.app_context():
        from flask import current_app
        current_app.config.update(SMTP_HOST="smtp.example", SMTP_FROM="Security <sec@example.com>",
                                  PUBLIC_BASE_URL="https://pg.example")
    auth_client.post("/assignments/create", data={
        "pid": [ali], f"m1_{ali}": "phishing-basics", "send": "1"})
    assert len(sent) == 1 and sent[0][1] == ["ali@corp.example"]
    import email
    msg = email.message_from_string(sent[0][2])
    text = " ".join(part.get_payload(decode=True).decode()
                    for part in msg.walk() if not part.is_multipart())
    assert re.search(r"https://pg\.example/learn/[\w-]+", text)
    with app.app_context():
        from app.models import TrainingAssignment
        assert TrainingAssignment.query.one().status == "sent"


def test_learn_link_unknown_token_404(client):
    assert client.get("/learn/not-a-real-token").status_code == 404


def test_dashboard_campaign_filter(auth_client, app, monkeypatch):
    _import(app, monkeypatch)
    second = copy.deepcopy(SAMPLE_GOPHISH_CAMPAIGN)
    second["name"] = "Second Import"
    cid2 = _import(app, monkeypatch, second, gid=8)
    all_view = auth_client.get("/dashboard").data
    assert b"All imported campaigns (2)" in all_view
    one = auth_client.get(f"/dashboard?campaign={cid2}").data
    assert b"Showing results for <strong>Second Import</strong>" in one


def test_imported_campaign_can_be_removed(auth_client, app, monkeypatch):
    cid = _import(app, monkeypatch)
    resp = auth_client.post(f"/campaigns/{cid}/delete", data={"next": "//evil.example"})
    assert resp.status_code == 302 and "evil" not in resp.headers["Location"]
    with app.app_context():
        from app.models import Campaign, CampaignEvent
        assert db.session.get(Campaign, cid) is None
        assert CampaignEvent.query.filter_by(campaign_id=cid).count() == 0


def test_locally_launched_campaign_still_protected(auth_client, app):
    tid, pid = seed_template_and_participant(app)
    create_campaign(auth_client, "Live Local", tid, [pid])
    cid = campaign_id_by_name(app, "Live Local")
    auth_client.post(f"/campaigns/{cid}/launch", follow_redirects=True)
    resp = auth_client.post(f"/campaigns/{cid}/delete", follow_redirects=True)
    assert b"Only draft or imported campaigns can be deleted" in resp.data
