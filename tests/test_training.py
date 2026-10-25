"""Security awareness training and quiz grading."""
from helpers import seed_training


def test_training_index_and_module(auth_client, app):
    seed_training(app)
    assert auth_client.get("/training/").status_code == 200
    resp = auth_client.get("/training/phishing-basics")
    assert resp.status_code == 200
    assert b"Quiz" in resp.data


def test_quiz_grading_records_attempt(auth_client, app):
    seed_training(app)
    with app.app_context():
        from app.models import TrainingModule
        mod = TrainingModule.query.filter_by(slug="phishing-basics").first()
        answers = {f"q{q.id}": q.correct_option for q in mod.questions}
        total = len(mod.questions)
    resp = auth_client.post("/training/phishing-basics", data=answers)
    assert resp.status_code == 200
    assert f"{total}/{total}".encode() in resp.data
    with app.app_context():
        from app.models import QuizAttempt
        a = QuizAttempt.query.first()
        assert a is not None and a.score == total


def test_quiz_wrong_answers_score_zero(auth_client, app):
    seed_training(app)
    with app.app_context():
        from app.models import TrainingModule
        mod = TrainingModule.query.filter_by(slug="phishing-basics").first()
        # Deliberately pick a wrong option for each question.
        answers = {}
        for q in mod.questions:
            wrong = "A" if q.correct_option != "A" else "B"
            answers[f"q{q.id}"] = wrong
    resp = auth_client.post("/training/phishing-basics", data=answers)
    assert b"0/" in resp.data


def test_seed_training_is_idempotent(app):
    with app.app_context():
        from app.services.training_content import seed_training as st
        from app.models import TrainingModule
        st(); first = TrainingModule.query.count()
        st(); second = TrainingModule.query.count()
        assert first == second
