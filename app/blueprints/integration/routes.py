"""Integration status + GoPhish campaign import.

Read-only status, plus (in live mode) the ability to pull a real GoPhish
campaign's recipients and events into the local database. Never displays the
API key or password.
"""
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request)
from flask_login import login_required, current_user

from app.extensions import db
from app.models import AuditLog, Campaign
from app.services import gophish_service
from app.services.gophish_service import GoPhishError
from app.services.mail_service import is_mailtrap_configured

integration_bp = Blueprint("integration", __name__, url_prefix="/integration")


@integration_bp.route("/")
@login_required
def index():
    status = gophish_service.check_status()
    gophish_campaigns = None
    fetch_error = None
    orphaned = []
    # In live + reachable mode, list available GoPhish campaigns to import.
    if status["mode"] == "live" and status["reachable"]:
        try:
            gophish_campaigns = gophish_service.fetch_campaigns()
        except GoPhishError as exc:
            fetch_error = str(exc)
        else:
            # Imported campaigns whose GoPhish campaign has since been deleted.
            live_ids = {c.get("id") for c in gophish_campaigns}
            orphaned = (Campaign.query
                        .filter(Campaign.gophish_campaign_id.isnot(None))
                        .filter(Campaign.gophish_campaign_id.notin_(live_ids))
                        .all()) if live_ids else (
                Campaign.query.filter(Campaign.gophish_campaign_id.isnot(None)).all())
    return render_template("integration/index.html",
                          gophish=status,
                          gophish_configured=gophish_service.is_configured(),
                          mailtrap_ok=is_mailtrap_configured(),
                          gophish_campaigns=gophish_campaigns,
                          fetch_error=fetch_error,
                          orphaned=orphaned)


@integration_bp.route("/import/<int:gophish_id>", methods=["POST"])
@login_required
def import_campaign(gophish_id):
    try:
        message = gophish_service.import_campaign(gophish_id)
        db.session.add(AuditLog(user_id=current_user.id,
                                action="gophish_import",
                                detail=f"GoPhish campaign {gophish_id}",
                                ip_address=request.remote_addr))
        db.session.commit()
        flash(message, "success")
    except GoPhishError as exc:
        flash(f"Import failed: {exc}", "danger")
    return redirect(url_for("integration.index"))
