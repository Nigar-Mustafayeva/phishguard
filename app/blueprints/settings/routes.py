"""Settings & audit (admin only).

- User management (create, activate/deactivate).
- Audit log viewer. Secrets are never written to audit logs.
"""
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, abort, current_app)
from flask_login import login_required, current_user

from app.extensions import db
from app.models import User, AuditLog
from app.blueprints.auth.decorators import admin_required
from app.services.gophish_service import check_status, is_configured
from app.services.mail_service import is_mailtrap_configured
from .forms import UserForm

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("/", methods=["GET", "POST"])
@login_required
@admin_required
def index():
    form = UserForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        if User.query.filter_by(email=email).first():
            flash("Bu email ilə istifadəçi artıq mövcuddur.", "danger")
        else:
            u = User(name=form.name.data.strip(), email=email, role=form.role.data)
            u.set_password(form.password.data)
            db.session.add(u)
            db.session.add(AuditLog(user_id=current_user.id, action="user_create",
                                    detail=email, ip_address=request.remote_addr))
            db.session.commit()
            flash("İstifadəçi yaradıldı.", "success")
            return redirect(url_for("settings.index"))

    users = User.query.order_by(User.id).all()
    config_info = {
        "demo_mode": current_app.config.get("DEMO_MODE", True),
        "gophish": check_status(),
        "gophish_configured": is_configured(),
        "mailtrap": is_mailtrap_configured(),
    }
    return render_template("settings/index.html", form=form, users=users,
                          config=config_info)


@settings_bp.route("/users/<int:uid>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_user(uid):
    u = db.session.get(User, uid) or abort(404)
    if u.id == current_user.id:
        flash("Öz hesabınızı deaktiv edə bilməzsiniz.", "danger")
        return redirect(url_for("settings.index"))
    u.active = not u.active
    db.session.add(AuditLog(user_id=current_user.id, action="user_toggle",
                            detail=f"{u.email} -> {'aktiv' if u.active else 'deaktiv'}",
                            ip_address=request.remote_addr))
    db.session.commit()
    flash("İstifadəçi statusu yeniləndi.", "success")
    return redirect(url_for("settings.index"))


@settings_bp.route("/audit")
@login_required
@admin_required
def audit():
    action = request.args.get("action", "").strip()
    q = AuditLog.query
    if action:
        q = q.filter(AuditLog.action == action)
    logs = q.order_by(AuditLog.created_at.desc()).limit(300).all()
    # distinct actions for the filter dropdown
    actions = [r[0] for r in db.session.query(AuditLog.action).distinct().all()]
    # map user ids to names
    user_names = {u.id: u.name for u in User.query.all()}
    return render_template("settings/audit.html", logs=logs, actions=sorted(actions),
                          current_action=action, user_names=user_names)
