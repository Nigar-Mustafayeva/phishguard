"""Database schema / migration sanity checks."""
from app.extensions import db

EXPECTED_TABLES = {
    "users", "departments", "participants", "email_templates", "campaigns",
    "campaign_participants", "campaign_events", "training_modules",
    "quiz_questions", "quiz_attempts", "report_records", "audit_logs",
    "integration_settings",
}


def test_all_expected_tables_exist(app):
    with app.app_context():
        from sqlalchemy import inspect
        tables = set(inspect(db.engine).get_table_names())
        missing = EXPECTED_TABLES - tables
        assert not missing, f"Missing tables: {missing}"


def test_campaign_has_gophish_column(app):
    """The Stage 7 migration added gophish_campaign_id."""
    with app.app_context():
        from sqlalchemy import inspect
        cols = {c["name"] for c in inspect(db.engine).get_columns("campaigns")}
        assert "gophish_campaign_id" in cols


def test_participant_email_is_unique(app):
    with app.app_context():
        from app.models import Participant
        p1 = Participant(first_name="A", last_name="A", email="u@example.com")
        db.session.add(p1)
        db.session.commit()
        p2 = Participant(first_name="B", last_name="B", email="u@example.com")
        db.session.add(p2)
        import pytest
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
