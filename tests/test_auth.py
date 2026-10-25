"""Authentication & access control."""
from app.extensions import db


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_protected_page_redirects_to_login(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_login_page_loads(client):
    assert client.get("/auth/login").status_code == 200


def test_bad_credentials_rejected(client):
    resp = client.post("/auth/login",
                       data={"email": "admin@example.com", "password": "wrong"})
    assert resp.status_code == 200
    assert "yanlış".encode() in resp.data


def test_dashboard_loads_when_logged_in(auth_client):
    resp = auth_client.get("/")
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data


def test_logout(auth_client):
    assert auth_client.get("/auth/logout").status_code == 302
    assert auth_client.get("/").status_code == 302


def test_unknown_page_404(auth_client):
    assert auth_client.get("/no-such-page").status_code == 404


def test_inactive_user_cannot_login(app):
    with app.app_context():
        from app.models import User
        u = User(name="Off", email="off@example.com", role="analyst", active=False)
        u.set_password("Test1234!")
        db.session.add(u)
        db.session.commit()
    c = app.test_client()
    resp = c.post("/auth/login",
                  data={"email": "off@example.com", "password": "Test1234!"})
    assert "yanlış".encode() in resp.data            # login refused
    assert c.get("/").status_code == 302             # not authenticated


def test_password_is_hashed(app):
    with app.app_context():
        from app.models import User
        u = User.query.filter_by(email="admin@example.com").first()
        assert u.password_hash != "Test1234!"
        assert u.check_password("Test1234!")
