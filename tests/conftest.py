"""Shared pytest fixtures for all test modules."""
import pytest

from app import create_app
from app.extensions import db
from app.models import User, ROLE_ADMIN


@pytest.fixture
def app(tmp_path):
    app = create_app("development", test_config={
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path/'test.db'}",
    })
    with app.app_context():
        db.create_all()
        admin = User(name="Test Admin", email="admin@example.com", role=ROLE_ADMIN)
        admin.set_password("Test1234!")
        db.session.add(admin)
        db.session.commit()
    # yield OUTSIDE the app context so client requests don't inherit a leaked
    # context (which would cache current_user across clients).
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(app):
    """Logged-in admin client."""
    c = app.test_client()
    c.post("/auth/login", data={"email": "admin@example.com",
                               "password": "Test1234!"})
    return c


@pytest.fixture
def analyst_client(app, auth_client):
    """Logged-in analyst client (created via the admin settings page)."""
    auth_client.post("/settings/", data={
        "name": "Analyst", "email": "analyst@example.com",
        "password": "Analyst123", "role": "analyst",
    }, follow_redirects=True)
    c = app.test_client()
    c.post("/auth/login", data={"email": "analyst@example.com",
                               "password": "Analyst123"})
    return c
