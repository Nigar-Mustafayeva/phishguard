"""Public training page reached from an emailed, per-person link.

No login: the long random token in the URL identifies the assignment. Only the
quiz score is stored — never the chosen answers.
"""
from flask import Blueprint, render_template, request, abort

from app.extensions import db
from app.models import TrainingAssignment, QuizAttempt, ASSIGN_COMPLETED
from app.services.assignment_service import mark_opened, mark_completed
from app.services.training_content import module_meta, render_article

learn_bp = Blueprint("learn", __name__, url_prefix="/learn")


def _options(q):
    pairs = [("A", q.option_a), ("B", q.option_b),
             ("C", q.option_c), ("D", q.option_d)]
    return [(k, v) for k, v in pairs if v]


@learn_bp.route("/<token>", methods=["GET", "POST"])
def take(token):
    a = TrainingAssignment.query.filter_by(token=token).first() or abort(404)
    mod = a.module
    questions = mod.questions
    ctx = {"a": a, "mod": mod, "meta": module_meta(mod.slug),
           "article": render_article(mod.content)}

    if request.method == "POST" and a.status != ASSIGN_COMPLETED:
        results, score = [], 0
        for q in questions:
            chosen = request.form.get(f"q{q.id}")
            ok = chosen == q.correct_option
            score += ok
            results.append({"q": q, "chosen": chosen, "options": _options(q)})
        mark_completed(a, score, len(questions))
        db.session.add(QuizAttempt(module_id=mod.id, participant_id=a.participant_id,
                                   score=score, total=len(questions)))
        db.session.commit()
        return render_template("learn/take.html", results=results, score=score,
                              total=len(questions), **ctx)

    if a.status != ASSIGN_COMPLETED:
        mark_opened(a)
        db.session.commit()
    return render_template("learn/take.html", results=None,
                          questions_opts=[(q, _options(q)) for q in questions], **ctx)
