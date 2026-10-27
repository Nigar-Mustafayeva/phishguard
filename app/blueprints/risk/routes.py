"""Risk Intelligence: org risk overview, per-participant profiles,
adaptive training recommendations and training-effectiveness trend.
"""
from flask import Blueprint, render_template, abort
from flask_login import login_required

from app.extensions import db
from app.models import Participant
from app.services.risk_service import (all_risk_profiles, org_summary,
                                       participant_risk, training_effectiveness)

risk_bp = Blueprint("risk", __name__, url_prefix="/risk")


@risk_bp.route("/")
@login_required
def index():
    profiles = all_risk_profiles()
    return render_template("risk/index.html",
                          profiles=profiles,
                          summary=org_summary(profiles),
                          effectiveness=training_effectiveness())


@risk_bp.route("/<int:pid>")
@login_required
def detail(pid):
    p = db.session.get(Participant, pid) or abort(404)
    return render_template("risk/detail.html", risk=participant_risk(p))
