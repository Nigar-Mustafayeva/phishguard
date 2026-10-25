"""Email template CRUD, validation, preview and test-send."""
from helpers import make_template


def test_create_template_and_preview(auth_client, app):
    resp = make_template(auth_client, name="IT Reset")
    assert resp.status_code == 200
    assert "Aysel".encode() in resp.data  # personalized preview
    with app.app_context():
        from app.models import EmailTemplate
        assert EmailTemplate.query.filter_by(name="IT Reset").count() == 1


def test_template_requires_html_body(auth_client, app):
    auth_client.post("/templates/new", data={
        "name": "NoBody", "subject": "S", "sender_name": "N",
        "sender_email": "n@example.com", "category": "credential",
        "html_body": "",   # missing
    }, follow_redirects=True)
    with app.app_context():
        from app.models import EmailTemplate
        assert EmailTemplate.query.filter_by(name="NoBody").count() == 0


def test_test_email_blocked_without_mailtrap(auth_client, app):
    make_template(auth_client, name="IT Reset")
    with app.app_context():
        from app.models import EmailTemplate
        tid = EmailTemplate.query.filter_by(name="IT Reset").first().id
    resp = auth_client.post(f"/templates/{tid}/preview",
                            data={"recipient": "x@example.com"},
                            follow_redirects=True)
    assert "konfiqurasiya".encode() in resp.data


def test_analyst_cannot_delete_template(auth_client, analyst_client, app):
    make_template(auth_client, name="KeepT")
    with app.app_context():
        from app.models import EmailTemplate
        tid = EmailTemplate.query.filter_by(name="KeepT").first().id
    resp = analyst_client.post(f"/templates/{tid}/delete")
    assert resp.status_code == 403


def test_personalization_is_safe_from_template_injection(app):
    """Ensure {{ }} tokens are replaced literally, not evaluated as code."""
    with app.app_context():
        from app.services.mail_service import render_personalized
        out = render_personalized("{{7*7}} {{first_name}}")
        assert "49" not in out          # not evaluated
        assert "Aysel" in out           # known token replaced
