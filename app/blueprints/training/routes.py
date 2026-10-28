"""Security awareness training: articles, quizzes and the phishing inbox lab.

The quiz is answered one question at a time with instant feedback in the
browser, then submitted for grading. Each answer shows whether it was correct
plus an educational explanation. Attempts are recorded for completion tracking.
"""
from flask import Blueprint, render_template, request, abort
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.models import TrainingModule, QuizAttempt
from app.services.training_content import module_meta, render_article

training_bp = Blueprint("training", __name__, url_prefix="/training")


def _options(q):
    pairs = [("A", q.option_a), ("B", q.option_b),
             ("C", q.option_c), ("D", q.option_d)]
    return [(k, v) for k, v in pairs if v]


@training_bp.route("/")
@login_required
def index():
    modules = TrainingModule.query.order_by(TrainingModule.order_index).all()
    attempts = dict(db.session.query(QuizAttempt.module_id, func.count(QuizAttempt.id))
                    .group_by(QuizAttempt.module_id).all())
    cards = [{"mod": m, "meta": module_meta(m.slug), "attempts": attempts.get(m.id, 0)}
             for m in modules]
    total_questions = sum(len(m.questions) for m in modules)
    total_minutes = sum(c["meta"]["minutes"] for c in cards)
    return render_template("training/index.html", cards=cards,
                          total_questions=total_questions,
                          total_minutes=total_minutes,
                          total_attempts=sum(attempts.values()))


@training_bp.route("/lab")
@login_required
def lab():
    """Interactive 'Phish or legit?' inbox simulation (runs in the browser)."""
    return render_template("training/lab.html")


@training_bp.route("/<slug>", methods=["GET", "POST"])
@login_required
def module(slug):
    mod = TrainingModule.query.filter_by(slug=slug).first() or abort(404)
    questions = mod.questions
    article = render_article(mod.content)
    meta = module_meta(mod.slug)
    next_mod = (TrainingModule.query
                .filter(TrainingModule.order_index > mod.order_index)
                .order_by(TrainingModule.order_index).first())

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
        return render_template("training/module.html", mod=mod, meta=meta,
                              article=article, next_mod=next_mod,
                              questions_opts=questions_opts, results=None)

    return render_template("training/module.html", mod=mod, meta=meta,
                          article=article, next_mod=next_mod, results=results,
                          score=score, total=total)
