"""Reports: downloadable PDF and CSV per campaign, built from stored data."""
import csv
import io
from datetime import datetime

from flask import (Blueprint, render_template, abort, Response, send_file,
                   request)
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Campaign, CampaignEvent, ReportRecord, AuditLog
from app.services.metrics import campaign_metrics
from app.services.report_service import build_pdf

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


def _safe_name(name):
    return "".join(c if c.isalnum() else "_" for c in name)[:40]


@reports_bp.route("/")
@login_required
def index():
    campaigns = Campaign.query.order_by(Campaign.id.desc()).all()
    rows = [(c, campaign_metrics(c)) for c in campaigns]
    return render_template("reports/index.html", rows=rows)


@reports_bp.route("/<int:cid>/csv")
@login_required
def csv_report(cid):
    camp = db.session.get(Campaign, cid) or abort(404)
    m = campaign_metrics(camp)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["PhishGuard Hesabatı"])
    w.writerow(["Yaradılma", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")])
    w.writerow(["Kampaniya", camp.name])
    w.writerow(["Status", camp.status])
    w.writerow(["Demo data", "Bəli" if camp.is_demo else "Xeyr"])
    w.writerow([])
    w.writerow(["Metrika", "Say", "Faiz"])
    w.writerow(["Hədəf iştirakçı", m["targeted"], ""])
    w.writerow(["Göndərildi", m["sent"], "100%"])
    w.writerow(["Açıldı", m["opened"], f"{m['open_rate']}%"])
    w.writerow(["Kliklədi", m["clicked"], f"{m['click_rate']}%"])
    w.writerow(["Form doldurdu", m["submitted"], f"{m['submit_rate']}%"])
    w.writerow(["Report etdi", m["reported"], f"{m['report_rate']}%"])
    w.writerow([])
    w.writerow(["Hadisələr"])
    w.writerow(["Vaxt", "İştirakçı", "Hadisə", "Mənbə"])
    events = (CampaignEvent.query.filter_by(campaign_id=cid)
              .order_by(CampaignEvent.occurred_at).all())
    for e in events:
        w.writerow([e.occurred_at.strftime("%Y-%m-%d %H:%M"),
                    e.participant.full_name if e.participant else "—",
                    e.event_type, e.source])

    _record(camp, "csv")
    filename = f"phishguard_{_safe_name(camp.name)}.csv"
    return Response("﻿" + out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})


@reports_bp.route("/<int:cid>/pdf")
@login_required
def pdf_report(cid):
    camp = db.session.get(Campaign, cid) or abort(404)
    m = campaign_metrics(camp)
    pdf_bytes = build_pdf(camp, m)
    _record(camp, "pdf")
    filename = f"phishguard_{_safe_name(camp.name)}.pdf"
    return send_file(io.BytesIO(pdf_bytes), mimetype="application/pdf",
                     as_attachment=True, download_name=filename)


def _record(camp, fmt):
    db.session.add(ReportRecord(campaign_id=camp.id, format=fmt,
                                file_name=f"phishguard_{_safe_name(camp.name)}.{fmt}",
                                generated_by_id=current_user.id))
    db.session.add(AuditLog(user_id=current_user.id, action="report_generate",
                            detail=f"{camp.name} ({fmt})",
                            ip_address=request.remote_addr))
    db.session.commit()
