"""Participant CRUD, CSV import and authorization."""
import io

from app.extensions import db


def test_create_participant(auth_client, app):
    auth_client.post("/participants/new", data={
        "first_name": "Test", "last_name": "User",
        "email": "new.user@example.com", "department": "IT",
    }, follow_redirects=True)
    with app.app_context():
        from app.models import Participant
        assert Participant.query.filter_by(email="new.user@example.com").count() == 1


def test_duplicate_participant_rejected(auth_client):
    data = {"first_name": "A", "last_name": "B",
            "email": "dup@example.com", "department": "IT"}
    auth_client.post("/participants/new", data=data, follow_redirects=True)
    resp = auth_client.post("/participants/new", data=data, follow_redirects=True)
    assert b"already exists" in resp.data


def test_invalid_email_rejected(auth_client, app):
    auth_client.post("/participants/new", data={
        "first_name": "Bad", "last_name": "Email",
        "email": "not-an-email", "department": "IT",
    }, follow_redirects=True)
    with app.app_context():
        from app.models import Participant
        assert Participant.query.filter_by(last_name="Email").count() == 0


def test_csv_import(auth_client, app):
    csv_data = ("first_name,last_name,email,department\n"
                "Imp,One,imp.one@example.com,HR\n"
                "Imp,Two,imp.two@example.com,HR\n"
                "Bad,Row,not-an-email,HR\n"
                "Imp,One,imp.one@example.com,HR\n")  # duplicate of row 1
    resp = auth_client.post("/participants/import",
                            data={"file": (io.BytesIO(csv_data.encode()), "p.csv")},
                            content_type="multipart/form-data",
                            follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        from app.models import Participant
        assert Participant.query.filter_by(email="imp.one@example.com").count() == 1
        assert Participant.query.filter_by(email="not-an-email").count() == 0


def test_sample_csv_downloads(auth_client):
    resp = auth_client.get("/participants/sample.csv")
    assert resp.status_code == 200
    assert b"first_name" in resp.data


def test_admin_can_delete_participant(auth_client, app):
    auth_client.post("/participants/new", data={
        "first_name": "Del", "last_name": "Me", "email": "del@example.com",
    }, follow_redirects=True)
    with app.app_context():
        from app.models import Participant
        pid = Participant.query.filter_by(email="del@example.com").first().id
    auth_client.post(f"/participants/{pid}/delete", follow_redirects=True)
    with app.app_context():
        from app.models import Participant
        assert db.session.get(Participant, pid) is None


def test_analyst_cannot_delete_participant(auth_client, analyst_client, app):
    auth_client.post("/participants/new", data={
        "first_name": "Keep", "last_name": "Me", "email": "keep@example.com",
    }, follow_redirects=True)
    with app.app_context():
        from app.models import Participant
        pid = Participant.query.filter_by(email="keep@example.com").first().id
    resp = analyst_client.post(f"/participants/{pid}/delete")
    assert resp.status_code == 403
    with app.app_context():
        from app.models import Participant
        assert db.session.get(Participant, pid) is not None
