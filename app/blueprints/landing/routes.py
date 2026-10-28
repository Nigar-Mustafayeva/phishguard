"""Public landing page: the first thing visitors see before signing in."""
from flask import Blueprint, render_template

from app.models import TrainingModule, QuizQuestion

landing_bp = Blueprint("landing", __name__)


@landing_bp.route("/")
def index():
    # Only non-sensitive aggregate counts are shown publicly.
    return render_template("landing/index.html",
                          module_count=TrainingModule.query.count(),
                          question_count=QuizQuestion.query.count())
