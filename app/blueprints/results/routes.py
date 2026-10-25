"""Results & event tracking.

Shows the funnel (sent -> opened -> clicked -> submitted / reported) per
campaign and a detailed event timeline. No passwords or submitted form values
are ever stored — only the FACT that an event occurred.
"""
from flask import Blueprint, render_template, abort
from flask_login import login_required

from app.extensions import db
from app.models import Campaign, CampaignEvent
from app.services.metrics import campaign_metrics

results_bp = Blueprint("results", __name__, url_prefix="/results")


@results_bp.route("/")
@login_required
def index():
    campaigns = Campaign.query.order_by(Campaign.id.desc()).all()
    rows = [(c, campaign_metrics(c)) for c in campaigns]
    return render_template("results/index.html", rows=rows)


@results_bp.route("/<int:cid>")
@login_required
def detail(cid):
    camp = db.session.get(Campaign, cid) or abort(404)
    metrics = campaign_metrics(camp)
    events = (CampaignEvent.query
              .filter_by(campaign_id=cid)
              .order_by(CampaignEvent.occurred_at.desc())
              .limit(200).all())
    return render_template("results/detail.html", camp=camp,
                          metrics=metrics, events=events)
