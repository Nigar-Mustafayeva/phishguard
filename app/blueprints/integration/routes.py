"""Integration status page: shows GoPhish and Mailtrap connection state.

Read-only. Never displays API keys or passwords.
"""
from flask import Blueprint, render_template
from flask_login import login_required

from app.services import gophish_service
from app.services.mail_service import is_mailtrap_configured

integration_bp = Blueprint("integration", __name__, url_prefix="/integration")


@integration_bp.route("/")
@login_required
def index():
    return render_template("integration/index.html",
                          gophish=gophish_service.check_status(),
                          gophish_configured=gophish_service.is_configured(),
                          mailtrap_ok=is_mailtrap_configured())
