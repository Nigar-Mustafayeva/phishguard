"""Security awareness training: articles + multiple-choice quizzes.

After submitting a quiz, each answer shows whether it was correct plus an
educational explanation. Attempts are recorded for completion tracking.
"""
from flask import Blueprint, render_template, request, abort
from flask_login import login_required

from app.extensions import db
from app.models import TrainingModule, QuizAttempt

training_bp = Blueprint("training", __name__, url_prefix="/training")


def _options(q):
    pairs = [("A", q.option_a), ("B", q.option_b),
             ("C", q.option_c), ("D", q.option_d)]
    return [(k, v) for k, v in pairs if v]


@training_bp.route("/")
@login_required
def index():
    modules = TrainingModule.query.order_by(TrainingModule.order_index).all()
    return render_template("training/index.html", modules=modules)


@training_bp.route("/<slug>", methods=["GET", "POST"])
@login_required
def module(slug):
    mod = TrainingModule.query.filter_by(slug=slug).first() or abort(404)
    questions = mod.questions

    results = None
    score = total = 0
    if request.method == "POST":
        results = []
        total = len(questions)
        for q in questions:
            chosen = request.form.get(f"q{q.id}")
            is_correct = (chosen == q.correct_option)
            if is_correct:
                score += 1
            results.append({"q": q, "chosen": chosen, "correct": is_correct,
                            "options": _options(q)})
        db.session.add(QuizAttempt(module_id=mod.id, participant_id=None,
                                   score=score, total=total))
        db.session.commit()
    else:
        questions_opts = [(q, _options(q)) for q in questions]
        return render_template("training/module.html", mod=mod,
                              questions_opts=questions_opts, results=None)

    return render_template("training/module.html", mod=mod, results=results,
                          score=score, total=total)
