"""Dashboard: all figures computed from real database records.

Demo (seeded) records are included and remain labelled as demo elsewhere in
the app; the dashboard reflects whatever is stored.
"""
from flask import Blueprint, render_template
from flask_login import login_required

from app.models import (Campaign, Participant, STATUS_DRAFT)
from app.services.metrics import (overall_metrics, campaign_metrics,
                                  department_breakdown)
from app.services.risk_service import all_risk_profiles, org_summary

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    totals = overall_metrics()
    totals["participants"] = Participant.query.count()

    # Per-campaign click% vs report% for launched campaigns (chart data)
    launched = (Campaign.query
                .filter(Campaign.status != STATUS_DRAFT)
                .order_by(Campaign.id.desc()).limit(8).all())
    launched = list(reversed(launched))
    chart = {"labels": [], "clicks": [], "reports": []}
    for c in launched:
        m = campaign_metrics(c)
        chart["labels"].append(c.name)
        chart["clicks"].append(m["click_rate"])
        chart["reports"].append(m["report_rate"])

    departments = [d for d in department_breakdown() if d["participants"] > 0]

    recent = []
    for c in Campaign.query.order_by(Campaign.id.desc()).limit(5).all():
        m = campaign_metrics(c)
        recent.append({"id": c.id, "name": c.name, "status": c.status,
                       "sent": m["sent"], "clicks": m["clicked"],
                       "click_rate": m["click_rate"]})

    risk = org_summary(all_risk_profiles())

    return render_template("dashboard/index.html", stats=totals, chart=chart,
                          departments=departments, recent=recent, risk=risk)
