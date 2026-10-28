"""Settings, user management and audit log (admin-only)."""
from app.extensions import db


def test_admin_can_open_settings_and_audit(auth_client):
    assert auth_client.get("/settings/").status_code == 200
    assert auth_client.get("/settings/audit").status_code == 200


def test_admin_creates_user(auth_client, app):
    auth_client.post("/settings/", data={
        "name": "New Analyst", "email": "na@example.com",
        "password": "Analyst123", "role": "analyst",
    }, follow_redirects=True)
    with app.app_context():
        from app.models import User
        u = User.query.filter_by(email="na@example.com").first()
        assert u is not None and u.role == "analyst"


def test_analyst_forbidden_from_settings(analyst_client):
    assert analyst_client.get("/settings/").status_code == 403
    assert analyst_client.get("/settings/audit").status_code == 403


def test_admin_cannot_deactivate_self(auth_client, app):
    with app.app_context():
        from app.models import User
        admin = User.query.filter_by(email="admin@example.com").first()
        aid = admin.id
    resp = auth_client.post(f"/settings/users/{aid}/toggle", follow_redirects=True)
    assert b"cannot deactivate your own account" in resp.data
    with app.app_context():
        from app.models import User
        assert db.session.get(User, aid).active is True


def test_audit_log_records_login(auth_client, app):
    with app.app_context():
        from app.models import AuditLog
        assert AuditLog.query.filter_by(action="login").count() >= 1


def test_audit_never_stores_password(auth_client, app):
    with app.app_context():
        from app.models import AuditLog
        for log in AuditLog.query.all():
            assert "Test1234!" not in (log.detail or "")
