"""Dashboard: figures for campaigns imported from GoPhish.

Only campaigns linked to a GoPhish campaign (gophish_campaign_id set) are
shown, so demo and locally created campaigns do not mix into the real numbers.
All figures are computed from stored database records.
"""
from flask import Blueprint, render_template
from flask_login import login_required

from app.models import Campaign, CampaignParticipant, STATUS_DRAFT
from app.services.metrics import (overall_metrics, campaign_metrics,
                                  department_breakdown)
from app.services.risk_service import all_risk_profiles, org_summary

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    imported = (Campaign.query
                .filter(Campaign.gophish_campaign_id.isnot(None))
                .order_by(Campaign.id.desc()).all())
    ids = [c.id for c in imported]

    totals = overall_metrics(imported)
    totals["participants"] = (CampaignParticipant.query
                              .filter(CampaignParticipant.campaign_id.in_(ids))
                              .with_entities(CampaignParticipant.participant_id)
                              .distinct().count()) if ids else 0

    # Per-campaign click% vs report% for launched campaigns (chart data)
    launched = [c for c in imported if c.status != STATUS_DRAFT][:8]
    launched = list(reversed(launched))
    chart = {"labels": [], "clicks": [], "reports": []}
    for c in launched:
        m = campaign_metrics(c)
        chart["labels"].append(c.name)
        chart["clicks"].append(m["click_rate"])
        chart["reports"].append(m["report_rate"])

    departments = [d for d in department_breakdown(ids) if d["participants"] > 0]

    recent = []
    for c in imported[:5]:
        m = campaign_metrics(c)
        recent.append({"id": c.id, "name": c.name, "status": c.status,
                       "sent": m["sent"], "clicks": m["clicked"],
                       "click_rate": m["click_rate"]})

    risk = org_summary(all_risk_profiles(ids)) if ids else org_summary([])

    return render_template("dashboard/index.html", stats=totals, chart=chart,
                          departments=departments, recent=recent, risk=risk,
                          has_imported=bool(ids))
